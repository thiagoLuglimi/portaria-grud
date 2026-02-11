from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
import sqlite3
from functools import wraps
from datetime import datetime, date
import pandas as pd
import os

app = Flask(__name__)
app.secret_key = 'portaria_secreta_123'

DB = 'database.db'

# ---------- BANCO ----------
def conectar():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def criar_tabelas():
    con = conectar()
    cur = con.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT,
            usuario TEXT UNIQUE,
            senha TEXT,
            perfil TEXT,
            unidade TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS portaria (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            unidade TEXT,
            evento TEXT,
            data_hora TEXT,
            motorista TEXT,
            cavalo TEXT,
            km TEXT,
            tipo_conjunto TEXT,
            placa1 TEXT,
            placa2 TEXT,
            lacre1 TEXT,
            lacre2 TEXT,
            destino TEXT,
            operacao TEXT,
            status TEXT,
            responsavel TEXT,
            usuario_id INTEGER
        )
    """)

    admin = cur.execute(
        "SELECT * FROM usuarios WHERE usuario='admin'"
    ).fetchone()

    if not admin:
        cur.execute("""
            INSERT INTO usuarios (nome, usuario, senha, perfil, unidade)
            VALUES ('Administrador', 'admin', 'admin123', 'ADMIN', 'TODAS')
        """)

    con.commit()
    con.close()


criar_tabelas()

# ---------- SEGURANÇA ----------
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'usuario_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('perfil') != 'ADMIN':
            return "Acesso negado", 403
        return f(*args, **kwargs)
    return decorated


# ---------- LOGIN ----------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form['usuario']
        senha = request.form['senha']

        con = conectar()
        user = con.execute(
            "SELECT * FROM usuarios WHERE usuario=? AND senha=?",
            (usuario, senha)
        ).fetchone()
        con.close()

        if user:
            session['usuario_id'] = user['id']
            session['nome'] = user['nome']
            session['perfil'] = user['perfil']
            session['unidade'] = user['unidade']
            return redirect(url_for('index'))

        flash('Usuário ou senha inválidos')

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


# ---------- PORTARIA ----------
@app.route('/')
@login_required
def index():
    con = conectar()

    if session['perfil'] == 'ADMIN':
        dados = con.execute("""
            SELECT portaria.*, usuarios.nome AS nome_porteiro
            FROM portaria
            LEFT JOIN usuarios ON usuarios.id = portaria.usuario_id
            ORDER BY data_hora DESC
        """).fetchall()
    else:
        dados = con.execute("""
            SELECT *
            FROM portaria
            WHERE unidade = ?
            ORDER BY data_hora DESC
        """, (session['unidade'],)).fetchall()

    con.close()
    return render_template('index.html', dados=dados)


@app.route('/novo', methods=['GET', 'POST'])
@login_required
def novo():
    if request.method == 'POST':
        dados = request.form
        data_hora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        con = conectar()
        con.execute("""
            INSERT INTO portaria VALUES (
                NULL,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?
            )
        """, (
            session['unidade'],
            dados['evento'],
            data_hora,
            dados['motorista'],
            dados['cavalo'],
            dados['km'],
            dados['tipo_conjunto'],
            dados.get('placa1'),
            dados.get('placa2'),
            dados.get('lacre1'),
            dados.get('lacre2'),
            dados['destino'],
            dados['operacao'],
            dados['status'],
            session['nome'],
            session['usuario_id']
        ))

        con.commit()
        con.close()
        return redirect('/')

    return render_template('form.html', registro=None)


# ---------- USUÁRIOS ----------
@app.route('/usuarios', methods=['GET', 'POST'])
@login_required
@admin_required
def usuarios():
    con = conectar()

    if request.method == 'POST':
        con.execute("""
            INSERT INTO usuarios (nome, usuario, senha, perfil, unidade)
            VALUES (?, ?, ?, ?, ?)
        """, (
            request.form['nome'],
            request.form['usuario'],
            request.form['senha'],
            request.form['perfil'],
            request.form['unidade']
        ))
        con.commit()

    usuarios = con.execute(
        "SELECT id, nome, usuario, perfil, unidade FROM usuarios"
    ).fetchall()
    con.close()

    return render_template('usuarios.html', usuarios=usuarios)


# ---------- EXPORTAR ----------
@app.route('/exportar')
@login_required
def exportar():
    hoje = date.today().strftime('%Y-%m-%d')
    con = conectar()

    if session['perfil'] == 'ADMIN':
        df = pd.read_sql_query(
            "SELECT * FROM portaria WHERE date(data_hora)=?",
            con, params=(hoje,)
        )
    else:
        df = pd.read_sql_query(
            "SELECT * FROM portaria WHERE date(data_hora)=? AND unidade=?",
            con, params=(hoje, session['unidade'])
        )

    con.close()

    arquivo = f"relatorio_portaria_{hoje}.xlsx"
    df.to_excel(arquivo, index=False)
    return send_file(arquivo, as_attachment=True)


# ---------- START ----------
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

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
            perfil TEXT
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

    # cria admin padrão
    admin = cur.execute(
        "SELECT * FROM usuarios WHERE usuario='admin'"
    ).fetchone()

    if not admin:
        cur.execute("""
            INSERT INTO usuarios (nome, usuario, senha, perfil)
            VALUES ('Administrador', 'admin', 'admin123', 'ADMIN')
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
            SELECT 
                portaria.*,
                usuarios.nome AS nome_porteiro
            FROM portaria
            LEFT JOIN usuarios ON usuarios.id = portaria.usuario_id
            ORDER BY data_hora DESC
        """).fetchall()
    else:
        dados = con.execute("""
            SELECT *
            FROM portaria
            WHERE usuario_id = ?
            ORDER BY data_hora DESC
        """, (session['usuario_id'],)).fetchall()

    con.close()
    return render_template('index.html', dados=dados)



@app.route('/novo', methods=['GET', 'POST'])
@login_required
def novo():
    if request.method == 'POST':
        dados = request.form

        if dados.get('evento') == 'SAIDA' and not dados.get('placa1'):
            return "Erro: Saída sem placa não é permitida"

        data_hora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        con = conectar()
        con.execute("""
            INSERT INTO portaria VALUES (
                NULL,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?
            )
        """, (
            dados['unidade'],
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
            session['nome'],            # RESPONSÁVEL AUTOMÁTICO
            session['usuario_id']
        ))

        con.commit()
        con.close()
        return redirect('/')

    return render_template('form.html', registro=None)


@app.route('/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar(id):
    con = conectar()
    registro = con.execute(
        "SELECT * FROM portaria WHERE id=?", (id,)
    ).fetchone()

    if session['perfil'] != 'ADMIN' and registro['usuario_id'] != session['usuario_id']:
        return "Acesso negado"

    if request.method == 'POST':
        dados = request.form

        con.execute("""
            UPDATE portaria SET
                unidade=?, evento=?, motorista=?, cavalo=?, km=?, tipo_conjunto=?,
                placa1=?, placa2=?, lacre1=?, lacre2=?, destino=?,
                operacao=?, status=?
            WHERE id=?
        """, (
            dados['unidade'],
            dados['evento'],
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
            id
        ))

        con.commit()
        con.close()
        return redirect('/')

    con.close()
    return render_template('form.html', registro=registro)


@app.route('/excluir/<int:id>')
@login_required
def excluir(id):
    con = conectar()
    registro = con.execute(
        "SELECT * FROM portaria WHERE id=?", (id,)
    ).fetchone()

    if session['perfil'] != 'ADMIN' and registro['usuario_id'] != session['usuario_id']:
        return "Acesso negado"

    con.execute("DELETE FROM portaria WHERE id=?", (id,))
    con.commit()
    con.close()
    return redirect('/')


@app.route('/exportar')
@login_required
def exportar():
    con = conectar()

    if session['perfil'] == 'ADMIN':
        df = pd.read_sql_query(
            """
            SELECT 
                portaria.*,
                usuarios.nome AS nome_porteiro
            FROM portaria
            LEFT JOIN usuarios ON usuarios.id = portaria.usuario_id
            ORDER BY data_hora DESC
            """,
            con
        )
    else:
        df = pd.read_sql_query(
            """
            SELECT *
            FROM portaria
            WHERE usuario_id=?
            ORDER BY data_hora DESC
            """,
            con, params=(session['usuario_id'],)
        )

    con.close()

    arquivo = "relatorio_portaria_geral.xlsx"
    df.to_excel(arquivo, index=False)

    return send_file(arquivo, as_attachment=True)


# ---------- USUÁRIOS ----------
@app.route('/usuarios', methods=['GET', 'POST'])
@login_required
@admin_required
def usuarios():
    con = conectar()

    if request.method == 'POST':
        con.execute("""
            INSERT INTO usuarios (nome, usuario, senha, perfil)
            VALUES (?, ?, ?, ?)
        """, (
            request.form['nome'],
            request.form['usuario'],
            request.form['senha'],
            request.form['perfil']
        ))
        con.commit()

    usuarios = con.execute(
        "SELECT id, nome, usuario, perfil FROM usuarios"
    ).fetchall()
    con.close()

    return render_template('usuarios.html', usuarios=usuarios)


# ---------- START ----------
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)


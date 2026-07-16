from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
import sqlite3
from functools import wraps
from datetime import datetime
from zoneinfo import ZoneInfo
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

    cur.execute("""
    CREATE TABLE IF NOT EXISTS veiculos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        placa TEXT UNIQUE NOT NULL,
        ativo INTEGER DEFAULT 1
    )
""")

    admin = cur.execute("SELECT * FROM usuarios WHERE usuario='admin'").fetchone()

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

    dados = con.execute("""
        SELECT portaria.*, usuarios.nome AS nome_porteiro
        FROM portaria
        LEFT JOIN usuarios ON usuarios.id = portaria.usuario_id
        ORDER BY data_hora DESC
    """).fetchall()

    con.close()
    return render_template('index.html', dados=dados)

# ---------- NOVO ----------
@app.route('/novo', methods=['GET', 'POST'])
@login_required
def novo():
    if request.method == 'POST':
        dados = request.form

        # DATA CORRIGIDA
        data_hora = dados.get('data_hora')

        if data_hora:
            data_hora = datetime.fromisoformat(data_hora).strftime('%Y-%m-%d %H:%M:%S')
        else:
            data_hora = datetime.now(ZoneInfo("America/Sao_Paulo")).strftime('%Y-%m-%d %H:%M:%S')

        con = conectar()
        con.execute("""
            INSERT INTO portaria (
                unidade, evento, data_hora, motorista, cavalo, km,
                tipo_conjunto, placa1, placa2, lacre1, lacre2,
                destino, operacao, status, responsavel, usuario_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            dados.get('unidade'),
            dados.get('evento'),
            data_hora,
            dados.get('motorista'),
            dados.get('cavalo'),
            dados.get('km'),
            dados.get('tipo_conjunto'),
            dados.get('placa1'),
            dados.get('placa2'),
            dados.get('lacre1'),
            dados.get('lacre2'),
            dados.get('destino'),
            dados.get('operacao'),
            dados.get('status'),
            session['nome'],
            session['usuario_id']
        ))

        con.commit()
        con.close()
        return redirect('/')

    #return render_template('form.html', registro=None)

    con = conectar()

    placas = con.execute("""
        SELECT placa
        FROM veiculos
        WHERE ativo = 1
        ORDER BY placa
    """).fetchall()

    con.close()

    return render_template(
        "form.html",
        registro=None,
        placas=placas
    )

# ---------- EDITAR ----------
@app.route('/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar(id):
    con = conectar()
    registro = con.execute("SELECT * FROM portaria WHERE id=?", (id,)).fetchone()

    if request.method == 'POST':
        dados = request.form

        data_hora = dados.get('data_hora')

        if data_hora:
            data_hora = datetime.fromisoformat(data_hora).strftime('%Y-%m-%d %H:%M:%S')
        else:
            data_hora = registro['data_hora']

        con.execute("""
            UPDATE portaria SET
                unidade=?, evento=?, data_hora=?, motorista=?, cavalo=?, km=?, tipo_conjunto=?,
                placa1=?, placa2=?, lacre1=?, lacre2=?, destino=?,
                operacao=?, status=?
            WHERE id=?
        """, (
            dados.get('unidade'),
            dados.get('evento'),
            data_hora,
            dados.get('motorista'),
            dados.get('cavalo'),
            dados.get('km'),
            dados.get('tipo_conjunto'),
            dados.get('placa1'),
            dados.get('placa2'),
            dados.get('lacre1'),
            dados.get('lacre2'),
            dados.get('destino'),
            dados.get('operacao'),
            dados.get('status'),
            id
        ))

        con.commit()
        con.close()
        return redirect('/')

    #con.close()
    #return render_template('form.html', registro=registro)

    placas = con.execute("""
        SELECT placa
        FROM veiculos
        WHERE ativo = 1
        ORDER BY placa
    """).fetchall()

    con.close()

    return render_template(
        "form.html",
        registro=registro,
        placas=placas
    )


@app.route("/cadastrar_placa", methods=["POST"])
@login_required
def cadastrar_placa():

    placa = request.form.get("placa", "").upper().strip()

    if placa == "":
        return {
            "sucesso": False,
            "mensagem": "Informe uma placa."
        }

    con = conectar()

    existe = con.execute(
        "SELECT id FROM veiculos WHERE placa=?",
        (placa,)
    ).fetchone()

    if existe:
        con.close()
        return {
            "sucesso": False,
            "mensagem": "Placa já cadastrada."
        }

    con.execute(
        "INSERT INTO veiculos (placa) VALUES (?)",
        (placa,)
    )

    con.commit()
    con.close()

    return {
        "sucesso": True,
        "placa": placa
    }


# ---------- DASHBOARD ----------
@app.route('/dashboard')
@login_required
def dashboard():
    con = conectar()
    df = pd.read_sql_query("SELECT * FROM portaria", con)
    # Formata Data/Hora para padrão brasileiro
    df['data_hora'] = pd.to_datetime(df['data_hora'])
    df['data_hora'] = df['data_hora'].dt.strftime('%d/%m/%Y %H:%M:%S')
    con.close()

    if df.empty:
        return render_template("dashboard.html", tabela=[], kpis={})

    df['evento'] = df['evento'].astype(str).str.upper().str.strip()

    df['data_hora'] = pd.to_datetime(
        df['data_hora'].astype(str).str.replace("T", " "),
        errors='coerce'
    )

    df = df.dropna(subset=['data_hora'])

    agora = datetime.now()

    placas = df['placa1'].dropna().unique()

    tabela = []
    tempo_lista = []
    patio = 0

    for placa in placas:
        df_placa = df[df['placa1'] == placa].sort_values('data_hora')

        entrada = df_placa[df_placa['evento'] == 'ENTRADA'].tail(1)
        saida = df_placa[df_placa['evento'] == 'SAIDA'].tail(1)

        if not entrada.empty:
            entrada_time = entrada.iloc[0]['data_hora']

            if not saida.empty and saida.iloc[0]['data_hora'] > entrada_time:
                tempo = saida.iloc[0]['data_hora'] - entrada_time
                status = "FINALIZADO"
            else:
                tempo = agora - entrada_time
                status = "NO PÁTIO"
                patio += 1

            horas = round(tempo.total_seconds() / 3600, 2)
            tempo_lista.append(horas)

            tabela.append({
                "operacao": entrada.iloc[0]['operacao'],
                "tipo": entrada.iloc[0]['tipo_conjunto'],
                "placa": placa,
                "status": status,
                "tempo": horas
            })

    hoje = datetime.now().date()

    entradas_hoje = len(df[(df['evento'] == 'ENTRADA') & (df['data_hora'].dt.date == hoje)])
    saidas_hoje = len(df[(df['evento'] == 'SAIDA') & (df['data_hora'].dt.date == hoje)])

    kpis = {
        "patio": patio,
        "entradas": entradas_hoje,
        "saidas": saidas_hoje,
        "tempo_medio": round(sum(tempo_lista)/len(tempo_lista), 2) if tempo_lista else 0
    }

    return render_template("dashboard.html", tabela=tabela, kpis=kpis)


# ---------- EXPORTAR EXCEL ----------
@app.route('/exportar')
@login_required
def exportar():

    inicio = request.args.get("inicio")
    fim = request.args.get("fim")

    con = conectar()

    consulta = """
        SELECT
            id,
            unidade,
            evento,
            data_hora,
            motorista,
            cavalo,
            km,
            tipo_conjunto,
            placa1,
            placa2,
            lacre1,
            lacre2,
            destino,
            operacao,
            status,
            responsavel
        FROM portaria
        WHERE DATE(data_hora) BETWEEN ? AND ?
        ORDER BY data_hora
    """

    df = pd.read_sql_query(
        consulta,
        con,
        params=(inicio, fim)
    )

    con.close()

    nome = f"Relatorio_Portaria_{inicio}_a_{fim}.xlsx"

    df.to_excel(nome, index=False)

    return send_file(
        nome,
        as_attachment=True
    )

# ---------- START ----------
if __name__ == '__main__':
    app.run(debug=True)
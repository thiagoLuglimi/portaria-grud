from flask import Flask, render_template, request, redirect, send_file
import sqlite3
from datetime import datetime, date
import pandas as pd

app = Flask(__name__)
DB = 'database.db'


# ---------- BANCO ----------
def conectar():
    return sqlite3.connect(DB)


def criar_tabela():
    con = conectar()
    cur = con.cursor()
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
            responsavel TEXT
        )
    """)
    con.commit()
    con.close()


criar_tabela()


# ---------- ROTAS ----------
@app.route('/')
def index():
    con = conectar()
    dados = con.execute("SELECT * FROM portaria ORDER BY data_hora DESC").fetchall()
    con.close()
    return render_template('index.html', dados=dados)


@app.route('/novo', methods=['GET', 'POST'])
def novo():
    if request.method == 'POST':
        dados = request.form

        # TRAVA INTELIGENTE
        if dados.get('evento') == 'SAIDA' and not dados.get('placa1'):
            return "Erro: Saída sem placa não é permitida"

        data_hora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        con = conectar()
        con.execute("""
    INSERT INTO portaria VALUES (NULL,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
""", (
    dados.get('unidade', ''),
    dados.get('evento', ''),
    data_hora,
    dados.get('motorista', ''),
    dados.get('cavalo', ''),
    dados.get('km', ''),
    dados.get('tipo_conjunto', ''),
    dados.get('placa1', ''),
    dados.get('placa2', ''),
    dados.get('lacre1', ''),
    dados.get('lacre2', ''),
    dados.get('destino', ''),
    dados.get('operacao', ''),
    dados.get('responsavel', '')
))


        con.commit()
        con.close()
        return redirect('/')

    return render_template('form.html', registro=None)



@app.route('/editar/<int:id>', methods=['GET', 'POST'])
def editar(id):
    con = conectar()

    if request.method == 'POST':
        dados = request.form

        # TRAVA INTELIGENTE
        if dados['evento'] == 'SAIDA' and not dados.get('placa1'):
            return "Erro: Saída sem placa não é permitida"

        con.execute("""
            UPDATE portaria SET
                unidade=?, evento=?, motorista=?, cavalo=?, km=?, tipo_conjunto=?,
                placa1=?, placa2=?, lacre1=?, lacre2=?, destino=?, operacao=?, responsavel=?
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
            dados.get('operacao'),
            dados['responsavel'],
            id
        ))
        con.commit()
        con.close()
        return redirect('/')

    registro = con.execute("SELECT * FROM portaria WHERE id=?", (id,)).fetchone()
    con.close()
    return render_template('form.html', registro=registro)


@app.route('/excluir/<int:id>')
def excluir(id):
    con = conectar()
    con.execute("DELETE FROM portaria WHERE id=?", (id,))
    con.commit()
    con.close()
    return redirect('/')


@app.route('/exportar')
def exportar():
    hoje = date.today().strftime('%Y-%m-%d')
    con = conectar()
    df = pd.read_sql_query("""
        SELECT * FROM portaria
        WHERE date(data_hora) = ?
    """, con, params=(hoje,))
    con.close()

    arquivo = f"relatorio_portaria_{hoje}.xlsx"
    df.to_excel(arquivo, index=False)

    return send_file(arquivo, as_attachment=True)


if __name__ == '__main__':
    #app.run(debug=True)
    app.run()

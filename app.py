from flask import Flask, request, jsonify, render_template
import psycopg2
import pandas as pd
from datetime import datetime
import pytz

app = Flask(__name__)

DATABASE_URL = "postgresql://neondb_owner:npg_lJHgpoh53QXM@ep-old-night-acgy3449-pooler.sa-east-1.aws.neon.tech/neondb?sslmode=require"

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/obra')
def obra():
    return render_template('obra.html')

@app.route('/registros')
def registros():
    return render_template('registros.html')

@app.route('/registros_obra')
def registros_obra():
    return render_template('registros_obra.html')

@app.route('/relatorio_obra')
def relatorio_obra():
    return render_template('relatorio_obra.html')

@app.route('/importar')
def importar_lista():
    return render_template('upload.html')

@app.route('/lista_carga')
def lista_carga():
    return render_template('lista_carga.html')

@app.route('/relatorio')
def relatorio():
    return render_template('relatorio.html')

@app.route('/registrar_qr', methods=['POST'])
def registrar_qr():
    data = request.json
    codigo_qr = data.get('codigo_qr')
    usuario = data.get('usuario')

    if not codigo_qr or not usuario:
        return jsonify({"erro": "Código QR e usuário são obrigatórios"}), 400

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO registros_qr (codigo_qr, usuario) VALUES (%s, %s)", (codigo_qr, usuario))
        conn.commit()
        return jsonify({"mensagem": "QR Code registrado com sucesso!"}), 201
    except Exception as e:
        return jsonify({"erro": str(e)}), 500
    finally:
        cur.close()
        conn.close()

@app.route('/listar_qr', methods=['GET'])
def listar_qr():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, codigo_qr, data_hora, usuario, status FROM registros_qr ORDER BY data_hora DESC")
    registros = cur.fetchall()

    tz = pytz.timezone('America/Sao_Paulo')
    registros_formatados = [
        {"id": r[0], "codigo_qr": r[1], "data_hora": r[2].astimezone(tz).strftime('%d/%m/%Y %H:%M:%S') if r[2] else "", "usuario": r[3], "status": r[4]}
        for r in registros
    ]
    cur.close()
    conn.close()
    return jsonify(registros_formatados)

@app.route('/listar_qr_obra', methods=['GET'])
def listar_qr_obra():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, codigo_qr, data_hora, usuario, status FROM recebimento_obra ORDER BY data_hora DESC")
    registros = cur.fetchall()

    tz = pytz.timezone('America/Sao_Paulo')
    registros_formatados = [
        {"id": r[0], "codigo_qr": r[1], "data_hora": r[2].astimezone(tz).strftime('%d/%m/%Y %H:%M:%S') if r[2] else "", "usuario": r[3], "status": r[4]}
        for r in registros
    ]
    cur.close()
    conn.close()
    return jsonify(registros_formatados)

@app.route('/excluir_qr/<int:id>', methods=['DELETE'])
def excluir_qr(id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM registros_qr WHERE id = %s", (id,))
    conn.commit()
    excluidos = cur.rowcount
    cur.close()
    conn.close()
    return jsonify({"sucesso": excluidos > 0, "erro": None if excluidos > 0 else "Registro não encontrado."}), 200 if excluidos else 404

@app.route('/excluir_qr_obra/<int:id>', methods=['DELETE'])
def excluir_qr_obra(id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM recebimento_obra WHERE id = %s", (id,))
    conn.commit()
    excluidos = cur.rowcount
    cur.close()
    conn.close()
    return jsonify({"sucesso": excluidos > 0, "erro": None if excluidos > 0 else "Registro não encontrado."}), 200 if excluidos else 404

# Mantenha aqui as demais rotas originais do seu arquivo inicial sem alterações.

if __name__ == '__main__':
    app.run(debug=True)

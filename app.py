from flask import Flask, request, jsonify, send_file
import psycopg2
import pandas as pd
from datetime import datetime
import pytz

app = Flask(__name__)

DATABASE_URL = "postgresql://neondb_owner:npg_lJHgpoh53QXM@ep-old-night-acgy3449-pooler.sa-east-1.aws.neon.tech/neondb?sslmode=require"

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

# Função utilitária para data/hora no fuso de Brasília
def data_hora_brasilia():
    fuso = pytz.timezone('America/Sao_Paulo')
    return datetime.now(fuso)

@app.route('/')
def index():
    return send_file('index.html')

@app.route('/registros')
def registros():
    return send_file('registros.html')

@app.route('/importar')
def importar_lista():
    return send_file('upload.html')

@app.route('/lista_carga')
def lista_carga():
    return send_file('lista_carga.html')

@app.route('/relatorio')
def relatorio():
    return send_file('relatorio.html')

# Rota para registrar QR Code no modo FÁBRICA
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
        cur.execute("""
            INSERT INTO registros_qr (codigo_qr, usuario, data_hora)
            VALUES (%s, %s, %s)
        """, (codigo_qr, usuario, data_hora_brasilia()))
        conn.commit()
        return jsonify({"mensagem": "QR Code registrado com sucesso!"}), 201
    except Exception as e:
        return jsonify({"erro": str(e)}), 500
    finally:
        cur.close()
        conn.close()

# NOVA ROTA: Registrar QR Code no modo OBRA
@app.route('/registrar_qr_obra', methods=['POST'])
def registrar_qr_obra():
    data = request.json
    codigo_qr = data.get('codigo_qr')
    usuario = data.get('usuario')

    if not codigo_qr or not usuario:
        return jsonify({"erro": "Código QR e usuário são obrigatórios"}), 400

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO recebimento_obra (codigo_qr, usuario, data_hora)
            VALUES (%s, %s, %s)
        """, (codigo_qr, usuario, data_hora_brasilia()))
        conn.commit()
        return jsonify({"mensagem": "QR Code registrado no modo OBRA!"}), 201
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
    cur.close()
    conn.close()

    registros_formatados = [
        {"id": r[0], "codigo_qr": r[1], "data_hora": r[2], "usuario": r[3], "status": r[4]} for r in registros
    ]
    return jsonify(registros_formatados)

@app.route('/excluir_qr/<int:registro_id>', methods=['DELETE'])
def excluir_qr(registro_id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM registros_qr WHERE id = %s", (registro_id,))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"sucesso": True})
    except Exception as e:
        return jsonify({"sucesso": False, "erro": str(e)})

# As demais rotas (upload, lista_carga, relatorio_diferencas) permanecem as mesmas

if __name__ == '__main__':
    app.run(debug=True)

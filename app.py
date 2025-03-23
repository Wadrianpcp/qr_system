from flask import Flask, request, jsonify, send_file
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from datetime import datetime, timedelta
import pytz

app = Flask(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://neondb_owner:npg_lJHgpoh53QXM@ep-old-night-acgy3449-pooler.sa-east-1.aws.neon.tech/neondb?sslmode=require")

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

# Páginas HTML
@app.route('/')
def index():
    return send_file('index.html')

@app.route('/obra')
def obra():
    return send_file('obra.html')

@app.route('/registros')
def registros():
    return send_file('registros.html')

@app.route('/registros_obra')
def registros_obra():
    return send_file('registros_obra.html')

@app.route('/importar')
def importar_lista():
    return send_file('upload.html')

@app.route('/relatorio')
def relatorio():
    return send_file('relatorio.html')

@app.route('/lista_carga')
def lista_carga():
    return send_file('lista_carga.html')

# Rotas de banco de dados
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
        cur.execute("INSERT INTO recebimento_obra (codigo_qr, usuario) VALUES (%s, %s)", (codigo_qr, usuario))
        conn.commit()
        return jsonify({"mensagem": "QR Code registrado com sucesso (obra)!"}), 201
    except Exception as e:
        return jsonify({"erro": str(e)}), 500
    finally:
        cur.close()
        conn.close()

@app.route('/listar_qr', methods=['GET'])
def listar_qr():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT id, codigo_qr, data_hora AT TIME ZONE 'UTC' AT TIME ZONE 'America/Sao_Paulo' AS data_hora, usuario, status FROM registros_qr ORDER BY data_hora DESC")
    registros = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify(registros)

@app.route('/listar_qr_obra', methods=['GET'])
def listar_qr_obra():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT id, codigo_qr, data_hora AT TIME ZONE 'UTC' AT TIME ZONE 'America/Sao_Paulo' AS data_hora, usuario, status FROM recebimento_obra ORDER BY data_hora DESC")
    registros = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify(registros)

@app.route('/excluir_qr/<int:id>', methods=['DELETE'])
def excluir_qr(id):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM registros_qr WHERE id = %s", (id,))
        conn.commit()
        return jsonify({"sucesso": True})
    except Exception as e:
        return jsonify({"erro": str(e)}), 500
    finally:
        cur.close()
        conn.close()

@app.route('/excluir_qr_obra/<int:id>', methods=['DELETE'])
def excluir_qr_obra(id):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM recebimento_obra WHERE id = %s", (id,))
        conn.commit()
        return jsonify({"sucesso": True})
    except Exception as e:
        return jsonify({"erro": str(e)}), 500
    finally:
        cur.close()
        conn.close()

if __name__ == '__main__':
    app.run(debug=True)

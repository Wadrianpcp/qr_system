from flask import Flask, request, jsonify, send_file
import psycopg2

app = Flask(__name__)

# ✅ SUA URL REAL DO BANCO NEON:
DATABASE_URL = "postgresql://neondb_owner:npg_lJHgpoh53QXM@ep-old-night-acgy3449-pooler.sa-east-1.aws.neon.tech/neondb?sslmode=require"

# Conectar ao banco de dados
def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

# Página inicial (interface web)
@app.route('/')
def index():
    return send_file('index.html')

# Página de registros
@app.route('/registros')
def registros():
    return send_file('registros.html')

# Rota para registrar um QR Code no banco
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

# Rota para listar os registros do banco
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

if __name__ == '__main__':
    app.run(debug=True)

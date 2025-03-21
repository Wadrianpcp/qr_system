from flask import Flask, request, jsonify, send_file
import psycopg2
import pandas as pd

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

# Página para importar lista de carga
@app.route('/importar')
def importar_lista():
    return send_file('upload.html')

# Página para visualizar a lista de carga
@app.route('/lista_carga')
def lista_carga():
    return send_file('lista_carga.html')

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

# Rota para importar planilha Excel da lista de carga
@app.route('/upload_lista_carga', methods=['POST'])
def upload_lista_carga():
    if 'arquivo' not in request.files:
        return jsonify({'erro': 'Nenhum arquivo enviado'}), 400

    arquivo = request.files['arquivo']

    if arquivo.filename == '':
        return jsonify({'erro': 'Nome de arquivo vazio'}), 400

    try:
        df = pd.read_excel(arquivo)

        colunas_esperadas = ["COD INSUMO", "PRODUTO", "UHS", "OBRA", "CARGAS", "TOTAL", "PAV"]
        if not all(col in df.columns for col in colunas_esperadas):
            return jsonify({'erro': 'As colunas do Excel não correspondem às esperadas.'}), 400

        conn = get_db_connection()
        cur = conn.cursor()

        for _, row in df.iterrows():
            cur.execute("""
                INSERT INTO lista_de_carga (cod_insumo, produto, uhs, obra, cargas, total, pav)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                row["COD INSUMO"], row["PRODUTO"], row["UHS"], row["OBRA"],
                row["CARGAS"], row["TOTAL"], row["PAV"]
            ))

        conn.commit()
        cur.close()
        conn.close()

        return jsonify({'mensagem': 'Lista de carga importada com sucesso.'}), 200

    except Exception as e:
        return jsonify({'erro': str(e)}), 500

# Rota para listar os dados da tabela "lista_de_carga"
@app.route('/listar_carga', methods=['GET'])
def listar_carga():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM lista_de_carga ORDER BY OBRA")
    dados = cur.fetchall()
    colunas = [desc[0] for desc in cur.description]
    cur.close()
    conn.close()

    registros_formatados = [dict(zip(colunas, linha)) for linha in dados]

    return jsonify(registros_formatados)

if __name__ == '__main__':
    app.run(debug=True)

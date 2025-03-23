from flask import Flask, request, jsonify, send_file
import psycopg2
from datetime import timedelta
import pandas as pd

app = Flask(__name__)

DATABASE_URL = "postgresql://neondb_owner:npg_lJHgpoh53QXM@ep-old-night-acgy3449-pooler.sa-east-1.aws.neon.tech/neondb?sslmode=require"

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

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

@app.route('/relatorio')
def relatorio():
    return send_file('relatorio.html')

@app.route('/relatorio_obra')
def relatorio_obra():
    return send_file('relatorio_obra.html')

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
        return jsonify({"mensagem": "QR Code registrado com sucesso no modo Obra!"}), 201
    except Exception as e:
        return jsonify({"erro": str(e)}), 500
    finally:
        cur.close()
        conn.close()

@app.route('/listar_qr')
def listar_qr():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, codigo_qr, data_hora, usuario, status FROM registros_qr ORDER BY data_hora DESC")
    registros = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify([
        {
            "id": r[0],
            "codigo_qr": r[1],
            "data_hora": (r[2] - timedelta(hours=3)).strftime("%d/%m/%Y %H:%M:%S") if r[2] else "",
            "usuario": r[3],
            "status": r[4]
        } for r in registros
    ])

@app.route('/listar_qr_obra')
def listar_qr_obra():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, codigo_qr, data_hora, usuario, status FROM recebimento_obra ORDER BY data_hora DESC")
    registros = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify([
        {
            "id": r[0],
            "codigo_qr": r[1],
            "data_hora": (r[2] - timedelta(hours=3)).strftime("%d/%m/%Y %H:%M:%S") if r[2] else "",
            "usuario": r[3],
            "status": r[4]
        } for r in registros
    ])

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

@app.route('/relatorio_obra_dados')
def relatorio_obra_dados():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT cod_insumo, produto, obra, cargas, total FROM lista_de_carga")
    lista = cur.fetchall()

    cur.execute("SELECT codigo_qr, COUNT(*) FROM registros_qr GROUP BY codigo_qr")
    bipados = cur.fetchall()
    bipados_dict = {codigo: qtd for codigo, qtd in bipados}

    cur.execute("SELECT codigo_qr, COUNT(*) FROM recebimento_obra GROUP BY codigo_qr")
    recebidos = cur.fetchall()
    recebidos_dict = {codigo: qtd for codigo, qtd in recebidos}

    relatorio = []
    for cod_insumo, produto, obra, cargas, total in lista:
        bipado = bipados_dict.get(cod_insumo, 0)
        if bipado > 0:
            recebido = recebidos_dict.get(cod_insumo, 0)
            faltando = bipado - recebido
            relatorio.append({
                "cod_insumo": cod_insumo,
                "produto": produto,
                "obra": obra,
                "cargas": cargas,
                "total_necessario": bipado,
                "bipado": recebido,
                "faltando": faltando
            })

    cur.close()
    conn.close()
    return jsonify(relatorio)

if __name__ == '__main__':
    app.run(debug=True)


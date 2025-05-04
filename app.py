from flask import Flask, request, jsonify, send_file, render_template
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
    return send_file('index.html')

@app.route('/etiquetas')
def etiquetas():
    return send_file('etiquetas.html')

@app.route('/grafico_auto')
def grafico_auto():
    return send_file('grafico_relatorio_auto.html')


@app.route('/grafico')
def grafico():
    return send_file('grafico_relatorio.html')

@app.route('/cadastro_funcionario')
def pagina_cadastro_funcionario():
    return send_file('cadastro_funcionario.html')

@app.route('/obra')
def obra():
    return send_file('obra.html')

@app.route('/registros')
def registros():
    return send_file('registros.html')

@app.route('/registros_obra')
def registros_obra():
    return send_file('registros_obra.html')

@app.route('/relatorio_obra')
def relatorio_obra():
    return send_file('relatorio.html')

@app.route('/importar')
def importar_lista():
    return send_file('upload.html')

@app.route('/lista_carga')
def lista_carga():
    return send_file('lista_carga.html')

@app.route('/relatorio')
def relatorio():
    return send_file('relatorio.html')

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
def listar_qr_server_side():
    draw = int(request.args.get('draw', 1))
    start = int(request.args.get('start', 0))
    length = int(request.args.get('length', 10))
    filtro_qr = request.args.get('filtroQR')
    filtro_usuario = request.args.get('filtroUsuario')

    conn = get_db_connection()
    cur = conn.cursor()

    filtros = []
    valores = []

    if filtro_qr:
        filtros.append("codigo_qr = %s")
        valores.append(filtro_qr)
    if filtro_usuario:
        filtros.append("usuario = %s")
        valores.append(filtro_usuario)

    where_clause = f"WHERE {' AND '.join(filtros)}" if filtros else ""

    # total filtrado
    cur.execute(f"SELECT COUNT(*) FROM registros_qr {where_clause}", valores)
    records_total = cur.fetchone()[0]

    # dados paginados
    cur.execute(f"""
        SELECT id, codigo_qr, usuario, data_hora
        FROM registros_qr
        {where_clause}
        ORDER BY data_hora DESC
        LIMIT %s OFFSET %s
    """, (*valores, length, start))
    dados = cur.fetchall()

    tz = pytz.timezone('America/Sao_Paulo')
    registros = [
        {
            "id": r[0],
            "codigo_qr": r[1],
            "usuario": r[2],
            "data_hora": r[3].replace(tzinfo=pytz.utc).astimezone(tz).strftime('%d/%m/%Y %H:%M:%S') if r[3] else ""
        }
        for r in dados
    ]

    cur.close()
    conn.close()

    return jsonify({
        "draw": draw,
        "recordsTotal": records_total,
        "recordsFiltered": records_total,
        "data": registros
    })


@app.route('/listar_qr_filtros')
def listar_qr_filtros():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT codigo_qr, usuario FROM registros_qr")
    dados = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify([
        {"codigo_qr": r[0], "usuario": r[1]}
        for r in dados
        if r[0] and r[1]
    ])


@app.route('/listar_qr_obra', methods=['GET'])
def listar_qr_obra():
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id, codigo_qr, data_hora, usuario, status FROM recebimento_obra ORDER BY data_hora DESC")
        registros = cur.fetchall()
        cur.close()
        conn.close()

        tz = pytz.timezone('America/Sao_Paulo')  # fuso de Brasília
        registros_formatados = [
            {
                "id": r[0],
                "codigo_qr": r[1],
                "data_hora": r[2].replace(tzinfo=pytz.utc).astimezone(tz).strftime('%d/%m/%Y %H:%M:%S') if r[2] else "",
                "usuario": r[3],
                "status": r[4]
            }
            for r in registros
        ]
        return jsonify(registros_formatados)
    except Exception as e:
        return jsonify({"erro": str(e)}), 500


@app.route('/excluir_qr/<int:id>', methods=['DELETE'])
def excluir_qr(id):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM registros_qr WHERE id = %s", (id,))
        conn.commit()
        return jsonify({"sucesso": True})
    except Exception as e:
        return jsonify({"sucesso": False, "erro": str(e)})
    finally:
        cur.close()
        conn.close()

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
            cur.execute(
                "INSERT INTO lista_de_carga (cod_insumo, produto, uhs, obra, cargas, total, pav) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (row["COD INSUMO"], row["PRODUTO"], row["UHS"], row["OBRA"], row["CARGAS"], row["TOTAL"], row["PAV"])
            )

        conn.commit()
        cur.close()
        conn.close()

        return jsonify({'mensagem': 'Lista de carga importada com sucesso.'}), 200

    except Exception as e:
        return jsonify({'erro': str(e)}), 500

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
        return jsonify({"mensagem": "QR Code registrado com sucesso na obra!"}), 201
    except Exception as e:
        return jsonify({"erro": str(e)}), 500
    finally:
        cur.close()
        conn.close()

@app.route('/relatorio_diferencas')
def relatorio_diferencas():
    obra_filtro = request.args.get("obra")
    cargas_param = request.args.get("cargas")
    cargas_lista = cargas_param.split(",") if cargas_param else []

    if not obra_filtro or not cargas_lista:
        return jsonify([])

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # 1. Busca todos os registros da obra para usar na lógica de bipagem (em ordem)
                cur.execute("""
                    SELECT cod_insumo, produto, uhs, obra, cargas, total, pav, id
                    FROM lista_de_carga
                    WHERE obra = %s
                    ORDER BY id
                """, (obra_filtro,))
                lista_toda = cur.fetchall()
                colunas = [desc[0] for desc in cur.description]
                todos_registros = [dict(zip(colunas, linha)) for linha in lista_toda]

                # 2. Filtra somente os registros das cargas selecionadas para exibição
                registros_filtrados = [r for r in todos_registros if r["cargas"] in cargas_lista]

                if not registros_filtrados:
                    return jsonify([])

                # 3. Pega os cod_insumo únicos da carga filtrada (não da obra toda)
                cods_insumo = tuple(set(r["cod_insumo"] for r in registros_filtrados))
                placeholder = ','.join(['%s'] * len(cods_insumo))

                # 4. Busca os bipados da fábrica e obra para toda a obra
                cur.execute(f"""
                    SELECT codigo_qr, COUNT(*) 
                    FROM registros_qr
                    WHERE codigo_qr IN ({placeholder}) AND codigo_qr IN (
                        SELECT cod_insumo FROM lista_de_carga WHERE obra = %s
                    )
                    GROUP BY codigo_qr
                """, (*cods_insumo, obra_filtro))
                bipado_fabrica_dict = dict(cur.fetchall())

                cur.execute(f"""
                    SELECT codigo_qr, COUNT(*) 
                    FROM recebimento_obra
                    WHERE codigo_qr IN ({placeholder}) AND codigo_qr IN (
                        SELECT cod_insumo FROM lista_de_carga WHERE obra = %s
                    )
                    GROUP BY codigo_qr
                """, (*cods_insumo, obra_filtro))
                bipado_obra_dict = dict(cur.fetchall())

                # 5. Abate os bipados na ordem dos registros da obra (não só das cargas filtradas)
                disponivel_fabrica = bipado_fabrica_dict.copy()
                disponivel_obra = bipado_obra_dict.copy()
                bipagem_aplicada = []

                for registro in todos_registros:
                    cod_insumo = registro["cod_insumo"]
                    total = int(registro["total"])

                    usado_fabrica = min(disponivel_fabrica.get(cod_insumo, 0), total)
                    disponivel_fabrica[cod_insumo] = disponivel_fabrica.get(cod_insumo, 0) - usado_fabrica

                    usado_obra = min(disponivel_obra.get(cod_insumo, 0), total)
                    disponivel_obra[cod_insumo] = disponivel_obra.get(cod_insumo, 0) - usado_obra

                    registro_resultado = {
                        "cod_insumo": cod_insumo,
                        "produto": registro["produto"],
                        "obra": registro["obra"],
                        "cargas": registro["cargas"],
                        "total_necessario": total,
                        "bipado_fabrica": usado_fabrica,
                        "bipado_obra": usado_obra
                    }

                    bipagem_aplicada.append(registro_resultado)

                # 6. Filtra novamente só os registros das cargas selecionadas para exibir
                relatorio = [r for r in bipagem_aplicada if r["cargas"] in cargas_lista]
                return jsonify(relatorio)

    except Exception as e:
        return jsonify({"erro": str(e)}), 500


@app.route('/excluir_qr_obra/<int:id>', methods=['DELETE'])
def excluir_qr_obra(id):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM recebimento_obra WHERE id = %s", (id,))
        conn.commit()
        return jsonify({"sucesso": True})
    except Exception as e:
        return jsonify({"sucesso": False, "erro": str(e)})
    finally:
        cur.close()
        conn.close()

@app.route('/gerar_etiquetas')
def gerar_etiquetas():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM lista_de_carga ORDER BY obra")
    dados = cur.fetchall()
    colunas = [desc[0] for desc in cur.description]
    cur.close()
    conn.close()
    registros = [dict(zip(colunas, linha)) for linha in dados]
    return render_template("etiquetas.html", registros=registros)

from werkzeug.security import generate_password_hash, check_password_hash

@app.route('/cadastrar_funcionario', methods=['POST'])
def cadastrar_funcionario():
    data = request.json
    nome = data.get('nome')
    senha = data.get('senha')

    if not nome or not senha:
        return jsonify({"erro": "Nome e senha são obrigatórios"}), 400

    senha_hash = generate_password_hash(senha)

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO funcionarios (nome, senha) VALUES (%s, %s)", (nome, senha_hash))
        conn.commit()
        return jsonify({"mensagem": "Funcionário cadastrado com sucesso!"}), 201
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        return jsonify({"erro": "Funcionário já existe."}), 409
    except Exception as e:
        return jsonify({"erro": str(e)}), 500
    finally:
        cur.close()
        conn.close()

@app.route('/verificar_senha', methods=['POST'])
def verificar_senha():
    data = request.json
    nome = data.get('nome')
    senha = data.get('senha')

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT senha FROM funcionarios WHERE nome = %s", (nome,))
    resultado = cur.fetchone()
    cur.close()
    conn.close()

    if resultado and check_password_hash(resultado[0], senha):
        return jsonify({"valido": True})
    else:
        return jsonify({"valido": False}), 401

@app.route('/listar_funcionarios', methods=['GET'])
def listar_funcionarios():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT nome FROM funcionarios ORDER BY nome")
    funcionarios = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify([{"nome": f[0]} for f in funcionarios])

from flask import jsonify
from sqlalchemy import text

@app.route('/obras_disponiveis')
def obras_disponiveis():
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT DISTINCT obra FROM lista_de_carga ORDER BY obra")
        resultados = cur.fetchall()
        obras = [row[0] for row in resultados]
        return jsonify(obras)
    except Exception as e:
        return jsonify({"erro": str(e)}), 500
    finally:
        cur.close()
        conn.close()

@app.route('/cargas_disponiveis')
def cargas_disponiveis():
    obra = request.args.get("obra")
    if not obra:
        return jsonify([])

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT DISTINCT cargas FROM lista_de_carga WHERE obra = %s ORDER BY cargas", (obra,))
        resultados = cur.fetchall()
        cargas = [row[0] for row in resultados]
        return jsonify(cargas)
    except Exception as e:
        return jsonify({"erro": str(e)}), 500
    finally:
        cur.close()
        conn.close()

def relatorio_diferencas_interno(obra_filtro, carga_filtro):
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                SELECT cod_insumo, produto, uhs, obra, cargas, total, pav
                FROM lista_de_carga
                WHERE obra = %s AND cargas = ANY(%s)
                ORDER BY id
                """, (obra_filtro, tuple(carga_filtro)))

                lista = cur.fetchall()
                colunas = [desc[0] for desc in cur.description]
                registros = [dict(zip(colunas, linha)) for linha in lista]

                if not registros:
                    return jsonify([])

                cods_insumo = tuple(set(r["cod_insumo"] for r in registros))
                placeholder = ','.join(['%s'] * len(cods_insumo))

                cur.execute(f"""
                    SELECT codigo_qr, COUNT(*) 
                    FROM registros_qr 
                    WHERE codigo_qr IN ({placeholder})
                    GROUP BY codigo_qr
                """, cods_insumo)
                bipado_fabrica_dict = dict(cur.fetchall())

                cur.execute(f"""
                    SELECT codigo_qr, COUNT(*) 
                    FROM recebimento_obra 
                    WHERE codigo_qr IN ({placeholder})
                    GROUP BY codigo_qr
                """, cods_insumo)
                bipado_obra_dict = dict(cur.fetchall())

        relatorio = []
        for registro in registros:
            cod_insumo = registro["cod_insumo"]
            total = int(registro["total"])

            disponivel_fabrica = bipado_fabrica_dict.get(cod_insumo, 0)
            usado_fabrica = min(disponivel_fabrica, total)
            bipado_fabrica_dict[cod_insumo] = disponivel_fabrica - usado_fabrica

            disponivel_obra = bipado_obra_dict.get(cod_insumo, 0)
            usado_obra = min(disponivel_obra, total)
            bipado_obra_dict[cod_insumo] = disponivel_obra - usado_obra

            relatorio.append({
                "cod_insumo": cod_insumo,
                "produto": registro["produto"],
                "obra": registro["obra"],
                "cargas": registro["cargas"],
                "total_necessario": total,
                "bipado_fabrica": usado_fabrica,
                "bipado_obra": usado_obra
            })

        return jsonify(relatorio)

    except Exception as e:
        return jsonify({"erro": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)

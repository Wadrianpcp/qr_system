from flask import Flask, request, jsonify, send_file, render_template
import psycopg2
import pandas as pd
from datetime import datetime
import pytz

from psycopg2.extensions import register_adapter, AsIs

def adapt_list(lst):
    return AsIs("ARRAY[" + ",".join(["'%s'" % item for item in lst]) + "]")

register_adapter(list, adapt_list)



app = Flask(__name__)

DATABASE_URL = "postgresql://neondb_owner:npg_lJHgpoh53QXM@ep-old-night-acgy3449-pooler.sa-east-1.aws.neon.tech/neondb?sslmode=require"

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)


@app.route('/')
def index():
    return send_file('index.html')


@app.route('/grafico_nes')
def grafico_nes():
    return send_file('grafico_nes.html')


@app.route('/inicio')
def tela_inicial():
    return send_file('tela_inicial.html')

@app.route('/produtividade')
def produtividade():
    return send_file('produtividade.html')

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

@app.route('/registros embarque')
def registros_embarque():
    return send_file('registros embarque.html')

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

@app.route('/registrar_embarque')
def registrar_embarque():
    return send_file('Embarque.html')

@app.route('/materiais_por_maquina')
def materiais_por_maquina():
    maquina = request.args.get("maquina")
    data_inicio = request.args.get("data_inicio")
    data_fim = request.args.get("data_fim")
    obras = request.args.getlist("obras[]")

    conn = get_db_connection()
    cur = conn.cursor()

    query = """
        SELECT DISTINCT material
        FROM registro_produtividade
        WHERE material IS NOT NULL
    """
    params = []

    if maquina:
        query += " AND maquina = %s"
        params.append(maquina)
    if obras:
        query += " AND obra = ANY(%s)"
        params.append(obras)
    if data_inicio:
        query += " AND data >= %s"
        params.append(data_inicio)
    if data_fim:
        query += " AND data <= %s"
        params.append(data_fim)

    query += " ORDER BY material"

    cur.execute(query, tuple(params))
    materiais = [row[0] for row in cur.fetchall()]

    cur.close()
    conn.close()

    return jsonify(materiais)




@app.route('/operadores')
def operadores():
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id, operadores FROM operadores ORDER BY operadores")
        resultados = cur.fetchall()
        dados = [{"id": r[0], "operadores": r[1]} for r in resultados]
        return jsonify(dados)
    except Exception as e:
        return jsonify({"erro": str(e)}), 500
    finally:
        cur.close()
        conn.close()


@app.route('/soma_horas_disponivel')
def soma_horas_disponivel():
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT SUM(EXTRACT(EPOCH FROM horas_disponivel) / 3600) AS total_horas
            FROM registro_produtividade
        """)
        total = cur.fetchone()[0] or 0

        cur.close()
        conn.close()

        return jsonify({"total_horas_disponivel": round(total, 2)})
    except Exception as e:
        return jsonify({"erro": str(e)}), 500


@app.route('/maquinas_disponiveis')
def maquinas_disponiveis():
    data_inicio = request.args.get("data_inicio")
    data_fim = request.args.get("data_fim")

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        query = """
            SELECT DISTINCT maquina
            FROM registro_produtividade
            WHERE maquina IS NOT NULL AND maquina <> ''
        """
        params = []

        if data_inicio:
            query += " AND data >= %s"
            params.append(data_inicio)
        if data_fim:
            query += " AND data <= %s"
            params.append(data_fim)

        query += " ORDER BY maquina"

        cur.execute(query, params)
        maquinas = [r[0] for r in cur.fetchall()]
        return jsonify(maquinas)

    except Exception as e:
        return jsonify({"erro": str(e)}), 500
    finally:
        cur.close()
        conn.close()


@app.route('/registrar_produtividade', methods=['POST'])
def registrar_produtividade():
    data = request.get_json()

    operacao = data.get("operacao")
    obra = data.get("obra")
    ocorrencia = data.get("ocorrencia")
    hr_inicio = data.get("hr_inicio")
    hr_fim = data.get("hr_fim")
    data_registro = data.get("data")
    operador = data.get("operador")
    material = data.get("material")
    maquina = data.get("maquina")
    observacao = data.get("observacao")

    try:
        pecas_cortadas = int(data.get("pecas_cortadas")) if data.get("pecas_cortadas") not in ("", None) else 0
    except ValueError:
        pecas_cortadas = 0

    try:
        qtd_ch = int(data.get("qtd_ch")) if data.get("qtd_ch") not in ("", None) else 0
    except ValueError:
        qtd_ch = 0

    try:
        h_inicio = datetime.strptime(hr_inicio, "%H:%M")
        h_fim = datetime.strptime(hr_fim, "%H:%M")
        duracao = h_fim - h_inicio
        if duracao.total_seconds() < 0:
            duracao += timedelta(days=1)

        horas_disponivel = str(duracao)

        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO registro_produtividade (
                operacao, obra, ocorrencia, hr_inicio, hr_fim, qtd_ch,
                data, operador, material, horas_disponivel, maquina, pecas_cortadas, observacao
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            operacao, obra, ocorrencia, hr_inicio, hr_fim,
            qtd_ch, data_registro, operador, material,
            horas_disponivel, maquina, pecas_cortadas, observacao
        ))

        conn.commit()
        cur.close()
        conn.close()

        return jsonify({"sucesso": True})

    except Exception as e:
        return jsonify({"erro": str(e)}), 500


@app.route('/material')
def material():
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id, material FROM material ORDER BY material")
        resultados = cur.fetchall()
        dados = [{"id": r[0], "material": r[1]} for r in resultados]
        return jsonify(dados)
    except Exception as e:
        return jsonify({"erro": str(e)}), 500
    finally:
        cur.close()
        conn.close()


@app.route('/ocorrencia')
def ocorrencia():
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id, ocorrencia FROM ocorrencia ORDER BY ocorrencia")
        resultados = cur.fetchall()
        dados = [{"id": r[0], "ocorrencia": r[1]} for r in resultados]
        return jsonify(dados)
    except Exception as e:
        return jsonify({"erro": str(e)}), 500
    finally:
        cur.close()
        conn.close()



@app.route('/obras_lotes')
def obras_lotes():
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT DISTINCT obra, lote FROM obras_lotes ORDER BY obra, lote")
        resultados = cur.fetchall()
        dados = [{"obra": r[0], "lote": r[1]} for r in resultados]
        return jsonify(dados)
    except Exception as e:
        return jsonify({"erro": str(e)}), 500
    finally:
        cur.close()
        conn.close()



@app.route('/dados_grafico', methods=['POST'])
def dados_grafico():
    data = request.get_json()
    obra = data.get('obra')
    cargas = data.get('cargas', [])

    conn = get_db_connection()
    cur = conn.cursor()

    # Atualiza a view antes de consultar
    cur.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY relatorio_atendimento_carga_embarque_mv;")

    query = """
        SELECT 
            SUM(total_necessario) AS total_carga,
            SUM(bipado_fabrica) AS bipado_fabrica,
            SUM(bipado_obra) AS bipado_obra
        FROM relatorio_atendimento_carga_embarque_mv
        WHERE 1=1
    """
    params = []

    if obra:
        query += " AND obra = %s"
        params.append(obra)
    if cargas:
        query += " AND cargas = ANY(%s)"
        params.append(cargas)

    cur.execute(query, tuple(params))
    row = cur.fetchone()
    cur.close()
    conn.close()

    total_carga = row[0] or 0
    bipado_fabrica = row[1] or 0
    bipado_obra = row[2] or 0
    nao_bipado = total_carga - bipado_fabrica

    return jsonify({
        'total_carga': total_carga,
        'bipado_fabrica': bipado_fabrica,
        'bipado_obra': bipado_obra,
        'nao_bipado': max(0, nao_bipado)
    })




@app.route('/registrar_qr_embarque', methods=['POST'])
def registrar_qr_embarque():
    data = request.json
    codigo_qr = data.get('codigo_qr')
    usuario = data.get('usuario')

    if not codigo_qr or not usuario:
        return jsonify({"erro": "Código QR e usuário são obrigatórios"}), 400

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO registros_qr_embarque (codigo_qr, usuario) VALUES (%s, %s)", (codigo_qr, usuario))
        conn.commit()
        return jsonify({"mensagem": "QR Code registrado com sucesso no embarque!"}), 201
    except Exception as e:
        return jsonify({"erro": str(e)}), 500
    finally:
        cur.close()
        conn.close()



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
    filtro_qr = request.args.get('filtroQR', '').strip()
    filtro_usuario = request.args.get('filtroUsuario', '').strip()

    conn = get_db_connection()
    cur = conn.cursor()

    where_clauses = []
    valores = []

    if filtro_qr:
        where_clauses.append("codigo_qr ILIKE %s")
        valores.append(f"%{filtro_qr}%")

    if filtro_usuario:
        where_clauses.append("usuario = %s")
        valores.append(filtro_usuario)

    where_sql = " AND ".join(where_clauses)
    if where_sql:
        where_sql = "WHERE " + where_sql

    # Total de registros (sem filtro)
    cur.execute("SELECT COUNT(*) FROM registros_qr")
    records_total = cur.fetchone()[0]

    # Total de registros filtrados
    cur.execute(f"SELECT COUNT(*) FROM registros_qr {where_sql}", tuple(valores))
    records_filtered = cur.fetchone()[0]

    # Dados da página
    cur.execute(f"""
        SELECT id, codigo_qr, usuario, data_hora
        FROM registros_qr
        {where_sql}
        ORDER BY data_hora DESC
        LIMIT %s OFFSET %s
    """, (*valores, length, start))
    dados = cur.fetchall()

    tz = pytz.timezone('America/Sao_Paulo')
    data = [{
        "id": r[0],
        "codigo_qr": r[1],
        "usuario": r[2],
        "data_hora": r[3].replace(tzinfo=pytz.utc).astimezone(tz).strftime('%d/%m/%Y %H:%M:%S') if r[3] else ""
    } for r in dados]

    cur.close()
    conn.close()

    return jsonify({
        "draw": draw,
        "recordsTotal": records_total,
        "recordsFiltered": records_filtered,
        "data": data
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


@app.route('/listar_qr_embarque', methods=['GET'])
def listar_qr_embarque_server_side():
    draw = int(request.args.get('draw', 1))
    start = int(request.args.get('start', 0))
    length = int(request.args.get('length', 10))
    filtro_qr = request.args.get('filtroQR', '').strip()
    filtro_usuario = request.args.get('filtroUsuario', '').strip()

    conn = get_db_connection()
    cur = conn.cursor()

    where_clauses = []
    valores = []

    if filtro_qr:
        where_clauses.append("codigo_qr ILIKE %s")
        valores.append(f"%{filtro_qr}%")

    if filtro_usuario:
        where_clauses.append("usuario = %s")
        valores.append(filtro_usuario)

    where_sql = " AND ".join(where_clauses)
    if where_sql:
        where_sql = "WHERE " + where_sql

    # Total de registros (sem filtro)
    cur.execute("SELECT COUNT(*) FROM registros_qr_embarque")
    records_total = cur.fetchone()[0]

    # Total de registros filtrados
    cur.execute(f"SELECT COUNT(*) FROM registros_qr_embarque {where_sql}", tuple(valores))
    records_filtered = cur.fetchone()[0]

    # Dados da página
    cur.execute(f"""
        SELECT id, codigo_qr, usuario, data_hora
        FROM registros_qr_embarque
        {where_sql}
        ORDER BY data_hora DESC
        LIMIT %s OFFSET %s
    """, (*valores, length, start))
    dados = cur.fetchall()

    tz = pytz.timezone('America/Sao_Paulo')
    data = [{
        "id": r[0],
        "codigo_qr": r[1],
        "usuario": r[2],
        "data_hora": r[3].replace(tzinfo=pytz.utc).astimezone(tz).strftime('%d/%m/%Y %H:%M:%S') if r[3] else ""
    } for r in dados]

    cur.close()
    conn.close()

    return jsonify({
        "draw": draw,
        "recordsTotal": records_total,
        "recordsFiltered": records_filtered,
        "data": data
    })




@app.route('/listar_qr_obra', methods=['GET'])
def listar_qr_obra_server_side():
    draw = int(request.args.get('draw', 1))
    start = int(request.args.get('start', 0))
    length = int(request.args.get('length', 10))
    filtro_qr = request.args.get('filtroQR', '').strip()
    filtro_usuario = request.args.get('filtroUsuario', '').strip()

    conn = get_db_connection()
    cur = conn.cursor()

    where_clauses = []
    valores = []

    if filtro_qr:
        where_clauses.append("codigo_qr ILIKE %s")
        valores.append(f"%{filtro_qr}%")

    if filtro_usuario:
        where_clauses.append("usuario = %s")
        valores.append(filtro_usuario)

    where_sql = " AND ".join(where_clauses)
    if where_sql:
        where_sql = "WHERE " + where_sql

    # Total de registros (sem filtro)
    cur.execute("SELECT COUNT(*) FROM recebimento_obra")
    records_total = cur.fetchone()[0]

    # Total de registros filtrados
    cur.execute(f"SELECT COUNT(*) FROM recebimento_obra {where_sql}", tuple(valores))
    records_filtered = cur.fetchone()[0]

    # Dados da página
    cur.execute(f"""
        SELECT id, codigo_qr, usuario, data_hora
        FROM recebimento_obra
        {where_sql}
        ORDER BY data_hora DESC
        LIMIT %s OFFSET %s
    """, (*valores, length, start))
    dados = cur.fetchall()

    tz = pytz.timezone('America/Sao_Paulo')
    data = [{
        "id": r[0],
        "codigo_qr": r[1],
        "usuario": r[2],
        "data_hora": r[3].replace(tzinfo=pytz.utc).astimezone(tz).strftime('%d/%m/%Y %H:%M:%S') if r[3] else ""
    } for r in dados]

    cur.close()
    conn.close()

    return jsonify({
        "draw": draw,
        "recordsTotal": records_total,
        "recordsFiltered": records_filtered,
        "data": data
    })




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


@app.route("/atualizar_relatorio_mv")
def atualizar_relatorio_mv():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("REFRESH MATERIALIZED VIEW relatorio_atendimento_carga_embarque_mv;")  # 🔄 sem CONCURRENTLY
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"mensagem": "View atualizada com sucesso"})
    except Exception as e:
        return jsonify({"erro": str(e)}), 500



@app.route('/relatorio_diferencas', methods=['POST'])
def relatorio_diferencas():
    try:
        dados = request.get_json()
        obra = dados.get('obra')
        cargas = dados.get('cargas', [])

        conn = get_db_connection()
        cur = conn.cursor()

        query = "SELECT * FROM relatorio_atendimento_carga_embarque_mv WHERE 1=1"
        parametros = []

        if obra:
            query += " AND obra = %s"
            parametros.append(obra)

        if cargas:
            query += " AND cargas = ANY(%s)"
            parametros.append(cargas)

        cur.execute(query, tuple(parametros))
        resultados = cur.fetchall()

        # 🔽 aqui você usa os índices conforme a ordem da sua materialized view
        data = [{
            "cod_insumo": r[0],
            "produto": r[1],
            "obra": r[2],
            "cargas": r[3],
            "total_necessario": r[4],
            "bipado_fabrica": r[5],
            "bipado_embarque": r[6],  # ✅ novo campo
            "bipado_obra": r[7]
        } for r in resultados]

        cur.close()
        conn.close()
        return jsonify(data)

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

@app.route('/excluir_qr_embarque/<int:id>', methods=['DELETE'])
def excluir_qr_embarque(id):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM registros_qr_embarque WHERE id = %s", (id,))
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

@app.route('/atualizar_view', methods=['POST'])
def atualizar_view():
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute('REFRESH MATERIALIZED VIEW CONCURRENTLY relatorio_atendimento_carga_embarque_mv;')
        conn.commit()
        return jsonify({'status': 'success'})
    except Exception as e:
        conn.rollback()
        return jsonify({'status': 'error', 'message': str(e)})
    finally:
        cur.close()
        conn.close()


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


@app.route('/obras_disponiveis_maquinas')
def obras_disponiveis_maquinas():
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT DISTINCT obra FROM registro_produtividade WHERE obra IS NOT NULL ORDER BY obra")
        resultados = cur.fetchall()
        obras = [{"obra": r[0]} for r in resultados if r[0]]
        return jsonify(obras)
    except Exception as e:
        return jsonify({"erro": str(e)}), 500
    finally:
        cur.close()
        conn.close()



@app.route('/obras_filtradas_por_material')
def obras_filtradas_por_material():
    material = request.args.get("material")
    data_inicio = request.args.get("data_inicio")
    data_fim = request.args.get("data_fim")

    conn = get_db_connection()
    cur = conn.cursor()

    query = """
        SELECT DISTINCT obra FROM registro_produtividade
        WHERE 1=1
    """
    params = []

    if material:
        query += " AND material = %s"
        params.append(material)
    if data_inicio:
        query += " AND data >= %s"
        params.append(data_inicio)
    if data_fim:
        query += " AND data <= %s"
        params.append(data_fim)

    cur.execute(query, tuple(params))
    obras = [r[0] for r in cur.fetchall()]
    cur.close()
    conn.close()
    return jsonify(obras)


@app.route('/materiais_filtrados_por_obra')
def materiais_filtrados_por_obra():
    obra = request.args.get("obra")
    data_inicio = request.args.get("data_inicio")
    data_fim = request.args.get("data_fim")

    conn = get_db_connection()
    cur = conn.cursor()

    query = """
        SELECT DISTINCT material FROM registro_produtividade
        WHERE 1=1
    """
    params = []

    if obra:
        query += " AND obra = %s"
        params.append(obra)
    if data_inicio:
        query += " AND data >= %s"
        params.append(data_inicio)
    if data_fim:
        query += " AND data <= %s"
        params.append(data_fim)

    cur.execute(query, tuple(params))
    materiais = [r[0] for r in cur.fetchall()]
    cur.close()
    conn.close()
    return jsonify(materiais)


@app.route('/obras_disponiveis_produtividade')
def obras_disponiveis_produtividade():
    data_inicio = request.args.get("data_inicio")
    data_fim = request.args.get("data_fim")
    maquina = request.args.get("maquina")
    material = request.args.get("material")

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        query = """
            SELECT DISTINCT obra
            FROM registro_produtividade
            WHERE (COALESCE(qtd_ch, 0) > 0 OR COALESCE(pecas_cortadas, 0) > 0)
        """
        params = []

        if data_inicio:
            query += " AND data >= %s"
            params.append(data_inicio)
        if data_fim:
            query += " AND data <= %s"
            params.append(data_fim)
        if maquina and maquina != "Todos":
            query += " AND maquina = %s"
            params.append(maquina)
        if material and material != "Todos":
            query += " AND material = %s"
            params.append(material)

        query += " ORDER BY obra"

        cur.execute(query, tuple(params))
        obras = [r[0] for r in cur.fetchall()]
        return jsonify(obras)

    except Exception as e:
        return jsonify({"erro": str(e)}), 500
    finally:
        cur.close()
        conn.close()




@app.route('/materiais_disponiveis')
def materiais_disponiveis():
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT DISTINCT material FROM registro_produtividade WHERE material IS NOT NULL ORDER BY material")
        materiais = [row[0] for row in cur.fetchall()]
        return jsonify(materiais)
    except Exception as e:
        return jsonify({"erro": str(e)}), 500
    finally:
        cur.close()
        conn.close()


@app.route('/materiais_disponiveis_produtividade')
def materiais_disponiveis_produtividade():
    data_inicio = request.args.get("data_inicio")
    data_fim = request.args.get("data_fim")

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        query = "SELECT DISTINCT material FROM registro_produtividade WHERE material IS NOT NULL"
        valores = []

        if data_inicio:
            query += " AND data >= %s"
            valores.append(data_inicio)
        if data_fim:
            query += " AND data <= %s"
            valores.append(data_fim)

        query += " ORDER BY material"

        cur.execute(query, tuple(valores))
        resultados = cur.fetchall()
        materiais = [r[0] for r in resultados]
        return jsonify(materiais)
    except Exception as e:
        return jsonify({"erro": str(e)}), 500
    finally:
        cur.close()
        conn.close()


@app.route('/dados_relatorio_produtividade', methods=['POST'])
def dados_relatorio_produtividade():
    dados = request.json
    obra = dados.get('obra')
    data_inicio = dados.get('data_inicio')
    data_fim = dados.get('data_fim')
    operacao = dados.get('operacao')
    material = dados.get('material')
    maquina = dados.get('maquina')

    filtros = []
    valores = []

    if obra and "Todos" not in obra:
        filtros.append("obra = ANY(%s)")
        valores.append(obra if isinstance(obra, list) else [obra])
    if data_inicio:
        filtros.append("data >= %s")
        valores.append(data_inicio)
    if data_fim:
        filtros.append("data <= %s")
        valores.append(data_fim)
    if operacao:
        filtros.append("operacao = %s")
        valores.append(operacao)
    if material:
        filtros.append("material = %s")
        valores.append(material)
    if maquina:
        filtros.append("maquina = %s")
        valores.append(maquina)

    where_clause = "WHERE " + " AND ".join(filtros) if filtros else ""

    query_total = f"""
        SELECT
            COALESCE(SUM(CAST(qtd_ch AS INTEGER)), 0) as qtd_ch,
            COALESCE(SUM(EXTRACT(EPOCH FROM (hr_fim - hr_inicio)) / 60), 0) as minutos_totais,
            COALESCE(SUM(CAST(pecas_cortadas AS INTEGER)), 0) as qtd_pecas
        FROM registro_produtividade
        {where_clause}
    """

    query_paradas = f"""
        SELECT ocorrencia, SUM(EXTRACT(EPOCH FROM (hr_fim - hr_inicio)) / 60) as minutos
        FROM registro_produtividade
        WHERE operacao = 'Ocorrência'
        {"AND " + " AND ".join(filtros) if filtros else ""}
        GROUP BY ocorrencia
        ORDER BY minutos DESC
    """

    query_producao = f"""
        SELECT data, SUM(CAST(qtd_ch AS INTEGER)) as qtd
        FROM registro_produtividade
        WHERE operacao IN ('Plano', 'Reposição', 'Assistência', 'Teste')
        {"AND " + " AND ".join(filtros) if filtros else ""}
        GROUP BY data
        ORDER BY data
    """

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(query_total, tuple(valores))
        qtd_ch, minutos_totais, qtd_pecas = cur.fetchone()
        minutos_totais = minutos_totais or 0

        cur.execute(query_paradas, tuple(valores))
        paradas = [{"ocorrencia": r[0], "minutos": int(r[1])} for r in cur.fetchall()]
        soma_paradas = sum(p["minutos"] for p in paradas)

        cur.execute(query_producao, tuple(valores))
        producao = [{"data": r[0].strftime("%d/%m"), "qtd": int(r[1])} for r in cur.fetchall()]

        cur.close()
        conn.close()

        return jsonify({
            "qtd_ch": int(qtd_ch),
            "qtd_pecas": int(qtd_pecas),
            "horas_disp": int(minutos_totais),
            "horas_trab": max(int(minutos_totais - soma_paradas), 0),
            "horas_parada": soma_paradas,
            "paradas": paradas,
            "producao": producao,
            "sucesso": True
        })
    except Exception as e:
        return jsonify({"sucesso": False, "erro": str(e)})


@app.route('/materiais_por_obra')
def materiais_por_obra():
    obras = request.args.getlist("obras[]")
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        query = """
            SELECT DISTINCT material
            FROM registro_produtividade
            WHERE obra = ANY(%s)
            ORDER BY material
        """
        cur.execute(query, (obras,))
        resultados = cur.fetchall()
        materiais = [r[0] for r in resultados if r[0]]
        return jsonify(materiais)
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


@app.route('/listar_registros_produtividade', methods=['GET'])
def listar_registros_produtividade():
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        maquina = request.args.get("maquina")
        valores = []
        where_clause = ""

        if maquina:
            where_clause = "WHERE maquina = %s"
            valores.append(maquina)

        cur.execute(f"""
            SELECT id, operacao, obra, qtd_ch, pecas_cortadas, hr_inicio, hr_fim,
                   operador, maquina, data, ocorrencia, material, observacao
            FROM registro_produtividade
            {where_clause}
            ORDER BY id DESC
        """, tuple(valores))

        registros = cur.fetchall()

        dados = []
        for r in registros:
            dados.append({
                "id": r[0],
                "operacao": r[1],
                "obra": r[2],
                "qtd_ch": r[3],
                "pecas_cortadas": r[4],
                "hr_inicio": r[5].strftime("%H:%M") if r[5] else "",
                "hr_fim": r[6].strftime("%H:%M") if r[6] else "",
                "operador": r[7],
                "maquina": r[8],
                "data": r[9].strftime("%d/%m/%Y") if r[9] else "",
                "ocorrencia": r[10] or "",
                "material": r[11] or "",
                "observacao": r[12] or ""
            })

        return jsonify({"data": dados})
    except Exception as e:
        return jsonify({"erro": str(e)}), 500
    finally:
        cur.close()
        conn.close()


@app.route("/obter_registro/<int:id>")
def obter_registro(id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, operacao, obra, ocorrencia, hr_inicio, hr_fim,
               qtd_ch, pecas_cortadas, data, operador, material, maquina, observacao
        FROM registro_produtividade
        WHERE id = %s
    """, (id,))
    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row:
        return jsonify({"erro": "Registro não encontrado"}), 404

    resultado = {
        "id": row[0],
        "operacao": row[1],
        "obra": row[2],
        "ocorrencia": row[3],
        "hr_inicio": row[4].strftime('%H:%M') if row[4] else "",
        "hr_fim": row[5].strftime('%H:%M') if row[5] else "",
        "qtd_ch": row[6],
        "pecas_cortadas": row[7],
        "data": row[8].strftime('%Y-%m-%d') if row[8] else "",
        "operador": row[9],
        "material": row[10],
        "maquina": row[11],
        "observacao": row[12] or ""
    }

    return jsonify(resultado)


@app.route('/atualizar_produtividade/<int:id>', methods=['PUT'])
def atualizar_produtividade(id):
    data = request.get_json()

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            UPDATE registro_produtividade
            SET operacao = %s, obra = %s, ocorrencia = %s,
                hr_inicio = %s, hr_fim = %s, qtd_ch = %s,
                data = %s, operador = %s, material = %s,
                maquina = %s, pecas_cortadas = %s, observacao = %s
            WHERE id = %s
        """, (
            data.get("operacao"),
            data.get("obra"),
            data.get("ocorrencia"),
            data.get("hr_inicio"),
            data.get("hr_fim"),
            int(data.get("qtd_ch") or 0),
            data.get("data"),
            data.get("operador"),
            data.get("material"),
            data.get("maquina"),
            int(data.get("pecas_cortadas") or 0),
            data.get("observacao"),  # ✅ novo campo
            id
        ))

        conn.commit()
        cur.close()
        conn.close()

        return jsonify({"sucesso": True})
    except Exception as e:
        return jsonify({"erro": str(e)}), 500


@app.route("/excluir_registro/<int:id>", methods=["DELETE"])
def excluir_registro(id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM registro_produtividade WHERE id = %s", (id,))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"sucesso": True})
    except Exception as e:
        return jsonify({"erro": str(e)}), 500



@app.route('/verificar_storage_render')
def verificar_storage_render():
    base_paths = ["/", "/var", "/mnt", "/tmp", "/srv", "/opt"]
    arquivos_grandes = []

    for base in base_paths:
        for raiz, _, arquivos in os.walk(base):
            for nome in arquivos:
                try:
                    caminho = os.path.join(raiz, nome)
                    tamanho = os.path.getsize(caminho) / (1024 * 1024)  # MB
                    if tamanho > 10:  # Filtrar arquivos maiores que 10 MB
                        arquivos_grandes.append({
                            "arquivo": caminho,
                            "tamanho_MB": round(tamanho, 2)
                        })
                except:
                    continue  # ignora erros de acesso a arquivos protegidos

    arquivos_ordenados = sorted(arquivos_grandes, key=lambda x: x["tamanho_MB"], reverse=True)
    return jsonify(arquivos_ordenados[:100])  # retorna os 100 maiores


if __name__ == '__main__':
    app.run(debug=True)
                                                                            

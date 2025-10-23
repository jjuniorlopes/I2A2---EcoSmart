# ==============================================================================
# OBJETIVO: Módulo de Extração e Carregamento (ETL) de Dados Fiscais (NF-e)
#
# RESUMO E FINALIDADE DO CÓDIGO:
#
# Este módulo é responsável pela extração, transformação e carregamento (ETL)
# dos dados fiscais (NF-e) para o banco de dados MySQL.
#
# Principais Funções:
# 1. Permite ao usuário selecionar o período (AAAAMM) e o formato do arquivo (CSV/XML).
# 2. Busca e lê os arquivos de dados simulados (Cabeçalho e Itens) de um repositório GitHub.
# 3. Realiza o parsing robusto do XML (quando aplicável) para converter os dados em DataFrames.
# 4. Conecta-se ao MySQL e verifica a duplicidade de dados para o período informado.
# 5. Mapeia as colunas e realiza o carregamento (`load_to_mysql`) das tabelas NFE_Cabecalho
#    e NFE_Itens.
# 6. Inclui o botão "Voltar à Página Principal" na sidebar para navegação.
#
# ==============================================================================

import streamlit as st
import pandas as pd
import io
from sqlalchemy import create_engine
import os
import mysql.connector
import pymysql
import base64
import xml.etree.ElementTree as ET
import requests

# =================================================
# CÓDIGO PARA CONFIGURAR IMAGEM DE FUNDO VIA CSS
# =================================================
def set_background(image_file):
    """
    Injeta CSS customizado no Streamlit para usar uma imagem local como fundo.
    Requer que o arquivo de imagem esteja no mesmo diretório.
    """
    try:
        with open(image_file, "rb") as f:
            img_data = f.read()
            b64 = base64.b64encode(img_data).decode()
            st.markdown(
                f"""
                    <style>
                        .stApp {{
                            background-image: url("data:image/png;base64,{b64}");
                            background-size: cover;
                            background-attachment: fixed;
                        }}
                    </style>
                """,
                unsafe_allow_html=True
            )
    except FileNotFoundError:
        st.warning(f"Aviso Visual: Arquivo 'fundo.jpg' não encontrado. Usando fundo padrão do Streamlit.")

set_background('fundo.jpg')

# ============================
# 1. CONSTANTES E CONFIGURAÇÕES
# ============================

# Nota: A string de conexão DB_CONNECTION_STRING é mantida para o SQLAlchemy,
# mas as credenciais MySQL diretas serão lidas via st.secrets.
DB_CONNECTION_STRING = 'mysql+mysqlconnector://st.secrets["mysql"]["user"]:st.secrets["mysql"]["password"]@st.secrets["mysql"]["host"]:3306/st.secrets["mysql"]["database"]'
TABLE_CABECALHO = 'NFE_Cabecalho'
TABLE_ITENS = 'NFE_Itens'

# URL base para buscar arquivos de dados simulados (GitHub RAW)
GITHUB_RAW_URL_BASE = 'https://raw.githubusercontent.com/EcoSmart2025/Desafio-Final/refs/heads/main/fiscal-data/'
URL_LOGO = 'logo.jpg'

# Dicionários de mapeamento... (mantidos)
COL_MAPPING_CABECALHO = {
    'chave_de_acesso': 'CHAVE_DE_ACESSO',
    'modelo': 'MODELO',
    's_rie': 'SERIE',
    'n_mero': 'NUMERO',
    'natureza_da_opera_o': 'NATUREZA_DA_OPERACAO',
    'data_emiss_o': 'DATA_EMISSAO',
    'evento_mais_recente': 'EVENTO_RECENTE',
    'data_hora_evento_mais_recente': 'DATA_EVENTO_RECENTE',
    'cpf_cnpj_emitente': 'CPF_CNPJ_EMITENTE',
    'raz_o_social_emitente': 'RAZAO_SOCIAL_EMITENTE',
    'inscri_o_estadual_emitente': 'INSC_ESTADUAL_EMITENTE',
    'uf_emitente': 'UF_EMITENTE',
    'munic_pio_emitente': 'MUNICIPIO_EMITENTE',
    'cnpj_destinat_rio': 'CNPJ_DESTINATARIO',
    'nome_destinat_rio': 'NOME_DESTINATARIO',
    'uf_destinat_rio': 'UF_DESTINATARIO',
    'indicador_ie_destinat_rio': 'INDICADOR_IE_DESTINATARIO',
    'destino_da_opera_o': 'DESTINO_OPERACAO',
    'consumidor_final': 'CONSUMIDOR_FINAL',
    'presen_a_do_comprador': 'PRESENCA_COMPRADOR',
    'valor_nota_fiscal': 'VALOR_NOTA_FISCAL'
}

COL_MAPPING_ITENS = {
    'chave_de_acesso': 'CHAVE_DE_ACESSO',
    'modelo': 'MODELO',
    's_rie': 'SERIE',
    'n_mero': 'NUMERO',
    'natureza_da_opera_o': 'NATUREZA_DA_OPERACAO',
    'data_emiss_o': 'DATA_EMISSAO',
    'cpf_cnpj_emitente': 'CPF_CNPJ_EMITENTE',
    'raz_o_social_emitente': 'RAZAO_SOCIAL_EMITENTE',
    'inscri_o_estadual_emitente': 'INSC_ESTADUAL_EMITENTE',
    'uf_emitente': 'UF_EMITENTE',
    'munic_pio_emitente': 'MUNICIPIO_EMITENTE',
    'cnpj_destinat_rio': 'CNPJ_DESTINATARIO',
    'nome_destinat_rio': 'NOME_DESTINATARIO',
    'uf_destinat_rio': 'UF_DESTINATARIO',
    'indicador_ie_destinat_rio': 'INDICADOR_IE_DESTINATARIO',
    'destino_da_opera_o': 'DESTINO_OPERACAO',
    'consumidor_final': 'CONSUMIDOR_FINAL',
    'presen_a_do_comprador': 'PRESENCA_COMPRADOR',
    'n_mero_produto': 'NUMERO_PRODUTO',
    'descri_o_do_produto_servi_o': 'DESCRICAO_PRODUTO_SERVICO',
    'c_digo_ncm_sh': 'CODIGO_NCM_SH',
    'ncm_sh_tipo_de_produto': 'NCM_SH_TIPO_PRODUTO',
    'cfop': 'CFOP',
    'quantidade': 'QUANTIDADE',
    'unidade': 'UNIDADE',
    'valor_unit_rio': 'VALOR_UNITARIO',
    'valor_total': 'VALOR_TOTAL'
}

# =============================
# 2. FUNÇÕES DE BANCO DE DADOS
# =============================

def get_db_connection():
    """Cria e retorna o motor de conexão SQLAlchemy para o MySQL, compatível com Streamlit Cloud."""
    try:
        # Força o uso do driver PyMySQL
        connection_string = st.secrets.get("DBCONNECTIONSTRING", "")
        if not connection_string:
            host = st.secrets["mysql"]["host"]
            user = st.secrets["mysql"]["user"]
            password = st.secrets["mysql"]["password"]
            database = st.secrets["mysql"]["database"]
            connection_string = f"mysql+pymysql://{user}:{password}@{host}:3306/{database}"
        else:
            # Garante troca para pymysql caso a string tenha outro driver
            connection_string = connection_string.replace("mysql+mysqlconnector", "mysql+pymysql")

        engine = create_engine(connection_string, pool_pre_ping=True)
        return engine

    except KeyError as e:
        st.error(f"Erro: campo {e} ausente em secrets.toml. Verifique suas credenciais.")
        return None
    except Exception as e:
        st.error(f"Erro ao simular conexão com o banco de dados. Detalhe: {e}")
        return None

def get_mysql_credentials():
    """
    NOVA FUNÇÃO: Retorna um dicionário de argumentos de conexão lidos do st.secrets.
    Assume que as credenciais estão estruturadas sob a chave 'mysql' no secrets.toml.
    """
    try:
        return {
            "host": st.secrets["mysql"]["host"],
            "port": 3306,
            "user": st.secrets["mysql"]["user"],
            "password": st.secrets["mysql"]["password"],
            "database": st.secrets["mysql"]["database"]
        }
    except KeyError:
        st.error("Erro de Configuração: Credenciais MySQL não encontradas em st.secrets. Certifique-se de que 'secrets.toml' possui a seção [mysql].")
        return None

def check_existing_data(engine, ano_mes):
    """Verifica se já existem dados para o período (ANO_MES) na tabela de Cabeçalho."""
    st.info(f"Verificando existência de dados para {ano_mes}.")
    db_params = get_mysql_credentials() # Obtém as credenciais de forma segura
    
    if db_params is None:
        return False

    try:
        # Usa o conector MySQL puro para a verificação de contagem, usando db_params
        conn = mysql.connector.connect(**db_params) 
        cursor = conn.cursor()
        query = f"SELECT COUNT(*) FROM {TABLE_CABECALHO} WHERE ANO_MES = %s"
        cursor.execute(query, (ano_mes,))
        count = cursor.fetchone()[0]
        conn.close()
        return count > 0
    except Exception as e:
        # Retorna False se houver qualquer erro (incluindo falha de conexão)
        # st.error(f"Erro na verificação de dados existentes: {e}") # Opcional para debug
        return False

def update_ano_mes_on_success(table_name, ano_mes):
    """Atualiza a coluna ANO_MES (necessário devido à forma como os dados de teste são gerados)."""
    st.info(f"Atualizando campo ANO_MES na tabela {table_name} para '{ano_mes}'.")
    db_params = get_mysql_credentials() # Obtém as credenciais de forma segura
    
    if db_params is None:
        return

    try:
        # Conexão direta para a operação de UPDATE, usando db_params
        conn = mysql.connector.connect(**db_params)
        cursor = conn.cursor()
        update_query = f"UPDATE {table_name} SET ANO_MES = %s WHERE ANO_MES = %s"
        cursor.execute(update_query, (ano_mes, ano_mes))
        conn.commit()
        cursor.close()
        conn.close()
        st.success(f"Campo ANO_MES atualizado com sucesso na tabela {table_name}.")
    except Exception as e:
        st.error(f"Erro ao executar o UPDATE do ANO_MES na tabela {table_name}: {e}")

def update_mysql_on_failure(table_name, ano_mes):
    """Função de placeholder para indicar que a carga falhou (não faz nada real aqui)."""
    st.warning(f"Carga falhou. Nenhuma alteração final no registro de status na tabela {table_name}.")

def load_to_mysql(engine, df: pd.DataFrame, table_name: str, ano_mes: str, col_mapping: dict):
    """Carrega o DataFrame para a tabela MySQL especificada."""
    try:
        # Renomeia as colunas do DataFrame usando o mapeamento
        df.rename(columns=col_mapping, inplace=True)
        # Adiciona a coluna ANO_MES
        df['ANO_MES'] = ano_mes
        # Seleciona apenas as colunas mapeadas e 'ANO_MES'
        cols_to_keep = ['ANO_MES'] + list(col_mapping.values())
        df_final = df[[col for col in cols_to_keep if col in df.columns]]
        
        st.info(f"Iniciando carga na tabela '{table_name}'. Linhas: {len(df_final)}")
        
        # Uso do to_sql para inserção em massa
        df_final.to_sql(
            name=table_name,
            con=engine,
            if_exists='append',
            index=False # Não salva o índice do DataFrame
        )
        
        st.success(f"Carregamento da tabela '{table_name}' concluído com sucesso!")
        st.subheader(f"Primeiras 10 linhas da tabela '{table_name}' carregada:")
        st.dataframe(df_final.head(10))
        st.write(f"Total de linhas importadas: **{len(df_final)}**")
        return True, len(df_final)
    except Exception as e:
        st.error(f"Erro ao carregar dados na tabela '{table_name}'. Tipo de erro: {type(e).__name__}.")
        st.warning(f"Detalhe do erro: {e}")
        return False, 0

# ===============================
# 3. FUNÇÃO DE PARSING XML CORRIGIDA (Mantida)
# ===============================
def parse_xml_to_dataframe(xml_content, target_type):
    """Analisa o conteúdo XML para criar um DataFrame de Cabeçalho ou Itens."""
    try:
        root = ET.fromstring(xml_content)
        # Define a tag de registro e o mapeamento com base no tipo
        if target_type == 'Cabecalho':
            tag_registro = 'registro_cabecalho'
            col_map = COL_MAPPING_CABECALHO
        else:
            tag_registro = 'registro_item'
            col_map = COL_MAPPING_ITENS
            
        registros = root.findall(tag_registro)
        data = []
        
        # Extrai os dados dos elementos XML
        for record in registros:
            linha = {}
            for child in record:
                linha[child.tag] = child.text
            data.append(linha)
            
        df = pd.DataFrame(data)
        
        if df.empty:
            st.error(f"Erro no parsing XML. Nenhum registro encontrado com tag '{tag_registro}'.")
            return pd.DataFrame(columns=list(col_map.keys()))
            
        # Cria um DataFrame final apenas com as colunas esperadas
        df_final = pd.DataFrame()
        for internalcol, dbcol in col_map.items():
            df_final[internalcol] = df.get(internalcol, None)
            
        st.info(f"Parsing XML {target_type} concluído. Registros encontrados: {len(df_final)}")
        return df_final
        
    except Exception as e:
        st.error(f"Erro crítico ao processar XML. Falha: {e}")
        return None

# ============================
# 4. FUNÇÃO DE LEITURA DE ARQUIVO CSV/XML (Mantida)
# ============================
def fetch_files_from_github(ano_mes: str, file_format: str) -> dict:
    """Busca e carrega os arquivos de dados simulados do repositório GitHub."""
    ext = file_format.lower()
    file_cabecalho_name = f"{ano_mes}_NFs_Cabecalho.{ext}"
    file_itens_name = f"{ano_mes}_NFs_Itens.{ext}"
    base = GITHUB_RAW_URL_BASE
    url_cabecalho = f"{base}{file_cabecalho_name}"
    url_itens = f"{base}{file_itens_name}"
    results = {'found': False}
    
    try:
        st.info(f"Tentando buscar arquivos do GitHub ({ext.upper()}): {file_cabecalho_name} e {file_itens_name}...")
        df_cabecalho = None
        df_itens = None
        
        if ext == 'csv':
            # Leitura de CSV diretamente da URL
            df_cabecalho = pd.read_csv(url_cabecalho, header=None, skiprows=1)
            df_cabecalho.columns = COL_MAPPING_CABECALHO.keys()
            df_itens = pd.read_csv(url_itens, header=None, skiprows=1)
            df_itens.columns = COL_MAPPING_ITENS.keys()
            st.success(f"Arquivos CSV encontrados e carregados com sucesso do GitHub!")
            
        elif ext == 'xml':
            # Busca e parse de XML
            content_cabecalho = requests.get(url_cabecalho).content.decode('utf-8')
            content_itens = requests.get(url_itens).content.decode('utf-8')
            df_cabecalho = parse_xml_to_dataframe(content_cabecalho, 'Cabecalho')
            df_itens = parse_xml_to_dataframe(content_itens, 'Itens')
            
            if df_cabecalho is None or df_itens is None:
                st.error("Falha ao converter XML para DataFrame. Processo de ETL não pode prosseguir.")
                return {'found': False}
                
            st.success(f"Arquivos XML encontrados e convertidos para DataFrame com sucesso!")
            
        if df_cabecalho is not None and df_itens is not None and not df_cabecalho.empty and not df_itens.empty:
            results = {
                'cabecalho': df_cabecalho,
                'itens': df_itens,
                'found': True
            }
            return results
            
        st.error("Arquivos encontrados, mas estão vazios ou o formato não pôde ser lido corretamente.")
        return {'found': False}
        
    except Exception as e:
        st.error(f"Arquivos não encontrados! (Erro: {e})")
        return {'found': False}


# ============================
# 5. FUNÇÃO PRINCIPAL DA INTERFACE
# ============================
def app():
    # Configuração de layout para uso standalone
    st.set_page_config(layout="wide") 

    # Bloco de título (Logo e Texto)
    col_img, col_title = st.columns([1, 4])
    with col_img:
        st.image(URL_LOGO, width=100)
    with col_title:
        st.markdown("# 📊 Módulo de Carga e Análise Fiscal")
        st.markdown("---")
        st.markdown("Automatize a importação de Notas Fiscais (NF-e) para sua base de dados.")

    # --- Sidebar de Parâmetros ---
    st.sidebar.header("🎯 Parâmetros de Carga")
    
    file_type_input = st.sidebar.selectbox("Escolha o tipo de arquivo:", ("CSV", "XML"))
    
    ano_mes_input = st.sidebar.text_input(
        "Digite o Ano e Mês (Formato AAAAMM, ex: 202401):",
        value="202401",
        max_chars=6
    )

    # Botão "Executar Carga de Dados (ETL)"
    if st.sidebar.button("Executar Carga de Dados (ETL)"):
        st.session_state['run_process'] = True
    else:
        if 'run_process' not in st.session_state:
            st.session_state['run_process'] = False

    # Botão: "Voltar à Página Principal"
    st.sidebar.markdown("---")
    if st.sidebar.button("⬅️ Voltar à Página Principal", key="back_to_main_sidebar"):
        st.session_state['page'] = 'main'
        st.rerun()

    # --- Lógica de Processamento da Carga ---
    if ano_mes_input:
        if not ano_mes_input.isdigit() or len(ano_mes_input) != 6:
            st.error("❌ Erro de Input: Digite valores numéricos no formato AAAAMM (6 dígitos)!")
        else:
            ano = ano_mes_input[:4]
            mes = ano_mes_input[4:]
            engine = get_db_connection()
            
            if engine is None:
                st.stop()
            
            # 1. Checa Duplicidade
            if check_existing_data(engine, ano_mes_input):
                st.warning(f"⚠️ **Dados Já Carregados:** Os dados do mês de {mes}/{ano} já foram encontrados no banco de dados.")
                st.markdown("---")
                st.stop()
            
            st.success("✅ Verificação concluída: Período livre para carga.")
            
            # 2. Inicia o Processo ETL (se o botão 'Executar Carga' foi pressionado)
            if st.session_state.get('run_process', False):
                
                file_results = fetch_files_from_github(ano_mes_input, file_type_input)
                
                if file_results['found']:
                    st.header("2. 🚀 Processo de Carga no MySQL")
                    st.info("Carregando os dados das notas fiscais...")
                    total_rows_imported = 0
                    
                    # Carga da Tabela de Cabeçalho
                    st.markdown("#### Tabela: NFE_Cabecalho")
                    df_cabecalho = file_results['cabecalho']
                    success_cab, rows_cab = load_to_mysql(
                        engine,
                        df_cabecalho,
                        TABLE_CABECALHO,
                        ano_mes_input,
                        COL_MAPPING_CABECALHO
                    )
                    total_rows_imported += rows_cab
                    
                    if not success_cab:
                        update_mysql_on_failure(TABLE_CABECALHO, ano_mes_input)
                        st.error("❌ **FALHA CRÍTICA:** Processo de carga abortado devido a erro no Cabeçalho.")
                        st.stop()
                    else:
                        update_ano_mes_on_success(TABLE_CABECALHO, ano_mes_input)
                        
                    # Carga da Tabela de Itens
                    st.markdown("#### Tabela: NFE_Itens")
                    df_itens = file_results['itens']
                    success_itens, rows_itens = load_to_mysql(
                        engine,
                        df_itens,
                        TABLE_ITENS,
                        ano_mes_input,
                        COL_MAPPING_ITENS
                    )
                    total_rows_imported += rows_itens
                    
                    if not success_itens:
                        update_mysql_on_failure(TABLE_ITENS, ano_mes_input)
                        st.error("❌ **FALHA CRÍTICA:** Processo de carga abortado devido a erro nos Itens.")
                        st.stop()
                    else:
                        update_ano_mes_on_success(TABLE_ITENS, ano_mes_input)
                        
                    # Finalização
                    if success_cab and success_itens:
                        st.balloons()
                        st.success(f"🎉 **DADOS CARREGADOS COM SUCESSO!** Total de registros: **{total_rows_imported}**")
                        
    # =======================================================================
    # SOLUÇÃO CRÍTICA: Limpar caches para forçar a atualização em app_resultados.py
    # =======================================================================
                        # 1. Limpa o Agente de SQL (para usar o banco atualizado)
                        if 'fiscal_agent' in st.session_state:
                            del st.session_state.fiscal_agent
                        
                        # 2. Limpa o cache de dados do Streamlit (para atualizar o Dashboard)
                        st.cache_data.clear()
                        
                        st.info("✅ O Dashboard e o Agente de IA foram reinicializados. Retorne à página de Resultados para ver os novos dados.")
                        # =======================================================================
                        
                        st.markdown("---")
                        st.info(f"Processo ETL concluído para o período {mes}/{ano}.")
                        st.session_state['run_process'] = False

# Chamada de execução para uso modular
if __name__ == '__main__':

    app()



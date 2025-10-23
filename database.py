# database.py

# ==============================================================================
# RESUMO E FINALIDADE DO CÓDIGO:
#
# Este módulo gerencia toda a lógica de conexão com o banco de dados MySQL
# utilizando Streamlit Secrets e SQLAlchemy.
#
# Principais Funções:
# 1. Carrega as credenciais e constrói a URL de conexão (get_db_connection_url).
# 2. Inicializa o motor (Engine) do SQLAlchemy com resiliência (`@st.cache_resource`).
# 3. Fornece a função central (`load_data_from_mysql`) para carregar dados das
#    tabelas NFE_Cabecalho e NFE_Itens para DataFrames, realizando conversões de
#    tipo para garantir a integridade dos dados para análise.
# ==============================================================================

import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
import os
import mysql.connector # Garantindo que a biblioteca do conector está sendo usada

# --- Leitura Segura de Secrets ---

def get_db_connection_url():
    """Constrói a URL de conexão ao MySQL usando os secrets do Streamlit."""
    try:
        # Tenta obter a string completa (ideal para debug e fácil configuração)
        full_string = st.secrets.get("DB_CONNECTION_STRING")
        if full_string and 'SUA_SENHA_AQUI_DO_MYSQL' not in full_string:
            # Assume que a string completa foi definida corretamente no secrets.toml
            return full_string
        
        # Constrói a string a partir dos componentes
        host = st.secrets["mysql"]["host"]
        user = st.secrets["mysql"]["user"]
        password = st.secrets["mysql"]["password"]
        database = st.secrets["mysql"]["database"]
        
        # Formato de URL de conexão do SQLAlchemy
        # Usa 'mysql+mysqlconnector' para garantir que o driver correto seja utilizado
        return f"mysql+mysqlconnector://{user}:{password}@{host}:3306/{database}"
        
    except KeyError as e:
        # Erro se as chaves não estiverem no secrets.toml
        st.error(f"Erro: Credenciais do MySQL não encontradas em 'secrets.toml'. Verifique a chave: {e}")
        return None

# Constrói e retorna o motor de conexão (com correções de resiliência)
@st.cache_resource
def get_sql_engine():
    """
    Retorna o motor (Engine) do SQLAlchemy, configurado para resiliência de conexão.
    - pool_pre_ping=True: Verifica se a conexão está viva antes de usá-la.
    - pool_recycle=3600: Força a reconexão após 1 hora para evitar timeout do servidor.
    - connect_timeout=30: Aumenta o timeout para estabelecer a conexão inicial.
    """
    db_url = get_db_connection_url()
    if db_url:
        try:
            # Criação do Engine com parâmetros de resiliência e o driver 'mysqlconnector'
            engine = create_engine(
                db_url,
                pool_pre_ping=True,
                pool_recycle=3600,
                connect_args={
                    'connect_timeout': 30, # 30 segundos de timeout de conexão
                }
            )
            return engine
        except Exception as e:
            st.error(f"Erro ao criar o motor SQL: {e}")
            return None
    return None

def get_table_names():
    """Retorna os nomes das tabelas (incluindo as três novas) definidos nos secrets."""
    return (
        st.secrets.get("TABLE_CABECALHO", "NFE_Cabecalho"), 
        st.secrets.get("TABLE_ITENS", "NFE_Itens"),
        st.secrets.get("TABLE_PIS_COFINS", "PIS_COFINS"),
        st.secrets.get("TABLE_ICMS", "ICMS"),
        st.secrets.get("TABLE_NCM_TPI", "NCM_TPI")
    )

# **MODIFICAÇÃO AQUI: ADICIONANDO O CACHE DE DADOS**
@st.cache_data(ttl=3600)
# Função para carregar dados do MySQL para DataFrame (Usado no Dashboard)
def load_data_from_mysql(table_name):
    """Carrega todos os dados de uma tabela específica para um DataFrame, aplicando conversões de tipo."""
    engine = get_sql_engine()
    if engine:
        try:
            # Consulta SQL para carregar a tabela
            query = f"SELECT * FROM {table_name}"
            
            # Usando pd.read_sql para carregar dados
            df = pd.read_sql(query, engine)
            
            # --- Conversão de Tipos para Análise (Garante Integridade) ---
            if 'DATA_EMISSAO' in df.columns:
                df['DATA_EMISSAO'] = pd.to_datetime(df['DATA_EMISSAO'], errors='coerce')
            
            # Colunas de valor, forçamos para numérico
            if 'VALOR_NOTA_FISCAL' in df.columns:
                df['VALOR_NOTA_FISCAL'] = pd.to_numeric(df['VALOR_NOTA_FISCAL'], errors='coerce')
            if 'VALOR_TOTAL' in df.columns:
                # O 'VALOR_TOTAL' do item é usado para agregação
                df['VALOR_TOTAL'] = pd.to_numeric(df['VALOR_TOTAL'], errors='coerce')
            if 'QUANTIDADE' in df.columns:
                # Cria uma coluna numérica para a quantidade a partir da coluna 'QUANTIDADE'
                df['QUANTIDADE_NUM'] = pd.to_numeric(df['QUANTIDADE'].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
                
            return df
        except Exception as e:
            st.error(f"Erro ao carregar dados da tabela {table_name}: {e}")
            return pd.DataFrame()
    return pd.DataFrame()
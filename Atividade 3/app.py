# app.py

import os
import sqlite3
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
import zipfile
from io import TextIOWrapper

from gemini_llm import GeminiLLM
from langchain_community.utilities import SQLDatabase
# from langchain_core.prompts import PromptTemplate
from langchain_community.agent_toolkits.sql.base import create_sql_agent
from langchain.agents.agent_types import AgentType
from langchain_community.agent_toolkits import SQLDatabaseToolkit

# 1. Carregar variáveis de ambiente (.env)
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    st.error("⚠️ Defina a variável GEMINI_API_KEY no seu arquivo .env")
    st.stop()

# 2. Ler os CSVs em DataFrames Pandas
@st.cache_data(show_spinner=False)
def carregar_dados():
    zip_path = "./202401_NFs.zip"
    # nomes exatos dos arquivos dentro do ZIP
    cab_name   = "202401_NFs_Cabecalho.csv"
    itens_name = "202401_NFs_Itens.csv"

    with zipfile.ZipFile(zip_path, "r") as z:
        # lê o CSV de cabeçalho
        with z.open(cab_name) as f_cab:
            df_cab = pd.read_csv(
                TextIOWrapper(f_cab, encoding="utf-8"),
                sep=",",
                decimal=".",
                parse_dates=["DATA EMISSÃO", "DATA/HORA EVENTO MAIS RECENTE"],
                dayfirst=False,
            )
        # lê o CSV de itens
        with z.open(itens_name) as f_itens:
            df_itens = pd.read_csv(
                TextIOWrapper(f_itens, encoding="utf-8"),
                sep=",",
                decimal=".",
                parse_dates=["DATA EMISSÃO"],
                dayfirst=False,
            )
    return df_cab, df_itens


df_cabecalho, df_itens = carregar_dados()

# 3. Criar SQLite em arquivo e injetar as tabelas
@st.cache_resource(show_spinner=False)
def criar_database_sql():
    conn = sqlite3.connect("database_temp.db", check_same_thread=False)
    df_cabecalho.to_sql("cabecalho", conn, index=False, if_exists="replace")
    df_itens.to_sql("itens", conn, index=False, if_exists="replace")
    return conn

conn = criar_database_sql()

# 4. Configurar LangChain SQLDatabase + Agente
db = SQLDatabase.from_uri("sqlite:///database_temp.db")

# Modelos disponíveis
modelos_disponiveis = [
    "gemini-2.0-flash",
    "gemini-1.5-flash",
    "gemini-1.5-flash-8b",
    "gemma-3-27b-it"
]

# 5. Streamlit Interface
st.set_page_config(page_title="Consulta NF-e (Jan/2024)", page_icon="🧾", layout="wide")
st.title("🧾 Consulta a Notas Fiscais (Janeiro/2024)")

modelo_selecionado = st.selectbox("Selecione o modelo:", modelos_disponiveis)

llm = GeminiLLM(
    api_key=API_KEY,
    model_name=modelo_selecionado,
    temperature=0,
)

toolkit = SQLDatabaseToolkit(db=db, llm=llm)

agent = create_sql_agent(
    llm=llm,
    toolkit=toolkit,
    agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=False,
)

if "history" not in st.session_state:
    st.session_state.history = []

st.markdown(
    """
    Faça perguntas em linguagem natural sobre as 100 NF-e de janeiro/2024.
    Exemplos de perguntas:
    - “Qual a soma total dos valores dos itens para cada NF?”  
    - “Liste as notas cujo valor total (campo `valor_total`) seja maior que 50.000.”  
    - “Quantas notas foram emitidas em 2024-01-15?”  
    - “Mostre os cinco fornecedores com maior quantidade de itens adquiridos.”  
    """
)

col1, col2 = st.columns([3, 1])
with col1:
    pergunta = st.text_input("🖋️ Faça sua pergunta:")
    if st.button("Enviar"):
        if pergunta.strip():
            resposta = agent.run(pergunta)
            st.session_state.history.append({"role": "user", "content": pergunta})
            st.session_state.history.append({"role": "assistant", "content": resposta})
        
            st.text_area(
                "Resposta do Agente:",
                value=resposta,
                height=200,
                disabled=True,
            )
        
        else:
            st.warning("Digite uma pergunta.")

# Histórico de conversas
st.markdown("---")
st.subheader("💬 Histórico")
for msg in st.session_state.history[-10:]:
    autor = "Você" if msg["role"] == "user" else "Agente"
    st.markdown(f"**{autor}:** {msg['content']}")

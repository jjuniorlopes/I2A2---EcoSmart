# ==============================================================================
# RESUMO E FINALIDADE DO CÓDIGO:
#
# Este é o arquivo principal (Página Inicial e Roteador) da aplicação Streamlit.
# Sua principal função é:
# 1. Configurar o layout 'wide' e aplicar o fundo customizado (set_background).
# 2. Exibir a página de apresentação (`show_main_page`), que detalha o
#    propósito do projeto (EcoSmart), a arquitetura (Python, LangChain, MySQL, Gemini)
#    e a equipe, utilizando DataFrames para melhor visualização das tabelas.
# 3. Gerenciar a navegação entre as diferentes seções da aplicação (Carga de NF-e
#    e Resultados/Insights) utilizando o `st.session_state` como um roteador
#    simples. Ele importa e chama as funções `app()` dos outros módulos (`app_carga.py`
#    e `app_resultados.py`).
# ==============================================================================

import streamlit as st
import base64
import os
import pandas as pd 

# 1. Configuração de Layout e Fundo
# ==============================================================================

# Adiciona a configuração de layout 'wide' para ocupar o espaço do navegador
st.set_page_config(layout="wide") 

# CÓDIGO CSS PARA ESTILIZAÇÃO DOS BOTÕES
BUTTON_STYLE = """
<style>
/* Estilo geral para botões principais (Carga e Agente) */
div.stButton > button {
    background-color: #666666 !important; /* Cinza */
    color: white !important;             /* Texto branco */
    border: none;
    border-radius: 5px;
    padding: 10px 20px;
    font-size: 16px;
    transition: background-color 0.2s;
}

/* Efeito hover */
div.stButton > button:hover {
    background-color: #444444 !important; /* Cinza mais escuro no hover */
    color: white !important;
}

/* Estilo específico para botões na barra lateral (Voltar) */
div[data-testid="stSidebarContent"] div.stButton button {
    background-color: #666666 !important;
    color: white !important;
    border: none !important; 
    padding: 10px 10px !important;
}
</style>
"""
st.markdown(BUTTON_STYLE, unsafe_allow_html=True)


# CÓDIGO PARA CONFIGURAR IMAGEM DE FUNDO VIA CSS
# =================================================
def set_background(image_file):
    """
    Injeta CSS customizado no Streamlit para usar uma imagem local como fundo.
    """
    try:
        # Tenta abrir e codificar a imagem de fundo
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
        # Exibe um aviso se o arquivo de fundo não for encontrado
        st.warning(f"Aviso Visual: Arquivo 'fundo.jpg' não encontrado. Usando fundo padrão do Streamlit.")

# Tenta aplicar o fundo ao iniciar a aplicação
# Nota: Assumindo que 'fundo.jpg' existe no diretório
set_background('fundo.jpg') 

# URL do logo (assumindo que 'logo.jpg' está no mesmo diretório)
URL_LOGO = 'logo.jpg'

# Função para exibir a página principal
def show_main_page():
    col_img, col_title = st.columns([1, 4])
    with col_img:
        st.image(URL_LOGO, width=100)
    with col_title:
        st.markdown("# Desafio-Final")
        st.markdown("MVP (Curso I2A2) de Automação Inteligente de NFs. O projeto foca na integração de dados fiscais (SEFAZ ↔ ERPs de PMEs) usando Python, LangChain e MySQL. O MVP simula a extração de NFs (CSV/XML) para o MySQL e utiliza um Agente LLM (Gemini 2.5 Flash) para facilitar a análise e o gerenciamento eficiente dos dados fiscais.")
    
    st.markdown("## 🤖 EcoSmart: Automação Inteligente da Emissão e Análise de Notas Fiscais (NFs)")
    
    # MODIFICAÇÃO DE BADGES: Mantidos na mesma linha
    badges = """
    [![Licença MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
    [![Python](https://img.shields.io/badge/Python-3.9%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
    [![LangChain](https://img.shields.io/badge/LangChain-v0.1.0%2B-green?logo=chainlink&logoColor=white)](https://www.langchain.com/)
    [![MySQL](https://img.shields.io/badge/MySQL-Database-orange?logo=mysql&logoColor=white)](https://www.mysql.com/)
    [![Google Gemini](https://img.shields.io/badge/Google_Gemini-2.5_Flash-4285F4?logo=google&logoColor=white)](https://ai.google.dev/gemini)
    """
    st.markdown(badges, unsafe_allow_html=True)
    
    st.markdown("Este projeto foi desenvolvido pela equipe **EcoSmart** como o MVP (Produto Mínimo Viável) final do **Curso Agentes Autônomos com Redes Generativas** (I2A2).")
    
    st.markdown("---")
    
    st.markdown("### 💡 Ideia do Projeto (O Desafio)")
    st.markdown("O projeto visa criar um protótipo de solução para **automatizar a integração de dados fiscais (Notas Fiscais - NFs)** entre as Secretarias da Fazenda (SEFAZ) e os ERPs de pequenas e médias empresas. O principal objetivo é facilitar a **análise e o gerenciamento eficiente** dos dados de NFs, liberando profissionais de tarefas rotineiras e complexas através da automação inteligente.")
    
    st.markdown("### 🎯 Tema do Projeto Final (Curso I2A2)")
    st.markdown("O trabalho final aborda a criação de **Ferramentas Gerenciais** com foco nos seguintes tópicos, diretamente endereçados pela arquitetura do nosso MVP:")
    
    st.markdown("#### 1. Relatórios Personalizados")
    st.markdown("**Geração de relatórios personalizados:** Possibilidade de criar relatórios com informações relevantes para o setor.")
    st.markdown("**Utilizar informações internas:** Análise baseada nos dados de NFs coletadas e emitidas e armazenados no MySQL.")
    st.markdown("**Agregar informações externas relevantes:** Novos módulos (ex: análise de conformidade, geração de relatórios personalizados) podem ser facilmente integrados.")
    st.markdown("**Análises preditivas e simulações de cenários:** O armazenamento seguro e estruturado no MySQL permite análises gerenciais e auditorias eficientes.")
    
    st.markdown("#### 2. Assistente Consultor Especializado")
    st.markdown("**Suporte para dúvidas e decisões estratégicas:** O **Agente Especialista de Dados Fiscais** atua como um consultor virtual, processando solicitações de emissão e validação de NFs e interagindo com sistemas externos automaticamente.")
    st.markdown("**Informações sobre contabilidade e tributação:** O LLM (`gemini-2.5-flash`) é orquestrado pela LangChain para processar e responder com informações sobre as regras brasileiras e linguagem fiscal.")
    
    st.markdown("#### 3. Desafios Abordados")
    st.markdown("**Qualidade das Informações:** Garantida pela validação automatizada de informações nos pipelines de processamento e pelos testes de validação dos agentes LLM.")
    st.markdown("**Experiência do Usuário:** Maximizada pelo uso de agentes autônomos que interpretam instruções em linguagem natural.")
    
    st.markdown("### 🏗️ Estratégia do Agente de SQL (Text-to-SQL)")
    
    # CONSTRUÇÃO DA NOVA TABELA COM DATAFRAME
    data_estrategia_agente = {
        "Componente da Estratégia": [
            "Modelo Central",
            "Framework de Orquestração",
            "Persona e Diretiva",
            "Instrução de Qualidade de Dados",
            "Memória",
            "Visualização de Dados",
            "Base de Conhecimento"
        ],
        "Tecnologia Chave": [
            "Gemini 2.5 Flash",
            "LangChain (SQL Agent)",
            "Prompt de Sistema",
            "Prompt de Sistema (CAST)",
            "ConversationBufferWindowMemory",
            "Instrução JSON",
            "MySQL (tabelas NFE)"
        ],
        "Resumo da Função": [
            "Atua como a inteligência central, convertendo a pergunta do usuário em linguagem natural em uma consulta SQL otimizada.",
            "Gerencia o fluxo de trabalho 'Text-to-SQL', fornecendo as ferramentas necessárias para interagir com o MySQL.",
            "Define o LLM como um 'Especialista Tributário e Consultor Fiscal'.",
            "Força o Agente a usar funções como CAST() nas colunas de valor para garantir que os cálculos sejam feitos corretamente.",
            "Mantém o contexto das 5 conversas anteriores, permitindo que o Agente responda a perguntas subsequentes (ex: 'E o valor médio deles?').",
            "Direciona o Agente a retornar os dados para gráficos (rankings ou 'top X') exclusivamente no formato JSON estruturado.",
            "Serve como a única fonte de dados para o Agente gerar insights e responder às consultas fiscais."
        ]
    }
    df_estrategia_agente = pd.DataFrame(data_estrategia_agente)
    # Exibe a tabela Estratégia do Agente no formato Streamlit DataFrame
    st.dataframe(df_estrategia_agente, hide_index=True, use_container_width=True)
    
    st.markdown("---")
    
    st.markdown("### 👥 Equipe EcoSmart")
    
    # CONSTRUÇÃO DA SEGUNDA TABELA COM DATAFRAME
    data_equipe = {
        "Nome": ["Jair", "Rogério", "Robson", "Javan"],
        "E-mail": ["jjuniorlopes@gmail.com", "rogerio.batista.teixeira@gmail.com", "santos.robson@gmail.com", "javanoalmeida@gmail.com"]
    }
    df_equipe = pd.DataFrame(data_equipe)
    st.dataframe(df_equipe, hide_index=True, use_container_width=True)

    
    st.markdown("---")
    
    st.markdown("### 📜 Licença")
    st.markdown("Este projeto está licenciado sob a **Licença MIT** - veja o arquivo [LICENSE](LICENSE) para mais detalhes.")
    
    st.markdown("## Funcionalidades")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Carga de NF-e"): 
            st.session_state.page = 'carga'
            st.rerun()
    with col2:
        if st.button("Fale com o Agente Especialista"): 
            st.session_state.page = 'resultados'
            st.rerun()

# Inicializa o estado da página se ainda não estiver definido
if 'page' not in st.session_state:
    st.session_state.page = 'main'

# Lógica de roteamento
if st.session_state.page == 'main':
    show_main_page()
elif st.session_state.page == 'carga':
    import app_carga
    app_carga.app() 
elif st.session_state.page == 'resultados':
    import app_resultados
    app_resultados.app()

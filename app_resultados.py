# app_resultados.py

# ==============================================================================
# RESUMO E FINALIDADE DO CÓDIGO:
#
# Este módulo é a página de "Resultados e Insights" da aplicação, focada em:
# 1. Exibir um Dashboard Gerencial completo com KPIs e gráficos dinâmicos.
# 2. IMPLEMENTAR NOVO CÁLCULO DE IMPOSTOS (PIS/COFINS, ICMS, IPI) utilizando
#    as novas tabelas auxiliares (ICMS, PIS_COFINS, NCM_TPI) para um cálculo
#    mais preciso.
# 3. Adicionar novos gráficos (Total Impostos por UF e Comparativo Totais).
# 4. Fornecer a interface para o Agente LLM (Gemini 2.5 Flash).
# ==============================================================================

import streamlit as st
import pandas as pd
import plotly.express as px
import json  
import os
import io
import numpy as np

# Importa módulos de conexão e agente
from database import load_data_from_mysql, get_table_names
from llm_agent import initialize_sql_agent, run_fiscal_analysis

# FATOR DE IMPOSTO CALCULADO (32.25%) - VARIÁVEL ANTIGA, IGNORADA PELO NOVO CÁLCULO
TAX_RATE_FACTOR = 0.3225 

# Definição dos Ícones para uso na interface
AGENT_ICON = "🤖" 
USER_ICON = "🙋" 
DASHBOARD_ICON = "📊" 
KPI_ICON = "📈"
TABLE_ICON = "📋"
REPORT_ICON = "🗺️"
AUDIT_ICON = "📑"
INSIGHT_ICON = "🧠"


# --- 1. FUNÇÕES DE SUPORTE ---

def format_brl(value):
    """Formata um valor float para a moeda brasileira (R$ X.XXX,XX) com separador de milhar."""
    if pd.isna(value):
        return "R$ 0,00"
    # Adicionado tratamento para garantir separador de milhar (.) e decimal (,)
    return "R$ {:,.2f}".format(value).replace(",", "X").replace(".", ",").replace("X", ".")

def render_visualization_or_text(response_output, user_question):
    """
    Decide se o output do LLM deve ser renderizado como gráfico (se for JSON estruturado)
    ou como texto simples.
    """
    
    # 1. Tentar detectar o formato JSON para plotagem
    try:
        data = json.loads(response_output)
        
        # Tenta extrair dados do formato estruturado ou array de objetos
        if isinstance(data, dict) and "graph_data" in data and isinstance(data["graph_data"], list):
            df_plot = pd.DataFrame(data["graph_data"])
        elif isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
            df_plot = pd.DataFrame(data)
        else:
            raise ValueError("Formato JSON não reconhecido para plotagem.")

        # --- Lógica de Plotagem Comum ---
        if not df_plot.empty and len(df_plot.columns) >= 2:
            col_x = df_plot.columns[0]
            col_y = df_plot.columns[1]
            
            fig = px.bar(
                df_plot, 
                x=col_y, # Valor no eixo X (para barras horizontais)
                y=col_x, # Categoria no eixo Y
                orientation='h',
                title=f"Visualização de Dados Fiscais: {user_question}",
                labels={col_x: col_x.replace('_', ' ').title(), col_y: col_y.replace('_', ' ').title()}
            )
            fig.update_layout(yaxis={'categoryorder':'total ascending'})
            
            st.plotly_chart(fig, use_container_width=True)
            st.success("Gráfico gerado com sucesso a partir dos dados estruturados pelo Agente.")
            return
        
    except (json.JSONDecodeError, ValueError):
        pass # Não é JSON ou falhou na conversão/estrutura, trata como texto abaixo
    except Exception as e:
        st.error(f"Erro ao tentar renderizar o gráfico a partir do JSON. Detalhe: {e}")
        
    # 3. Se não for gráfico (JSON), exibe a resposta como texto
    st.subheader(f"Resposta do Especialista: {AGENT_ICON}")
    st.write(response_output)

# --- 2. CARREGAMENTO E PRÉ-PROCESSAMENTO DOS DADOS PARA O DASHBOARD ---

@st.cache_data(ttl=3600)
def get_dashboard_data():
    """
    Carrega dados do MySQL para o Dashboard, recalcula impostos
    com base nas novas tabelas auxiliares e prepara o CFOP.
    """
    # Carrega as tabelas principais e auxiliares
    TABLES = get_table_names()
    df_cabecalho = load_data_from_mysql(TABLES[0])
    df_itens = load_data_from_mysql(TABLES[1])
    
    if df_cabecalho.empty or df_itens.empty:
        return None, None
    
    # Carrega as novas tabelas auxiliares (assumindo que estão na ordem correta na tupla TABLES)
    # [2] = PIS_COFINS, [3] = ICMS, [4] = NCM_TPI
    df_pis_cofins = load_data_from_mysql(TABLES[2])
    df_icms = load_data_from_mysql(TABLES[3])
    df_ncm_tpi = load_data_from_mysql(TABLES[4])
    
    # Pré-processamento e Limpeza de Valores (Mantido)
    df_cabecalho['VALOR_NOTA_FISCAL'] = pd.to_numeric(
        df_cabecalho['VALOR_NOTA_FISCAL'].astype(str).str.replace(',', '.'), errors='coerce'
    ).fillna(0)
    
    df_itens['VALOR_TOTAL_ITEM'] = pd.to_numeric(
        df_itens['VALOR_TOTAL'].astype(str).str.replace(',', '.'), errors='coerce'
    ).fillna(0)
    
    df_itens['QUANTIDADE_NUM'] = pd.to_numeric(
        df_itens['QUANTIDADE'].astype(str).str.replace(',', '.'), errors='coerce'
    ).fillna(0)

    # ==============================================================
    # INÍCIO: NOVO CÁLCULO DE IMPOSTOS (ICMS, PIS/COFINS, IPI)
    # ==============================================================

    # Função auxiliar para normalizar alíquotas (divide por 100 se > 1)
    def normalize_aliquota(aliquota):
        # Esta função corrige o problema onde 18.00 (percentual) é lido e tratado como 18 (decimal)
        return aliquota / 100.0 if aliquota > 1.0 else aliquota

    # 1. PIS/COFINS (Aplicação no Valor Total da Nota * PIS_COFINS.VALOR)
    aliquota_pis_cofins_raw = df_pis_cofins['VALOR'].mean() if not df_pis_cofins.empty and 'VALOR' in df_pis_cofins.columns else 0.0925
    aliquota_pis_cofins = normalize_aliquota(aliquota_pis_cofins_raw)
    
    df_cabecalho['VALOR_PIS_COFINS'] = df_cabecalho['VALOR_NOTA_FISCAL'] * aliquota_pis_cofins
    df_cabecalho['VALOR_PIS_COFINS'].fillna(0, inplace=True)


    # 2. ICMS (Aplicação no Valor Total da Nota * ICMS.ALIQUOTA [por UF Emitente])
    df_cabecalho['VALOR_ICMS'] = 0.0
    if not df_icms.empty and 'SIGLA' in df_icms.columns and 'ALIQUOTA' in df_icms.columns:
        # Mapeia a alíquota ICMS pela UF Emitente (SIGLA)
        icms_map = df_icms.set_index('SIGLA')['ALIQUOTA'].apply(normalize_aliquota).to_dict()
        # Aplica a alíquota no cabeçalho
        df_cabecalho['ICMS_ALIQUOTA'] = df_cabecalho['UF_EMITENTE'].map(icms_map).fillna(0)
        df_cabecalho['VALOR_ICMS'] = df_cabecalho['VALOR_NOTA_FISCAL'] * df_cabecalho['ICMS_ALIQUOTA']
        df_cabecalho.drop(columns=['ICMS_ALIQUOTA'], errors='ignore', inplace=True)
    df_cabecalho['VALOR_ICMS'].fillna(0, inplace=True)
    
    
    # 3. IPI (Aplicação no Valor Total do Item * NCM_TPI.ALIQUOTA [por NCM])
    df_itens['VALOR_IPI'] = 0.0
    if not df_ncm_tpi.empty and 'NCM' in df_ncm_tpi.columns and 'ALIQUOTA' in df_ncm_tpi.columns:
        
        # 1. Preparação para Merge
        df_itens['NCM_NUM'] = pd.to_numeric(df_itens['CODIGO_NCM_SH'], errors='coerce').fillna(0).astype(int)
        df_ncm_tpi['NCM_KEY'] = pd.to_numeric(df_ncm_tpi['NCM'], errors='coerce').fillna(0).astype(int)
        
        # 2. Normaliza a alíquota NCM e faz o merge para trazer a IPI_ALIQUOTA para a tabela de itens
        ncm_aliquota_map = df_ncm_tpi.set_index('NCM_KEY')['ALIQUOTA'].apply(normalize_aliquota).to_dict()
        df_itens['IPI_ALIQUOTA'] = df_itens['NCM_NUM'].map(ncm_aliquota_map).fillna(0)
        
        # 3. Calcula o IPI no nível do item
        df_itens['VALOR_IPI'] = df_itens['VALOR_TOTAL_ITEM'] * df_itens['IPI_ALIQUOTA']
        df_itens['VALOR_IPI'].fillna(0, inplace=True)
        
        # 4. Limpeza das colunas auxiliares
        df_itens.drop(columns=['NCM_NUM', 'IPI_ALIQUOTA'], errors='ignore', inplace=True) 

    
    # Agrega IPI do item para o Cabeçalho (PIS/COFINS e ICMS já estão no cabeçalho)
    imposto_ipi_por_nota = df_itens.groupby('CHAVE_DE_ACESSO')['VALOR_IPI'].sum().reset_index()
    imposto_ipi_por_nota.rename(columns={'VALOR_IPI': 'TOTAL_IPI_ITENS'}, inplace=True)
    
    # Merge com o Cabeçalho para ter o total de IPI
    df_cabecalho = pd.merge(
        df_cabecalho,
        imposto_ipi_por_nota[['CHAVE_DE_ACESSO', 'TOTAL_IPI_ITENS']],
        on='CHAVE_DE_ACESSO',
        how='left'
    )
    df_cabecalho['TOTAL_IPI_ITENS'] = df_cabecalho['TOTAL_IPI_ITENS'].fillna(0)
    
    # VALOR TOTAL DE IMPOSTOS (VALOR_IMPOSTOS) = PIS/COFINS + ICMS + IPI
    df_cabecalho['VALOR_IMPOSTOS'] = (
        df_cabecalho['VALOR_PIS_COFINS'] + 
        df_cabecalho['VALOR_ICMS'] + 
        df_cabecalho['TOTAL_IPI_ITENS']
    )
    
    # Remove colunas auxiliares temporárias do cabeçalho
    df_cabecalho.drop(columns=['VALOR_PIS_COFINS', 'VALOR_ICMS', 'TOTAL_IPI_ITENS'], errors='ignore', inplace=True)
    
    # FIM: NOVO CÁLCULO DE IMPOSTOS
    # ==============================================================

    # Cria a coluna de tipo de operação (Interna vs Interestadual) (Mantido)
    df_cabecalho['TIPO_OPERACAO'] = df_cabecalho.apply(
        lambda row: 'Interna' if row['UF_EMITENTE'] == row['UF_DESTINATARIO'] else 'Interestadual', 
        axis=1
    )
    
    # --- CARREGAMENTO E MERGE DA TABELA CFOP --- (Mantido)
    try:
        cfop_file_path = "CFOP.csv" 
        
        if not os.path.exists(cfop_file_path):
            df_itens['DESCRICAO_TRUNCADA'] = df_itens['CFOP'].astype(str)
        else:
            # Leitura do CSV do CFOP para mapeamento
            df_cfop_map = pd.read_csv(
                cfop_file_path, 
                dtype={'CFOP': str}, 
                encoding='latin1',
                sep=';', 
                quotechar='"',
                on_bad_lines='skip' 
            ) 
            
            df_cfop_map.columns = ['CFOP', 'DESCRICAO']
            df_itens['CFOP'] = pd.to_numeric(df_itens['CFOP'], errors='coerce').fillna(0).astype(int).astype(str)
            df_cfop_map['CFOP'] = df_cfop_map['CFOP'].astype(str)
            
            # Truncagem da Descrição para caber nos gráficos
            df_cfop_map['DESCRICAO_TRUNCADA'] = df_cfop_map['DESCRICAO'].str.slice(0, 40) + '...'
            
            # Realiza o Merge com a tabela de itens
            df_itens = pd.merge(
                df_itens,
                df_cfop_map[['CFOP', 'DESCRICAO_TRUNCADA']],
                on='CFOP',
                how='left'
            )
            df_itens['DESCRICAO_TRUNCADA'].fillna('CFOP Não Encontrado', inplace=True) 

    except Exception as e:
        df_itens['DESCRICAO_TRUNCADA'] = df_itens['CFOP'].astype(str) 
    
    return df_cabecalho, df_itens

# --- Função Principal 'app()' ---

def app():
    # Carregamento dos dados
    df_cabecalho, df_itens = get_dashboard_data()

    # --- Configurações Iniciais ---
    try:
        st.set_page_config(layout="wide", page_title="FiscalIA: Análise Fiscal Inteligente", initial_sidebar_state="expanded")
    except st.errors.StreamlitAPIException:
        pass # Ignora se já foi chamado

    # NOVO BOTÃO DE VOLTAR À PÁGINA PRINCIPAL
    if st.button("⬅️ Voltar à Página Principal", key="back_to_main"):
        # Lógica de navegação para a página 'main' no script principal
        st.session_state['page'] = 'main'
        st.rerun() 

    st.title("Resultados/Insights e Agente Inteligente")
    st.markdown("---")

    # --- 3. PAINEL DE DASHBOARD CENTRAL (Visão Geral - Pré-LLM) ---

    st.header(f"{DASHBOARD_ICON} 1. Painel Gerencial (Visão Geral da NF)")

    if df_cabecalho is not None:
        
        # #############################################################
        # 3.1 Geração de KPIs (Painel de Indicadores)
        # #############################################################
        st.subheader(f"{KPI_ICON} Resumo/Painel de Indicadores Insights Fiscais/Gerenciais")
        
        # Cálculos de Totais e Médias (necessários para KPIs e Gráfico 10)
        total_bruto = df_cabecalho['VALOR_NOTA_FISCAL'].sum()
        total_impostos = df_cabecalho['VALOR_IMPOSTOS'].sum()
        qtde_total_nfs = len(df_cabecalho)
        valor_medio = total_bruto / qtde_total_nfs if qtde_total_nfs > 0 else 0
        
        # Cálculos de Valor Médio por Tipo de Operação
        df_medio_op = df_cabecalho.groupby('TIPO_OPERACAO')['VALOR_NOTA_FISCAL'].mean()
        valor_medio_interna = df_medio_op.get('Interna', 0)
        valor_medio_interestadual = df_medio_op.get('Interestadual', 0)

        df_itens_por_nota = df_itens.groupby('CHAVE_DE_ACESSO')['NUMERO_PRODUTO'].count().reset_index()
        num_medio_itens = df_itens_por_nota['NUMERO_PRODUTO'].mean() if not df_itens_por_nota.empty else 0
        
        nfs_anomalias = df_cabecalho[df_cabecalho['EVENTO_RECENTE'].astype(str).str.contains('Cancelada|Rejeitada', case=False, na=False)]
        qtde_anomalias = len(nfs_anomalias)
        percentual_anomalias = (qtde_anomalias / qtde_total_nfs) * 100 if qtde_total_nfs > 0 else 0
        
        # Exibição dos KPIs em 5 colunas (títulos encurtados)
        col_kpi1, col_kpi2, col_kpi3, col_kpi4, col_kpi5 = st.columns(5)
        
        # OTIMIZAÇÃO DE ESPAÇO E NOMES CONFORME REQUISITADO:
        with col_kpi1:
            st.metric("Total Faturado", format_brl(total_bruto))
        with col_kpi2:
            st.metric("Quantidade NFe", f"{qtde_total_nfs:,}") # Renomeado
        with col_kpi3:
            st.metric("Valor Tributado", format_brl(total_impostos)) # Substituído Vl. Médio Geral por Valor Tributado (total_impostos)
        with col_kpi4:
            st.metric("Média NFe Internas", format_brl(valor_medio_interna)) # Renomeado
        with col_kpi5:
            st.metric("Média NFe Interestadual", format_brl(valor_medio_interestadual)) # Renomeado

        st.markdown("---")
        
        # #############################################################
        # 3.2 Geração de Gráficos (Organização 2x4)
        # #############################################################
        st.subheader(f"{DASHBOARD_ICON} Gráficos")
        
        # --- LINHA 1: Top Clientes vs Top Produtos ---
        col_g1, col_g2 = st.columns(2)
        
        # GRÁFICO 1: Top 10 Clientes por Valor Faturado
        with col_g1:
            df_top_clientes = df_cabecalho.groupby('NOME_DESTINATARIO')['VALOR_NOTA_FISCAL'].sum().nlargest(10).sort_values(ascending=True).reset_index()
            
            fig1 = px.bar(
                df_top_clientes, 
                y='NOME_DESTINATARIO', 
                x='VALOR_NOTA_FISCAL', 
                color='NOME_DESTINATARIO', 
                orientation='h', 
                title='Top 10 Clientes por Valor Faturado',
                labels={'VALOR_NOTA_FISCAL': 'Valor Total (R$)', 'NOME_DESTINATARIO': 'Cliente/Destinatário'}
            )
            fig1.update_layout(yaxis={'categoryorder':'total ascending'}, showlegend=False, height=400)
            st.plotly_chart(fig1, use_container_width=True)
            st.caption("Motivo: Identificar a concentração de mercado e principais parceiros.")

        # GRÁFICO 2: Top 5 Produtos/Serviços por Valor
        with col_g2:
            df_top_produtos = df_itens.groupby('DESCRICAO_PRODUTO_SERVICO')['VALOR_TOTAL_ITEM'].sum().nlargest(5).reset_index()
            
            fig2 = px.bar(
                df_top_produtos, 
                x='VALOR_TOTAL_ITEM', 
                y='DESCRICAO_PRODUTO_SERVICO', 
                orientation='h',
                color='DESCRICAO_PRODUTO_SERVICO', 
                title='Top 5 Produtos/Serviços por Valor',
                labels={'VALOR_TOTAL_ITEM': 'Valor Total (R$)', 'DESCRICAO_PRODUTO_SERVICO': 'Produto/Serviço'}
            )
            fig2.update_layout(yaxis={'categoryorder':'total ascending'}, showlegend=False, height=400)
            st.plotly_chart(fig2, use_container_width=True)
            st.caption("Motivo: Análise de rentabilidade e foco estratégico de vendas.")


        # --- LINHA 2: Evolução Mensal vs Distribuição CFOP ---
        col_g3, col_g4 = st.columns(2)
        
        # GRÁFICO 3: Evolução do Valor Total de Notas Emitidas por Mês
        with col_g3:
            df_cabecalho['ANO_MES_EMISSAO'] = df_cabecalho['DATA_EMISSAO'].dt.to_period('M').astype(str)
            df_evolucao = df_cabecalho.groupby('ANO_MES_EMISSAO')['VALOR_NOTA_FISCAL'].sum().reset_index()
            
            fig3 = px.line(
                df_evolucao, 
                x='ANO_MES_EMISSAO', 
                y='VALOR_NOTA_FISCAL', 
                title='Evolução Mensal do Faturamento Bruto',
                labels={'ANO_MES_EMISSAO': 'Mês de Emissão', 'VALOR_NOTA_FISCAL': 'Valor Total (R$)'},
                markers=True
            )
            fig3.update_layout(height=400)
            st.plotly_chart(fig3, use_container_width=True)
            st.caption("Motivo: Acompanhar tendências de faturamento e sazonalidade.")

        # GRÁFICO 4: Distribuição de CFOP
        with col_g4:
            df_cfop_desc = df_itens['DESCRICAO_TRUNCADA'].value_counts().nlargest(10).reset_index()
            df_cfop_desc.columns = ['DESCRICAO', 'Count']
            fig4 = px.pie(
                df_cfop_desc, 
                values='Count', 
                names='DESCRICAO', 
                title='Distribuição de CFOP (Descrição da Operação)', 
                hole=0.3
            )
            fig4.update_layout(
                height=400, 
                margin=dict(l=10, r=10, t=50, b=10),
                legend={'orientation': 'h', 'yanchor': 'bottom', 'y': -0.3} 
            )
            st.plotly_chart(fig4, use_container_width=True)
            st.caption("Motivo: Entender a natureza das operações – essencial para a área fiscal.")


        # --- LINHA 3: Proporção Operações vs Natureza ---
        col_g5, col_g6 = st.columns(2)

        # GRÁFICO 5: Proporção de Operações Internas vs Interestaduais
        with col_g5:
            df_tipo_op = df_cabecalho['TIPO_OPERACAO'].value_counts().reset_index()
            df_tipo_op.columns = ['Tipo', 'Count']
            
            fig5 = px.pie(
                df_tipo_op, 
                values='Count', 
                names='Tipo', 
                title='Proporção Operações Internas vs Interestaduais', 
                hole=0.4
            )
            fig5.update_layout(height=400, margin=dict(l=10, r=10, t=50, b=10))
            st.plotly_chart(fig5, use_container_width=True)
            st.caption("Motivo: Impacto na tributação (diferencial de alíquota, Substituição Tributária).")


        # GRÁFICO 6: Distribuição por Natureza da Operação
        with col_g6:
            # Agregação para simplificar 'Venda'
            df_natureza = df_cabecalho['NATUREZA_DA_OPERACAO'].astype(str).str.upper()
            df_natureza[df_natureza.str.contains('VENDA', na=False)] = 'VENDAS GERAIS'
            
            df_natureza_count = df_natureza.value_counts().nlargest(10).reset_index()
            df_natureza_count.columns = ['Natureza', 'Count']
            
            fig6 = px.pie(
                df_natureza_count, 
                values='Count', 
                names='Natureza', 
                color='Natureza', 
                title='Distribuição por Natureza da Operação', 
                hole=0.4
            )
            fig6.update_layout(
                height=400, 
                margin=dict(l=10, r=10, t=50, b=10),
                legend={'orientation': 'h', 'yanchor': 'bottom', 'y': -0.3}
            )
            st.plotly_chart(fig6, use_container_width=True)
            st.caption("Motivo: Analisar a finalidade predominante das NFs.")


        # --- LINHA 4: Heatmap vs Ranking UF Emitente ---
        col_g7, col_g8 = st.columns(2)

        # GRÁFICO 7: Heatmap (Mapa de Calor) das Operações por UF
        with col_g7:
            df_heatmap = df_cabecalho.groupby(['UF_EMITENTE', 'UF_DESTINATARIO'])['VALOR_NOTA_FISCAL'].sum().reset_index()
            df_pivot = df_heatmap.pivot_table(
                index='UF_EMITENTE', 
                columns='UF_DESTINATARIO', 
                values='VALOR_NOTA_FISCAL', 
                fill_value=0
            )
            
            fig7 = px.imshow(
                df_pivot,
                text_auto=True,
                aspect="auto",
                color_continuous_scale='Viridis',
                title='Mapa de Calor: Faturamento UF Emitente x Destinatário'
            )
            fig7.update_layout(height=400, margin=dict(l=10, r=10, t=50, b=10))
            st.plotly_chart(fig7, use_container_width=True)
            st.caption("Motivo: Identificar fluxos fiscais mais intensos (Origem x Destino).")


        # GRÁFICO 8: Valor Total das Notas Emitidas por UF Emitente
        with col_g8:
            df_uf_faturamento = df_cabecalho.groupby('UF_EMITENTE')['VALOR_NOTA_FISCAL'].sum().sort_values(ascending=False).reset_index()
            df_uf_faturamento.columns = ['UF_EMITENTE', 'Valor Total Faturado']
            
            fig8 = px.bar(
                df_uf_faturamento, 
                x='UF_EMITENTE', 
                y='Valor Total Faturado', 
                color='UF_EMITENTE', 
                title='Valor Total das Notas Emitidas por UF Emitente',
                labels={'Valor Total Faturado': 'Valor (R$)', 'UF_EMITENTE': 'UF Emitente'}
            )
            
            fig8.update_xaxes(categoryorder='total descending')
            fig8.update_layout(xaxis_tickangle=-45, height=400, showlegend=False)
            
            st.plotly_chart(fig8, use_container_width=True)
            st.caption("Motivo: Análise de concentração geográfica do faturamento da empresa.")

        
        st.markdown("---")


        # #############################################################
        # 4. TÓPICO: RELATÓRIOS
        # #############################################################
        st.header(f"{REPORT_ICON} Relatórios")

        # Tabela com resumo mensal de operações
        df_relatorio_mensal = df_cabecalho.groupby('ANO_MES')['CHAVE_DE_ACESSO'].count().reset_index()
        df_relatorio_mensal.rename(columns={'CHAVE_DE_ACESSO': 'Total de Notas'}, inplace=True)
        
        # Adiciona Valor Total (Continua a lógica de cálculo)
        df_valor_total_mensal = df_cabecalho.groupby('ANO_MES')['VALOR_NOTA_FISCAL'].sum().reset_index()
        df_relatorio_mensal = pd.merge(df_relatorio_mensal, df_valor_total_mensal, on='ANO_MES')
        df_relatorio_mensal.rename(columns={'VALOR_NOTA_FISCAL': 'Valor Total'}, inplace=True)
        
        # Adiciona Número Médio de Itens por Nota
        df_itens_count = df_itens.groupby('CHAVE_DE_ACESSO')['NUMERO_PRODUTO'].count().reset_index()
        df_itens_count.rename(columns={'NUMERO_PRODUTO': 'Total Itens na Nota'}, inplace=True)
        
        df_merge_itens_nota = df_cabecalho[['ANO_MES', 'CHAVE_DE_ACESSO']]
        df_merge_itens_nota = pd.merge(df_merge_itens_nota, df_itens_count, on='CHAVE_DE_ACESSO', how='left')
        df_merge_itens_nota['Total Itens na Nota'] = df_merge_itens_nota['Total Itens na Nota'].fillna(0)
        
        df_medio_itens = df_merge_itens_nota.groupby('ANO_MES')['Total Itens na Nota'].mean().reset_index()
        df_medio_itens.rename(columns={'Total Itens na Nota': 'Nº Médio de Itens por Nota'}, inplace=True)
        
        df_relatorio_mensal = pd.merge(df_relatorio_mensal, df_medio_itens, on='ANO_MES', how='left')
        
        # Formatação Final para exibição
        df_relatorio_mensal['Valor Total'] = df_relatorio_mensal['Valor Total'].apply(format_brl)
        df_relatorio_mensal['Nº Médio de Itens por Nota'] = df_relatorio_mensal['Nº Médio de Itens por Nota'].round(2)

        # =============================================================
        # MODIFICAÇÃO: Ordena a tabela por ANO_MES em ordem decrescente
        # =============================================================
        df_relatorio_mensal = df_relatorio_mensal.sort_values(by='ANO_MES', ascending=False)
        
        st.markdown("### Resumo de Operações por Mês")
        st.dataframe(df_relatorio_mensal, hide_index=True, use_container_width=True)


        # #############################################################
        # 5. TÓPICO: AUDITORIA
        # #############################################################
        st.header(f"{AUDIT_ICON} Auditoria")
        col_a1, col_a2 = st.columns(2)

        # Tabela 1: Notas com Diferença de Valor (Cabeçalho vs Itens)
        with col_a1:
            st.markdown("### Notas com Diferença de Valor (Cabeçalho vs Itens)")
            
            df_soma_itens = df_itens.groupby('CHAVE_DE_ACESSO')['VALOR_TOTAL_ITEM'].sum().reset_index()
            df_soma_itens.rename(columns={'VALOR_TOTAL_ITEM': 'Soma_Itens'}, inplace=True)
            
            df_audit = pd.merge(df_cabecalho[['CHAVE_DE_ACESSO', 'NUMERO', 'VALOR_NOTA_FISCAL']], df_soma_itens, on='CHAVE_DE_ACESSO', how='left')
            df_audit['Soma_Itens'] = df_audit['Soma_Itens'].fillna(0)
            
            # Filtra diferenças significativas (ex: > R$ 0.01)
            df_audit['DIFERENCA'] = np.abs(df_audit['VALOR_NOTA_FISCAL'] - df_audit['Soma_Itens'])
            df_diferentes = df_audit[df_audit['DIFERENCA'] > 0.01].copy()
            
            # Formatação para visualização
            df_diferentes_view = df_diferentes[['NUMERO', 'VALOR_NOTA_FISCAL', 'Soma_Itens', 'DIFERENCA']].copy()
            df_diferentes_view['VALOR_NOTA_FISCAL'] = df_diferentes_view['VALOR_NOTA_FISCAL'].apply(format_brl)
            df_diferentes_view['Soma_Itens'] = df_diferentes_view['Soma_Itens'].apply(format_brl)
            df_diferentes_view['DIFERENCA'] = df_diferentes_view['DIFERENCA'].apply(format_brl)
            
            st.dataframe(df_diferentes_view, hide_index=True, use_container_width=True)
            st.markdown(f"**Total de Notas com Diferença:** **{len(df_diferentes)}**")

        # Tabela 2: Duplicidade de CHAVE_DE_ACESSO
        with col_a2:
            st.markdown("### Duplicidade de Chave de Acesso")
            
            df_duplicadas = df_cabecalho[df_cabecalho.duplicated(subset=['CHAVE_DE_ACESSO'], keep=False)]
            df_duplicadas_view = df_duplicadas[['CHAVE_DE_ACESSO', 'NUMERO', 'RAZAO_SOCIAL_EMITENTE']].sort_values(by='CHAVE_DE_ACESSO').copy()
            
            st.dataframe(df_duplicadas_view, hide_index=True, use_container_width=True)
            st.markdown(f"**Total de CHAVE_DE_ACESSO Duplicadas:** **{len(df_duplicadas['CHAVE_DE_ACESSO'].unique())}**")


        col_a3, col_a4 = st.columns(2)
        
        # Tabela 3: Notas sem Inscrição Estadual (IE) do Emitente
        with col_a3:
            st.markdown("### Notas Emitidas Sem IE do Emitente")
            df_sem_ie = df_cabecalho[df_cabecalho['INSC_ESTADUAL_EMITENTE'].isna() | (df_cabecalho['INSC_ESTADUAL_EMITENTE'] == 0)].copy()
            df_sem_ie_view = df_sem_ie[['NUMERO', 'RAZAO_SOCIAL_EMITENTE', 'UF_EMITENTE']].copy()
            
            st.dataframe(df_sem_ie_view, hide_index=True, use_container_width=True)
            st.markdown(f"**Total de Notas Sem IE do Emitente:** **{len(df_sem_ie)}**")

        # Tabela 4: Múltiplas UFs para o Mesmo CNPJ Destinatário
        with col_a4:
            st.markdown("### CNPJ Destinatário com Múltiplas UFs")
            
            df_multi_uf = df_cabecalho.groupby('CNPJ_DESTINATARIO')['UF_DESTINATARIO'].nunique().reset_index()
            df_multi_uf = df_multi_uf[df_multi_uf['UF_DESTINATARIO'] > 1]
            
            df_risco_ie = df_cabecalho[df_cabecalho['CNPJ_DESTINATARIO'].isin(df_multi_uf['CNPJ_DESTINATARIO'])].copy()
            
            df_risco_ie_view = df_risco_ie[['CNPJ_DESTINATARIO', 'NOME_DESTINATARIO', 'UF_DESTINATARIO']].sort_values(by='CNPJ_DESTINATARIO').copy()
            
            st.dataframe(df_risco_ie_view.head(10), hide_index=True, use_container_width=True)
            st.markdown(f"**Total de CNPJs com Risco de IE:** **{len(df_multi_uf)}**")


        # #############################################################
        # 6. TÓPICO: GERAÇÃO DE INSIGHTS AUTOMÁTICOS
        # #############################################################
        st.header(f"{INSIGHT_ICON} Geração de Insights Automáticos")

        col_i1, col_i2 = st.columns(2)

        # Gráfico 1: Outliers no Valor das Notas
        with col_i1:
            st.markdown("### Outliers no Valor das Notas (Acima de 3 Desvios Padrão)")
            
            valor_medio_nf = df_cabecalho['VALOR_NOTA_FISCAL'].mean()
            desvio_padrao = df_cabecalho['VALOR_NOTA_FISCAL'].std()
            limite_superior = valor_medio_nf + (3 * desvio_padrao)
            
            fig_outliers = px.scatter(
                df_cabecalho, 
                y='VALOR_NOTA_FISCAL', 
                x=df_cabecalho.index, 
                color=(df_cabecalho['VALOR_NOTA_FISCAL'] > limite_superior).map({True: 'Outlier', False: 'Normal'}),
                color_discrete_map={'Outlier': 'red', 'Normal': 'darkgreen'}, 
                title='Distribuição de Valores de Notas Fiscais (Outliers)',
                labels={'VALOR_NOTA_FISCAL': 'Valor NF (R$)', 'index': 'Índice da Nota'}
            )
            fig_outliers.update_layout(height=400)
            st.plotly_chart(fig_outliers, use_container_width=True)
            st.caption(f"Motivo: Identifica notas que podem ser erros de lançamento ou operações atípicas (limite > {format_brl(limite_superior)}).")

        # Gráfico 2: Valor Médio de Notas Interestaduais vs Internas
        with col_i2:
            st.markdown("### Valor Médio de Notas: Interestadual vs Interna")
            
            df_medio_op = df_cabecalho.groupby('TIPO_OPERACAO')['VALOR_NOTA_FISCAL'].mean().reset_index()
            df_medio_op.columns = ['Tipo Operação', 'Valor Médio']
            
            fig_medio = px.bar(
                df_medio_op,
                x='Tipo Operação',
                y='Valor Médio',
                color='Tipo Operação',
                color_discrete_map={
                    'Interestadual': 'darkorange', 
                    'Interna': 'sandybrown'       
                },
                title='Comparativo de Valor Médio por Tipo de Operação',
                labels={'Valor Médio': 'Valor Médio (R$)'}
            )
            fig_medio.update_layout(height=400, showlegend=False)
            st.plotly_chart(fig_medio, use_container_width=True)
            st.caption("Motivo: Indica se as operações fora do estado possuem um tíquete médio diferente.")


        st.markdown("---")


        # #############################################################
        # 7. TÓPICO: RANKINGS TOP 5 
        # #############################################################
        st.header(f"{TABLE_ICON} Rankings Top 5 (Detalhes)")
        
        col_t1, col_t2 = st.columns(2)
        
        # 1. Top 5 Clientes por Valor Total Faturado
        with col_t1:
            st.markdown("**Os clientes que mais contribuíram para o faturamento total são:**")
            df_t1 = df_cabecalho.groupby('NOME_DESTINATARIO')['VALOR_NOTA_FISCAL'].sum().nlargest(5).reset_index()
            df_t1.columns = ['Cliente', 'Valor Faturado']
            df_t1['Valor Faturado'] = df_t1['Valor Faturado'].apply(format_brl)
            st.dataframe(df_t1, hide_index=True, use_container_width=True)

        # 2. Top 5 Clientes por Valor Total de Impostos
        with col_t2:
            st.markdown("**Os clientes que mais impostos recolhidos são:**")
            df_t2 = df_cabecalho.groupby('NOME_DESTINATARIO')['VALOR_IMPOSTOS'].sum().nlargest(5).reset_index()
            df_t2.columns = ['Cliente', 'Valor Tributos']
            df_t2['Valor Tributos'] = df_t2['Valor Tributos'].apply(format_brl)
            st.dataframe(df_t2, hide_index=True, use_container_width=True)

        col_t3, col_t4 = st.columns(2)
        
        # 3. Top 5 Principais Produtos/Serviços por Valor Total Faturado
        with col_t3:
            st.markdown("**Os produtos ou serviços que geraram o maior valor de faturamento são:**")
            df_t3 = df_itens.groupby('DESCRICAO_PRODUTO_SERVICO')['VALOR_TOTAL_ITEM'].sum().nlargest(5).reset_index()
            df_t3.columns = ['Produto ou Serviço', 'Valor Faturado']
            df_t3['Valor Faturado'] = df_t3['Valor Faturado'].apply(format_brl)
            st.dataframe(df_t3, hide_index=True, use_container_width=True)

        # 4. Top 5 Principais Produtos/Serviços por Quantidade Vendida
        with col_t4:
            st.markdown("**Os produtos ou serviços com maior volume de vendas (quantidade) são:**")
            df_t4 = df_itens.groupby('DESCRICAO_PRODUTO_SERVICO')['QUANTIDADE_NUM'].sum().nlargest(5).reset_index()
            df_t4.columns = ['Produto ou Serviço', 'Quantidade Vendida']
            
            st.dataframe(
                df_t4, 
                hide_index=True, 
                use_container_width=True,
                column_config={
                    "Produto ou Serviço": st.column_config.TextColumn(
                        "Produto ou Serviço", 
                        width="large" 
                    )
                }
            )

    else:
        st.error("⚠️ Dashboard não pode ser exibido. Verifique se os dados foram carregados corretamente no Banco de Dados').")

    # --- 8. CONSULTOR ESPECIALISTA LLM (Não Alterado) ---

    st.markdown("---")
    st.header(f"{AGENT_ICON} - Consultor Especialista em Análise Fiscal")
    st.markdown("Use o Agente de IA para fazer perguntas complexas sobre os dados fiscais da empresa.")

    # 4.1. Inicialização do Agente
    if 'fiscal_agent' not in st.session_state:
        with st.spinner("Inicializando o Agente LLM (Gemini 2.5 Flash) e a Conexão MySQL..."):
            # Inicializa o Agente de SQL da LangChain/Gemini
            st.session_state.fiscal_agent = initialize_sql_agent()

    # 4.2. Interface de Chat
    if st.session_state.fiscal_agent:
        
        user_question = st.text_input(
            f"{USER_ICON} Sua Pergunta ao Especialista:",
            placeholder="Olá! Como seu assistente tributário e fiscal, faça sua pergunta sobre os dados fiscais da empresa.",
            key="user_input"
        )
        
        # O botão inicia o processo Text-to-SQL
        if st.button("Clique aqui para falar com especialista inteligente", key="run_agent"):
            if user_question:
                with st.spinner("Analisando dados e gerando insights..."):
                    
                    if 'history' not in st.session_state:
                        st.session_state['history'] = []

                    # Executa a cadeia LangChain (Text-to-SQL)
                    response = run_fiscal_analysis(st.session_state.fiscal_agent, user_question)
                    
                    output = response.get("output", "Resposta indisponível.")
                    
                    # Decide se renderiza gráfico ou texto
                    render_visualization_or_text(output, user_question)
                    
                    # Armazena histórico da conversação
                    st.session_state.history.append({"user": user_question, "agent": output})
                    
                    # Exibe o histórico
                    st.markdown("---")
                    st.subheader("Histórico de Perguntas Recentes:")
                    
                    for idx, chat in enumerate(reversed(st.session_state.history[-5:])): 
                        st.text_area(f"{USER_ICON} Você:", chat["user"], disabled=True, key=f"user_chat_{idx}")
                        st.text_area(f"{AGENT_ICON} Especialista:", chat["agent"], disabled=True, key=f"agent_chat_{idx}")
            else:
                st.warning("Por favor, insira uma pergunta.")

    else:
        st.error("Agente não pode ser inicializado. Verifique as credenciais no secrets.toml e a conectividade com o MySQL.")

# Adiciona a chamada de execução para permitir que o script rode diretamente
if __name__ == '__main__':
    app()
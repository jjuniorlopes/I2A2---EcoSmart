# Desafio-Final
MVP (Curso I2A2) de Automação Inteligente de NFs. O projeto foca na integração de dados fiscais (SEFAZ ↔ ERPs de PMEs) usando Python, LangChain e MySQL. O MVP simula a extração de NFs (CSV/XML) para o MySQL e utiliza um Agente LLM (Gemini 2.5 Flash) para facilitar a análise e o gerenciamento eficiente dos dados fiscais.

## 🤖 EcoSmart: Automação Inteligente da Emissão e Análise de Notas Fiscais (NFs)

[![Licença MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.9%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![LangChain](https://img.shields.io/badge/LangChain-v0.1.0%2B-green?logo=chainlink&logoColor=white)](https://www.langchain.com/)
[![MySQL](https://img.shields.io/badge/MySQL-Database-orange?logo=mysql&logoColor=white)](https://www.mysql.com/)
[![Google Gemini](https://img.shields.io/badge/Google_Gemini-2.5_Flash-4285F4?logo=google&logoColor=white)](https://ai.google.dev/gemini)

Este projeto foi desenvolvido pela equipe **EcoSmart** como o MVP (Produto Mínimo Viável) final do **Curso Agentes Autônomos com Redes Generativas** (I2A2).

---

### 💡 Ideia do Projeto (O Desafio)

O projeto visa criar um protótipo de solução para **automatizar a integração de dados fiscais (Notas Fiscais - NFs)** entre as Secretarias da Fazenda (SEFAZ) e os ERPs de pequenas e médias empresas. O principal objetivo é facilitar a **análise e o gerenciamento eficiente** dos dados de NFs, liberando profissionais de tarefas rotineiras e complexas através da automação inteligente.

### 🎯 Tema do Projeto Final (Curso I2A2)

O trabalho final aborda a criação de **Ferramentas Gerenciais** com foco nos seguintes tópicos, diretamente endereçados pela arquitetura do nosso MVP:

#### 1. Relatórios Personalizados
**Geração de relatórios personalizados:** Possibilidade de criar relatórios com informações relevantes para o setor.
**Utilizar informações internas:** Análise baseada nos dados de NFs coletadas e emitidas e armazenados no MySQL.
**Agregar informações externas relevantes:** Novos módulos (ex: análise de conformidade, geração de relatórios personalizados) podem ser facilmente integrados.
**Análises preditivas e simulações de cenários:** O armazenamento seguro e estruturado no MySQL permite análises gerenciais e auditorias eficientes.

#### 2. Assistente Consultor Especializado
**Suporte para dúvidas e decisões estratégicas:** O **Agente Especialista de Dados Fiscais** atua como um consultor virtual, processando solicitações de emissão e validação de NFs e interagindo com sistemas externos automaticamente.
**Informações sobre contabilidade e tributação:** O LLM (`gemini-2.5-flash`) é orquestrado pela LangChain para processar e responder com informações sobre as regras brasileiras e linguagem fiscal.

#### 3. Desafios Abordados
**Qualidade das Informações:** Garantida pela validação automatizada de informações nos pipelines de processamento e pelos testes de validação dos agentes LLM.
**Experiência do Usuário:** Maximizada pelo uso de agentes autônomos que interpretam instruções em linguagem natural.

### 🏗️ Arquitetura e Tecnologias

A arquitetura do projeto é modular e utiliza ferramentas de ponta para a orquestração de IA Generativa:

| Componente | Tecnologia | Função no Projeto |
| :--- | :--- | :--- |
| **Orquestração Principal** | **Python** | Linguagem principal para arquitetar a lógica, conectar LLMs, bancos de dados e APIs. Facilita a automação de *pipelines*. |
| **Framework LLM** | **LangChain** | Atua como interface genérica para LLMs, orquestrando agentes virtuais e facilitando a integração com APIs e bancos de dados. |
| **Modelo de Linguagem** | **Gemini 2.5 Flash** | Modelo que impulsiona o Agente Especialista de Dados Fiscais, ideal para raciocínio e casos de uso de agentes (mencionado no prompt do usuário). |
| **Persistência de Dados** | **MySQL** | Banco de dados relacional que garante a **segurança, integridade e escalabilidade** para armazenar todas as informações fiscais, logs e interações. |

---

### 👥 Equipe EcoSmart

| Nome | E-mail | Telefone |
| :--- | :--- | :--- |
| Jair | jjuniorlopes@gmail.com | +5571992888890 |
| Rogério | rogerio.batista.teixeira@gmail.com | +5561991810140 |
| Robson  |  santos.robson@gmail.com  | +5521996696180 |
| Javan | javanoalmeida@gmail.com | +5533988066314 |

---

### 📝 Orientação do sistema para funcionaento da solução

🤖 EcoSmart: Automação Inteligente da Emissão e Análise de Notas Fiscais (NFs)

1. Acessar o sistema
➡️ Acesse o link: https://fiscal-data.streamlit.app/

➡️ A tela inicial exibirá o menu principal da aplicação, com as opções Carga de NF-e e Fale com o Agente Especialista.

2. Realizar a carga dos dados mensais
   
➡️ No menu lateral esquerdo, clique em Executar Cargas de Dados (ETL).

➡️ Em Selecionar Mês de Referência, escolha 202508, CSV ou XML e pressione o botão Realizar Carga.

➡️ O sistema carregará as notas fiscais correspondentes ao mês de agosto de 2025. Aguarde até que o status de conclusão seja exibido.

➡️ Repita o procedimento, agora escolhendo o mês 202509, CSV ou XML e pressionando Realizar Carga.

➡️ Este mês contém inconsistências simuladas propositalmente — diferenças entre valores de cabeçalho e itens, e duplicidade de chaves de acesso — para demonstrar o funcionamento da auditoria fiscal automatizada.

3. Visualizar resultados e inconsistências

➡️ Após a carga dos dois meses:

➡️ Clique na aba Resultados e Auditoria no menu principal.

➡️ O painel exibirá indicadores de validação e inconsistências detectadas.

➡️ Acesse a seção Notas com Diferença de Valor (Cabeçalho vs Itens):

➡️ Mostra as notas fiscais em que o total do cabeçalho diverge da soma de itens.

➡️Acesse a seção Duplicidade de Chave de Acesso:

➡️ Apresenta notas que foram emitidas mais de uma vez com o mesmo identificador fiscal.

4. Interagir com o agente fiscal inteligente

➡️ Após a simulação de carga e auditoria, clique na aba Fale com o Agente Especialista.

➡️ Digite, por exemplo:

“Liste as inconsistências encontradas no mês de 202509.”
ou
“Explique por que há diferença entre os valores do cabeçalho e dos itens.”

➡️ O agente utiliza integração com LangChain e Google Gemini para interpretar as perguntas e gerar respostas explicativas, técnicas e fiscais baseadas nos dados processados. Ele pode fornecer diagnósticos, propor correções e gerar relatórios sintéticos sob demanda.

5. Recomendações finais

➡️ Execute sempre primeiro o mês sem erro (202508) antes do mês com inconsistência (202509), para facilitar a comparação.

➡️ No ambiente do Streamlit Cloud, os dados são processados em memória; portanto, cada nova execução reinicia o contexto de trabalho.

✅ Este roteiro cobre o fluxo completo de demonstração da aplicação fiscal inteligente — da carga à auditoria automática e explicação das inconsistências via agente especializado.

### 📜 Licença

Este projeto está licenciado sob a **Licença MIT** - veja o arquivo [LICENSE](LICENSE) para mais detalhes.

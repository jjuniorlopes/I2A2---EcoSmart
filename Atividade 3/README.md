# Descrição para executar código da Atividade 3

## Como executar o código

O arquivo `app.py` é uma aplicação Streamlit que permite consultar e analisar notas fiscais eletrônicas (NF-e) de janeiro de 2024 utilizando linguagem natural. Ele faz uso do modelo Gemini, implementado em `gemini_llm.py`, para interpretar perguntas e gerar respostas inteligentes.

## Funcionamento

- O `app.py` carrega os dados das notas fiscais a partir de arquivos CSV.
- Cria um banco de dados SQLite temporário com esses dados.
- Utiliza o modelo Gemini (definido em `gemini_llm.py`) para responder perguntas em linguagem natural sobre os dados, via interface web do Streamlit.
- O usuário pode digitar perguntas como “Qual a soma total dos valores dos itens para cada NF?” e receber respostas automáticas.

## Como executar

1. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```

2. Crie um arquivo `.env` na pasta do projeto com sua chave de API Gemini:
   ```
   GEMINI_API_KEY="suachaveaqui"
   ```

3. Execute o aplicativo Streamlit:
   ```bash
   streamlit run app.py
   ```

4. Acesse o endereço exibido no terminal para usar a interface web.

## Onde adiquirir a chave de API para adicionar no arquivo .env

1. Acesse o site: [Google AI Studio](https://aistudio.google.com/prompts/new_chat)

2. Clique em "Get API KEY"

3. Crie uma nova chave de API em "+ Criar chave de API"

4. Adicione a chave de API criada no arquivo .env
   ```
   GEMINI_API_KEY="suachaveaqui"
   ```

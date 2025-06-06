# gemini_llm.py

import google.generativeai as genai
from langchain_core.language_models import LLM
from typing import List, Optional

# Se genai.GenerationConfig não funcionar diretamente, você pode precisar importar de types:
# from google.generativeai.types import GenerationConfig

class GeminiLLM(LLM):
    model_name: str = "gemini-pro"
    api_key: Optional[str] = None
    temperature: float = 0.7
    # Você pode adicionar outros parâmetros de GenerationConfig aqui se desejar,
    # como top_p, top_k, max_output_tokens

    def _call(self, prompt: str, stop: Optional[List[str]] = None) -> str:
        if self.api_key:
            genai.configure(api_key=self.api_key)

        # print(f"Usando modelo: {self.model_name} com temperatura: {self.temperature}") # Debug aprimorado

        model = genai.GenerativeModel(self.model_name)

        # Crie o objeto GenerationConfig
        # A maioria das versões recentes do SDK permitem usar genai.GenerationConfig
        # Se der erro aqui, use: from google.generativeai.types import GenerationConfig
        generation_config = genai.GenerationConfig(
            temperature=self.temperature,
            stop_sequences=stop,
            # candidate_count=1 # O SDK geralmente assume 1 por padrão
            # Adicione outros parâmetros de configuração aqui, se necessário
            # ex: top_p=self.top_p, top_k=self.top_k, max_output_tokens=self.max_output_tokens
        )

        response = model.generate_content(
            prompt,
            generation_config=generation_config # Passe o objeto config aqui
        )

        # Tratamento de resposta (response.text é um atalho para o texto da primeira candidata)
        try:
            return response.text.strip()
        except ValueError:
            # Isso pode acontecer se a resposta for bloqueada ou não contiver texto.
            # Você pode querer logar o response.prompt_feedback ou response.candidates
            # para entender melhor o que aconteceu.
            print(f"Erro ao acessar response.text. Feedback do prompt: {response.prompt_feedback}")
            # Retornar uma string vazia ou levantar um erro, dependendo de como o Langchain deve tratar isso.
            return "Não foi possível gerar uma resposta."


    @property
    def _llm_type(self) -> str:
        return "gemini-llm-custom" # Alterado para refletir que é uma classe customizada
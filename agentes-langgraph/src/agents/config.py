"""Configurações centralizadas do projeto usando pydantic-settings.

POR QUE pydantic-settings?
    - Carrega variáveis de ambiente automaticamente (.env ou OS env)
    - Validação de tipos: erro IMEDIATO se faltar uma chave obrigatória
    - Type hints em todo o projeto: settings.google_api_key tem tipo `str`
    - Defaults seguros: campos com valor padrão são opcionais
    - Fail-fast: o app não sobe se a configuração estiver inválida
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configurações carregadas de variáveis de ambiente ou arquivo .env."""

    # Diz ao pydantic-settings para procurar um arquivo .env na raiz do projeto.
    # Variáveis do OS sobrescrevem as do .env (útil em produção/CI).
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # --- API Keys ---
    # google_api_key NÃO tem default → é OBRIGATÓRIA. Se faltar, o app
    # falha no startup com mensagem clara — melhor que erros crípticos depois.
    google_api_key: str
    # tavily_api_key tem default vazio → o agente de pesquisa pode rodar
    # sem ela (com funcionalidade reduzida).
    tavily_api_key: str = ""

    # --- Modelo LLM ---
    # gemini-2.5-flash é rápido e barato — ideal para sala de aula.
    # Pode ser sobrescrito via env var GEMINI_MODEL.
    gemini_model: str = "gemini-2.5-flash"


# Instância singleton — importar de qualquer lugar do projeto.
# Como Settings() é executado no import, qualquer erro de config aparece logo.
settings = Settings()

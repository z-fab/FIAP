"""Ferramentas do Estúdio de Roteiro.

Só Tavily (`buscar_web`). Diferente dos Agentes 1 e 3 — onde o LLM
*escolhe* quando chamar tools via ReAct — aqui a tool é invocada
**pelo nó `pesquisar` do grafo**. O modelo não decide a chamada;
o workflow decide. Esse contraste pedagógico é o ponto central do
Agente 2.

Referência no textbook: Capítulo 4 (tools vs. orquestração explícita).
"""

from langchain_core.tools import tool

from agents.config import settings


@tool
def buscar_web(query: str) -> str:
    """Busca informações na web via Tavily e retorna os principais resultados.

    Args:
        query: Consulta de busca (ex.: "estrutura de roteiro curta terror").

    Returns:
        Lista formatada de títulos, URLs e trechos, ou mensagem de erro.
    """
    from tavily import TavilyClient

    if not settings.tavily_api_key:
        return (
            "TAVILY_API_KEY não configurada. Defina a chave no .env para habilitar a pesquisa web."
        )

    try:
        client = TavilyClient(api_key=settings.tavily_api_key)
        resposta = client.search(query=query, max_results=5)
    except Exception as e:
        return f"Erro ao realizar busca na web: {e}"

    resultados = resposta.get("results", [])
    if not resultados:
        return "Nenhum resultado encontrado para a query informada."

    linhas = []
    for i, resultado in enumerate(resultados, start=1):
        titulo = resultado.get("title", "Sem título")
        url = resultado.get("url", "URL não disponível")
        snippet = resultado.get("content", "Conteúdo não disponível.")
        linhas.append(f"{i}. **{titulo}**\n   URL: {url}\n   Trecho: {snippet}")

    return "\n\n".join(linhas)

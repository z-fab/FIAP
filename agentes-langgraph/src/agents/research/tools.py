"""Ferramentas do agente de pesquisa acadêmica.

Integra com Semantic Scholar (artigos científicos), Tavily (busca web)
e o próprio Gemini (resumo de textos).
"""

import httpx
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI

from agents.config import settings


@tool
def buscar_artigos(query: str) -> str:
    """Busca artigos científicos no Semantic Scholar pela query informada."""
    url = "https://api.semanticscholar.org/graph/v1/paper/search"
    params = {
        "query": query,
        "limit": 5,
        "fields": "title,authors,year,abstract,citationCount",
    }

    try:
        resposta = httpx.get(url, params=params, timeout=15)
        resposta.raise_for_status()
        dados = resposta.json()
    except httpx.HTTPStatusError as e:
        return f"Erro ao acessar o Semantic Scholar: {e.response.status_code} — {e.response.text}"
    except httpx.RequestError as e:
        return f"Erro de conexão ao Semantic Scholar: {e}"

    artigos = dados.get("data", [])
    if not artigos:
        return "Nenhum artigo encontrado para a query informada."

    linhas = []
    for i, artigo in enumerate(artigos, start=1):
        titulo = artigo.get("title", "Sem título")
        ano = artigo.get("year", "Ano desconhecido")
        citacoes = artigo.get("citationCount", 0)
        abstract = artigo.get("abstract") or "Abstract não disponível."
        abstract_resumido = abstract[:200] + "..." if len(abstract) > 200 else abstract

        # Formata autores: até 3 nomes, depois "et al."
        autores_raw = artigo.get("authors", [])
        nomes = [a.get("name", "") for a in autores_raw if a.get("name")]
        if len(nomes) > 3:
            autores_str = ", ".join(nomes[:3]) + " et al."
        else:
            autores_str = ", ".join(nomes) if nomes else "Autores desconhecidos"

        linhas.append(
            f"{i}. **{titulo}**\n"
            f"   Autores: {autores_str}\n"
            f"   Ano: {ano} | Citações: {citacoes}\n"
            f"   Abstract: {abstract_resumido}"
        )

    return "\n\n".join(linhas)


@tool
def buscar_web(query: str) -> str:
    """Busca informações na web via Tavily e retorna os principais resultados."""
    from tavily import TavilyClient

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


@tool
def resumir_texto(texto: str) -> str:
    """Resume um texto longo em 2-3 frases concisas usando o modelo Gemini."""
    try:
        llm = ChatGoogleGenerativeAI(
            model=settings.gemini_model,
            google_api_key=settings.google_api_key,
        )
        prompt = f"Resuma o texto a seguir em 2-3 frases concisas, em português:\n\n{texto}"
        resposta = llm.invoke(prompt)
        return resposta.content
    except Exception as e:
        return f"Erro ao resumir texto: {e}"

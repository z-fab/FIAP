"""Estúdio de Roteiro — StateGraph com pipeline e loop de crítica.

Este agente NÃO é um ReAct genérico. Em vez de deixar o LLM decidir
quais tools chamar, o grafo orquestra nós especializados:

    START → brief → pesquisar → roteirizar → validar
                                          ↘ (rejeitado e revision_count < 2)
                                            → roteirizar (loop)
    validar → (aprovado OU revision_count >= 2) → finalizar → END

Contraste pedagógico com os outros agentes:
    - Agente 1 (financeiro): `create_agent` — ReAct prebuilt em uma linha
    - Agente 2 (este): workflow multi-nó + loop de crítico; Tavily chamada
      **pelo nó**, não escolhida pelo LLM
    - Agente 3 (trade): ReAct manual + HITL via interrupt()

Referência no textbook: Capítulo 4 (StateGraph manual, arestas
condicionais, padrões de validação/revisão).
"""

import logging
import re

from langchain_core.messages import AIMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import END, START, StateGraph

from agents.config import settings
from agents.roteiro.state import RoteiroState
from agents.roteiro.tools import buscar_web

logger = logging.getLogger("agents.roteiro")

# Máximo de passagens pelo validador. Com revision_count >= MAX_REVISIONS
# finalizamos mesmo sem aprovação — evita loop infinito em sala de aula.
MAX_REVISIONS = 2

model = ChatGoogleGenerativeAI(
    model=settings.gemini_model,
    google_api_key=settings.google_api_key,
)


def _texto(mensagem) -> str:
    """Normaliza content do Gemini (str ou lista de blocos) para string."""
    content = mensagem.content if hasattr(mensagem, "content") else mensagem
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        partes = []
        for bloco in content:
            if isinstance(bloco, dict) and "text" in bloco:
                partes.append(bloco["text"])
            elif isinstance(bloco, str):
                partes.append(bloco)
        return "\n".join(partes)
    return str(content)


def _ultima_mensagem_usuario(state: RoteiroState) -> str:
    """Extrai o pedido original do usuário a partir de `messages`."""
    for msg in reversed(state["messages"]):
        if isinstance(msg, HumanMessage):
            return _texto(msg)
        if isinstance(msg, dict) and msg.get("role") == "user":
            return str(msg.get("content", ""))
        role = getattr(msg, "type", None) or getattr(msg, "role", None)
        if role in ("human", "user"):
            return _texto(msg)
    return ""


# --------------------------------------------------------------------------
# Nós do pipeline
# --------------------------------------------------------------------------
def brief(state: RoteiroState) -> dict:
    """Extrai gênero, tom, logline e restrições do pedido do usuário."""
    logger.info("Nó 'brief' — extraindo briefing criativo")
    pedido = _ultima_mensagem_usuario(state)

    prompt = f"""Você é um roteirista sênior preparando um briefing.

A partir do pedido abaixo, produza um BRIEF estruturado em português com:
- Gênero
- Tom / referências de estilo
- Logline (1–2 frases)
- Formato (curta, episódio, etc.) e extensão aproximada
- Restrições / must-haves do usuário

Pedido do usuário:
{pedido}
"""
    resposta = model.invoke(prompt)
    texto = _texto(resposta).strip()
    logger.info("Brief gerado (%d chars)", len(texto))
    return {"brief": texto}


def pesquisar(state: RoteiroState) -> dict:
    """Monta 1–2 queries a partir do brief e chama Tavily no nó.

    IMPORTANTE (didático): a tool `buscar_web` é invocada AQUI pelo grafo,
    não pelo LLM via tool_calls. Compare com financial/trade, onde o modelo
    decide sozinho quando chamar ferramentas.
    """
    logger.info("Nó 'pesquisar' — gerando queries e chamando Tavily")
    brief_txt = state.get("brief") or ""

    prompt = f"""Com base neste briefing de roteiro, proponha exatamente 2
consultas curtas (uma por linha, sem numeração) para pesquisa web.
Foque em: tropes do gênero, referências de tom, e fatos/locações úteis.

Briefing:
{brief_txt}
"""
    resposta = model.invoke(prompt)
    linhas = [ln.strip(" -•\t") for ln in _texto(resposta).splitlines() if ln.strip()]
    queries = linhas[:2] or [brief_txt[:120] or "roteiro de curta cinematográfica"]

    notas: list[str] = []
    for i, query in enumerate(queries, start=1):
        logger.info("Tavily query %d: %s", i, query)
        # Chamada explícita da tool pelo nó — não via ReAct/tool_calls
        resultado = buscar_web.invoke({"query": query})
        notas.append(f"### Busca {i}: {query}\n{resultado}")

    research_notes = "\n\n".join(notas)
    logger.info("Pesquisa concluída (%d chars de notas)", len(research_notes))
    return {"research_notes": research_notes}


def roteirizar(state: RoteiroState) -> dict:
    """Escreve ou revisa o roteiro usando brief + notas + crítica."""
    revisao = (state.get("revision_count") or 0) > 0
    logger.info(
        "Nó 'roteirizar' — %s",
        "revisando draft com base na crítica" if revisao else "primeira versão",
    )

    brief_txt = state.get("brief") or ""
    notas = state.get("research_notes") or ""
    critica = state.get("critique") or ""
    draft_atual = state.get("draft") or ""

    if revisao and critica:
        prompt = f"""Você é roteirista. REVISE o draft abaixo incorporando a crítica.
Mantenha o formato de roteiro (cenas, didascalias, diálogos).
Responda só com o roteiro revisado, em português.

BRIEF:
{brief_txt}

NOTAS DE PESQUISA:
{notas}

CRÍTICA A INCORPORAR:
{critica}

DRAFT ATUAL:
{draft_atual}
"""
    else:
        prompt = f"""Você é roteirista. Escreva um roteiro completo em português
seguindo o briefing. Use o formato clássico (INT./EXT., didascalias, diálogos).
Incorpore insights úteis das notas de pesquisa (sem citar URLs no corpo).
Responda só com o roteiro.

BRIEF:
{brief_txt}

NOTAS DE PESQUISA:
{notas}
"""

    resposta = model.invoke(prompt)
    draft = _texto(resposta).strip()
    logger.info("Draft pronto (%d chars)", len(draft))
    return {"draft": draft}


def validar(state: RoteiroState) -> dict:
    """Crítico de roteiro: aprova ou rejeita e incrementa revision_count."""
    count = (state.get("revision_count") or 0) + 1
    logger.info("Nó 'validar' — revisão #%d", count)

    prompt = f"""Você é um crítico de roteiro rigoroso mas justo.

Avalie o draft abaixo em: estrutura dramática, diálogo, coerência com o
brief e aproveitamento das notas de pesquisa.

Responda EXATAMENTE neste formato:
APROVADO: sim
ou
APROVADO: não

CRÍTICA:
<feedback concreto e acionável em 3–6 frases>

BRIEF:
{state.get("brief") or ""}

DRAFT:
{state.get("draft") or ""}
"""
    resposta = model.invoke(prompt)
    texto = _texto(resposta).strip()

    aprovado = bool(re.search(r"APROVADO:\s*sim", texto, re.IGNORECASE))
    match = re.search(r"CRÍTICA:\s*(.*)", texto, re.IGNORECASE | re.DOTALL)
    critica = match.group(1).strip() if match else texto

    logger.info(
        "Validação #%d → approved=%s",
        count,
        aprovado,
    )
    return {
        "approved": aprovado,
        "critique": critica,
        "revision_count": count,
    }


def finalizar(state: RoteiroState) -> dict:
    """Empacota roteiro final + fontes em uma mensagem para o usuário."""
    logger.info("Nó 'finalizar' — empacotando resposta")
    aprovado = bool(state.get("approved"))
    count = state.get("revision_count") or 0
    status = (
        "aprovado pelo crítico"
        if aprovado
        else f"entregue após {count} revisão(ões) (limite atingido)"
    )

    # Extrai URLs das notas para listar fontes
    notas = state.get("research_notes") or ""
    urls = re.findall(r"URL:\s*(\S+)", notas)
    fontes = "\n".join(f"- {u}" for u in dict.fromkeys(urls)) or "- (sem URLs capturadas)"

    corpo = (
        f"# Estúdio de Roteiro — entrega final\n\n"
        f"**Status:** {status}\n\n"
        f"## Brief\n{state.get('brief') or '(vazio)'}\n\n"
        f"## Roteiro\n{state.get('draft') or '(vazio)'}\n\n"
        f"## Fontes consultadas\n{fontes}\n"
    )
    if not aprovado and state.get("critique"):
        corpo += f"\n## Última crítica (não incorporada por completo)\n{state['critique']}\n"

    return {"messages": [AIMessage(content=corpo)]}


def depois_de_validar(state: RoteiroState) -> str:
    """Aresta condicional: finaliza se aprovado ou se esgotou revisões."""
    aprovado = bool(state.get("approved"))
    count = state.get("revision_count") or 0
    if aprovado or count >= MAX_REVISIONS:
        logger.info(
            "Roteamento pós-validar → finalizar (approved=%s, count=%d)",
            aprovado,
            count,
        )
        return "finalizar"
    logger.info("Roteamento pós-validar → roteirizar (revisão necessária)")
    return "roteirizar"


# --------------------------------------------------------------------------
# Construção do grafo
# --------------------------------------------------------------------------
builder = StateGraph(RoteiroState)

builder.add_node("brief", brief)
builder.add_node("pesquisar", pesquisar)
builder.add_node("roteirizar", roteirizar)
builder.add_node("validar", validar)
builder.add_node("finalizar", finalizar)

builder.add_edge(START, "brief")
builder.add_edge("brief", "pesquisar")
builder.add_edge("pesquisar", "roteirizar")
builder.add_edge("roteirizar", "validar")
builder.add_conditional_edges(
    "validar",
    depois_de_validar,
    {"finalizar": "finalizar", "roteirizar": "roteirizar"},
)
builder.add_edge("finalizar", END)

# Sem checkpointer: cada pedido é um pipeline completo e independente.
graph = builder.compile()

"""Agente de pesquisa acadêmica construído manualmente com StateGraph.

Este agente demonstra a construção "tijolo por tijolo" de um agente ReAct:
cada nó, aresta e transição é definida explicitamente, dando controle
total sobre o fluxo de execução.

Referência no textbook: Capítulo 4, Seção 4.4.2 (Abordagem Manual).

Grafo:
    START → assistant → [tools_condition] → tools → assistant → ... → END

O ciclo se repete enquanto o modelo decidir chamar ferramentas.
Quando o modelo responde diretamente (sem tool_calls), o grafo termina.

POR QUE construir manualmente em vez de usar create_agent?
    - Aprender como o ReAct funciona por baixo dos panos
    - Customizar nós (adicionar lógica entre LLM e tools)
    - Adicionar nós extras (ex.: validação, logging, guardrails)
    - Trocar componentes (ex.: usar um router customizado)
    Compare com src/agents/financial/agent.py — mesma capacidade,
    mas com create_agent o código fica em UMA linha.
"""

import logging

from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import START, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from agents.config import settings
from agents.research.state import ResearchState
from agents.research.tools import buscar_artigos, buscar_web, resumir_texto

logger = logging.getLogger("agents.research")

# Prompt de sistema
SYSTEM_PROMPT = """Você é um assistente de pesquisa acadêmica especializado.

Suas capacidades:
- Buscar artigos científicos no Semantic Scholar
- Buscar informações e tutoriais na web via Tavily
- Resumir textos longos de forma concisa

Diretrizes:
- Sempre responda em português brasileiro
- Ao buscar artigos, priorize os mais citados e recentes
- Ao apresentar resultados, organize por relevância
- Use a ferramenta de resumo para condensar textos longos encontrados
- Cite as fontes (títulos de papers, URLs) nas suas respostas
- Seja acadêmico mas acessível
"""

# --------------------------------------------------------------------------
# 1. Definir as ferramentas
# --------------------------------------------------------------------------
tools = [buscar_artigos, buscar_web, resumir_texto]

# --------------------------------------------------------------------------
# 2. Configurar o modelo com ferramentas (bind_tools)
# --------------------------------------------------------------------------
model = ChatGoogleGenerativeAI(
    model=settings.gemini_model,
    google_api_key=settings.google_api_key,
)
model_with_tools = model.bind_tools(tools)


# --------------------------------------------------------------------------
# 3. Definir o nó do assistente
# --------------------------------------------------------------------------
def assistant(state: ResearchState) -> dict:
    """Nó do assistente — invoca o LLM com o histórico de mensagens."""
    logger.info("Executando nó 'assistant' — %d mensagens no estado", len(state["messages"]))
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + state["messages"]
    response = model_with_tools.invoke(messages)

    # Log se o modelo decidiu chamar ferramentas ou responder
    if hasattr(response, "tool_calls") and response.tool_calls:
        tool_names = [tc["name"] for tc in response.tool_calls]
        logger.info("Modelo chamou ferramentas: %s", tool_names)
    else:
        logger.info("Modelo respondeu diretamente (sem tool calls)")

    return {"messages": [response]}


# --------------------------------------------------------------------------
# 4. Construir o grafo
# --------------------------------------------------------------------------
# StateGraph é o builder do LangGraph. Recebe o tipo do estado, que define
# o "schema" dos dados que fluem entre nós.
builder = StateGraph(ResearchState)
# Nó customizado (nossa função assistant)
builder.add_node("assistant", assistant)
# ToolNode é um nó pronto que executa qualquer tool chamada nas tool_calls
# da última mensagem do estado. Substitui muito boilerplate.
builder.add_node("tools", ToolNode(tools))

# --------------------------------------------------------------------------
# 5. Definir as arestas
# --------------------------------------------------------------------------
# Aresta fixa: o grafo SEMPRE começa indo para o assistant
builder.add_edge(START, "assistant")
# Aresta CONDICIONAL: tools_condition inspeciona a última mensagem.
# Se tem tool_calls → vai pro nó "tools". Se não tem → vai pro END.
builder.add_conditional_edges("assistant", tools_condition)
# Após executar tools, volta pro assistant (fechando o LOOP do ReAct)
builder.add_edge("tools", "assistant")

# --------------------------------------------------------------------------
# 6. Compilar o grafo
# --------------------------------------------------------------------------
# compile() valida o grafo e retorna um objeto invocável.
# Sem checkpointer aqui — este agente é stateless, cada query é independente.
graph = builder.compile()

"""Pokémon Trade Center — Agente Conversacional com HITL.

Este agente demonstra o padrão mais avançado do LangGraph:
- ReAct loop conversacional (o LLM decide quando usar tools)
- interrupt() para aprovação humana (trocas raras)
- Aprovação externa via tool de check (trocas lendárias)
- Checkpointing para persistir estado entre interações

Grafo:
    START → assistant → [tools_condition] → tools → assistant → ... → END

Importante: o nó assistant é um ReAct PURO. Ele não sabe nada sobre tiers
de troca ou aprovação humana. Toda a lógica de HITL vive DENTRO da tool
propor_troca, que chama interrupt() quando detecta uma troca rara. Isso
mantém o nó simples e isola as regras de negócio nas tools.

Referência no textbook: Capítulo 4.

Conceitos-chave para estudantes:
    - **ReAct loop**: O LLM "raciocina" (Reason) e "age" (Act) em ciclo.
      Ele decide sozinho quando chamar ferramentas e quando responder.
    - **HITL (Human-in-the-Loop)**: Padrão onde o agente PAUSA a execução
      e espera uma decisão humana antes de continuar.
    - **interrupt()**: Primitiva do LangGraph que pausa o grafo. Pode ser
      chamada em QUALQUER lugar — dentro de um nó OU dentro de uma tool.
      O estado é salvo pelo checkpointer e pode ser retomado com Command(resume=...).
    - **Checkpointing**: Salva snapshots do estado em cada passo. Permite
      retomar conversas e inspecionar o histórico.
"""

import logging

# --- Imports do LangChain / LangGraph ---
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.memory import InMemorySaver  # Checkpointer em memória (dev/testes)
from langgraph.graph import START, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition  # Componentes prontos do ReAct

from agents.config import settings
from agents.trade.state import TradeState
from agents.trade.tools import (
    check_professor_approval,
    comparar_poder_pokemon,
    consultar_pokemon,
    propor_troca,
    registrar_troca,
)

logger = logging.getLogger("agents.trade")

# --- System Prompt ---
# O system prompt é crucial: ele define a "personalidade" e as regras do agente.
# O LLM usa essas instruções para decidir QUANDO chamar cada ferramenta.
# Note que incluímos regras específicas sobre os tiers de troca — isso guia
# o comportamento do agente sem precisar de lógica hard-coded no grafo.
SYSTEM_PROMPT = """\
Você é o atendente do Pokémon Trade Center, um assistente simpático e \
conhecedor do universo Pokémon.

Suas capacidades:
- Consultar informações detalhadas de qualquer Pokémon
- Comparar o poder entre dois Pokémon
- Propor e processar trocas de Pokémon
- Verificar aprovações pendentes do Professor Oak

Diretrizes:
- Sempre responda em português brasileiro
- Seja conversacional e simpático — responda cumprimentos, tire dúvidas
- Use referências ao universo Pokémon quando apropriado
- Só proponha uma troca quando o treinador pedir explicitamente
- Ao receber uma proposta de troca, use a ferramenta propor_troca
- Para trocas raras, após receber o resultado da tool, peça confirmação \
ao treinador antes de prosseguir
- Para trocas lendárias, informe que o Professor Oak precisa aprovar
- Quando o treinador perguntar sobre uma troca pendente, use \
check_professor_approval
- IMPORTANTE: passe sempre o thread_id para as ferramentas que pedem. \
O thread_id da conversa atual é fornecido no estado.
"""

# --- Ferramentas disponíveis para o agente ---
# Cada ferramenta é decorada com @tool e tem docstring que o LLM lê para
# decidir quando usá-la. A ORDEM aqui não importa — o LLM escolhe com base
# no contexto da conversa e nas docstrings.
tools = [
    consultar_pokemon,
    comparar_poder_pokemon,
    propor_troca,
    registrar_troca,
    check_professor_approval,
]

# --- Configuração do modelo ---
model = ChatGoogleGenerativeAI(
    model=settings.gemini_model,
    google_api_key=settings.google_api_key,
)
# bind_tools() "ensina" o modelo sobre as ferramentas disponíveis.
# Internamente, converte as docstrings das tools em function calling schema.
# O modelo agora pode decidir chamar ferramentas nas suas respostas.
model_with_tools = model.bind_tools(tools)


# --- Nó principal do assistente ---
# Este nó é o ReAct puro: chama o LLM, ele decide se usa tools ou responde.
# Toda a lógica de HITL (interrupt para trocas raras) vive DENTRO da tool
# propor_troca — o nó assistant não precisa saber sobre tiers de troca.
def assistant(state: TradeState) -> dict:
    """Nó do assistente — invoca o LLM com o histórico de mensagens.

    Padrão ReAct simples (idêntico ao agente de pesquisa). O HITL é
    transparente do ponto de vista deste nó: quando a tool propor_troca
    chama interrupt() internamente, o grafo pausa naturalmente na execução
    da tool. Após resume, a tool retorna seu valor e o ReAct continua.
    """
    logger.info("Nó 'assistant' — processando mensagem")

    # Prepend do system prompt — ele não é persistido no estado para evitar
    # duplicação a cada turno. É adicionado fresco a cada chamada do LLM.
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + state["messages"]
    response = model_with_tools.invoke(messages)

    if hasattr(response, "tool_calls") and response.tool_calls:
        tool_names = [tc["name"] for tc in response.tool_calls]
        logger.info("Modelo chamou ferramentas: %s", tool_names)
    else:
        logger.info("Modelo respondeu diretamente")

    return {"messages": [response]}


# --------------------------------------------------------------------------
# Construção do grafo
# --------------------------------------------------------------------------
# Aqui montamos o grafo "tijolo por tijolo": criamos os nós, ligamos com
# arestas, e finalmente compilamos com um checkpointer para HITL funcionar.
builder = StateGraph(TradeState)

# --- Nós ---
# "assistant": ReAct puro — chama o LLM e devolve a resposta
# "tools": ToolNode executa qualquer tool chamada pelo LLM. É AQUI que
#          o interrupt() de propor_troca acontece, transparentemente
builder.add_node("assistant", assistant)
builder.add_node("tools", ToolNode(tools))

# --- Arestas ---
# START → assistant: ponto de entrada do grafo
builder.add_edge(START, "assistant")
# assistant → tools (se houver tool_calls) OU END (se resposta final).
# tools_condition é um helper que inspeciona a última mensagem do estado
# e roteia automaticamente baseado na presença de tool_calls.
builder.add_conditional_edges("assistant", tools_condition)
# tools → assistant: depois de executar tools, volta pro assistente para
# que o LLM processe os resultados. Isso forma o LOOP do ReAct.
builder.add_edge("tools", "assistant")

# --- Checkpointer ---
# InMemorySaver guarda os snapshots em RAM (perde tudo ao reiniciar).
# Em produção use SqliteSaver ou PostgresSaver para persistência real.
# CHECKPOINTER É OBRIGATÓRIO para que interrupt()/resume() funcionem!
checkpointer = InMemorySaver()
graph = builder.compile(checkpointer=checkpointer)

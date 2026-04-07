"""Agente financeiro usando create_agent (LangGraph >= 1.0).

Este é o exemplo mais simples de criação de agente: basta fornecer
o modelo, as ferramentas e um prompt de sistema. O LangGraph cuida
de todo o ciclo ReAct automaticamente.

Referência no textbook: Capítulo 4, Seção 4.4.1 (Abordagem Prebuilt).
"""

from langchain.agents import create_agent
from langchain_google_genai import ChatGoogleGenerativeAI

from agents.config import settings
from agents.financial.tools import (
    calcular_retorno_acao,
    comparar_acoes,
    consultar_cotacao_acao,
    consultar_cotacao_moeda,
)

# Prompt de sistema que define o comportamento do agente
SYSTEM_PROMPT = """Você é um assistente financeiro especializado em mercado de ações e câmbio.

Suas capacidades:
- Consultar cotações de moedas (dólar, euro, bitcoin, etc.) em tempo real
- Consultar preços de ações na bolsa (brasileira e americana)
- Calcular retorno histórico de ações em qualquer período
- Comparar performance de múltiplas ações

Diretrizes:
- Sempre responda em português brasileiro
- Apresente valores monetários formatados (R$ para reais)
- Quando comparar ações, destaque a de melhor desempenho
- Se o usuário não especificar o sufixo .SA para ações brasileiras, adicione automaticamente
- Seja objetivo e direto nas respostas
"""

# Lista de ferramentas disponíveis para o agente
tools = [
    consultar_cotacao_moeda,
    consultar_cotacao_acao,
    calcular_retorno_acao,
    comparar_acoes,
]

# Modelo Gemini configurado via variáveis de ambiente
model = ChatGoogleGenerativeAI(
    model=settings.gemini_model,
    google_api_key=settings.google_api_key,
)

# --------------------------------------------------------------------------
# Criação do agente — é só isso!
# --------------------------------------------------------------------------
# O create_agent é a abordagem PREBUILT — recomendada para a maioria dos
# casos. Internamente ele monta o mesmo grafo ReAct que construímos
# manualmente em research/agent.py:
#
#   START → assistant → [tools_condition] → tools → assistant → ... → END
#
# Quando usar create_agent vs construção manual?
#   - Use create_agent quando você só precisa do loop ReAct padrão
#   - Construa manualmente quando precisar customizar nós, adicionar
#     guardrails, HITL, ou orquestrar múltiplos sub-agentes
graph = create_agent(model, tools=tools, system_prompt=SYSTEM_PROMPT)

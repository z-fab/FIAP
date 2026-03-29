"""
Controle de timeouts — Stage 04 (Production).

Por que timeouts sao criticos em servicos com LLM?
----------------------------------------------------
Modelos de linguagem sao nao-deterministicos em latencia: a mesma
pergunta pode levar 2s ou 60s dependendo da complexidade da resposta,
do loop de ferramentas e da carga do provider (Google, OpenAI, etc.).

Sem timeout:
- Uma requisicao travada mantem o semaforo ocupado indefinidamente
- O cliente espera para sempre (ou ate o timeout do load balancer)
- Resources leak: memoria, conexoes, file descriptors

Camadas de timeout neste estagio
---------------------------------
1. AGENT_TIMEOUT (20s) — tempo maximo para o agente completar todo o
   loop ReAct (inclui todas as chamadas de ferramenta + inferencias).
   Esse e o timeout REAL que cancela a coroutine via asyncio.wait_for.

2. TOOL_TIMEOUT (10s) — tempo maximo por chamada individual de
   ferramenta. Implementado DENTRO da ferramenta como protecao:
   se uma query SQL travar, a ferramenta retorna uma STRING de erro
   para o LLM (que pode tentar de novo), em vez de consumir todo o
   budget do AGENT_TIMEOUT.

   IMPORTANTE: o TOOL_TIMEOUT nao levanta excecao. No LangGraph,
   ferramentas que levantam excecoes abortam o agente. Ferramentas
   que retornam strings de erro permitem que o LLM se adapte
   (corrigir a query, tentar outra abordagem). Essa e a convencao
   do ecossistema LangChain/LangGraph.

Por que nao existe REQUEST_TIMEOUT como middleware?
----------------------------------------------------
Em producao real, o timeout HTTP e responsabilidade do reverse proxy
(nginx, envoy, ALB) — nao da aplicacao. Definir um timeout HTTP na
app cria uma "corrida" entre o proxy e a app que dificulta debug.
O AGENT_TIMEOUT ja garante que a app responde em tempo finito.
"""

from __future__ import annotations

import asyncio
import os
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

from errors import AgentTimeoutError

# ---------------------------------------------------------------------------
# Configuracao via variaveis de ambiente
# ---------------------------------------------------------------------------

AGENT_TIMEOUT: int = int(os.getenv("AGENT_TIMEOUT", "20"))
"""
Timeout para a execucao completa do agente em segundos.

Esse e o unico timeout que CANCELA a operacao. Quando dispara:
1. asyncio.wait_for cancela a coroutine do agente
2. AgentTimeoutError e levantada (HTTP 504)
3. O exception handler converte em JSON para o cliente
"""

TOOL_TIMEOUT: int = int(os.getenv("TOOL_TIMEOUT", "10"))
"""
Timeout por chamada individual de ferramenta em segundos.

Diferente do AGENT_TIMEOUT, esse timeout NAO levanta excecao.
A ferramenta retorna uma string de erro que o LLM pode ler e
decidir como proceder (tentar de novo, responder sem dados, etc.).

Valor padrao 10s: metade do AGENT_TIMEOUT, garantindo que uma
ferramenta travada nao consuma todo o budget do agente.
"""


# ---------------------------------------------------------------------------
# Timeout assincrono — cancela a coroutine (usado no endpoint)
# ---------------------------------------------------------------------------


async def with_timeout(
    coro,
    timeout_seconds: float,
    context: str = "operacao",
) -> any:
    """
    Executa uma coroutine com timeout e converte asyncio.TimeoutError
    em AgentTimeoutError com contexto descritivo.

    Esse wrapper e usado nos endpoints HTTP para limitar o tempo total
    do agente. Quando o timeout dispara, asyncio CANCELA a coroutine
    (envia CancelledError), liberando recursos.

    Argumentos:
        coro: coroutine a ser executada.
        timeout_seconds: tempo maximo de espera em segundos.
        context: descricao da operacao (para mensagem de erro legivel).

    Retorna:
        Resultado da coroutine.

    Levanta:
        AgentTimeoutError: se a coroutine nao completar no tempo limite.

    Exemplo:
        result = await with_timeout(
            agent.run(message),
            timeout_seconds=20,
            context="execucao do agente",
        )
    """
    try:
        return await asyncio.wait_for(coro, timeout=timeout_seconds)
    except asyncio.TimeoutError:
        raise AgentTimeoutError(
            f"Timeout de {timeout_seconds}s excedido em: {context}"
        )


# ---------------------------------------------------------------------------
# Timeout sincrono — retorna erro como string (usado nas ferramentas)
# ---------------------------------------------------------------------------


def run_with_tool_timeout(func, timeout_seconds: float = TOOL_TIMEOUT, context: str = "ferramenta"):
    """
    Executa uma funcao sincrona com timeout. Em vez de levantar excecao,
    retorna uma tupla (resultado, erro) para que a ferramenta possa
    devolver o erro como string ao LLM.

    Por que nao levantar excecao?
    No LangGraph, excecoes de ferramentas abortam o loop do agente ou
    sao convertidas em mensagens de erro genericas. Retornando o erro
    como string, o LLM recebe contexto preciso e pode se adaptar.

    Por que ThreadPoolExecutor?
    Ferramentas como search_database usam sqlite3, que e sincrono.
    Nao podemos usar asyncio.wait_for em codigo sincrono. O executor
    roda a funcao em uma thread separada e aplica o timeout na espera.

    Limitacao conhecida: quando o timeout dispara, a thread continua
    executando ate terminar naturalmente. Para bancos de dados reais
    (PostgreSQL, MySQL), use o parametro statement_timeout do banco
    em vez deste wrapper.

    Argumentos:
        func: callable sem argumentos (use lambda/closure para capturar params).
        timeout_seconds: tempo maximo em segundos.
        context: nome da operacao para a mensagem de erro.

    Retorna:
        Tupla (resultado, None) em caso de sucesso, ou
        (None, "mensagem de erro") em caso de timeout.

    Exemplo:
        result, error = run_with_tool_timeout(
            lambda: conn.execute(query).fetchall(),
            timeout_seconds=10,
            context="search_database",
        )
        if error:
            return error  # LLM recebe a string de erro
    """
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(func)
        try:
            result = future.result(timeout=timeout_seconds)
            return result, None
        except FuturesTimeoutError:
            return None, (
                f"ERRO: Timeout de {timeout_seconds}s excedido em {context}. "
                f"A operacao demorou mais que o permitido."
            )

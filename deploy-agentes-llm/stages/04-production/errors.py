"""
Hierarquia de erros do servico — Stage 04 (Production).

Por que criar excecoes customizadas em vez de usar HTTPException?
-----------------------------------------------------------------
1. **Separacao de responsabilidades**: a logica de negocio (agent.py,
   concurrency.py, timeouts.py) nao precisa conhecer HTTP. Ela lanca
   excecoes de dominio; o handler da FastAPI converte para respostas HTTP.

2. **Codigo de status semantico**: cada excecao mapeia para um status HTTP
   que comunica claramente a natureza do problema ao cliente:
   - 429 → servidor sobrecarregado, tente depois
   - 504 → agente demorou demais
   - 502 → ferramenta externa falhou (uso direto, fora do LangGraph)
   - 500 → erro generico interno

3. **Observabilidade**: logs estruturados capturam a classe da excecao,
   facilitando dashboards de erro por tipo.

4. **Testabilidade**: testes unitarios verificam excecoes sem dependencia
   de HTTP.

Onde cada excecao e levantada
------------------------------
- AgentTimeoutError  → timeouts.py (with_timeout quando asyncio cancela)
- ConcurrencyLimitError → concurrency.py (semaforo cheio)
- ToolExecutionError → reservada para chamadas diretas de ferramenta
                        (fora do loop LangGraph, ex: health checks)
- AgentExecutionError → main.py (catch-all para erros nao categorizados)

Nota sobre ToolExecutionError e LangGraph
-------------------------------------------
Ferramentas chamadas pelo create_react_agent NAO devem levantar excecoes
— devem retornar strings de erro. O LangGraph captura excecoes de
ferramentas internamente e as converte em mensagens genericas,
perdendo contexto. ToolExecutionError existe para cenarios onde
ferramentas sao chamadas FORA do loop do agente (ex: validacao
pre-execucao, health checks de dependencias).
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


# ---------------------------------------------------------------------------
# Excecoes de dominio
# ---------------------------------------------------------------------------


class AgentServiceError(Exception):
    """
    Excecao base do servico. Todas as excecoes customizadas herdam desta.

    O exception handler registrado em register_error_handlers() captura
    QUALQUER subclasse de AgentServiceError e a converte automaticamente
    em uma resposta JSON com o status_code correto.

    Atributos:
        status_code: codigo HTTP que o handler deve retornar.
        detail: mensagem descritiva do erro.
    """

    status_code: int = 500

    def __init__(self, detail: str = "Erro interno do servico."):
        self.detail = detail
        super().__init__(detail)


class AgentTimeoutError(AgentServiceError):
    """
    O agente (ou uma etapa dele) excedeu o tempo limite configurado.

    HTTP 504 Gateway Timeout — indica ao cliente que o backend nao
    respondeu a tempo. Ideal para que load balancers e clientes
    implementem retry com backoff.

    Levantada por: timeouts.with_timeout() quando asyncio.wait_for
    cancela a coroutine do agente.
    """

    status_code: int = 504

    def __init__(self, detail: str = "Tempo limite de execucao excedido."):
        super().__init__(detail)


class ConcurrencyLimitError(AgentServiceError):
    """
    O servico atingiu o limite de execucoes simultaneas e a fila de
    espera tambem esta cheia.

    HTTP 429 Too Many Requests — instrui o cliente a aguardar antes de
    tentar novamente. Em producao, um header Retry-After pode ser
    adicionado para guiar o backoff.

    Levantada por: concurrency.AgentSemaphore.acquire() quando a fila
    atinge MAX_QUEUE_SIZE.
    """

    status_code: int = 429

    def __init__(self, detail: str = "Limite de concorrencia atingido. Tente novamente em instantes."):
        super().__init__(detail)


class ToolExecutionError(AgentServiceError):
    """
    Uma ferramenta externa (banco, API, etc.) falhou durante execucao
    FORA do loop do agente LangGraph.

    HTTP 502 Bad Gateway — o servico agiu como gateway e recebeu uma
    resposta invalida do upstream (a ferramenta).

    IMPORTANTE: ferramentas chamadas DENTRO do loop do agente (via
    create_react_agent) devem retornar strings de erro, nao levantar
    esta excecao. O LangGraph captura excecoes de ferramentas
    internamente — levantar aqui abortaria o agente sem dar chance
    ao LLM de se adaptar.

    Uso tipico: chamadas diretas a ferramentas fora do agente,
    como validacoes pre-execucao ou health checks de dependencias.
    """

    status_code: int = 502

    def __init__(self, detail: str = "Erro na execucao de ferramenta externa."):
        super().__init__(detail)


class AgentExecutionError(AgentServiceError):
    """
    Erro generico durante a execucao do agente LLM.

    HTTP 500 Internal Server Error — captura falhas nao categorizadas
    que ocorrem no pipeline do agente.

    Levantada por: main.py quando o agente falha com uma excecao que
    nao e AgentServiceError (ex: erro de rede, bug no codigo, etc.).
    """

    status_code: int = 500

    def __init__(self, detail: str = "Erro durante a execucao do agente."):
        super().__init__(detail)


# ---------------------------------------------------------------------------
# Registro de handlers na aplicacao FastAPI
# ---------------------------------------------------------------------------


def register_error_handlers(app: FastAPI) -> None:
    """
    Registra um exception handler global que converte qualquer
    AgentServiceError em uma resposta JSON padronizada.

    Este e o UNICO ponto de logging de erros de dominio. Os endpoints
    nao logam erros — apenas re-levantam. Centralizar o logging aqui
    evita duplicacao e garante formato consistente.

    Formato da resposta:
        {
            "error": "AgentTimeoutError",
            "detail": "Timeout de 20s excedido em: execucao do agente"
        }

    Niveis de log por tipo de erro:
    - 429 (ConcurrencyLimitError) → warning (comportamento esperado sob carga)
    - 504 (AgentTimeoutError) → warning (timeout e operacional, nao bug)
    - 502 (ToolExecutionError) → error (falha de dependencia externa)
    - 500 (AgentExecutionError) → error (falha inesperada, precisa investigar)
    """
    import structlog

    @app.exception_handler(AgentServiceError)
    async def _handle_agent_error(request: Request, exc: AgentServiceError) -> JSONResponse:
        logger = structlog.get_logger("error_handler")

        # Nivel de log baseado na severidade: erros 4xx sao operacionais
        # (warning), erros 5xx indicam falha real (error).
        # Excecao: 504 timeout e operacional em servicos LLM — a latencia
        # do modelo e imprevisivel e timeouts sao esperados sob carga.
        log_level = "warning" if exc.status_code in (429, 504) else "error"

        getattr(logger, log_level)(
            "agent_error_response",
            error=type(exc).__name__,
            detail=exc.detail,
            status_code=exc.status_code,
            path=request.url.path,
            method=request.method,
        )

        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": type(exc).__name__,
                "detail": exc.detail,
            },
        )

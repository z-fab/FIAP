"""
Agente de analise de vendas — Stage 04 (Production)

Implementacao de referencia: LangGraph ReAct + Gemini 2.5 Flash.
Contem duas ferramentas: consulta SQL e calculadora segura via modulo ast.

Tratamento de erros nas ferramentas
-------------------------------------
Ferramentas do LangGraph devem RETORNAR strings de erro, nao levantar
excecoes. Motivo: o create_react_agent captura excecoes internamente
e as converte em mensagens genericas. Retornando strings, o LLM recebe
contexto preciso sobre o que falhou e pode se adaptar (corrigir query,
tentar abordagem diferente, ou informar o usuario).

Timeout nas ferramentas
------------------------
Cada ferramenta usa run_with_tool_timeout para limitar o tempo de
operacoes sincronas (ex: queries SQL). O timeout retorna string de
erro — nao levanta excecao — permitindo que o LLM decida o proximo
passo dentro do budget do AGENT_TIMEOUT.

Nota de seguranca: a calculadora usa ast.parse() + travessia manual
da AST para avaliar expressoes matematicas de forma segura, percorrendo
a arvore sintatica noh por noh e aceitando apenas literais numericos,
operadores aritmeticos e funcoes da lista de permissoes.
"""

from __future__ import annotations

import ast
import operator
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, AsyncGenerator

from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent
from rich.console import Console

from timeouts import TOOL_TIMEOUT, run_with_tool_timeout

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

SEED_SQL_PATH = Path(__file__).parent / "seed.sql"

_console = Console(force_terminal=True)

# ---------------------------------------------------------------------------
# Tipos de retorno publicos
# ---------------------------------------------------------------------------


@dataclass
class AgentResult:
    """Resultado completo de uma invocacao do agente."""

    output: str
    """Resposta final em texto."""

    tools_used: list[str]
    """Nomes das ferramentas invocadas durante a invocacao."""

    token_count: int
    """Total de tokens consumidos (entrada + saida), quando disponivel."""

    step_count: int
    """Numero de passos (iteracoes) do loop ReAct."""

    duration_ms: int
    """Tempo total de invocacao em milissegundos."""


@dataclass
class AgentEvent:
    """Evento emitido durante a invocacao em streaming do agente."""

    type: str
    """
    Tipo do evento. Valores possiveis:
    - "step_start"   — inicio de um passo do loop ReAct
    - "tool_call"    — chamada de ferramenta pelo modelo
    - "tool_result"  — resultado devolvido pela ferramenta
    - "token"        — fragmento de texto gerado (streaming de tokens)
    - "done"         — invocacao concluida; data contem AgentResult completo
    """

    data: dict[str, Any]
    """Carga util do evento. Estrutura depende do tipo."""


# ---------------------------------------------------------------------------
# Banco de dados SQLite em memoria (singleton)
# ---------------------------------------------------------------------------

_db_connection: sqlite3.Connection | None = None


def _get_db() -> sqlite3.Connection:
    """
    Retorna a conexao SQLite em memoria, criando-a na primeira chamada.

    O banco e populado a partir de seed.sql e mantido durante toda a
    vida do processo (singleton, seguro para uso sincrono).
    """
    global _db_connection

    if _db_connection is None:
        _console.print("[bold cyan]Iniciando banco de dados em memoria...[/]")
        _db_connection = sqlite3.connect(":memory:", check_same_thread=False)
        _db_connection.row_factory = sqlite3.Row

        seed_sql = SEED_SQL_PATH.read_text(encoding="utf-8")
        _db_connection.executescript(seed_sql)
        _db_connection.commit()

        _console.print("[bold green]Banco de dados pronto.[/]")

    return _db_connection


# ---------------------------------------------------------------------------
# Ferramentas do agente
# ---------------------------------------------------------------------------


@tool
def search_database(query: str) -> str:
    """
    Roda uma consulta SELECT no banco de dados de vendas e retorna
    os resultados formatados como tabela de texto.

    Use esta ferramenta para buscar dados sobre produtos, regioes,
    trimestres, receita, unidades vendidas e custo.

    A tabela 'sales' possui as colunas:
    - id          (INTEGER) — identificador unico
    - product     (TEXT)    — nome do produto
    - region      (TEXT)    — regiao geografica
    - quarter     (TEXT)    — trimestre (Q1, Q2, Q3, Q4)
    - year        (INTEGER) — ano (2024 ou 2025)
    - revenue     (REAL)    — receita em reais
    - units_sold  (INTEGER) — unidades vendidas
    - cost        (REAL)    — custo em reais

    Argumentos:
        query: Instrucao SQL SELECT a ser rodada.

    Retorna:
        Tabela de resultados em texto ou mensagem de erro.
    """
    # ---- Validacao: apenas SELECT e permitido ----------------------------
    normalized = query.strip().upper()
    if not normalized.startswith("SELECT"):
        return (
            "ERRO: Apenas consultas SELECT sao permitidas. "
            f"A query recebida comeca com: '{query.strip()[:30]}'"
        )

    # ---- Execucao com timeout --------------------------------------------
    # run_with_tool_timeout roda a query em uma thread separada e aplica
    # TOOL_TIMEOUT. Se a query demorar demais, retorna (None, "mensagem")
    # em vez de levantar excecao — permitindo que o LLM leia o erro.
    conn = _get_db()

    def _exec_query():
        cursor = conn.execute(query)
        return cursor.description, cursor.fetchall()

    try:
        query_result, timeout_error = run_with_tool_timeout(
            _exec_query,
            timeout_seconds=TOOL_TIMEOUT,
            context="search_database",
        )
    except sqlite3.Error as e:
        # Erros SQL (sintaxe, tabela inexistente, etc.) sao retornados
        # como string para que o LLM possa corrigir a query e tentar
        # novamente — esse e o padrao do ecossistema LangChain/LangGraph.
        return f"ERRO ao rodar consulta SQL: {e}"

    # Se houve timeout, retorna a mensagem de erro para o LLM
    if timeout_error:
        return timeout_error

    # ---- Formatacao dos resultados ---------------------------------------
    col_info, rows = query_result

    if not rows:
        return "Nenhum resultado encontrado para esta consulta."

    column_names = [description[0] for description in col_info]

    col_widths = [len(name) for name in column_names]
    for row in rows:
        for i, value in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(value)))

    separator = "+" + "+".join("-" * (w + 2) for w in col_widths) + "+"
    header = (
        "|"
        + "|".join(
            f" {name:<{col_widths[i]}} " for i, name in enumerate(column_names)
        )
        + "|"
    )

    lines = [separator, header, separator]

    for row in rows:
        data_line = (
            "|"
            + "|".join(
                f" {str(value):<{col_widths[i]}} " for i, value in enumerate(row)
            )
            + "|"
        )
        lines.append(data_line)

    lines.append(separator)
    lines.append(f"Total: {len(rows)} linha(s)")

    return "\n".join(lines)


# Operadores binarios e unarios permitidos na calculadora
_SAFE_OPERATORS: dict[type, Any] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

# Funcoes matematicas da biblioteca padrao que sao permitidas
_SAFE_FUNCTIONS: dict[str, Any] = {
    "abs": abs,
    "round": round,
    "min": min,
    "max": max,
    "sum": sum,
    "pow": pow,
}


def _safe_ast_walk(node: ast.AST) -> int | float:
    """
    Avalia recursivamente um noh AST de forma segura.

    Utiliza o modulo ast para parsear a expressao e percorre a arvore
    sintatica manualmente. Apenas literais numericos, operadores
    aritmeticos e as funcoes da lista de permissoes sao aceitos.

    Retorna int quando o noh e um inteiro literal, float caso contrario.
    Isso e necessario para funcoes como round(x, n) que exigem n inteiro.
    """
    if isinstance(node, ast.Constant):
        if isinstance(node.value, int):
            return node.value
        if isinstance(node.value, float):
            return node.value
        raise ValueError(f"Literal nao numerico: {node.value!r}")

    if isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type not in _SAFE_OPERATORS:
            raise ValueError(f"Operador nao permitido: {op_type.__name__}")
        left = _safe_ast_walk(node.left)
        right = _safe_ast_walk(node.right)
        return _SAFE_OPERATORS[op_type](left, right)

    if isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type not in _SAFE_OPERATORS:
            raise ValueError(f"Operador unario nao permitido: {op_type.__name__}")
        operand = _safe_ast_walk(node.operand)
        return _SAFE_OPERATORS[op_type](operand)

    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name):
            raise ValueError("Chamadas de metodo encadeadas nao sao permitidas.")
        func_name = node.func.id
        if func_name not in _SAFE_FUNCTIONS:
            raise ValueError(f"Funcao nao permitida: {func_name!r}")
        args = [_safe_ast_walk(arg) for arg in node.args]
        return _SAFE_FUNCTIONS[func_name](*args)

    raise ValueError(f"Expressao nao suportada: {ast.dump(node)}")


@tool
def calculate(expression: str) -> str:
    """
    Avalia uma expressao matematica de forma segura via modulo ast.

    Suporta operadores: + - * / ** e parenteses.
    Funcoes disponiveis: abs, round, min, max, sum, pow.

    Exemplos validos:
    - "1500000 + 2300000"
    - "(540000 - 320000) / 320000 * 100"
    - "round(1234567.89, 2)"
    - "max(450000, 620000, 390000)"

    Argumentos:
        expression: Expressao matematica em texto.

    Retorna:
        Resultado numerico formatado ou mensagem de erro.
    """
    try:
        tree = ast.parse(expression.strip(), mode="eval")
        result = _safe_ast_walk(tree.body)

        if isinstance(result, float) and result == int(result) and abs(result) < 1e15:
            return str(int(result))

        return str(result)

    except (ValueError, ZeroDivisionError) as e:
        return f"ERRO na expressao: {e}"
    except SyntaxError as e:
        return f"ERRO de sintaxe na expressao: {e}"


# ---------------------------------------------------------------------------
# Prompt do sistema
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """Voce e Ana, analista senior de vendas da empresa.
Sua especialidade e transformar dados em insights claros e acionaveis.

Voce tem acesso a dois recursos:
1. **search_database** — consulta o banco de dados de vendas em SQL.
2. **calculate** — realiza calculos matematicos com seguranca.

Produtos disponiveis: Software Enterprise, Cloud Platform, Data Analytics,
Security Suite, AI Assistant.

Regioes: Norte, Sul, Sudeste, Nordeste, Centro-Oeste.

Periodos: Q1 a Q4 dos anos 2024 e 2025.

**Instrucoes de comportamento:**
- Sempre consulte o banco antes de responder sobre dados especificos.
- Use calculate para percentuais, variacoes e totais.
- Apresente os numeros em formato brasileiro (R$ com separadores de milhar).
- Destaque tendencias e variacoes relevantes.
- Seja objetiva e direta, sem rodeios desnecessarios.
- Se nao encontrar dados, informe claramente ao usuario.
"""

# ---------------------------------------------------------------------------
# Agente LangGraph (singleton)
# ---------------------------------------------------------------------------

_agent = None


def reset_agent() -> None:
    """Força a recriação do agente na próxima chamada.

    Necessário em workers Celery (fork): o httpx.AsyncClient interno ao
    ChatGoogleGenerativeAI guarda referência ao event loop do processo pai,
    que não existe nos processos filhos. Resetar o singleton garante que
    um novo client será criado no loop correto.
    """
    global _agent
    _agent = None


def _get_agent() -> Any:
    """
    Retorna o agente LangGraph, criando-o na primeira chamada (lazy init).

    Usa gemini-2.5-flash com o framework ReAct do LangGraph e as duas
    ferramentas registradas: search_database e calculate.
    """
    global _agent

    if _agent is None:
        _console.print("[bold cyan]Inicializando agente Gemini 2.5 Flash...[/]")

        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            temperature=0,
        )

        _agent = create_react_agent(
            model=llm,
            tools=[search_database, calculate],
            prompt=_SYSTEM_PROMPT,
        )

        _console.print("[bold green]Agente pronto.[/]")

    return _agent


# ---------------------------------------------------------------------------
# Interfaces publicas
# ---------------------------------------------------------------------------


async def run(message: str) -> AgentResult:
    """
    Invoca o agente de forma assincrona e retorna o resultado completo.

    Argumentos:
        message: Pergunta ou instrucao em linguagem natural.

    Retorna:
        AgentResult com resposta, metricas e metadados da invocacao.
    """
    agent = _get_agent()

    start_time = time.monotonic()

    tools_used: list[str] = []
    step_count = 0
    total_tokens = 0
    final_output = ""

    state = {"messages": [HumanMessage(content=message)]}
    result = await agent.ainvoke(state)

    messages = result.get("messages", [])

    for msg in messages:
        step_count += 1

        tool_calls = getattr(msg, "tool_calls", None)
        if tool_calls:
            for tc in tool_calls:
                tool_name = (
                    tc.get("name") if isinstance(tc, dict) else getattr(tc, "name", "")
                )
                if tool_name:
                    tools_used.append(tool_name)

        usage = getattr(msg, "usage_metadata", None)
        if usage:
            total_tokens += usage.get("total_tokens", 0) or 0

    last_msg = messages[-1] if messages else None
    if last_msg is not None:
        raw_content = getattr(last_msg, "content", str(last_msg))
        # Gemini via LangChain pode retornar content como lista de dicts
        # (ex: [{"type": "text", "text": "..."}]) em vez de string pura.
        if isinstance(raw_content, list):
            final_output = " ".join(
                part.get("text", "") if isinstance(part, dict) else str(part)
                for part in raw_content
            )
        else:
            final_output = str(raw_content)

    duration_ms = int((time.monotonic() - start_time) * 1000)

    return AgentResult(
        output=final_output,
        tools_used=tools_used,
        token_count=total_tokens,
        step_count=step_count,
        duration_ms=duration_ms,
    )


async def run_stream(message: str) -> AsyncGenerator[AgentEvent, None]:
    """
    Invoca o agente em modo streaming, emitindo eventos incrementalmente.

    Argumentos:
        message: Pergunta ou instrucao em linguagem natural.

    Yields:
        AgentEvent com tipo e dados do passo atual.
    """
    agent = _get_agent()

    start_time = time.monotonic()

    tools_used: list[str] = []
    step_count = 0
    total_tokens = 0
    final_output = ""

    state = {"messages": [HumanMessage(content=message)]}

    async for chunk in agent.astream(state, stream_mode="updates"):
        for node_name, node_output in chunk.items():
            step_count += 1

            yield AgentEvent(
                type="step_start",
                data={"node": node_name, "step": step_count},
            )

            messages = node_output.get("messages", [])
            for msg in messages:
                tool_calls = getattr(msg, "tool_calls", None)
                if tool_calls:
                    for tc in tool_calls:
                        tool_name = (
                            tc.get("name")
                            if isinstance(tc, dict)
                            else getattr(tc, "name", "")
                        )
                        tool_args = (
                            tc.get("args")
                            if isinstance(tc, dict)
                            else getattr(tc, "args", {})
                        )
                        if tool_name:
                            tools_used.append(tool_name)
                            yield AgentEvent(
                                type="tool_call",
                                data={"tool": tool_name, "args": tool_args},
                            )

                msg_type = getattr(msg, "type", "")
                if msg_type == "tool":
                    yield AgentEvent(
                        type="tool_result",
                        data={
                            "tool": getattr(msg, "name", ""),
                            "content": getattr(msg, "content", ""),
                        },
                    )

                usage = getattr(msg, "usage_metadata", None)
                if usage:
                    total_tokens += getattr(usage, "total_tokens", 0) or 0

                if msg_type == "ai":
                    content = getattr(msg, "content", "")
                    if content:
                        final_output = content
                        yield AgentEvent(
                            type="token",
                            data={"content": content},
                        )

    duration_ms = int((time.monotonic() - start_time) * 1000)

    yield AgentEvent(
        type="done",
        data={
            "result": AgentResult(
                output=final_output,
                tools_used=tools_used,
                token_count=total_tokens,
                step_count=step_count,
                duration_ms=duration_ms,
            )
        },
    )

"""
Agente de análise de vendas — Stage 01 (Síncrono)

Implementação de referência: LangGraph ReAct + Gemini 2.5 Flash.
Contém duas ferramentas: consulta SQL e calculadora segura via módulo ast.

Este arquivo é idêntico em todos os estágios do curso. O foco de cada
estágio é a infraestrutura de serving construída ao redor deste agente.
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

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

# Caminho do arquivo SQL com os dados de semente
SEED_SQL_PATH = Path(__file__).parent / "seed.sql"

# Console Rich para mensagens de inicialização
_console = Console(force_terminal=True)

# ---------------------------------------------------------------------------
# Tipos de retorno públicos
# ---------------------------------------------------------------------------


@dataclass
class AgentResult:
    """Resultado completo de uma execução do agente."""

    output: str
    """Resposta final em texto."""

    tools_used: list[str]
    """Nomes das ferramentas invocadas durante a execução."""

    token_count: int
    """Total de tokens consumidos (entrada + saída), quando disponível."""

    step_count: int
    """Número de passos (iterações) do loop ReAct."""

    duration_ms: int
    """Tempo total de execução em milissegundos."""


@dataclass
class AgentEvent:
    """Evento emitido durante a execução em streaming do agente."""

    type: str
    """
    Tipo do evento. Valores possíveis:
    - "step_start"   — início de um passo do loop ReAct
    - "tool_call"    — chamada de ferramenta pelo modelo
    - "tool_result"  — resultado devolvido pela ferramenta
    - "token"        — fragmento de texto gerado (streaming de tokens)
    - "done"         — execução concluída; data contém AgentResult completo
    """

    data: dict[str, Any]
    """Carga útil do evento. Estrutura depende do tipo."""


# ---------------------------------------------------------------------------
# Banco de dados SQLite em memória (singleton)
# ---------------------------------------------------------------------------

_db_connection: sqlite3.Connection | None = None


def _get_db() -> sqlite3.Connection:
    """
    Retorna a conexão SQLite em memória, criando-a na primeira chamada.

    O banco é populado a partir de seed.sql e mantido durante toda a
    vida do processo (singleton, seguro para uso síncrono).
    """
    global _db_connection

    if _db_connection is None:
        _console.print("[bold cyan]Iniciando banco de dados em memória...[/]")
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
    Executa uma consulta SELECT no banco de dados de vendas e retorna
    os resultados formatados como tabela de texto.

    Use esta ferramenta para buscar dados sobre produtos, regiões,
    trimestres, receita, unidades vendidas e custo.

    A tabela 'sales' possui as colunas:
    - id          (INTEGER) — identificador único
    - product     (TEXT)    — nome do produto
    - region      (TEXT)    — região geográfica
    - quarter     (TEXT)    — trimestre (Q1, Q2, Q3, Q4)
    - year        (INTEGER) — ano (2024 ou 2025)
    - revenue     (REAL)    — receita em reais
    - units_sold  (INTEGER) — unidades vendidas
    - cost        (REAL)    — custo em reais

    Argumentos:
        query: Instrução SQL SELECT a ser executada.

    Retorna:
        Tabela de resultados em texto ou mensagem de erro.
    """
    # Validação de segurança: apenas SELECT é permitido
    normalized = query.strip().upper()
    if not normalized.startswith("SELECT"):
        return (
            "ERRO: Apenas consultas SELECT são permitidas. "
            f"A query recebida começa com: '{query.strip()[:30]}'"
        )

    try:
        conn = _get_db()
        cursor = conn.execute(query)
        rows = cursor.fetchall()

        if not rows:
            return "Nenhum resultado encontrado para esta consulta."

        # Nomes das colunas
        column_names = [description[0] for description in cursor.description]

        # Calcula largura de cada coluna
        col_widths = [len(name) for name in column_names]
        for row in rows:
            for i, value in enumerate(row):
                col_widths[i] = max(col_widths[i], len(str(value)))

        # Monta cabeçalho
        separator = "+" + "+".join("-" * (w + 2) for w in col_widths) + "+"
        header = (
            "|"
            + "|".join(
                f" {name:<{col_widths[i]}} " for i, name in enumerate(column_names)
            )
            + "|"
        )

        lines = [separator, header, separator]

        # Monta linhas de dados
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

    except sqlite3.Error as exc:
        return f"ERRO ao executar consulta SQL: {exc}"


# Operadores binários e unários permitidos na calculadora
_SAFE_OPERATORS: dict[type, Any] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

# Funções matemáticas da biblioteca padrão que são permitidas
_SAFE_FUNCTIONS: dict[str, Any] = {
    "abs": abs,
    "round": round,
    "min": min,
    "max": max,
    "sum": sum,
    "pow": pow,
}


def _safe_eval(node: ast.AST) -> int | float:
    """
    Avalia recursivamente um nó AST de forma segura.

    Utiliza o módulo ast para parsear a expressão e percorre a árvore
    sintática manualmente, sem recorrer à execução arbitrária de código.
    Apenas literais numéricos, operadores aritméticos e as funções da
    lista de permissões são aceitos.

    Retorna int quando o nó é um inteiro literal, float caso contrário.
    Isso é necessário para funções como round(x, n) que exigem n inteiro.
    """
    if isinstance(node, ast.Constant):
        if isinstance(node.value, int):
            return node.value  # preserva int (necessário para round)
        if isinstance(node.value, float):
            return node.value
        raise ValueError(f"Literal não numérico: {node.value!r}")

    if isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type not in _SAFE_OPERATORS:
            raise ValueError(f"Operador não permitido: {op_type.__name__}")
        left = _safe_eval(node.left)
        right = _safe_eval(node.right)
        return _SAFE_OPERATORS[op_type](left, right)

    if isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type not in _SAFE_OPERATORS:
            raise ValueError(f"Operador unário não permitido: {op_type.__name__}")
        operand = _safe_eval(node.operand)
        return _SAFE_OPERATORS[op_type](operand)

    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name):
            raise ValueError("Chamadas de método encadeadas não são permitidas.")
        func_name = node.func.id
        if func_name not in _SAFE_FUNCTIONS:
            raise ValueError(f"Função não permitida: {func_name!r}")
        args = [_safe_eval(arg) for arg in node.args]
        return _SAFE_FUNCTIONS[func_name](*args)

    raise ValueError(f"Expressão não suportada: {ast.dump(node)}")


@tool
def calculate(expression: str) -> str:
    """
    Avalia uma expressão matemática de forma segura via módulo ast.

    Suporta operadores: + - * / ** e parênteses.
    Funções disponíveis: abs, round, min, max, sum, pow.

    Exemplos válidos:
    - "1500000 + 2300000"
    - "(540000 - 320000) / 320000 * 100"
    - "round(1234567.89, 2)"
    - "max(450000, 620000, 390000)"

    Argumentos:
        expression: Expressão matemática em texto.

    Retorna:
        Resultado numérico formatado ou mensagem de erro.
    """
    try:
        tree = ast.parse(expression.strip(), mode="eval")
        result = _safe_eval(tree.body)

        # Formata sem casas decimais quando o resultado é inteiro
        if isinstance(result, float) and result == int(result) and abs(result) < 1e15:
            return str(int(result))

        return str(result)

    except (ValueError, ZeroDivisionError) as exc:
        return f"ERRO na expressão: {exc}"
    except SyntaxError as exc:
        return f"ERRO de sintaxe na expressão: {exc}"


# ---------------------------------------------------------------------------
# Prompt do sistema
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """Você é Ana, analista sênior de vendas da empresa.
Sua especialidade é transformar dados em insights claros e acionáveis.

Você tem acesso a dois recursos:
1. **search_database** — consulta o banco de dados de vendas em SQL.
2. **calculate** — realiza cálculos matemáticos com segurança.

Produtos disponíveis: Software Enterprise, Cloud Platform, Data Analytics,
Security Suite, AI Assistant.

Regiões: Norte, Sul, Sudeste, Nordeste, Centro-Oeste.

Períodos: Q1 a Q4 dos anos 2024 e 2025.

**Instruções de comportamento:**
- Sempre consulte o banco antes de responder sobre dados específicos.
- Use calculate para percentuais, variações e totais.
- Apresente os números em formato brasileiro (R$ com separadores de milhar).
- Destaque tendências e variações relevantes.
- Seja objetiva e direta, sem rodeios desnecessários.
- Se não encontrar dados, informe claramente ao usuário.
"""

# ---------------------------------------------------------------------------
# Agente LangGraph (singleton)
# ---------------------------------------------------------------------------

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
# Interfaces públicas
# ---------------------------------------------------------------------------


async def run(message: str) -> AgentResult:
    """
    Executa o agente de forma assíncrona e retorna o resultado completo.

    Aguarda a conclusão de todos os passos antes de retornar. Use esta
    interface quando precisar da resposta final sem processamento incremental.

    Argumentos:
        message: Pergunta ou instrução em linguagem natural.

    Retorna:
        AgentResult com resposta, métricas e metadados da execução.
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

        # Contabiliza uso de ferramentas
        tool_calls = getattr(msg, "tool_calls", None)
        if tool_calls:
            for tc in tool_calls:
                tool_name = (
                    tc.get("name") if isinstance(tc, dict) else getattr(tc, "name", "")
                )
                if tool_name:
                    tools_used.append(tool_name)

        # Captura tokens de uso quando disponível
        usage = getattr(msg, "usage_metadata", None)
        if usage:
            total_tokens += usage.get("total_tokens", 0) or 0

    # Última mensagem do agente é a resposta final
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
    Executa o agente em modo streaming, emitindo eventos incrementalmente.

    Cada evento representa um passo ou fragmento da execução. Use esta
    interface para experiências de UX responsivas (ex.: chat em tempo real).

    Argumentos:
        message: Pergunta ou instrução em linguagem natural.

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
                # Detecta chamadas de ferramentas
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

                # Detecta resultados de ferramentas (ToolMessage)
                msg_type = getattr(msg, "type", "")
                if msg_type == "tool":
                    yield AgentEvent(
                        type="tool_result",
                        data={
                            "tool": getattr(msg, "name", ""),
                            "content": getattr(msg, "content", ""),
                        },
                    )

                # Captura tokens de uso
                usage = getattr(msg, "usage_metadata", None)
                if usage:
                    total_tokens += getattr(usage, "total_tokens", 0) or 0

                # Emite conteúdo da mensagem final do agente
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

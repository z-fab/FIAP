"""Estado do Pokémon Trade Center.

Padrão de extensão de estado:
    MessagesState é um TypedDict pré-definido pelo LangGraph que inclui
    o campo `messages` com o reducer add_messages (que faz append em vez
    de overwrite). Estendemos apenas se precisarmos de campos de domínio.

Trocas lendárias pendentes NÃO ficam neste estado: a chave é o
`thread_id` da sessão (`config["configurable"]["thread_id"]`), gravado
em `data/trades.json` pelas tools. Isso evita o antigo campo morto
`pending_trade_id` e alinha estado do grafo com a persistência JSON.
"""

from langgraph.graph import MessagesState


class TradeState(MessagesState):
    """Estado do agente de trocas Pokémon.

    Por enquanto só precisa do histórico de mensagens. O `thread_id` da
    sessão (usado em trocas lendárias) vem do RunnableConfig injetado
    nas tools — não precisa ser campo do estado nem argumento do LLM.
    """

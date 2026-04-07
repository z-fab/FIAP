"""Estado do agente de pesquisa acadêmica.

Define o estado tipado que flui entre os nós do grafo,
estendendo MessagesState com campos específicos do domínio.

Referência no textbook: Capítulo 4, Seção 4.3.1 (StateGraph e Definição de Estado).
"""

from langgraph.graph import MessagesState


# MessagesState já traz o campo `messages` com o reducer `add_messages`,
# que faz APPEND em vez de overwrite. Isso é fundamental para o ReAct loop:
# cada vez que um nó retorna {"messages": [nova_msg]}, a nova mensagem é
# adicionada ao histórico em vez de substituí-lo.
class ResearchState(MessagesState):
    """Estado do agente de pesquisa.

    Estende MessagesState (que já inclui o campo 'messages' com
    reducer add_messages) com campos adicionais para rastreamento.

    Attributes:
        query: Pergunta original do usuário.
        sources_found: Contador de fontes encontradas durante a pesquisa.
    """

    query: str
    sources_found: int

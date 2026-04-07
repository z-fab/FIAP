"""Estado do Pokémon Trade Center.

Padrão de extensão de estado:
    MessagesState é um TypedDict pré-definido pelo LangGraph que inclui
    o campo `messages` com o reducer add_messages (que faz append em vez
    de overwrite). Estendemos para adicionar campos específicos do domínio
    sem precisar reimplementar a lógica de mensagens.
"""

from langgraph.graph import MessagesState


class TradeState(MessagesState):
    """Estado do agente de trocas Pokémon.

    Extende MessagesState com um campo opcional para rastrear
    trocas pendentes de aprovação do Professor Oak.

    Attributes:
        pending_trade_id: ID da troca pendente (vazio quando não há).
            Mantido no estado para que o LLM possa referenciá-lo
            em turnos subsequentes da conversa.
    """

    pending_trade_id: str

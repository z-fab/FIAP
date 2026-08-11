"""Estado do Estúdio de Roteiro.

Diferente do ReAct genérico (onde o estado costuma ser só `messages`),
aqui CADA campo é lido e escrito pelos nós do pipeline. Isso torna o
fluxo didaticamente transparente: o aluno vê brief → research_notes →
draft → critique evoluírem entre nós.

Referência no textbook: Capítulo 4, Seção 4.3.1 (StateGraph e Definição
de Estado) e padrões de workflow com loop de crítica.
"""

from langgraph.graph import MessagesState


class RoteiroState(MessagesState):
    """Estado do Estúdio de Roteiro.

    Extende MessagesState (campo `messages` com reducer add_messages)
    com campos de domínio que os nós leem e escrevem de verdade.

    Attributes:
        brief: Gênero, tom, logline e restrições extraídos do pedido.
        research_notes: Trechos e fontes da pesquisa web (Tavily).
        draft: Roteiro atual (primeira versão ou revisão).
        critique: Feedback do nó validador.
        revision_count: Quantas vezes o validador já rodou.
        approved: Se o crítico aprovou o draft atual.
    """

    brief: str
    research_notes: str
    draft: str
    critique: str
    revision_count: int
    approved: bool

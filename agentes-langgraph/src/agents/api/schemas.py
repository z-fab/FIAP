"""Schemas Pydantic compartilhados entre os routers da API."""

from typing import Any

from pydantic import BaseModel, Field


def extract_text(message: Any) -> str:
    """Extrai texto de uma mensagem do LangChain.

    O content de mensagens do Gemini pode vir como string ou como
    lista de blocos (ex: [{"type": "text", "text": "..."}]).
    Esta função normaliza ambos os formatos para string.

    Por que isso é necessário? O Gemini suporta conteúdo MULTIMODAL
    (texto + imagens + áudio), então o `content` pode ser uma lista de
    blocos com diferentes tipos. Mesmo quando só há texto, alguns modelos
    retornam no formato de lista. Para o frontend basta o texto puro,
    então normalizamos aqui em um único lugar.
    """
    content = message.content if hasattr(message, "content") else message
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        # Formato multimodal: lista de blocos com type/text
        parts = []
        for block in content:
            if isinstance(block, dict) and "text" in block:
                parts.append(block["text"])
            elif isinstance(block, str):
                parts.append(block)
        return "\n".join(parts)
    return str(content)


class AgentRequest(BaseModel):
    """Request padrão para invocar um agente."""

    message: str = Field(..., description="Mensagem do usuário")
    thread_id: str | None = Field(None, description="ID da sessão (None = nova sessão)")


class AgentResponse(BaseModel):
    """Response padrão de um agente."""

    thread_id: str
    status: str = Field(description="completed | waiting_trainer | waiting_professor")
    response: str

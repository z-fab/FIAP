"""Ferramentas do Pokémon Trade Center.

Integra com a PokéAPI (gratuita, sem autenticação) para consultar dados
de Pokémon e inclui um registro mock de trocas.

Conceito-chave: cada função decorada com @tool vira uma "ferramenta" que
o LLM pode chamar. A docstring é OBRIGATÓRIA — é ela que o modelo lê para
decidir QUANDO e COMO usar a ferramenta. Pense nas docstrings como prompts
direcionados ao LLM, não para humanos.
"""

import uuid

import httpx
from langchain_core.tools import tool
from langgraph.types import interrupt

from agents.trade.db import (
    get_pending_trade,
    remove_pending_trade,
    save_completed_trade,
    save_pending_trade,
)

# URL base da PokéAPI
_POKEAPI_BASE = "https://pokeapi.co/api/v2"


def _fetch_pokemon(nome: str) -> dict | None:
    """Busca dados de um Pokémon na PokéAPI.

    Realiza duas requisições:
    1. GET /pokemon/{nome} — dados gerais (stats, tipos, habilidades)
    2. GET /pokemon-species/{nome} — dados da espécie (lendário, mítico, geração)

    Retorna um dicionário com os campos normalizados ou None em caso de erro.
    """
    nome = nome.lower().strip()

    try:
        # Primeira requisição: dados gerais do Pokémon
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(f"{_POKEAPI_BASE}/pokemon/{nome}")
            if resp.status_code != 200:
                return None
            data = resp.json()

            # Extrair stats e calcular BST (Base Stat Total)
            stats: dict[str, int] = {}
            for entry in data["stats"]:
                stat_nome = entry["stat"]["name"]
                stats[stat_nome] = entry["base_stat"]
            bst = sum(stats.values())

            # Extrair tipos (ex.: ["fire", "flying"])
            tipos = [t["type"]["name"] for t in data["types"]]

            # Extrair habilidades (máximo 3, excluindo habilidades ocultas se houver muitas)
            habilidades = [a["ability"]["name"] for a in data["abilities"]][:3]

            # URL da espécie para dados adicionais
            species_url: str = data["species"]["url"]

            # Segunda requisição: dados da espécie
            resp_species = client.get(species_url)
            if resp_species.status_code != 200:
                return None
            species_data = resp_species.json()

            is_legendary: bool = species_data.get("is_legendary", False)
            is_mythical: bool = species_data.get("is_mythical", False)

            # Geração (ex.: "generation-i" → "I")
            generation_raw: str = species_data["generation"]["name"]
            generation = generation_raw.replace("generation-", "").upper()

        return {
            "nome": data["name"],
            "tipos": tipos,
            "stats": stats,
            "bst": bst,
            "is_legendary": is_legendary,
            "is_mythical": is_mythical,
            "generation": generation,
            "abilities": habilidades,
        }

    except (httpx.RequestError, KeyError, ValueError):
        return None


def _format_pokemon_info(pokemon: dict) -> str:
    """Formata o dicionário de um Pokémon em uma string legível para o usuário.

    Inclui tags [LENDÁRIO] ou [MÍTICO] quando aplicável.
    """
    nome = pokemon["nome"].capitalize()
    tags = ""
    if pokemon["is_legendary"]:
        tags = " [LENDÁRIO]"
    elif pokemon["is_mythical"]:
        tags = " [MÍTICO]"

    tipos_str = " / ".join(t.capitalize() for t in pokemon["tipos"])
    habilidades_str = ", ".join(a.replace("-", " ").title() for a in pokemon["abilities"])

    # Formatar stats individuais
    stats = pokemon["stats"]
    stats_linhas = "\n".join(f"    {k.replace('-', ' ').title()}: {v}" for k, v in stats.items())

    return (
        f"🎮 {nome}{tags}\n"
        f"  Geração: {pokemon['generation']}\n"
        f"  Tipos: {tipos_str}\n"
        f"  Habilidades: {habilidades_str}\n"
        f"  Stats base:\n{stats_linhas}\n"
        f"  BST (Total): {pokemon['bst']}"
    )


# --------------------------------------------------------------------------
# Classificação de tier de troca
# --------------------------------------------------------------------------
# Esta é a regra de negócio central: define o "nível" de uma troca, que
# determina QUAL fluxo de aprovação será disparado:
#   - common    → executado automaticamente
#   - rare      → requer confirmação do treinador (HITL via interrupt)
#   - legendary → requer aprovação assíncrona do Professor Oak (admin)
def _classify_tier(poke_a: dict | None, poke_b: dict | None) -> str:
    """Classifica o tier de uma troca com base nos dados dos Pokémon.

    Returns:
        "common", "rare" ou "legendary".
    """
    # Fallback defensivo: se algum Pokémon não foi encontrado, trata como common
    if poke_a is None or poke_b is None:
        return "common"
    # Pokémon lendários/míticos sempre forçam tier legendary,
    # independentemente do BST do outro lado
    if poke_a["is_legendary"] or poke_a["is_mythical"]:
        return "legendary"
    if poke_b["is_legendary"] or poke_b["is_mythical"]:
        return "legendary"
    # BST (Base Stat Total) >= 500 indica Pokémon "fortes" → tier rare
    if poke_a["bst"] >= 500 or poke_b["bst"] >= 500:
        return "rare"
    return "common"


@tool
def consultar_pokemon(nome: str) -> str:
    """Consulta informações detalhadas de um Pokémon na PokéAPI.

    Busca nome, tipos, stats, BST, habilidades, geração e status de lendário/mítico.
    Use esta ferramenta quando o treinador quiser saber detalhes sobre um Pokémon específico.

    Args:
        nome: Nome do Pokémon (ex.: "pikachu", "charizard", "mewtwo").

    Returns:
        String formatada com as informações do Pokémon, ou mensagem de erro.
    """
    pokemon = _fetch_pokemon(nome)
    if pokemon is None:
        return (
            f"❌ Não foi possível encontrar o Pokémon '{nome}'. "
            "Verifique o nome e tente novamente (use o nome em inglês, ex.: 'bulbasaur')."
        )
    return _format_pokemon_info(pokemon)


@tool
def comparar_poder_pokemon(pokemon_a: str, pokemon_b: str) -> str:
    """Compara o poder de dois Pokémon com base em seus stats base.

    Mostra a diferença de BST, informações de tipo e um veredicto sobre qual é mais forte.
    Emite aviso caso algum dos Pokémon seja lendário ou mítico.

    Args:
        pokemon_a: Nome do primeiro Pokémon (ex.: "gengar").
        pokemon_b: Nome do segundo Pokémon (ex.: "alakazam").

    Returns:
        String com a comparação detalhada entre os dois Pokémon.
    """
    poke_a = _fetch_pokemon(pokemon_a)
    poke_b = _fetch_pokemon(pokemon_b)

    erros = []
    if poke_a is None:
        erros.append(f"'{pokemon_a}'")
    if poke_b is None:
        erros.append(f"'{pokemon_b}'")
    if erros:
        nomes = " e ".join(erros)
        return (
            f"❌ Não foi possível encontrar os dados de {nomes}. "
            "Verifique os nomes e tente novamente."
        )

    linhas = ["⚔️  COMPARAÇÃO DE PODER ⚔️", ""]

    # Avisos de lendário/mítico
    for poke in (poke_a, poke_b):
        nome = poke["nome"].capitalize()
        if poke["is_legendary"]:
            linhas.append(f"⚠️  Atenção: {nome} é um Pokémon LENDÁRIO!")
        elif poke["is_mythical"]:
            linhas.append(f"⚠️  Atenção: {nome} é um Pokémon MÍTICO!")

    if any(p["is_legendary"] or p["is_mythical"] for p in (poke_a, poke_b)):
        linhas.append("")

    # Informações individuais
    linhas.append(_format_pokemon_info(poke_a))
    linhas.append("")
    linhas.append(_format_pokemon_info(poke_b))
    linhas.append("")

    # Comparação de BST
    bst_a = poke_a["bst"]
    bst_b = poke_b["bst"]
    diff = abs(bst_a - bst_b)
    linhas.append("📊 RESULTADO:")

    nome_a = poke_a["nome"].capitalize()
    nome_b = poke_b["nome"].capitalize()

    if bst_a > bst_b:
        linhas.append(
            f"  {nome_a} é mais forte! (BST {bst_a} vs {bst_b}, diferença de {diff} pontos)"
        )
    elif bst_b > bst_a:
        linhas.append(
            f"  {nome_b} é mais forte! (BST {bst_b} vs {bst_a}, diferença de {diff} pontos)"
        )
    else:
        linhas.append(f"  Empate! Ambos têm BST {bst_a}.")

    # Tipos dos dois Pokémon
    tipos_a_str = " / ".join(t.capitalize() for t in poke_a["tipos"])
    tipos_b_str = " / ".join(t.capitalize() for t in poke_b["tipos"])
    linhas.append(f"  Tipos: {nome_a} ({tipos_a_str}) vs {nome_b} ({tipos_b_str})")
    linhas.append("  (Vantagens de tipo dependem da batalha específica)")

    return "\n".join(linhas)


@tool
def registrar_troca(offered: str, requested: str) -> str:
    """Registra uma troca de Pokémon no sistema do Trade Center.

    Use esta ferramenta APENAS após a troca ter sido aprovada
    (pelo treinador para trocas raras, ou pelo Professor Oak para lendárias).

    Args:
        offered: Nome do Pokémon oferecido.
        requested: Nome do Pokémon solicitado.

    Returns:
        Confirmação com o ID da troca registrada.
    """
    trade_id = "TRD-" + uuid.uuid4().hex[:6].upper()
    save_completed_trade(trade_id, offered, requested)
    return (
        f"Troca registrada com sucesso!\n"
        f"  ID: {trade_id}\n"
        f"  Oferece: {offered.capitalize()}\n"
        f"  Solicita: {requested.capitalize()}"
    )


@tool
def propor_troca(offered: str, requested: str, thread_id: str) -> str:
    """Propõe uma troca de Pokémon e classifica automaticamente o nível de aprovação.

    Consulta a PokéAPI para determinar se a troca é comum, rara ou lendária:
    - Comum (ambos BST < 500, nenhum lendário): troca aprovada automaticamente.
    - Rara (algum BST >= 500): pausa a conversa via interrupt() e pede
      confirmação do treinador. Após resposta, registra ou cancela a troca.
    - Lendária (envolve lendário/mítico): registra como pendente para o
      Professor Oak aprovar de forma assíncrona via endpoint admin.

    Use esta ferramenta quando o treinador propuser uma troca concreta.

    Args:
        offered: Nome do Pokémon que o treinador oferece.
        requested: Nome do Pokémon que o treinador deseja receber.
        thread_id: ID da conversa atual (para rastrear aprovações pendentes).

    Returns:
        Resultado final da troca: registrada, cancelada ou pendente.
    """
    poke_offered = _fetch_pokemon(offered)
    poke_requested = _fetch_pokemon(requested)

    erros = []
    if poke_offered is None:
        erros.append(f"'{offered}'")
    if poke_requested is None:
        erros.append(f"'{requested}'")
    if erros:
        nomes = " e ".join(erros)
        return f"Não foi possível encontrar {nomes}. Verifique os nomes (use nomes em inglês)."

    tier = _classify_tier(poke_offered, poke_requested)

    info_a = _format_pokemon_info(poke_offered)
    info_b = _format_pokemon_info(poke_requested)
    diff = abs(poke_offered["bst"] - poke_requested["bst"])

    analise = f"{info_a}\n\n{info_b}\n\nDiferença de BST: {diff} pontos."

    # --- Tier COMMON: executa imediatamente, sem aprovação ---
    if tier == "common":
        trade_id = "TRD-" + uuid.uuid4().hex[:6].upper()
        save_completed_trade(trade_id, offered, requested)
        return (
            f"TROCA COMUM — Aprovada automaticamente!\n\n"
            f"{analise}\n\n"
            f"Troca registrada com ID: {trade_id}"
        )

    # --- Tier RARE: HITL via interrupt() dentro da própria tool ---
    # interrupt() pausa o grafo AQUI dentro da tool. O valor passado é
    # enviado ao cliente (CLI/API) para mostrar ao treinador. Quando o
    # cliente faz Command(resume="sim/não"), a execução retoma deste ponto
    # exato, e user_response recebe o valor do resume.
    #
    # Padrão importante: o interrupt vive na tool porque é a tool quem
    # CONHECE a regra de negócio (o que é "rare"). O nó assistant fica
    # como ReAct puro, sem saber nada sobre tiers.
    if tier == "rare":
        confirmation_msg = (
            f"⚠️  TROCA RARA detectada!\n\n"
            f"{analise}\n\n"
            f"Esta troca envolve Pokémon de poder significativamente diferente. "
            f"Você confirma que deseja prosseguir?"
        )
        user_response = interrupt(confirmation_msg)

        # Após resume: a tool retorna o resultado da decisão do treinador.
        # O LLM verá esse retorno e gerará a resposta final naturalmente.
        positivas = ("sim", "s", "yes", "y", "confirmo", "aprovo", "ok", "claro")
        confirmou = any(p in str(user_response).lower() for p in positivas)

        if confirmou:
            trade_id = "TRD-" + uuid.uuid4().hex[:6].upper()
            save_completed_trade(trade_id, offered, requested)
            return (
                f"Treinador CONFIRMOU a troca rara. "
                f"Troca registrada com sucesso! "
                f"ID: {trade_id} — {offered.capitalize()} por {requested.capitalize()}."
            )
        return (
            f"Treinador CANCELOU a troca de {offered.capitalize()} por "
            f"{requested.capitalize()}. Nenhum registro foi feito."
        )

    # --- Tier LEGENDARY: salva como pendente, aprovação assíncrona ---
    # Aqui o fluxo é diferente do interrupt(): a troca fica salva no JSON
    # esperando um endpoint admin (Professor Oak) mudar o status.
    # O treinador continua conversando livremente e pode perguntar o status
    # depois — o LLM então chamará check_professor_approval.
    save_pending_trade(thread_id, offered, requested, analise)
    return (
        f"TROCA LENDÁRIA — Requer aprovação do Professor Oak.\n\n"
        f"{analise}\n\n"
        f"Esta troca envolve um Pokémon lendário ou mítico. "
        f"Foi registrada como pendente e o Professor Oak será notificado. "
        f"O treinador pode continuar conversando e perguntar pelo status depois."
    )


@tool
def check_professor_approval(thread_id: str) -> str:
    """Verifica se o Professor Oak já aprovou uma troca lendária pendente.

    Use quando o treinador perguntar sobre o status de uma troca
    que está aguardando aprovação do Professor Oak.

    Args:
        thread_id: ID da conversa com a troca pendente.

    Returns:
        Status da aprovação: aprovado, rejeitado ou pendente.
    """
    # Busca a troca pendente associada a este thread_id (conversa)
    trade = get_pending_trade(thread_id)
    if trade is None:
        return "Não há troca pendente de aprovação nesta conversa."

    status = trade["status"]
    # --- Aprovado: efetiva a troca AGORA ---
    # Importante: a troca só é "completada" quando o treinador pergunta pelo
    # status. Antes disso, mesmo que o admin tenha aprovado, ela continua só
    # como "approved" no JSON. Isso simplifica o fluxo (sem callbacks).
    if status == "approved":
        offered = trade["pokemon_offered"]
        requested = trade["pokemon_requested"]
        trade_id = "TRD-" + uuid.uuid4().hex[:6].upper()
        save_completed_trade(trade_id, offered, requested)
        remove_pending_trade(thread_id)
        return (
            f"Professor Oak APROVOU a troca! "
            f"Troca registrada com ID: {trade_id}. "
            f"{offered.capitalize()} por {requested.capitalize()} — concluída!"
        )
    if status == "rejected":
        remove_pending_trade(thread_id)
        return (
            "Professor Oak REJEITOU a troca. "
            "Ele acredita que não seria uma troca justa. "
            "O treinador pode propor outra troca."
        )
    return (
        "A troca ainda está PENDENTE. "
        "O Professor Oak ainda não tomou uma decisão. Aguarde."
    )

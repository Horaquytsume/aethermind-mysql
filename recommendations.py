"""Deterministic, explainable recommendations for the AetherMind prototype.

This module does not call a generative-AI model and does not use live labor-market
or sports data. It deliberately returns transparent heuristic suggestions.
"""
from __future__ import annotations

from typing import Any


FAMILIES: dict[str, dict[str, Any]] = {
    "operations": {
        "title": "Operações, logística e gestão de frotas",
        "roles": [
            "Assistente de operações ou logística",
            "Assistente de frota",
            "Auxiliar administrativo com foco em processos",
        ],
    },
    "technology": {
        "title": "Tecnologia, suporte e automação",
        "roles": [
            "Suporte técnico em TI",
            "Analista de automação júnior",
            "Assistente de sistemas e operações digitais",
        ],
    },
    "analysis": {
        "title": "Análise e melhoria de processos",
        "roles": [
            "Assistente de planejamento",
            "Analista de operações júnior",
            "Assistente de controle e indicadores",
        ],
    },
    "people": {
        "title": "Atendimento, coordenação e trabalho com pessoas",
        "roles": [
            "Assistente de atendimento ou relacionamento",
            "Assistente de treinamento",
            "Auxiliar de coordenação de equipes",
        ],
    },
    "creative": {
        "title": "Criação e comunicação digital",
        "roles": [
            "Assistente de conteúdo digital",
            "Auxiliar de design e produção multimídia",
            "Assistente de comunicação",
        ],
    },
}

KEYWORDS: dict[str, tuple[str, ...]] = {
    "operations": (
        "logistica", "frota", "transporte", "estoque", "operacao", "processo",
        "organizacao", "organizar", "planejamento", "administrativo", "veiculo",
    ),
    "technology": (
        "python", "programacao", "programar", "codigo", "computador", "tecnologia",
        "informatica", "sistema", "automacao", "software", "programacao", "computacao",
    ),
    "analysis": (
        "analise", "analitico", "logica", "planilha", "excel", "numero", "indicador",
        "pesquisa", "detalhe", "matematica", "estatistica",
    ),
    "people": (
        "equipe", "pessoas", "atendimento", "empatia", "ajudar", "ensinar", "lideranca",
        "comunicar", "colaboracao", "cliente", "coordenar",
    ),
    "creative": (
        "criatividade", "criativo", "design", "desenho", "arte", "video", "escrever",
        "conteudo", "musica", "ideia", "inovacao",
    ),
}

STYLE_LABELS = {
    "work_style": {
        "remote": "preferência por autonomia e trabalho remoto",
        "onsite": "preferência por interação presencial",
        "hybrid": "preferência por rotina híbrida e foco em entregas",
    },
    "decision_style": {
        "analytical": "decisões apoiadas em análise e lógica",
        "creative": "decisões com criatividade e rapidez",
        "collaborative": "decisões colaborativas e atenção às pessoas",
    },
}


def _fold(value: str) -> str:
    """Lowercase and remove accents for keyword matching only."""
    import unicodedata

    normalized = unicodedata.normalize("NFKD", value.casefold())
    return "".join(char for char in normalized if not unicodedata.combining(char))


def build_recommendation(target: str, answers: dict[str, Any]) -> dict[str, Any]:
    """Return an explainable career or playful team-profile suggestion."""
    if target == "team":
        work_style = answers.get("work_style", "hybrid")
        if work_style == "onsite":
            profile = "Torcida de comunidade e convivência"
            suggestions = [
                "Procure um clube com comunidade ativa na sua região.",
                "Veja se você valoriza história, jogos presenciais ou projetos sociais.",
                "Compare informações oficiais antes de escolher um time.",
            ]
        elif work_style == "remote":
            profile = "Torcida digital e aberta a novas comunidades"
            suggestions = [
                "Explore comunidades oficiais e transmissões dos clubes.",
                "Compare estilos de jogo e valores que combinem com você.",
                "Considere a tradição e a participação da torcida.",
            ]
        else:
            profile = "Torcida versátil e colaborativa"
            suggestions = [
                "Busque equilíbrio entre história, estilo de jogo e comunidade.",
                "Conheça mais de um clube antes de decidir.",
                "Use canais oficiais para conferir notícias e calendário.",
            ]
        return {
            "kind": "team",
            "title": profile,
            "summary": "Uma sugestão recreativa de perfil de torcida, não a indicação de um clube específico.",
            "suggestions": suggestions,
            "squad": [
                {"role": "Explorador", "description": "Pesquisa clubes e comunidades oficiais."},
                {"role": "Comparador", "description": "Organiza critérios que importam para você."},
                {"role": "Torcedor", "description": "A decisão final é sua — sem promessa de compatibilidade perfeita."},
            ],
            "basis": [STYLE_LABELS["work_style"].get(work_style, "preferência de rotina")],
            "notice": "Não consultamos clubes, resultados ou calendários em tempo real. Esta parte é apenas recreativa.",
        }

    scores = {family: 0 for family in FAMILIES}
    matched: list[str] = []
    text = " ".join(
        str(answers.get(field, ""))
        for field in ("education", "superpower", "hobby")
    )
    folded = _fold(text)
    for family, keywords in KEYWORDS.items():
        hits = [keyword for keyword in keywords if _fold(keyword) in folded]
        scores[family] += min(len(hits) * 2, 6)
        if hits:
            matched.append(f"temas associados a {FAMILIES[family]['title'].lower()}")

    work_style = answers.get("work_style", "hybrid")
    decision_style = answers.get("decision_style", "analytical")
    work_boosts = {
        "remote": {"technology": 1, "creative": 1},
        "onsite": {"operations": 1, "people": 1},
        "hybrid": {"analysis": 1, "operations": 1},
    }
    decision_boosts = {
        "analytical": {"analysis": 2, "operations": 1},
        "creative": {"creative": 2, "technology": 1},
        "collaborative": {"people": 2, "operations": 1},
    }
    for family, points in work_boosts.get(work_style, {}).items():
        scores[family] += points
    for family, points in decision_boosts.get(decision_style, {}).items():
        scores[family] += points

    # Stable tie-break order keeps the same answers reproducible.
    priority = ["operations", "technology", "analysis", "people", "creative"]
    winner = max(priority, key=lambda family: scores[family])
    family = FAMILIES[winner]
    basis = [STYLE_LABELS["work_style"].get(work_style, "preferência de rotina")]
    basis.append(STYLE_LABELS["decision_style"].get(decision_style, "estilo de decisão informado"))
    basis.extend(matched[:2])
    if not matched:
        basis.append("respostas de formação e interesses, sem palavras-chave específicas")

    return {
        "kind": "profession",
        "title": f"Afinidade inicial: {family['title']}",
        "summary": "Estas são áreas para investigar, não uma previsão de profissão ou garantia de contratação.",
        "roles": family["roles"],
        "squad": [
            {"role": "Mentor de carreira", "description": "Ajuda a comparar as opções com seus objetivos."},
            {"role": "Pesquisador de formação", "description": "Pode mapear cursos e requisitos oficiais para a área escolhida."},
            {"role": "Planejador de próximos passos", "description": "Transforma uma opção em pequenas ações de aprendizagem."},
        ],
        "basis": basis,
        "notice": "Resultado heurístico calculado no servidor a partir das respostas. Não usa IA generativa nem dados de mercado em tempo real.",
        "scores": scores,
    }

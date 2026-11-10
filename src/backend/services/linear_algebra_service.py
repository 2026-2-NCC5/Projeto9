"""
Serviço de Álgebra Linear — Entrega 1 e Entrega 2.
Mapeamento didático do Agente para o Estudante (FECAP).
Conceito: Transformações Lineares T: R^3 -> R^3 com Matriz de Ponderação.
"""
from typing import Dict, Any, List
import numpy as np

# Dados canônicos da Entrega 1 (notebook oficial):
# Categorias nos eixos: [Portal/Sistemas (x1), Documentos/Secretaria (x2), Canais/Setores (x3)]
V_PERGUNTA_ORIGINAL = np.array([0.8, 0.9, 0.2], dtype=float)

ARTIGOS_ORIGINAIS = [
    {
        "id": "artigo1",
        "title": "Guia de Emissão de Histórico Acadêmico",
        "category": "Documentos e Secretaria",
        "vector": np.array([0.7, 0.95, 0.1], dtype=float),
    },
    {
        "id": "artigo2",
        "title": "Canais de Atendimento do ASA e Setores",
        "category": "Canais e Setores de Atendimento",
        "vector": np.array([0.1, 0.2, 0.9], dtype=float),
    },
]

def calculate_metrics(v_query: np.ndarray, v_doc: np.ndarray) -> Dict[str, float]:
    """Calcula produto escalar, distância euclidiana e similaridade por cosseno."""
    dot_product = float(np.dot(v_query, v_doc))
    dist_euclid = float(np.linalg.norm(v_query - v_doc))
    
    norm_q = float(np.linalg.norm(v_query))
    norm_d = float(np.linalg.norm(v_doc))
    cosine_sim = float(dot_product / (norm_q * norm_d)) if (norm_q > 0 and norm_d > 0) else 0.0
    
    return {
        "dot_product": round(dot_product, 4),
        "euclidean_distance": round(dist_euclid, 4),
        "cosine_similarity": round(cosine_sim, 4),
    }

def apply_linear_transformation(
    w_portal: float = 1.0,
    w_documentos: float = 1.0,
    w_canais: float = 1.0,
) -> Dict[str, Any]:
    """
    Aplica a Transformação Linear T(v) = A * v onde A é a matriz 3x3 de ponderação de eixos.
    Calcula as métricas originais (Entrega 1) e as transformadas (Entrega 2), comparando-as.
    """
    # Matriz de Transformação Linear 3x3
    A = np.array([
        [w_portal, 0.0, 0.0],
        [0.0, w_documentos, 0.0],
        [0.0, 0.0, w_canais],
    ], dtype=float)

    # Vetor transformado da pergunta
    v_pergunta_trans = np.dot(A, V_PERGUNTA_ORIGINAL)

    comparison: List[Dict[str, Any]] = []

    for art in ARTIGOS_ORIGINAIS:
        v_doc_orig = art["vector"]
        v_doc_trans = np.dot(A, v_doc_orig)

        m_orig = calculate_metrics(V_PERGUNTA_ORIGINAL, v_doc_orig)
        m_trans = calculate_metrics(v_pergunta_trans, v_doc_trans)

        norm_q = float(np.linalg.norm(v_pergunta_trans))
        norm_d = float(np.linalg.norm(v_doc_trans))
        exact_cos_trans = float(np.dot(v_pergunta_trans, v_doc_trans) / (norm_q * norm_d)) if (norm_q > 0 and norm_d > 0) else 0.0

        comparison.append({
            "id": art["id"],
            "title": art["title"],
            "category": art["category"],
            "vector_original": [round(x, 4) for x in v_doc_orig.tolist()],
            "vector_transformed": [round(x, 4) for x in v_doc_trans.tolist()],
            "original_metrics": m_orig,
            "transformed_metrics": m_trans,
            "exact_cosine_trans": exact_cos_trans,
            "delta_cosine": round(m_trans["cosine_similarity"] - m_orig["cosine_similarity"], 4),
            "delta_euclidean": round(m_trans["euclidean_distance"] - m_orig["euclidean_distance"], 4),
        })

    # Ranking antes (pela similaridade de cosseno)
    ranking_orig = sorted(comparison, key=lambda x: x["original_metrics"]["cosine_similarity"], reverse=True)
    # Ranking depois (usando precisão total do ponto flutuante para desempates em limites)
    ranking_trans = sorted(comparison, key=lambda x: x["exact_cosine_trans"], reverse=True)

    winner_orig = ranking_orig[0]["title"]
    winner_trans = ranking_trans[0]["title"]
    ranking_changed = winner_orig != winner_trans

    interpretation = (
        f"A transformação linear A·v com pesos [{w_portal:.2f}, {w_documentos:.2f}, {w_canais:.2f}] "
        + ("ALTEROU o documento mais relevante no ranking: " if ranking_changed else "MANTEVE o documento líder inalterado: ")
        + f"antes o documento mais similar era '{winner_orig}' (cos={ranking_orig[0]['original_metrics']['cosine_similarity']:.4f}) "
        + f"e após a transformação o líder é '{winner_trans}' (cos={ranking_trans[0]['transformed_metrics']['cosine_similarity']:.4f}). "
        + ("Isso demonstra como transformações no espaço vetorial permitem priorizar eixos de atendimento em cenários de contingência." if ranking_changed else "Isso evidencia a estabilidade da geometria do espaço sob variações moderadas de escala.")
    )

    return {
        "disclaimer": "Representação matemática didática (Entrega 1 e 2 de Álgebra Linear em R^3). Não representa os embeddings densos reais do ChromaDB.",
        "axes": ["Portal/Sistemas (x1)", "Documentos/Secretaria (x2)", "Canais/Setores (x3)"],
        "matrix_transformation": [
            [round(x, 4) for x in row] for row in A.tolist()
        ],
        "question_original": [round(x, 4) for x in V_PERGUNTA_ORIGINAL.tolist()],
        "question_transformed": [round(x, 4) for x in v_pergunta_trans.tolist()],
        "comparison": comparison,
        "ranking_original": [r["title"] for r in ranking_orig],
        "ranking_transformed": [r["title"] for r in ranking_trans],
        "winner_original": winner_orig,
        "winner_transformed": winner_trans,
        "ranking_changed": ranking_changed,
        "mathematical_interpretation": interpretation,
    }

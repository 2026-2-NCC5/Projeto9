"""
inference.py — Classificador de assuntos para uso no SecretarIA.

Uso:
    from entrega_2_ia.inference import classificar

    resultado = classificar("Como faço minha carteirinha estudantil?")
    # {
    #   "categoria": "Carteirinha e Transporte",
    #   "confianca": 0.92,
    #   "top3": [
    #     {"categoria": "Carteirinha e Transporte", "prob": 0.92},
    #     {"categoria": "Atendimento Geral e Serviços do Campus", "prob": 0.05},
    #     {"categoria": "Documentação Acadêmica", "prob": 0.02},
    #   ],
    #   "baixa_confianca": False,
    #   "modelo": "Regressao Logistica",
    #   "versao": "v1",
    # }

Regras:
  - confiança < 0.40 → baixa_confianca=True (recomendar revisão humana)
  - Não grava nada no SQLite.
  - Não altera prioridades Alta/Média.
"""

import os
import json
import joblib
import pathlib

_DIR = pathlib.Path(__file__).parent
_MODEL_PATH  = _DIR / "models" / "asa_topic_best_v1.joblib"
_META_PATH   = _DIR / "models" / "metadata_v1.json"

LIMIAR_CONFIANCA = 0.40  # abaixo disso → encaminhar para revisão humana

# Cache do modelo (carregado uma vez)
_pipe = None
_meta = None


def _carregar_modelo():
    global _pipe, _meta
    if _pipe is None:
        _pipe = joblib.load(_MODEL_PATH)
        with open(_META_PATH, encoding="utf-8") as f:
            _meta = json.load(f)
    return _pipe, _meta


def classificar(texto: str) -> dict:
    """
    Classifica o assunto de um texto livre em uma das 8 categorias.

    Parâmetros
    ----------
    texto : str
        Texto da pergunta ou motivo a classificar.

    Retorno
    -------
    dict com campos:
        categoria      : str   — categoria predita
        confianca      : float — probabilidade da classe predita
        top3           : list  — 3 categorias mais prováveis com probabilidades
        baixa_confianca: bool  — True se confianca < LIMIAR_CONFIANCA
        modelo         : str   — nome do modelo usado
        versao         : str   — versão do modelo
    """
    pipe, meta = _carregar_modelo()

    if not texto or not str(texto).strip():
        return {
            "categoria": None,
            "confianca": 0.0,
            "top3": [],
            "baixa_confianca": True,
            "modelo": meta.get("melhor_modelo", "desconhecido"),
            "versao": meta.get("versao", "v1"),
            "erro": "Texto vazio ou nulo",
        }

    texto_limpo = str(texto).strip()
    probs = pipe.predict_proba([texto_limpo])[0]
    classes = pipe.classes_

    top_idx = probs.argsort()[::-1]
    top3 = [
        {"categoria": classes[i], "prob": round(float(probs[i]), 4)}
        for i in top_idx[:3]
    ]

    categoria   = classes[top_idx[0]]
    confianca   = float(probs[top_idx[0]])
    baixa_conf  = confianca < LIMIAR_CONFIANCA

    return {
        "categoria":       categoria,
        "confianca":       round(confianca, 4),
        "top3":            top3,
        "baixa_confianca": baixa_conf,
        "modelo":          meta.get("melhor_modelo", "desconhecido"),
        "versao":          meta.get("versao", "v1"),
    }


# Teste rápido ao rodar diretamente
if __name__ == "__main__":
    testes = [
        "Como faço minha carteirinha estudantil?",
        "Esqueci a senha do portal do aluno",
        "Preciso do atestado de matrícula urgente",
        "Quero saber sobre renegociação da minha mensalidade",
        "Como registro as horas de estágio?",
        "Faltei na prova, posso fazer substitutiva?",
        "Como trancar o curso?",
        "Preciso de apoio psicológico",
        "texto genérico sem contexto acadêmico",
    ]
    print("=" * 60)
    print("TESTE DO MÓDULO DE INFERÊNCIA")
    print("=" * 60)
    for t in testes:
        r = classificar(t)
        flag = " [BAIXA CONFIANCA]" if r["baixa_confianca"] else ""
        print(f"\n  Texto    : {t[:60]}")
        print(f"  Categoria: {r['categoria']}{flag}")
        print(f"  Confiança: {r['confianca']:.2%}")
        print(f"  Top3     : {[(x['categoria'][:20], x['prob']) for x in r['top3']]}")
    print("\n✅ Inferência funcionando corretamente.")

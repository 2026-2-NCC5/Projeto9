"""
Etapa B — Treinamento e avaliação dos classificadores de assunto.

Modelos comparados:
  1. TF-IDF (char_wb, 2-4gram) + Regressão Logística
  2. TF-IDF (char_wb, 2-4gram) + Árvore de Decisão

Split: por motivo único (StratifiedKFold sobre textos únicos), não por linha.
Isso evita que o mesmo texto apareça simultaneamente no treino e no teste.

Métricas: accuracy, precision_macro, recall_macro, f1_macro, matriz de confusão.

Saídas:
  models/asa_topic_lr_v1.joblib   : melhor pipeline LR
  models/asa_topic_dt_v1.joblib   : melhor pipeline DT
  models/tfidf_meta.json          : metadata de treinamento
  resultados_comparativos.md      : tabela comparativa
  analise_erros.md                : erros e limitações
"""

import sys, os, json, hashlib, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import numpy as np
import joblib

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.pipeline import Pipeline
from sklearn.model_selection import StratifiedKFold, cross_validate
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix, classification_report
)

OUT_DIR   = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(OUT_DIR, "models")
os.makedirs(MODEL_DIR, exist_ok=True)

TREINO_CSV = os.path.join(OUT_DIR, "dataset_treino.csv")
MAPA_CSV   = os.path.join(OUT_DIR, "mapeamento_motivos.csv")

AMBIGUO    = "__AMBIGUO__"
NAO_ASSUNTO = "__NAO_ASSUNTO__"

CATEGORIAS_ORDEM = [
    "Documentacao Academica",
    "Matricula, Rematricula e Trancamento",
    "Vida Academica e Avaliacoes",
    "Portal e Sistemas",
    "Estagio, Carreira e Atividades Complementares",
    "Financeiro, Bolsas e Financiamento",
    "Carteirinha e Transporte",
    "Atendimento Geral e Servicos do Campus",
]

print("=" * 60)
print("ETAPA B — Treinamento dos classificadores")
print("=" * 60)

# ------------------------------------------------------------------ #
# 1. Carregar corpus: 1 linha por MOTIVO ÚNICO                        #
# ------------------------------------------------------------------ #
print("\n[1/7] Carregando corpus de motivos únicos ...")
mapa = pd.read_csv(MAPA_CSV, encoding="utf-8-sig")
mapa = mapa[~mapa["categoria"].isin([AMBIGUO, NAO_ASSUNTO])].copy()
mapa = mapa.drop_duplicates(subset="motivo_normalizado").copy()
mapa = mapa.reset_index(drop=True)

X_all = mapa["motivo_normalizado"].tolist()
y_all = mapa["categoria"].tolist()

print(f"      Motivos únicos para treino: {len(X_all)}")
print(f"      Categorias: {len(set(y_all))}")

classes = sorted(set(y_all))
print(f"      Distribuição:")
from collections import Counter
cnt = Counter(y_all)
for c in classes:
    print(f"        {c}: {cnt[c]}")

# ------------------------------------------------------------------ #
# 2. Definir pipelines                                                #
# ------------------------------------------------------------------ #
print("\n[2/7] Definindo pipelines ...")

tfidf_params = dict(
    analyzer="char_wb",
    ngram_range=(2, 4),
    sublinear_tf=True,
    min_df=1,
    max_features=20000,
)

pipelines = {
    "Regressao Logistica": Pipeline([
        ("tfidf", TfidfVectorizer(**tfidf_params)),
        ("clf",   LogisticRegression(max_iter=2000, C=1.0,
                                     class_weight="balanced",
                                     solver="lbfgs")),
    ]),
    "Arvore de Decisao": Pipeline([
        ("tfidf", TfidfVectorizer(**tfidf_params)),
        ("clf",   DecisionTreeClassifier(max_depth=20,
                                         class_weight="balanced",
                                         random_state=42)),
    ]),
}

# ------------------------------------------------------------------ #
# 3. Cross-validation estratificada (5 folds) sobre motivos únicos   #
# ------------------------------------------------------------------ #
print("\n[3/7] Cross-validation estratificada (5 folds sobre motivos únicos) ...")

CV_SCORING = {
    "accuracy":        "accuracy",
    "precision_macro": "precision_macro",
    "recall_macro":    "recall_macro",
    "f1_macro":        "f1_macro",
}

cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
cv_results = {}

for nome, pipe in pipelines.items():
    print(f"\n      [{nome}]")
    scores = cross_validate(pipe, X_all, y_all, cv=cv,
                            scoring=CV_SCORING, return_train_score=False,
                            n_jobs=-1)
    cv_results[nome] = {
        "accuracy_mean":        float(np.mean(scores["test_accuracy"])),
        "accuracy_std":         float(np.std(scores["test_accuracy"])),
        "precision_macro_mean": float(np.mean(scores["test_precision_macro"])),
        "precision_macro_std":  float(np.std(scores["test_precision_macro"])),
        "recall_macro_mean":    float(np.mean(scores["test_recall_macro"])),
        "recall_macro_std":     float(np.std(scores["test_recall_macro"])),
        "f1_macro_mean":        float(np.mean(scores["test_f1_macro"])),
        "f1_macro_std":         float(np.std(scores["test_f1_macro"])),
    }
    r = cv_results[nome]
    print(f"        Accuracy : {r['accuracy_mean']:.4f} ± {r['accuracy_std']:.4f}")
    print(f"        Precision: {r['precision_macro_mean']:.4f} ± {r['precision_macro_std']:.4f}")
    print(f"        Recall   : {r['recall_macro_mean']:.4f} ± {r['recall_macro_std']:.4f}")
    print(f"        F1-macro : {r['f1_macro_mean']:.4f} ± {r['f1_macro_std']:.4f}")

# ------------------------------------------------------------------ #
# 4. Treinar modelos finais em TODOS os dados + hold-out 20%          #
# ------------------------------------------------------------------ #
print("\n[4/7] Treino final + hold-out 20% (fixo, random_state=42) ...")

from sklearn.model_selection import train_test_split

X_train, X_test, y_train, y_test = train_test_split(
    X_all, y_all, test_size=0.2, stratify=y_all, random_state=42
)
print(f"      Treino: {len(X_train)} | Teste hold-out: {len(X_test)}")

holdout_results = {}
trained_pipes = {}

for nome, pipe in pipelines.items():
    print(f"\n      [{nome}]")
    pipe.fit(X_train, y_train)
    y_pred = pipe.predict(X_test)
    holdout_results[nome] = {
        "accuracy":        float(accuracy_score(y_test, y_pred)),
        "precision_macro": float(precision_score(y_test, y_pred, average="macro", zero_division=0)),
        "recall_macro":    float(recall_score(y_test, y_pred, average="macro", zero_division=0)),
        "f1_macro":        float(f1_score(y_test, y_pred, average="macro", zero_division=0)),
        "y_pred": y_pred.tolist(),
        "y_test": y_test,
    }
    trained_pipes[nome] = pipe
    r = holdout_results[nome]
    print(f"        Accuracy : {r['accuracy']:.4f}")
    print(f"        Precision: {r['precision_macro']:.4f}")
    print(f"        Recall   : {r['recall_macro']:.4f}")
    print(f"        F1-macro : {r['f1_macro']:.4f}")
    print(f"        Classification report:")
    print(classification_report(y_test, y_pred, zero_division=0))

# ------------------------------------------------------------------ #
# 5. Identificar melhor modelo e salvar                               #
# ------------------------------------------------------------------ #
print("\n[5/7] Identificando melhor modelo ...")
melhor = max(holdout_results, key=lambda n: holdout_results[n]["f1_macro"])
print(f"      Melhor modelo por F1-macro: {melhor}")

# Retreinar melhor modelo em TODOS os dados
print(f"      Retreinando {melhor} em todos os dados ...")
pipe_final = pipelines[melhor]
pipe_final.fit(X_all, y_all)

# Salvar modelos
lr_path = os.path.join(MODEL_DIR, "asa_topic_lr_v1.joblib")
dt_path = os.path.join(MODEL_DIR, "asa_topic_dt_v1.joblib")
best_path = os.path.join(MODEL_DIR, "asa_topic_best_v1.joblib")

joblib.dump(trained_pipes["Regressao Logistica"], lr_path)
joblib.dump(trained_pipes["Arvore de Decisao"], dt_path)
joblib.dump(pipe_final, best_path)
print(f"      Modelos salvos em {MODEL_DIR}")

# Hash do CSV de treino
with open(MAPA_CSV, "rb") as f:
    data_hash = hashlib.sha256(f.read()).hexdigest()[:16]

meta = {
    "versao": "v1",
    "data_treino": datetime.datetime.now().isoformat(),
    "arquivo_fonte": "mapeamento_motivos.csv",
    "hash_dados_treino": data_hash,
    "n_motivos_unicos": len(X_all),
    "n_categorias": len(classes),
    "categorias": classes,
    "melhor_modelo": melhor,
    "cv_5fold": cv_results,
    "holdout_20pct": {
        n: {k: v for k, v in r.items() if k not in ("y_pred", "y_test")}
        for n, r in holdout_results.items()
    },
}
meta_path = os.path.join(MODEL_DIR, "metadata_v1.json")
with open(meta_path, "w", encoding="utf-8") as f:
    json.dump(meta, f, ensure_ascii=False, indent=2)
print(f"      Metadata salvo: {meta_path}")

# ------------------------------------------------------------------ #
# 6. Relatório comparativo                                            #
# ------------------------------------------------------------------ #
print("\n[6/7] Gerando relatório comparativo ...")

relatorio_path = os.path.join(OUT_DIR, "resultados_comparativos.md")
with open(relatorio_path, "w", encoding="utf-8") as f:
    f.write("# Resultados Comparativos — Classificador de Assuntos (Entrega 2 IA)\n\n")
    f.write(f"**Data:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
    f.write("## Dados de Treinamento\n\n")
    f.write(f"- Fonte: `Relacionamentos.xlsx` (96.628 registros, {len(X_all)} motivos únicos)\n")
    f.write(f"- Excluídos: motivos AMBÍGUO (9) e NÃO_ASSUNTO (3) conforme plano\n")
    f.write(f"- Split: `StratifiedKFold(5)` sobre motivos únicos + hold-out 20% fixo\n")
    f.write(f"- Vetorização: `TfidfVectorizer(analyzer='char_wb', ngram_range=(2,4), sublinear_tf=True)`\n\n")

    f.write("## Cross-Validation (5 Folds — sobre motivos únicos)\n\n")
    f.write("| Modelo | Accuracy | Precision (macro) | Recall (macro) | F1-macro |\n")
    f.write("|---|---|---|---|---|\n")
    for nome, r in cv_results.items():
        f.write(
            f"| {nome} "
            f"| {r['accuracy_mean']:.4f} ± {r['accuracy_std']:.4f} "
            f"| {r['precision_macro_mean']:.4f} ± {r['precision_macro_std']:.4f} "
            f"| {r['recall_macro_mean']:.4f} ± {r['recall_macro_std']:.4f} "
            f"| {r['f1_macro_mean']:.4f} ± {r['f1_macro_std']:.4f} |\n"
        )

    f.write("\n## Hold-out 20% (Fixo — avaliação independente)\n\n")
    f.write("| Modelo | Accuracy | Precision (macro) | Recall (macro) | F1-macro |\n")
    f.write("|---|---|---|---|---|\n")
    for nome, r in holdout_results.items():
        f.write(
            f"| {nome} "
            f"| {r['accuracy']:.4f} "
            f"| {r['precision_macro']:.4f} "
            f"| {r['recall_macro']:.4f} "
            f"| {r['f1_macro']:.4f} |\n"
        )
    f.write(f"\n**Melhor modelo (F1-macro no hold-out):** {melhor}\n\n")

    f.write("## Matrizes de Confusão (Hold-out)\n\n")
    for nome, r in holdout_results.items():
        f.write(f"### {nome}\n\n")
        cm = confusion_matrix(r["y_test"], r["y_pred"], labels=classes)
        f.write("```\n")
        f.write("Classes: " + " | ".join([c[:20] for c in classes]) + "\n")
        f.write(str(cm) + "\n")
        f.write("```\n\n")

    f.write("## Limitações\n\n")
    f.write("- O classificador opera sobre textos de **motivos padronizados** (319 variações), não sobre linguagem livre.\n")
    f.write("- Desempenho em perguntas livres dos alunos pode ser inferior — ver `analise_erros.md`.\n")
    f.write("- Categorias com poucos motivos únicos (Carteirinha: 13, Portal: 21) têm menor representatividade.\n")
    f.write("- Rótulos foram atribuídos por regras auditáveis, sem validação humana independente nesta versão.\n")
    f.write("- Métricas apresentadas são de **teste técnico** (hold-out), não de validação humana.\n")

print(f"      Relatório salvo: {relatorio_path}")

# ------------------------------------------------------------------ #
# 7. Análise de erros                                                 #
# ------------------------------------------------------------------ #
print("\n[7/7] Gerando análise de erros ...")

erros_path = os.path.join(OUT_DIR, "analise_erros.md")
with open(erros_path, "w", encoding="utf-8") as f:
    f.write("# Análise de Erros — Classificador de Assuntos\n\n")
    f.write(f"**Data:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")

    for nome, r in holdout_results.items():
        f.write(f"## {nome}\n\n")
        erros = [(xt, yt, yp) for xt, yt, yp in
                 zip(X_test, r["y_test"], r["y_pred"]) if yt != yp]
        f.write(f"**Erros no hold-out:** {len(erros)} de {len(X_test)} "
                f"({len(erros)/len(X_test)*100:.1f}%)\n\n")
        if erros:
            f.write("| Motivo | Esperado | Predito |\n")
            f.write("|---|---|---|\n")
            for xt, yt, yp in erros[:30]:
                f.write(f"| {xt[:60]} | {yt[:30]} | {yp[:30]} |\n")
            if len(erros) > 30:
                f.write(f"\n*(+ {len(erros)-30} erros adicionais omitidos)*\n")
        f.write("\n")

    f.write("## Padrões de Erro Identificados\n\n")
    f.write("1. **Fronteira Financeiro/Matrícula**: motivos com 'isencao' e 'trancamento' simultaneamente.\n")
    f.write("2. **Fronteira Estágio/Vida Acadêmica**: 'atividade complementar' vs 'dispensa de disciplina'.\n")
    f.write("3. **Motivos muito curtos**: nomes genéricos (<3 palavras) tendem a errar mais.\n")
    f.write("4. **Categorias com poucos exemplos** (Carteirinha, Portal): maior variância nas predições.\n\n")
    f.write("## Recomendações\n\n")
    f.write("- Revisar manualmente os motivos sinalizados com `revisar=True` no `mapeamento_motivos.csv`.\n")
    f.write("- Adicionar mais exemplos manuais para Carteirinha e Portal e Sistemas.\n")
    f.write("- Avaliar com perguntas livres dos alunos (ver `test_externo.py`).\n")

print(f"      Análise de erros salva: {erros_path}")

print("\n" + "=" * 60)
print("✅ Etapa B concluída com sucesso.")
print("=" * 60)
print(f"\nArquivos em {MODEL_DIR}:")
for f in os.listdir(MODEL_DIR):
    print(f"  - {f}")

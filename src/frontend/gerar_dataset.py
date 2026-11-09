"""
Etapa A — Geração do dataset rotulado para treinamento do classificador de assuntos.

Fonte: C:\\Users\\LENOVO\\Downloads\\Relacionamentos.xlsx
Saída:
  - mapeamento_motivos.csv   : 1 linha por motivo único com categoria atribuída
  - dataset_treino.csv       : registros com categoria definida (exclui AMBIGUO e NAO_ASSUNTO)
  - dataset_excluidos.csv    : registros removidos do treino, com motivo
  - estatisticas_rotulagem.txt : resumo quantitativo

Regras: ver rotulagem.py
"""

import sys
import os
import pandas as pd

# Garantir que rotulagem.py seja encontrado mesmo rodando de outro diretório
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rotulagem import rotular, normalizar_motivo, AMBIGUO, NAO_ASSUNTO

XLSX_PATH = r"C:\Users\LENOVO\Downloads\Relacionamentos.xlsx"
OUT_DIR = os.path.dirname(os.path.abspath(__file__))

print("=" * 60)
print("ETAPA A — Geração do dataset rotulado")
print("=" * 60)

# 1. Carregar dados
print(f"\n[1/6] Carregando {XLSX_PATH} ...")
df = pd.read_excel(XLSX_PATH, engine="openpyxl")
print(f"      {len(df):,} linhas × {df.shape[1]} colunas")
print(f"      Colunas: {list(df.columns)}")

coluna_motivo = "Motivo do Contato"
assert coluna_motivo in df.columns, f"Coluna '{coluna_motivo}' não encontrada!"

# 2. Rotular cada motivo único
print(f"\n[2/6] Rotulando motivos únicos ...")
motivos_uniq = df[coluna_motivo].dropna().unique()
print(f"      Motivos únicos encontrados: {len(motivos_uniq)}")

resultados = []
for m in motivos_uniq:
    norm, cat, regra, revisar = rotular(m)
    resultados.append({
        "motivo_original": m,
        "motivo_normalizado": norm,
        "categoria": cat,
        "regra_aplicada": regra,
        "revisar": revisar,
    })

mapa = pd.DataFrame(resultados)

# 3. Salvar mapeamento completo
mapa_path = os.path.join(OUT_DIR, "mapeamento_motivos.csv")
mapa.to_csv(mapa_path, index=False, encoding="utf-8-sig")
print(f"\n[3/6] mapeamento_motivos.csv salvo: {len(mapa)} linhas")

# 4. Estatísticas de rotulagem
print(f"\n[4/6] Distribuição de categorias nos motivos únicos:")
contagem = mapa["categoria"].value_counts()
for cat, n in contagem.items():
    pct = n / len(mapa) * 100
    marcador = " [EXCLUIDO]" if cat in (AMBIGUO, NAO_ASSUNTO) else ""
    print(f"      {cat}: {n} ({pct:.1f}%){marcador}")

# 5. Juntar categoria de volta ao dataset completo
df["motivo_normalizado"] = df[coluna_motivo].apply(
    lambda x: normalizar_motivo(x) if pd.notna(x) else None
)
df = df.merge(
    mapa[["motivo_original", "categoria", "regra_aplicada", "revisar"]],
    left_on=coluna_motivo,
    right_on="motivo_original",
    how="left",
)

# Registros sem motivo (nulos)
sem_motivo = df["categoria"].isna()
df.loc[sem_motivo, "categoria"] = NAO_ASSUNTO
df.loc[sem_motivo, "regra_aplicada"] = "nulo: sem motivo registrado"

# 6. Separar treino e excluídos
mask_treino = ~df["categoria"].isin([AMBIGUO, NAO_ASSUNTO])
df_treino = df[mask_treino].copy()
df_excluidos = df[~mask_treino].copy()

treino_path = os.path.join(OUT_DIR, "dataset_treino.csv")
excluidos_path = os.path.join(OUT_DIR, "dataset_excluidos.csv")

# Remover colunas potencialmente sensíveis (ID de aluno não é atributo)
colunas_treino = ["motivo_normalizado", "categoria", "regra_aplicada", "revisar"]
df_treino[colunas_treino].to_csv(treino_path, index=False, encoding="utf-8-sig")
df_excluidos[colunas_treino + [coluna_motivo]].to_csv(excluidos_path, index=False, encoding="utf-8-sig")

print(f"\n[5/6] Registros finais:")
print(f"      Total original           : {len(df):,}")
print(f"      Incluídos no treino      : {len(df_treino):,} ({len(df_treino)/len(df)*100:.1f}%)")
print(f"      Excluídos (AMBIGUO)      : {(df['categoria'] == AMBIGUO).sum():,}")
print(f"      Excluídos (NAO_ASSUNTO)  : {(df['categoria'] == NAO_ASSUNTO).sum():,}")

print(f"\n[6/6] Distribuição de registros por categoria (treino):")
treino_contagem = df_treino["categoria"].value_counts()
for cat, n in treino_contagem.items():
    pct = n / len(df_treino) * 100
    print(f"      {cat}: {n:,} ({pct:.1f}%)")

# Motivos únicos por categoria no treino
print(f"\n      Motivos únicos por categoria (treino):")
uniq_por_cat = (
    df_treino.groupby("categoria")["motivo_normalizado"]
    .nunique()
    .sort_values(ascending=False)
)
for cat, n in uniq_por_cat.items():
    print(f"      {cat}: {n} motivos únicos")

# 7. Salvar estatísticas em txt
stats_path = os.path.join(OUT_DIR, "estatisticas_rotulagem.txt")
with open(stats_path, "w", encoding="utf-8") as f:
    f.write("ESTATÍSTICAS DE ROTULAGEM — ENTREGA 2 IA\n")
    f.write("=" * 50 + "\n\n")
    f.write(f"Arquivo fonte: {XLSX_PATH}\n")
    f.write(f"Total de registros: {len(df):,}\n")
    f.write(f"Motivos únicos (original): {len(motivos_uniq)}\n\n")
    f.write("Distribuição de MOTIVOS ÚNICOS por categoria:\n")
    for cat, n in contagem.items():
        marcador = " [EXCLUÍDO]" if cat in (AMBIGUO, NAO_ASSUNTO) else ""
        f.write(f"  {cat}: {n}{marcador}\n")
    f.write(f"\nRegistros no dataset de treino: {len(df_treino):,}\n")
    f.write(f"Registros excluídos: {len(df_excluidos):,}\n\n")
    f.write("Distribuição de REGISTROS por categoria (treino):\n")
    for cat, n in treino_contagem.items():
        f.write(f"  {cat}: {n:,} ({n/len(df_treino)*100:.1f}%)\n")
    f.write("\nMotivos únicos por categoria (treino):\n")
    for cat, n in uniq_por_cat.items():
        f.write(f"  {cat}: {n}\n")

print(f"\n      Estatísticas salvas em: {stats_path}")
print("\n✅ Etapa A concluída com sucesso.")
print(f"   Arquivos gerados em: {OUT_DIR}")

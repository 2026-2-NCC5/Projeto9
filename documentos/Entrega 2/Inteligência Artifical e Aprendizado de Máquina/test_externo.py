"""
Etapa C — Teste externo do classificador com:
  1. Perguntas reais anonimizadas do histórico do SecretarIA (SQLite, read-only)
  2. Perguntas sintéticas (claramente identificadas como tal)

IMPORTANTE:
  - SQLite é acessado em modo READ-ONLY (não há escrita).
  - Nenhum dado pessoal (RA, e-mail, nome) é usado como atributo.
  - Os dois conjuntos são avaliados e reportados SEPARADAMENTE.
  - Perguntas sintéticas são identificadas em todos os relatórios.
  - Essas perguntas NÃO foram usadas no treinamento.
"""

import sys, os, re, sqlite3
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import joblib
from sklearn.metrics import (
    accuracy_score, f1_score, classification_report, confusion_matrix
)

OUT_DIR    = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR  = os.path.join(OUT_DIR, "models")
DB_PATH    = r"C:\SecretaRIA\fecap-guia\backend\fecap_guia.db"
BEST_MODEL = os.path.join(MODEL_DIR, "asa_topic_best_v1.joblib")

print("=" * 60)
print("ETAPA C — Teste externo do classificador")
print("=" * 60)

# ------------------------------------------------------------------ #
# 1. Carregar o melhor modelo                                          #
# ------------------------------------------------------------------ #
print(f"\n[1/4] Carregando modelo: {BEST_MODEL}")
pipe = joblib.load(BEST_MODEL)
print("      Modelo carregado com sucesso.")


# ------------------------------------------------------------------ #
# 2. Perguntas reais do SQLite (read-only, anonimizadas)              #
# ------------------------------------------------------------------ #
print(f"\n[2/4] Buscando perguntas reais no SQLite: {DB_PATH}")

resultados_reais = None
msgs_reais = []

# Padrões de dados pessoais para exclusão (anonimização)
REGEX_PESSOAL = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"  # email
    r"|\b\d{5,}\b"                                             # RA / números longos
    r"|\b(cpf|rg|ra|rm)\b",                                   # siglas sensíveis
    re.IGNORECASE,
)

try:
    # Conectar em modo read-only via URI
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    # Tentar tabelas comuns; ajustar se necessário
    tabelas = pd.read_sql(
        "SELECT name FROM sqlite_master WHERE type='table'", conn
    )
    print(f"      Tabelas encontradas: {tabelas['name'].tolist()}")

    # Tentar ler mensagens do usuário
    df_msgs = None
    for tabela_cand in ["messages", "chat_messages", "conversations", "logs"]:
        if tabela_cand in tabelas["name"].values:
            colunas = pd.read_sql(
                f"PRAGMA table_info({tabela_cand})", conn
            )["name"].tolist()
            print(f"      Tabela '{tabela_cand}' — colunas: {colunas}")

            # Detectar coluna de texto e coluna de remetente
            col_text   = next((c for c in colunas if c in
                               ["content","text","message","body","pergunta"]), None)
            col_sender = next((c for c in colunas if c in
                               ["sender","role","type","origem"]), None)

            if col_text:
                if col_sender:
                    df_msgs = pd.read_sql(
                        f"SELECT {col_text} as texto FROM {tabela_cand} "
                        f"WHERE {col_sender} IN ('user','usuario','aluno','student') "
                        f"LIMIT 500",
                        conn,
                    )
                else:
                    df_msgs = pd.read_sql(
                        f"SELECT {col_text} as texto FROM {tabela_cand} LIMIT 500", conn
                    )
                print(f"      {len(df_msgs)} mensagens recuperadas de '{tabela_cand}'.")
                break

    conn.close()

    if df_msgs is not None and len(df_msgs) > 0:
        # Anonimizar: remover linhas com padrões pessoais óbvios
        df_msgs = df_msgs.dropna(subset=["texto"])
        df_msgs["texto"] = df_msgs["texto"].astype(str).str.strip()
        df_msgs = df_msgs[df_msgs["texto"].str.len() >= 10]
        mask_sensivel = df_msgs["texto"].str.contains(REGEX_PESSOAL, regex=True)
        n_removidas = mask_sensivel.sum()
        df_msgs = df_msgs[~mask_sensivel].copy()
        print(f"      Mensagens com dados pessoais removidas: {n_removidas}")
        print(f"      Mensagens prontas para classificacao: {len(df_msgs)}")
        msgs_reais = df_msgs["texto"].tolist()
    else:
        print("      AVISO: Nenhuma mensagem de usuario encontrada ou tabela incompativel.")

except Exception as e:
    print(f"      AVISO: Nao foi possivel acessar o SQLite — {e}")
    print("      Continuando apenas com perguntas sinteticas.")


# ------------------------------------------------------------------ #
# 3. Perguntas sintéticas (100 exemplos, 8 categorias)                #
# ------------------------------------------------------------------ #
print(f"\n[3/4] Carregando perguntas sinteticas ...")

SINTETICAS = [
    # Documentação Acadêmica (12)
    ("Como obtenho meu atestado de matrícula?",           "Documentação Acadêmica"),
    ("Preciso de uma declaração de conclusão de curso.",  "Documentação Acadêmica"),
    ("Quando sai meu diploma?",                           "Documentação Acadêmica"),
    ("Como solicitar o histórico escolar?",               "Documentação Acadêmica"),
    ("Preciso de certidão de regularidade.",              "Documentação Acadêmica"),
    ("Como pedir comprovante de matrícula?",              "Documentação Acadêmica"),
    ("Onde retiro meu certificado de conclusão?",         "Documentação Acadêmica"),
    ("Preciso de um atestado de frequência.",             "Documentação Acadêmica"),
    ("Como solicitar declaração para estágio?",           "Documentação Acadêmica"),
    ("Meu diploma ainda não chegou, o que fazer?",        "Documentação Acadêmica"),
    ("Preciso do prontuário acadêmico.",                  "Documentação Acadêmica"),
    ("Como obter o histórico em inglês?",                 "Documentação Acadêmica"),

    # Matrícula, Rematrícula e Trancamento (12)
    ("Como faço rematrícula para o próximo semestre?",    "Matrícula, Rematrícula e Trancamento"),
    ("Quero trancar meu curso, como procedo?",            "Matrícula, Rematrícula e Trancamento"),
    ("Perdi o prazo de matrícula, ainda consigo?",        "Matrícula, Rematrícula e Trancamento"),
    ("Como cancelar minha matrícula?",                    "Matrícula, Rematrícula e Trancamento"),
    ("Quero destravar o trancamento do meu curso.",       "Matrícula, Rematrícula e Trancamento"),
    ("Como fazer transferência para outra instituição?",  "Matrícula, Rematrícula e Trancamento"),
    ("Sou ingressante e ainda não fiz matrícula.",        "Matrícula, Rematrícula e Trancamento"),
    ("Quero reverter o cancelamento do meu curso.",       "Matrícula, Rematrícula e Trancamento"),
    ("Qual o prazo de rematrícula?",                      "Matrícula, Rematrícula e Trancamento"),
    ("Esqueci de fazer rematrícula, e agora?",            "Matrícula, Rematrícula e Trancamento"),
    ("Quero solicitar afastamento temporário.",           "Matrícula, Rematrícula e Trancamento"),
    ("Como entrar com pedido de matrícula especial?",     "Matrícula, Rematrícula e Trancamento"),

    # Vida Acadêmica e Avaliações (12)
    ("Qual a data da prova substitutiva?",                "Vida Acadêmica e Avaliações"),
    ("Quero solicitar revisão de nota.",                  "Vida Acadêmica e Avaliações"),
    ("Faltei em muitas aulas, vou reprovar?",             "Vida Acadêmica e Avaliações"),
    ("Como faço DP (dependência)?",                       "Vida Acadêmica e Avaliações"),
    ("Preciso de dispensa de disciplina por aproveitamento.", "Vida Acadêmica e Avaliações"),
    ("Como funciona a grade curricular do meu curso?",    "Vida Acadêmica e Avaliações"),
    ("Posso cursar disciplina como ouvinte?",             "Vida Acadêmica e Avaliações"),
    ("Quero solicitar antecipação de disciplina.",        "Vida Acadêmica e Avaliações"),
    ("Qual o critério de avaliação do curso?",            "Vida Acadêmica e Avaliações"),
    ("Como verificar minha lista de presença?",           "Vida Acadêmica e Avaliações"),
    ("Quero participar das aulas concentradas.",          "Vida Acadêmica e Avaliações"),
    ("Tenho sobreposição de horário em duas disciplinas.","Vida Acadêmica e Avaliações"),

    # Portal e Sistemas (12)
    ("Esqueci minha senha do portal do aluno.",           "Portal e Sistemas"),
    ("O Moodle não está abrindo para mim.",               "Portal e Sistemas"),
    ("Como acesso o e-mail institucional?",               "Portal e Sistemas"),
    ("Preciso me conectar ao Wi-Fi da faculdade.",        "Portal e Sistemas"),
    ("Como uso a VPN da instituição remotamente?",        "Portal e Sistemas"),
    ("O Office 365 parou de funcionar.",                  "Portal e Sistemas"),
    ("Preciso de crédito de impressão.",                  "Portal e Sistemas"),
    ("Como acesso o sistema de serviços online?",         "Portal e Sistemas"),
    ("Minha senha do portal expirou.",                    "Portal e Sistemas"),
    ("O computador do laboratório não está funcionando.", "Portal e Sistemas"),
    ("Como configurar o Zoom institucional?",             "Portal e Sistemas"),
    ("Não consigo acessar o portal do aluno.",            "Portal e Sistemas"),

    # Estágio, Carreira e Atividades Complementares (12)
    ("Como registro meu estágio obrigatório?",            "Estágio, Carreira e Atividades Complementares"),
    ("Quantas horas complementares preciso?",             "Estágio, Carreira e Atividades Complementares"),
    ("Como validar atividades complementares?",           "Estágio, Carreira e Atividades Complementares"),
    ("Quero participar de monitoria como atividade.",     "Estágio, Carreira e Atividades Complementares"),
    ("Como acessar o FECAP+ oportunidades?",              "Estágio, Carreira e Atividades Complementares"),
    ("Quero submeter meu TCC para avaliação.",            "Estágio, Carreira e Atividades Complementares"),
    ("Como faço intercâmbio acadêmico?",                  "Estágio, Carreira e Atividades Complementares"),
    ("Preciso de ajuda para montar meu currículo.",       "Estágio, Carreira e Atividades Complementares"),
    ("Quando começa o programa de iniciação científica?", "Estágio, Carreira e Atividades Complementares"),
    ("Como participar do NAF?",                           "Estágio, Carreira e Atividades Complementares"),
    ("Quero informações sobre soft skills.",              "Estágio, Carreira e Atividades Complementares"),
    ("Como validar horas de curso externo?",              "Estágio, Carreira e Atividades Complementares"),

    # Financeiro, Bolsas e Financiamento (12)
    ("Como emito o boleto da mensalidade?",               "Financeiro, Bolsas e Financiamento"),
    ("Minha parcela está em aberto, o que faço?",         "Financeiro, Bolsas e Financiamento"),
    ("Quero renegociar minha dívida.",                    "Financeiro, Bolsas e Financiamento"),
    ("Como funciona o FIES?",                             "Financeiro, Bolsas e Financiamento"),
    ("Tenho bolsa ProUni, como renovo?",                  "Financeiro, Bolsas e Financiamento"),
    ("Preciso de carta de quitação financeira.",          "Financeiro, Bolsas e Financiamento"),
    ("Como solicito reembolso de parcela paga a mais?",   "Financeiro, Bolsas e Financiamento"),
    ("Meu desconto de bolsa não foi aplicado.",           "Financeiro, Bolsas e Financiamento"),
    ("Preciso do demonstrativo de pagamentos para IR.",   "Financeiro, Bolsas e Financiamento"),
    ("Como altero o responsável financeiro?",             "Financeiro, Bolsas e Financiamento"),
    ("Quero solicitar assistência financeira.",           "Financeiro, Bolsas e Financiamento"),
    ("Tenho multa por atraso, posso contestar?",          "Financeiro, Bolsas e Financiamento"),

    # Carteirinha e Transporte (12)
    ("Como faço minha carteirinha estudantil?",           "Carteirinha e Transporte"),
    ("Perdi a carteirinha, como obtenho outra?",          "Carteirinha e Transporte"),
    ("Como solicitar bilhete único estudantil?",          "Carteirinha e Transporte"),
    ("Meu passe escolar não foi renovado.",               "Carteirinha e Transporte"),
    ("Preciso de carteirinha para ir ao cinema.",         "Carteirinha e Transporte"),
    ("Como tirar o passe livre estudantil?",              "Carteirinha e Transporte"),
    ("Meu crachá de acesso está bloqueado.",              "Carteirinha e Transporte"),
    ("Como renovar a carteirinha semestral?",             "Carteirinha e Transporte"),
    ("Onde retiro minha carteirinha?",                    "Carteirinha e Transporte"),
    ("Preciso de segunda via da carteirinha.",            "Carteirinha e Transporte"),
    ("Como habilitar a carteirinha no sistema?",          "Carteirinha e Transporte"),
    ("Meu bilhete único foi cancelado.",                  "Carteirinha e Transporte"),

    # Atendimento Geral e Serviços do Campus (12)
    ("Como reservar uma sala de estudo?",                 "Atendimento Geral e Serviços do Campus"),
    ("Quero empréstimo de livro na biblioteca.",          "Atendimento Geral e Serviços do Campus"),
    ("Preciso de apoio psicológico.",                     "Atendimento Geral e Serviços do Campus"),
    ("Como acessar o sistema de achados e perdidos?",     "Atendimento Geral e Serviços do Campus"),
    ("O elevador do bloco B está com problema.",          "Atendimento Geral e Serviços do Campus"),
    ("Como faço pesquisa bibliográfica com normas ABNT?", "Atendimento Geral e Serviços do Campus"),
    ("Quero participar de evento no campus.",             "Atendimento Geral e Serviços do Campus"),
    ("Como acessar os recursos de pesquisa da biblioteca?","Atendimento Geral e Serviços do Campus"),
    ("Preciso de informações sobre cursos de extensão.",  "Atendimento Geral e Serviços do Campus"),
    ("Quero fazer um tour pelo campus.",                  "Atendimento Geral e Serviços do Campus"),
    ("Como reservo o co-lab para meu grupo?",             "Atendimento Geral e Serviços do Campus"),
    ("Minha restrição religiosa afeta provas?",           "Atendimento Geral e Serviços do Campus"),
]

df_sint = pd.DataFrame(SINTETICAS, columns=["pergunta", "categoria_esperada"])
df_sint["fonte"] = "sintetico"

sint_path = os.path.join(OUT_DIR, "test_sintetico.csv")
df_sint.to_csv(sint_path, index=False, encoding="utf-8-sig")
print(f"      {len(df_sint)} perguntas sinteticas salvas em: {sint_path}")
print(f"      Distribuicao: {df_sint['categoria_esperada'].value_counts().to_dict()}")


# ------------------------------------------------------------------ #
# 4. Avaliar e gerar relatório                                         #
# ------------------------------------------------------------------ #
print("\n[4/4] Avaliando e gerando relatorio ...")

relatorio = []
relatorio.append("# Avaliação Externa do Classificador — Entrega 2 IA\n")
relatorio.append("**IMPORTANTE:** estes conjuntos NÃO foram usados no treinamento.\n")
relatorio.append("Perguntas sintéticas são claramente identificadas como tal.\n\n")

# --- 4a. Conjunto sintético ---
relatorio.append("## 1. Perguntas Sintéticas (fonte: equipe SecretarIA)\n")
relatorio.append(f"- **Total:** {len(df_sint)} perguntas (12 por categoria, 8 categorias)\n")
relatorio.append("- **Rótulos:** definidos pela equipe, revisados antes da avaliação\n")
relatorio.append("- **Fonte:** sintético — NÃO representam perguntas reais de alunos\n\n")

X_sint = df_sint["pergunta"].tolist()
y_sint_true = df_sint["categoria_esperada"].tolist()
y_sint_pred = pipe.predict(X_sint)

acc_sint  = accuracy_score(y_sint_true, y_sint_pred)
f1_sint   = f1_score(y_sint_true, y_sint_pred, average="macro", zero_division=0)

relatorio.append(f"| Métrica | Valor |\n|---|---|\n")
relatorio.append(f"| Accuracy | {acc_sint:.4f} |\n")
relatorio.append(f"| F1-macro | {f1_sint:.4f} |\n\n")
relatorio.append("### Classification Report (Sintético)\n\n```\n")
relatorio.append(classification_report(y_sint_true, y_sint_pred, zero_division=0))
relatorio.append("```\n\n")

# Erros sintéticos
erros_sint = [(x, yt, yp) for x, yt, yp in
              zip(X_sint, y_sint_true, y_sint_pred) if yt != yp]
relatorio.append(f"### Erros no conjunto sintético: {len(erros_sint)} de {len(X_sint)}\n\n")
if erros_sint:
    relatorio.append("| Pergunta | Esperado | Predito |\n|---|---|---|\n")
    for x, yt, yp in erros_sint:
        relatorio.append(f"| {x[:70]} | {yt[:30]} | {yp[:30]} |\n")
relatorio.append("\n")

print(f"\n      [Sintetico] Accuracy={acc_sint:.4f} | F1-macro={f1_sint:.4f}")
print(f"      Erros: {len(erros_sint)}/{len(X_sint)}")

# --- 4b. Conjunto real (se disponível) ---
relatorio.append("## 2. Perguntas Reais Anonimizadas (histórico SQLite)\n\n")

if msgs_reais:
    relatorio.append(f"- **Total recuperado:** {len(msgs_reais)} mensagens de usuários\n")
    relatorio.append("- **Anonimização:** e-mails, RAs e siglas pessoais removidos\n")
    relatorio.append("- **Rótulos:** NÃO disponíveis (ausência de ground truth rotulado)\n")
    relatorio.append("- **Avaliação possível:** distribuição das predições (sem métricas de acurácia)\n\n")

    y_reais_pred = pipe.predict(msgs_reais)
    dist_pred = pd.Series(y_reais_pred).value_counts()
    relatorio.append("### Distribuição das Categorias Preditas (sem ground truth)\n\n")
    relatorio.append("| Categoria | Predições | % |\n|---|---|---|\n")
    for cat, n in dist_pred.items():
        pct = n / len(msgs_reais) * 100
        relatorio.append(f"| {cat} | {n} | {pct:.1f}% |\n")

    # Salvar predições
    df_reais_pred = pd.DataFrame({
        "pergunta_anonimizada": msgs_reais,
        "categoria_predita": y_reais_pred,
        "fonte": "real_anonimizado"
    })
    reais_path = os.path.join(OUT_DIR, "test_reais_predicoes.csv")
    df_reais_pred.to_csv(reais_path, index=False, encoding="utf-8-sig")
    relatorio.append(f"\n*Predições salvas em `test_reais_predicoes.csv`.*\n\n")
    print(f"\n      [Real] {len(msgs_reais)} mensagens classificadas (sem ground truth)")
    print(f"      Distribuicao: {dist_pred.to_dict()}")
else:
    relatorio.append("> **LIMITAÇÃO REPORTADA:** Não foi possível recuperar perguntas reais\n")
    relatorio.append("> do histórico SQLite (tabela incompatível, banco vazio ou inacessível).\n")
    relatorio.append("> A avaliação com perguntas reais de alunos permanece como pendência.\n")
    relatorio.append("> Esta limitação NÃO é substituída silenciosamente pelas perguntas sintéticas.\n\n")
    print("\n      [Real] AVISO: nenhuma pergunta real disponivel.")

relatorio.append("## 3. Limitações da Avaliação Externa\n\n")
relatorio.append("1. O modelo foi treinado em **motivos padronizados** (texto administrativo curto).\n")
relatorio.append("2. Perguntas livres dos alunos têm vocabulário diferente — desempenho pode ser menor.\n")
relatorio.append("3. Perguntas sintéticas foram criadas pela equipe e podem não refletir dúvidas reais.\n")
relatorio.append("4. Ausência de ground truth rotulado para perguntas reais impede cálculo de acurácia.\n")
relatorio.append("5. Validação humana independente ainda não realizada.\n")

relatorio_ext_path = os.path.join(OUT_DIR, "avaliacao_externa.md")
with open(relatorio_ext_path, "w", encoding="utf-8") as f:
    f.writelines(relatorio)
print(f"\n      Relatorio externo salvo: {relatorio_ext_path}")

print("\n" + "=" * 60)
print("✅ Etapa C concluida com sucesso.")
print("=" * 60)

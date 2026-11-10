"""
Rotulagem auditável dos motivos de contato (Relacionamentos.xlsx) em 8 categorias
do Agente 3 — Orientação ao Estudante (SecretarIA).

Cada motivo recebe: motivo_normalizado, categoria, regra_aplicada, revisar.
As regras são aplicadas em ordem (a primeira que casa vence). Regras "manual:" são
exceções explícitas registradas com justificativa.
"""
import re
import unicodedata

CATEGORIAS = [
    "Documentação Acadêmica",
    "Matrícula, Rematrícula e Trancamento",
    "Vida Acadêmica e Avaliações",
    "Portal e Sistemas",
    "Estágio, Carreira e Atividades Complementares",
    "Financeiro, Bolsas e Financiamento",
    "Carteirinha e Transporte",
    "Atendimento Geral e Serviços do Campus",
]
NAO_ASSUNTO = "__NAO_ASSUNTO__"
AMBIGUO = "__AMBIGUO__"


def sem_acento(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)).lower()


def normalizar_motivo(m: str) -> str:
    """Remove marcadores de obsolescência para unir variantes ao motivo ativo."""
    s = str(m).strip()
    s = re.sub(r"\s*-\s*INATIVO\s*", " ", s, flags=re.I)
    s = re.sub(r"\s*\(Obsoleto\)\s*", " ", s, flags=re.I)
    s = re.sub(r"\s+", " ", s).strip()
    return s


# Exceções manuais (motivo normalizado sem acento, minúsculo) -> (categoria, justificativa)
MANUAL = {
    "nao compareceu ao atendimento": (NAO_ASSUNTO, "descreve resultado do atendimento, não assunto"),
    "atendimento cancelado": (NAO_ASSUNTO, "descreve resultado do atendimento, não assunto"),
    "contato nao realizado": (NAO_ASSUNTO, "descreve resultado do atendimento, não assunto"),
    "servico especial": (AMBIGUO, "rótulo genérico sem assunto identificável"),
    "reclame aqui": (AMBIGUO, "canal de manifestação, assunto variável"),
    "ouvidoria": (AMBIGUO, "canal de manifestação, assunto variável"),
    "procon": (AMBIGUO, "canal de manifestação, assunto variável"),
    "sugestoes": (AMBIGUO, "assunto variável"),
    "alunos com baixo desempenho": (AMBIGUO, "situação do aluno, não pedido de serviço"),
    "abertura de comissao de etica": (AMBIGUO, "processo disciplinar, fora do escopo de orientação"),
    "bolsa estagio": ("Financeiro, Bolsas e Financiamento", "modalidade de bolsa (fronteira com Estágio)"),
    "disciplinas em ingles - validacao de horas complementares": ("Estágio, Carreira e Atividades Complementares", "validação de horas complementares"),
    "abatimento de valores de disciplinas em ingles": ("Financeiro, Bolsas e Financiamento", "abatimento de valor"),
    "isencao de uma mensalidade devido ao trancamento": ("Financeiro, Bolsas e Financiamento", "isenção de mensalidade"),
    "trancamento de curso - para cursar antecipacao": ("Matrícula, Rematrícula e Trancamento", "trancamento"),
    "entrega de documentos pendentes": ("Matrícula, Rematrícula e Trancamento", "pendência documental de matrícula"),
    "entrega de documentos para ingresso especial": ("Matrícula, Rematrícula e Trancamento", "documentação de ingresso"),
    "historico escolar (risco de evasao)": ("Documentação Acadêmica", "histórico escolar"),
    "entrega de trabalho de conclusao de curso": ("Estágio, Carreira e Atividades Complementares", "TCC"),
    "entrega de trabalho e solicitacao diploma": ("Documentação Acadêmica", "diploma"),
    "alteracao de dados cadastrais": ("Atendimento Geral e Serviços do Campus", "cadastro"),
    "inclusao de nome social do estudante na matricula": ("Atendimento Geral e Serviços do Campus", "dados cadastrais"),
    "alteracao de genero no registro de matricula": ("Atendimento Geral e Serviços do Campus", "dados cadastrais"),
    "disponibilizacao do numero de matricula": ("Atendimento Geral e Serviços do Campus", "dados cadastrais"),
    "confeccao de cracha de visitante (para estudantes nao rematriculados)": ("Carteirinha e Transporte", "crachá de acesso"),
    "reuniao com a coordenacao de curso": ("Vida Acadêmica e Avaliações", "coordenação de curso"),
    "coach academico": ("Atendimento Geral e Serviços do Campus", "apoio ao estudante"),
    "ajuste de ponderacao": ("Vida Acadêmica e Avaliações", "ponderação de notas"),
    "sistema de achados e perdidos": ("Atendimento Geral e Serviços do Campus", "serviço do campus"),
    "cadastro de senha": ("Portal e Sistemas", "credenciais de sistemas"),
    "suporte para impressao": ("Portal e Sistemas", "serviço de TI"),
    "credito de impressao": ("Portal e Sistemas", "serviço de TI"),
}

# Regras por palavra-chave (sem acento), em ordem de precedência
REGRAS = [
    ("Carteirinha e Transporte", ["carteirinha", "cracha", "bilhete unico", "passe escolar", "passe livre"]),
    ("Estágio, Carreira e Atividades Complementares", ["estagio", "atividade complementar", "horas complementares",
        "fecap+ oportunidades", "carreira", "linkedin", "curriculo", "iniciacao cientifica", "monitoria",
        "intercambio", "alumni", "naf", "peiex", "soft skills"]),
    ("Financeiro, Bolsas e Financiamento", ["boleto", "mensalidade", "parcela", "restitui", "reembols", "negociacao",
        "contrato de prestacao", "responsavel financeiro", "bolsa", "prouni", "fies", "pagamento", "financeir",
        "debito", "adimplencia", "semestralidade", "assistencia financeira", "parcelamento", "multas", "isencao",
        "abono de valores", "demonstrativo", "carta de quitacao", "beneficio"]),
    ("Portal e Sistemas", ["portal", "e-mail", "email", "moodle", "wi-fi", "vpn", "zoom", "office 365", "senha",
        "laboratorios de informatica", "computadores", "servicos on-line", "online", "on-line"]),
    ("Documentação Acadêmica", ["atestado", "declaracao", "historico escolar", "diploma", "certificado", "certidao",
        "colacao", "prontuario", "documentos", "traducao juramentada", "assinatura da secretaria", "comprovante"]),
    ("Matrícula, Rematrícula e Trancamento", ["rematricula", "matricula", "trancamento", "destrancamento",
        "cancelamento de curso", "cancelamento do curso", "reverter cancelamento", "transferencia", "ingressante",
        "afastamento"]),
    ("Vida Acadêmica e Avaliações", ["prova", "exame", "nota", "falta", "dp", "adapt", "grade", "dispensa",
        "disciplina", "pedp", "nivelamento", "conteudo programatico", "antecipacao", "ouvinte", "aproveitamento",
        "criterio de avaliacao", "lista de presenca", "eletiva", "concentradas", "remanejamento", "sobreposic",
        "plantoes", "metodos quantitativos", "laboratorios de portugues", "english corner", "libras"]),
    ("Atendimento Geral e Serviços do Campus", ["biblioteca", "bibliotec", "emprestimo", "evento", "reserva",
        "apoio psicologico", "coach", "manutencao", "limpeza", "elevador", "estacionamento", "socorros",
        "visitantes", "cameras", "conseg", "inicio das aulas", "primeiros passos", "tour", "materiais",
        "livros", "levantamento bibliografico", "abnt", "recursos de pesquisas", "coletivos", "divulgacao",
        "comut", "chaves", "entorno", "restricao religiosa", "curso de curta duracao", "extensao", "cursos de extensao",
        "audiovisuais", "infraestrutura", "co-labs"]),
]


def rotular(motivo_original: str):
    norm = normalizar_motivo(motivo_original)
    chave = sem_acento(norm)
    if chave in MANUAL:
        cat, just = MANUAL[chave]
        return norm, cat, f"manual: {just}", cat in (AMBIGUO,)
    for cat, palavras in REGRAS:
        for p in palavras:
            if re.search(r"(?<![a-z])" + re.escape(p), chave):
                return norm, cat, f"palavra-chave: '{p}'", False
    return norm, AMBIGUO, "sem regra aplicável", True

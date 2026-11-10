import json

notebook = {
 "cells": [
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "# FECAP — Álgebra Linear, Vetores e Geometria Analítica\n",
    "## Entrega 2 — Aplicação Avançada de Álgebra Linear no Agente SecretarIA\n",
    "**Projeto Interdisciplinar:** ASA (Agente de Serviços Acadêmicos) — Agente 3: Orientação ao Estudante\n",
    "**Conceito Aplicado:** Transformações Lineares no $\\mathbb{R}^3$ ($T(\\vec{v}) = A \\cdot \\vec{v}$) com Matriz de Ponderação de Eixos de Atendimento\n",
    "**Integrantes:** Grupo SecretarIA / Ciência da Computação FECAP 2026\n",
    "\n",
    "---\n",
    "\n",
    "### 1. Contexto e Relação com a Entrega 1\n",
    "\n",
    "Na **Entrega 1**, modelamos o espaço de busca semântica em $\\mathbb{R}^3$ utilizando três dimensões conceituais:\n",
    "- **Eixo $x_1$:** Sistemas e Portal Acadêmico (ex.: Aluno Online, AVA, Moodle, login, senhas).\n",
    "- **Eixo $x_2$:** Documentos e Procedimentos da Secretaria (ex.: emissão de histórico, atestados, certidões, prazos).\n",
    "- **Eixo $x_3$:** Canais e Setores de Atendimento (ex.: guichê presencial, e-mail do ASA, WhatsApp, agendamento).\n",
    "\n",
    "Com essa representação, a pergunta do estudante e os documentos da base de conhecimento foram modelados como vetores no $\\mathbb{R}^3$:\n",
    "- $\\vec{v}_{pergunta} = [0.8, 0.9, 0.2]^T$ (dúvida do aluno: *\"Como emitir meu histórico escolar oficial no portal?\"*)\n",
    "- $\\vec{v}_{artigo1} = [0.7, 0.95, 0.1]^T$ (*\"Guia de Emissão de Histórico Acadêmico via Portal\"*)\n",
    "- $\\vec{v}_{artigo2} = [0.1, 0.2, 0.9]^T$ (*\"Canais de Atendimento Presencial e Telefônico do ASA\"*)\n",
    "\n",
    "Na Entrega 1, comparamos esses vetores usando o **Produto Escalar**, a **Distância Euclidiana** e a **Similaridade de Cosseno**, demonstrando que o Artigo 1 era o mais próximo semântico da dúvida do aluno.\n",
    "\n",
    "--- \n",
    "\n",
    "### 2. O Conceito Avançado da Entrega 2: Transformações Lineares ($T: \\mathbb{R}^3 \\to \\mathbb{R}^3$)\n",
    "\n",
    "Em um sistema de produção real, o contexto institucional pode demandar **reponderação dinâmica dos eixos de busca** sem que seja necessário recriar ou retreinar todos os modelos. Por exemplo:\n",
    "1. **Cenário de Contingência ou Greve de Atendimento Presencial:** O agente deve atenuar canais físicos e amplificar soluções de autoatendimento no portal.\n",
    "2. **Cenário de Instabilidade Técnica nos Sistemas:** O agente deve priorizar canais humanos de contato e contingência.\n",
    "\n",
    "Matematicamente, uma **Transformação Linear** $T: \\mathbb{R}^3 \\to \\mathbb{R}^3$ é uma função que preserva as operações de adição vetorial e multiplicação por escalar:\n",
    "$$T(u + v) = T(u) + T(v)$$\n",
    "$$T(\\alpha \\cdot v) = \\alpha \\cdot T(v)$$\n",
    "\n",
    "Toda transformação linear em $\\mathbb{R}^3$ pode ser representada pela multiplicação por uma matriz canônica $A \\in \\mathbb{R}^{3 \\times 3}$:\n",
    "$$T(\\vec{v}) = A \\cdot \\vec{v}$$\n",
    "\n",
    "Definimos nossa matriz de transformação $A$ como uma matriz diagonal de ponderação:\n",
    "$$A = \\begin{bmatrix} w_{portal} & 0 & 0 \\\\ 0 & w_{documentos} & 0 \\\\ 0 & 0 & w_{canais} \\end{bmatrix}$$\n",
    "\n",
    "Quando aplicamos $A$ aos vetores $\\vec{v}_{pergunta}$ e $\\vec{v}_{artigo}$, o espaço vetorial sofre uma **deformação linear (estiramento ou compressão ao longo dos eixos coordenados)**, alterando as distâncias e os ângulos entre os vetores de forma controlada e matematicamente previsível."
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "import numpy as np\n",
    "import pandas as pd\n",
    "import matplotlib.pyplot as plt\n",
    "\n",
    "# 1. Definição dos vetores originais da Entrega 1\n",
    "v_pergunta = np.array([0.8, 0.9, 0.2], dtype=float)\n",
    "v_artigo1 = np.array([0.7, 0.95, 0.1], dtype=float)  # Guia Histórico\n",
    "v_artigo2 = np.array([0.1, 0.2, 0.9], dtype=float)   # Canais de Atendimento\n",
    "\n",
    "eixos = [\"Portal/Sistemas (x1)\", \"Documentos/Secretaria (x2)\", \"Canais/Setores (x3)\"]\n",
    "\n",
    "print(\"Vetores originais da Entrega 1:\")\n",
    "print(f\"v_pergunta : {v_pergunta}\")\n",
    "print(f\"v_artigo1  : {v_artigo1} (Guia Histórico)\")\n",
    "print(f\"v_artigo2  : {v_artigo2} (Canais de Atendimento)\")"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "### 3. Funções Matemáticas de Comparação Vetorial\n",
    "\n",
    "Relembrando as formulações matemáticas fundamentais:\n",
    "1. **Produto Escalar:** $\\vec{u} \\cdot \\vec{v} = \\sum_{i=1}^n u_i v_i$\n",
    "2. **Distância Euclidiana:** $d(\\vec{u}, \\vec{v}) = \\|\\vec{u} - \\vec{v}\\|_2 = \\sqrt{\\sum_{i=1}^n (u_i - v_i)^2}$\n",
    "3. **Similaridade de Cosseno:** $\\cos(\\theta) = \\frac{\\vec{u} \\cdot \\vec{v}}{\\|\\vec{u}\\| \\|\\vec{v}\\|}$"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "def calcular_metricas(u: np.ndarray, v: np.ndarray):\n",
    "    dot = float(np.dot(u, v))\n",
    "    dist = float(np.linalg.norm(u - v))\n",
    "    norm_u = float(np.linalg.norm(u))\n",
    "    norm_v = float(np.linalg.norm(v))\n",
    "    cos_sim = float(dot / (norm_u * norm_v)) if (norm_u > 0 and norm_v > 0) else 0.0\n",
    "    return dot, dist, cos_sim\n",
    "\n",
    "# Métricas na base original (Entrega 1)\n",
    "dot1_orig, dist1_orig, cos1_orig = calcular_metricas(v_pergunta, v_artigo1)\n",
    "dot2_orig, dist2_orig, cos2_orig = calcular_metricas(v_pergunta, v_artigo2)\n",
    "\n",
    "df_orig = pd.DataFrame({\n",
    "    \"Documento\": [\"Artigo 1 (Guia Histórico)\", \"Artigo 2 (Canais Atendimento)\"],\n",
    "    \"Produto Escalar\": [dot1_orig, dot2_orig],\n",
    "    \"Distância Euclidiana\": [dist1_orig, dist2_orig],\n",
    "    \"Similaridade Cosseno\": [cos1_orig, cos2_orig]\n",
    "})\n",
    "display(df_orig)"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "### 4. Aplicação da Transformação Linear $T(\\vec{v}) = A \\cdot \\vec{v}$\n",
    "\n",
    "Vamos realizar dois experimentos acadêmicos:\n",
    "1. **Experimento 1 (Matriz Identidade):** $A_1 = I_3$, validando a preservação exata dos valores da Entrega 1.\n",
    "2. **Experimento 2 (Transformação de Contingência / Foco em Canais):** Atenuação dos eixos de portal e documentos e amplificação do eixo de canais de atendimento presencial/humano:\n",
    "$$A_2 = \\begin{bmatrix} 0.1 & 0 & 0 \\\\ 0 & 0.1 & 0 \\\\ 0 & 0 & 10.0 \\end{bmatrix}$$\n",
    "\n",
    "Aplicando a transformação linear aos vetores:"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "# Matriz de Transformação A2 (Foco em Canais de Atendimento)\n",
    "w_portal = 0.1\n",
    "w_documentos = 0.1\n",
    "w_canais = 10.0\n",
    "\n",
    "A2 = np.diag([w_portal, w_documentos, w_canais])\n",
    "print(\"Matriz de Transformação Linear A:\")\n",
    "print(A2)\n",
    "\n",
    "# Novos vetores transformados no R^3: T(v) = A * v\n",
    "v_pergunta_trans = A2 @ v_pergunta\n",
    "v_artigo1_trans = A2 @ v_artigo1\n",
    "v_artigo2_trans = A2 @ v_artigo2\n",
    "\n",
    "print(\"\\nNovos vetores após T(v) = A * v:\")\n",
    "print(f\"v_pergunta_trans : {v_pergunta_trans}\")\n",
    "print(f\"v_artigo1_trans  : {v_artigo1_trans}\")\n",
    "print(f\"v_artigo2_trans  : {v_artigo2_trans}\")\n",
    "\n",
    "# Novas métricas calculadas\n",
    "dot1_trans, dist1_trans, cos1_trans = calcular_metricas(v_pergunta_trans, v_artigo1_trans)\n",
    "dot2_trans, dist2_trans, cos2_trans = calcular_metricas(v_pergunta_trans, v_artigo2_trans)"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "### 5. Tabela Comparativa de Resultados (Antes vs. Depois da Transformação)\n",
    "\n",
    "Abaixo consolidamos a comparação detalhada dos vetores, produtos escalares, distâncias euclidianas e similaridades de cosseno, bem como o $\\Delta$ resultante."
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "df_comp = pd.DataFrame({\n",
    "    \"Documento\": [\"Artigo 1 (Guia Histórico)\", \"Artigo 2 (Canais Atendimento)\"],\n",
    "    \"Vetor Original\": [str(v_artigo1.tolist()), str(v_artigo2.tolist())],\n",
    "    \"Vetor Transformado\": [str(v_artigo1_trans.tolist()), str(v_artigo2_trans.tolist())],\n",
    "    \"Cosseno Original\": [round(cos1_orig, 4), round(cos2_orig, 4)],\n",
    "    \"Cosseno Transformado\": [round(cos1_trans, 4), round(cos2_trans, 4)],\n",
    "    \"Delta Cosseno\": [round(cos1_trans - cos1_orig, 4), round(cos2_trans - cos2_orig, 4)],\n",
    "    \"Distância Original\": [round(dist1_orig, 4), round(dist2_orig, 4)],\n",
    "    \"Distância Transformada\": [round(dist1_trans, 4), round(dist2_trans, 4)],\n",
    "})\n",
    "display(df_comp)\n",
    "\n",
    "print(\"Ranking Original:\")\n",
    "print(\"1º Lugar:\", \"Artigo 1\" if cos1_orig > cos2_orig else \"Artigo 2\")\n",
    "print(\"\\nRanking Pós-Transformação Linear:\")\n",
    "print(\"1º Lugar:\", \"Artigo 1\" if cos1_trans > cos2_trans else \"Artigo 2\")"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "### 6. Visualização Gráfica do Efeito da Transformação Linear\n",
    "\n",
    "O gráfico a seguir ilustra a evolução da Similaridade de Cosseno entre a dúvida do estudante e cada artigo antes e depois da transformação linear."
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "fig, ax = plt.subplots(figsize=(8, 5))\n",
    "labels = ['Artigo 1\\n(Guia Histórico)', 'Artigo 2\\n(Canais Atendimento)']\n",
    "x = np.arange(len(labels))\n",
    "width = 0.35\n",
    "\n",
    "bars1 = ax.bar(x - width/2, [cos1_orig, cos2_orig], width, label='Original (Entrega 1)', color='#004D34')\n",
    "bars2 = ax.bar(x + width/2, [cos1_trans, cos2_trans], width, label='Transformado T(v) = A·v', color='#00E676')\n",
    "\n",
    "ax.set_ylabel('Similaridade de Cosseno')\n",
    "ax.set_title('Impacto da Transformação Linear no Espaço Semântico (Entrega 2)')\n",
    "ax.set_xticks(x)\n",
    "ax.set_xticklabels(labels)\n",
    "ax.set_ylim(0, 1.15)\n",
    "ax.legend()\n",
    "ax.grid(axis='y', linestyle='--', alpha=0.5)\n",
    "\n",
    "for bar in bars1:\n",
    "    yval = bar.get_height()\n",
    "    ax.text(bar.get_x() + bar.get_width()/2, yval + 0.02, f'{yval:.4f}', ha='center', va='bottom', fontsize=9, fontweight='bold')\n",
    "for bar in bars2:\n",
    "    yval = bar.get_height()\n",
    "    ax.text(bar.get_x() + bar.get_width()/2, yval + 0.02, f'{yval:.4f}', ha='center', va='bottom', fontsize=9, fontweight='bold')\n",
    "\n",
    "plt.tight_layout()\n",
    "plt.show()"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "### 7. Interpretação dos Resultados Matemáticos e Tomada de Decisão do Agente\n",
    "\n",
    "1. **Estabilidade e Sensibilidade da Geometria:**\n",
    "   - Na representação original, o Artigo 1 vencia com grande folga ($cos = 0.9927$ contra $cos = 0.3887$).\n",
    "   - Quando aplicamos a matriz de transformação $A = \\text{diag}(0.1, 0.1, 10.0)$, o terceiro eixo (Canais) passa a dominar a norma e o produto interno dos vetores.\n",
    "   - Com essa transformação drástica, a similaridade do Artigo 2 subiu de $0.3887$ para **$0.9983$**, superando o Artigo 1 e **invertendo a liderança do ranking**.\n",
    "2. **Tomada de Decisão do Agente:**\n",
    "   - Essa propriedade matemática permite que o agente SecretarIA adapte dinamicamente sua prioridade de recuperação de informação diante de regras institucionais ou contextos de contingência (ex.: encaminhar para o atendimento humano ou presencial quando os canais digitais estiverem comprometidos).\n",
    "\n",
    "--- \n",
    "\n",
    "### 8. Integração Prática na Aplicação SecretarIA\n",
    "\n",
    "Conforme solicitado pelo professor e desenvolvido na aplicação:\n",
    "1. **Interface do Chat:** Abaixo de cada resposta do assistente no chat do estudante, há uma seção expansível **\"Entenda como a IA encontrou esta resposta\"**.\n",
    "2. **Painel Interativo:** Clicando em **\"Ver análise avançada — Álgebra Linear\"**, o estudante abre um modal com controles deslizantes interativos ($w_1, w_2, w_3$), cálculos em tempo real via endpoint autenticado `POST /api/v1/algebra/transform`, tabela comparativa e interpretação matemática dinâmica.\n",
    "3. **Transparência e Explicabilidade:** A aplicação deixa explícito o disclaimer de que a representação em $\\mathbb{R}^3$ é um **modelo didático** da disciplina de Álgebra Linear, enquanto a busca operacional em produção utiliza embeddings densos de 384 dimensões no ChromaDB."
   ]
  }
 ],
 "metadata": {
  "language_info": {
   "name": "python"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 2
}

with open("C:/SecretaRIA/entrega_2_algebra_linear/Entrega2_AlgebraLinear_SecretarIA.ipynb", "w", encoding="utf-8") as f:
    json.dump(notebook, f, indent=2, ensure_ascii=False)

print("Notebook salvo com sucesso em C:/SecretaRIA/entrega_2_algebra_linear/Entrega2_AlgebraLinear_SecretarIA.ipynb")

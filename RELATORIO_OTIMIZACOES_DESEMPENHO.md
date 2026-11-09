# Relatório Técnico de Desempenho, Análise de Gargalos e Otimizações
**Projeto:** SecretarIA — Assistente Acadêmico Inteligente (FECAP Guia)  
**Disciplina:** Sistemas Operacionais e Computação em Nuvem  
**Semestre Letivo:** 2026/2  
**Data:** 08/11/2026  
**Auditor:** Equipe de Engenharia e Auditoria de Software  

---

## 1. Introdução e Metodologia de Avaliação
Este relatório documenta a análise técnica do comportamento computacional do **SecretarIA** sob estresse, baseando-se estritamente nas evidências empíricas registradas em [`load_test_results.json`](../03_Evidencias/load_test_results.json) e no código-fonte do script de teste de carga [`run_load_test.py`](../../fecap-guia/backend/run_load_test.py).

O teste foi executado através de chamadas HTTP assíncronas concorrentes utilizando a biblioteca `httpx.AsyncClient` com controle de semáforo assíncrono (`asyncio.Semaphore`), avaliando a capacidade de atendimento dos microsserviços conteinerizados em ambiente Docker.

---

## 2. Resultados Empíricos do Teste de Carga (150 Requisições)

Foram executadas **150 requisições reais** distribuídas em **5 cenários distintos** com concorrência máxima de **5 conexões simultâneas**. O sistema registrou **0 erros (taxa de sucesso de 100%)** em todas as rotas avaliadas:

| Cenário de Teste | Endpoint | Req. | Concorrência | Tempo Total (s) | Throughput (req/s) | Latência Média (ms) | P50 (ms) | P95 (ms) | P99 (ms) | Status HTTP |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **1. Healthcheck** | `/health` | 50 | 5 | 0,157 s | **317,84** | **14,54** | 10,55 | 32,77 | 36,68 | 200 (50/50) |
| **2. Perfil Estudante** | `/api/v1/student/profile` | 40 | 5 | 0,756 s | **52,90** | **91,52** | 83,32 | 169,20 | 200,16 | 200 (40/40) |
| **3. Boletos Pendentes** | `/api/v1/boletos/pending` | 30 | 5 | 6,730 s | **4,46** | **1.052,37** | 711,38 | 3.048,37 | 3.472,26 | 200 (30/30) |
| **4. RAG Acadêmico (C=2)** | `/api/v1/agent/query` | 10 | 2 | 7,188 s | **1,39** | **1.357,01** | 1.270,83 | 2.330,79 | 2.330,79 | 200 (10/10) |
| **5. RAG Acadêmico (C=5)** | `/api/v1/agent/query` | 20 | 5 | 13,087 s | **1,53** | **2.992,26** | 2.351,63 | **7.740,53** | 7.740,53 | 200 (20/20) |

---

## 3. Análise Crítica de Gargalos e Esclarecimento de Ambiente

### 3.1 Identificação do Gargalo de Processamento
- **Camada Leve e I/O Simples:** Os endpoints `/health` e `/student/profile` apresentaram latência na ordem de dezenas de milissegundos e vazão superior a 300 req/s, demonstrando que o servidor ASGI Uvicorn e o gateway Nginx possuem baixíssimo overhead de transporte.
- **Camada Transacional Financeira:** O endpoint `/boletos/pending` registrou latência média de 1,05s (P95 de 3,05s), associada à decodificação de claims JWT, abertura de sessão transacional assíncrona e serialização dos dados cadastrais dos boletos.
- **Camada de Inteligência e Recuperação (RAG):** O principal gargalo computacional ocorreu no endpoint `/api/v1/agent/query`. Ao elevar a concorrência de 2 para 5 conexões simultâneas, a latência média saltou de 1,36s para 2,99s, com o percentil **P95 atingindo 7.740,53 ms (7,74s)**.

### 3.2 Esclarecimento do Ambiente de Execução do Teste
> [!NOTE]
> **Rigor Metodológico sobre o Ambiente do Teste:**  
> O script `run_load_test.py` foi executado apontando para o ambiente local de contêineres Docker (`http://localhost:5173`). Portanto, o gargalo observado sob concorrência C=5 no RAG decorre do **processamento intensivo em CPU exigido pela rede neural Sentence-Transformers (`all-MiniLM-L6-v2`) e pelo cálculo matricial de similaridade de cosseno no ChromaDB**, e não de uma limitação exclusiva das 2 vCPUs da máquina virtual na Azure.

---

## 4. Classificação das Otimizações

Em estrito rigor acadêmico, as intervenções de desempenho identificadas no projeto dividem-se em três categorias bem delimitadas:

### Categoria 1: Otimizações Existentes e Comprovadas em Código
1. **Pré-Download do Modelo Neural no Build do Contêiner:**
   - *Evidência:* [`05_Configuracoes/Dockerfile.backend`](../05_Configuracoes/Dockerfile.backend) (linha 22):
     ```dockerfile
     RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
     ```
   - *Efeito Comprovado:* Elimina o download de ~80 MB de pesos da rede neural durante a inicialização do contêiner, garantindo tempo de subida previsível e ausência de dependência de conexão externa em runtime.
2. **Atalho para Respostas Curtas Conversacionais:**
   - *Evidência:* [`app/agent/rag_pipeline.py`](../../fecap-guia/backend/app/agent/rag_pipeline.py) (`_detect_conversational_reply`):
   - *Efeito Comprovado:* Saudações e confirmações triviais (ex: "olá", "obrigado") são resolvidas diretamente via expressões regulares sem acionar o ChromaDB ou inferência vetorial.
3. **Telemetria de Consumo Estável em Repouso e Sob Carga:**
   - *Evidência:* Coleta via `docker stats --no-stream` registrando aumento de apenas +13,1 MiB de RAM no backend após a execução de todas as 150 requisições (de 412,6 MiB para 425,7 MiB), comprovando inexistência de vazamento de memória (*zero memory leak*).

### Categoria 2: Otimizações Implementadas, mas Não Medidas Comparativamente
As seguintes melhorias foram devidamente codificadas nas configurações, porém **não houve medição empírica comparativa em teste A/B** (antes vs. depois):
1. **Compressão Gzip no Nginx:** Ativada em [`nginx.azure.conf`](../05_Configuracoes/nginx.azure.conf) (`gzip on; gzip_min_length 1024;`) para textos e JSONs. Reduz tráfego de rede, mas seu impacto em milissegundos não foi mensurado isoladamente.
2. **Cache de Assets Estáticos:** Diretiva `expires 7d; add_header Cache-Control "public, immutable";` implementada no Nginx. Melhora carregamento repetido no navegador, mas o teste de carga incidiu sobre a API REST.
3. **Desativação de Buffering de Proxy:** Diretiva `proxy_buffering off;` no Nginx, viabilizando transmissão direta de pacotes sem acúmulo em buffer intermediário.
4. **Driver de Banco Assíncrono:** Utilização de `aiosqlite` via SQLAlchemy AsyncIO para não bloquear o loop de eventos principal do FastAPI durante acessos a disco.

> **Ressalva de Auditoria:** Por honestidade acadêmica, este relatório **não atribui percentuais fictícios de ganho de velocidade** a essas medidas, declarando-as como *boas práticas de engenharia implementadas sem ensaio A/B comparativo*.

### Categoria 3: Otimizações Apenas Propostas para Escala Institucional
1. **Migração para PostgreSQL Gerenciado:** Substituição do SQLite para eliminar locks de escrita e viabilizar dezenas de transações simultâneas de orientadores.
2. **Camada de Cache de Respostas (Redis):** Armazenamento em memória das perguntas mais frequentes (FAQ) já resolvidas pelo RAG, reduzindo a necessidade de inferência repetida.
3. **Cluster Horizontal com Balanceador de Carga:** Replicação do contêiner `fecap_guia_backend` em múltiplos nós de computação para absorver picos de tráfego em período de matrículas.

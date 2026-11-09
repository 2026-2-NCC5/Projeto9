# Relatório de Auditoria Definitiva — Sistemas Operacionais e Computação em Nuvem
**Projeto:** SecretarIA — Assistente Acadêmico Inteligente (FECAP Guia)  
**Instituição:** Fundação Escola de Comércio Álvares Penteado (FECAP)  
**Semestre Letivo:** 2026/2  
**Data da Auditoria:** 08/11/2026  
**Auditor Responsável:** Equipe de Engenharia e Auditoria de Software  

---

## 1. Identificação e Escopo da Auditoria

Este relatório consolida a auditoria final, técnica e documental de todos os entregáveis do projeto **SecretarIA** para a disciplina de **Sistemas Operacionais e Computação em Nuvem**.

O escopo da auditoria abrangeu a verificação estática, sintática, métrica e de integridade de todos os artefatos contidos no diretório oficial de entrega:
- `01_Entrega_1/relatorio_configuracao_linux.md` (Configuração Linux, permissões e processos)
- `02_Entrega_2/relatorio_arquitetura_nuvem_docker.md` (Arquitetura Docker, nuvem Azure e resiliência)
- `03_Evidencias/Ubuntu_evidencias(1).docx` (Documento com 27 capturas autenticadas)
- `03_Evidencias/load_test_results.json` (Resultados brutos e telemetria do teste de estresse)
- `03_Evidencias/backup_restore_evidence.json` (Evidências de validação SHA-256 e PRAGMA do banco)
- `04_Diagramas/arquitetura_infraestrutura_nuvem.mmd` (Diagrama em formato Mermaid)
- `05_Configuracoes/` (Dockerfiles, Docker Compose, Nginx e scripts de backup/restauração)
- `06_Relatorios/` (Relatórios acadêmicos, checklist oficial e relatórios de auditoria)

---

## 2. Metodologia de Verificação

A auditoria foi conduzida estritamente com base em regras de integridade e não-destruição:
1. **Inspeção Estática e Cruzamento de Dados:** Verificação de coerência entre os textos dos relatórios acadêmicos e os dados empíricos registrados nos arquivos `.json` e no `.docx`.
2. **Auditoria de Segurança de Credenciais:** Busca automatizada por padrões de chaves privadas, senhas em texto puro (`POSTGRES_PASSWORD`), chaves de API e segredos JWT.
3. **Validação de Links e Rastreabilidade:** Eliminação de caminhos absolutos locais (prefixos de protocolo absoluto), substituindo-os por referências relativas funcionais dentro do pacote.
4. **Validação Estrutural em Ambiente Isolado:** Restauração e inspeção do banco SQLite e da base vetorial ChromaDB em diretório temporário isolado (`scratch`), utilizando ambiente Python com biblioteca `chromadb 1.5.9`.

---

## 3. Resultados Detalhados da Auditoria por Requisito

### 3.1 Implantação em Nuvem e Arquitetura Docker
- **Comprovação:** A máquina virtual Azure Standard_B2s (2 vCPUs, 8 GiB RAM) executando Ubuntu Server 24.04.5 LTS foi documentada nas Capturas 16 a 20 de [`Ubuntu_evidencias(1).docx`](../03_Evidencias/Ubuntu_evidencias%281%29.docx).
- **Rede e Portas:** O IP público `191.233.19.182` e o FQDN `vm-fecap-secretaria.brazilsouth.cloudapp.azure.com` foram provisionados com regras restritas no NSG (Porta 22 via chave RSA, Portas 80 e 8000). O acesso seguro foi demonstrado através de túnel SSH redirecionando a porta remota 80 para `http://localhost:8080/`.
- **Topologia de Contêineres:** Implementada via Docker Compose com rede isolada `fecap_azure_net`, desacoplando o gateway Nginx do backend FastAPI.
- **Classificação:** **CONCLUÍDO E COMPROVADO**.

### 3.2 Telemetria e Monitoramento de Recursos
- **Comprovação:** Comando `docker stats --no-stream` registrado no arquivo [`load_test_results.json`](../03_Evidencias/load_test_results.json) e nas Capturas 21 a 23 de [`Ubuntu_evidencias(1).docx`](../03_Evidencias/Ubuntu_evidencias%281%29.docx).
- **Métricas:**
  - `fecap_guia_backend`: 0,26% a 0,38% CPU, 412,6 a 436,2 MiB RAM (5,24% a 5,54% da memória da VM), 29 processos ativos.
  - `fecap_guia_frontend`: 0,00% CPU, 5,84 a 9,13 MiB RAM (0,07% a 0,12% da memória), 5 processos ativos.
- **Classificação:** **CONCLUÍDO E COMPROVADO**.

### 3.3 Teste de Carga e Análise Crítica de Gargalos
- **Comprovação:** Script assíncrono `run_load_test.py` executando 150 requisições reais distribuídas em 5 cenários com concorrência até C=5, registrado em [`load_test_results.json`](../03_Evidencias/load_test_results.json).
- **Consistência Numérica:** Todos os relatórios foram alinhados exatamente com o JSON:
  - `/health` (50 req, C=5): Throughput 317,84 req/s | Média 14,54 ms | P95 32,77 ms.
  - `/api/v1/student/profile` (40 req, C=5): Throughput 52,90 req/s | Média 91,52 ms | P95 169,20 ms.
  - `/api/v1/boletos/pending` (30 req, C=5): Throughput 4,46 req/s | Média 1.052,37 ms | P95 3.048,37 ms.
  - `/api/v1/agent/query` (10 req, C=2): Throughput 1,39 req/s | Média 1.357,01 ms | P95 2.330,79 ms.
  - `/api/v1/agent/query` (20 req, C=5): Throughput 1,53 req/s | Média 2.992,26 ms | P95 **7.740,53 ms**.
- **Gargalo:** Identificado e documentado o custo de CPU na inferência de embeddings (`all-MiniLM-L6-v2`) e busca vetorial durante concorrência simultânea.
- **Classificação:** **CONCLUÍDO E COMPROVADO**.

### 3.4 Backup e Restauração (SQLite e ChromaDB)
- **Comprovação:** Scripts [`backup.sh`](../05_Configuracoes/backup.sh) e [`restore.sh`](../05_Configuracoes/restore.sh), validados pelo relatório [`backup_restore_evidence.json`](../03_Evidencias/backup_restore_evidence.json).
- **SQLite:** Snapshot atômico com API online `sqlite3.backup()`. Restauração isolada com hash SHA-256 idêntico (`85e89ffa45...`), `PRAGMA integrity_check = "ok"` e 100% dos dados preservados.
- **ChromaDB:** Extração em diretório temporário isolado testada via script Python com a biblioteca `chromadb 1.5.9`. Integridade estrutural do `chroma.sqlite3` aprovada (`PRAGMA integrity_check = "ok"`), hash SHA-256 idêntico (`a0187c3774...`) e coleção `fecap_knowledge` verificada com **55 embeddings** íntegros.
- **Classificação:** **CONCLUÍDO E COMPROVADO**.

### 3.5 Segurança, Credenciais e Configurações
- **Comprovação:** Varredura de segurança em todos os arquivos de configuração (`Dockerfile`, `docker-compose`, `Nginx`, `Bash`).
- **Sanitização:** Substituição de senhas fixas de exemplo por variáveis `${POSTGRES_PASSWORD}`.
- **Protocolo de Rede:** O ambiente opera exclusivamente sob **HTTP na porta 80** (e 8000). A documentação não declara falsamente a existência de HTTPS ativo, e a publicação da porta 443 foi omitida dos arquivos entregáveis.
- **Classificação:** **CONCLUÍDO E COMPROVADO** (com HTTPS classificado como *Implementado em bloco Nginx preparatório, mas não validado por ausência de certificado TLS*).

---

## 4. Matriz Síntese de Auditoria

| Item Auditado | Status | Evidência Central |
| :--- | :---: | :--- |
| Instalação Linux e Comandos de SO | **APROVADO** | Capturas 01 a 09 em `Ubuntu_evidencias(1).docx` |
| Orquestração Docker e Nginx Proxy | **APROVADO** | Dockerfiles, Compose sanitizado e `nginx.azure.conf` |
| Implantação na VM Microsoft Azure | **APROVADO** | IP `191.233.19.182`, FQDN e Capturas 16 a 20 |
| Monitoramento de CPU e Memória | **APROVADO** | `docker stats --no-stream` em `load_test_results.json` |
| Teste de Carga (150 requisições) | **APROVADO** | 5 cenários reais com P50/P95 e análise de gargalos |
| Backup e Restauração SQLite | **APROVADO** | SHA-256 idêntico e `PRAGMA integrity_check = ok` |
| Backup e Restauração ChromaDB | **APROVADO** | Validação isolada com `chromadb 1.5.9` (55 embeddings) |
| Política de Variáveis e Segredos | **APROVADO** | Injeção via variáveis de ambiente; sem credenciais no Git |
| Transparência de Limitações (HTTP) | **APROVADO** | Ausência de TLS documentada; sem declaração indevida de HTTPS |
| Links Relativos e Integridade de Arquivos | **APROVADO** | 100% dos links markdown com alvos locais existentes |

---

## 5. Parecer Conclusivo da Auditoria

O pacote auditado apresenta **rigor técnico, consistência empírica integral e total aderência às diretrizes acadêmicas da FECAP**. Nenhuma inconsistência métrica ou link quebrado foi detectado.

O pacote consolidado está aprovado para compilação no arquivo final:
📦 `PACOTE_ENTREGA2_SISTEMAS_OPERACIONAIS_NUVEM_FECAP_DEFINITIVO.zip`

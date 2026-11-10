# CHECKLIST FINAL DE ATENDIMENTO — SISTEMAS OPERACIONAIS E COMPUTAÇÃO EM NUVEM
## Projeto Interdisciplinar: SecretarIA (FECAP Guia)
**Instituição:** Fundação Escola de Comércio Álvares Penteado (FECAP)  
**Ano Letivo / Semestre:** 2026/2  
**Diretório Central dos Entregáveis:** `entrega_fecap_sistemas_operacionais_nuvem/`  
**Documento Fonte de Evidências:** `03_Evidencias/Ubuntu_evidencias(1).docx` (Capturas 01 a 27)

---

## 1. Matriz de Rastreabilidade e Validação Técnica

| Requisito FECAP | Arquivo de Entrega | Evidência Analisada | Classificação Técnica | Observações e Limitações Declaradas |
| :--- | :--- | :--- | :---: | :--- |
| **1. Instalação e Configuração do Linux** | [`relatorio_configuracao_linux.md`](../01_Entrega_1/relatorio_configuracao_linux.md) | Capturas 01, 02, 03 em `Ubuntu_evidencias(1).docx` | **CONCLUÍDO E COMPROVADO** | Evidenciado no host local (WSL 2 Kernel 6.18) e na VM Azure (Ubuntu 24.04.5 LTS Kernel 7.0.0-azure). |
| **2. Usuários, Grupos e Permissões** | [`relatorio_configuracao_linux.md`](../01_Entrega_1/relatorio_configuracao_linux.md) | Capturas 04, 05, 12 em `Ubuntu_evidencias(1).docx` | **CONCLUÍDO E COMPROVADO** | Usuário `azureuser` em grupos `sudo` e `docker`. Chaves SSH com permissão restrita `chmod 600`. |
| **3. Comandos Essenciais e Manipulação** | [`relatorio_configuracao_linux.md`](../01_Entrega_1/relatorio_configuracao_linux.md) | Capturas 03, 04, 08 em `Ubuntu_evidencias(1).docx` | **CONCLUÍDO E COMPROVADO** | Operações com `uname`, `ls -la`, `mkdir`, `tar`, `grep`, `systemctl`, `journalctl`. |
| **4. Processos, Serviços e Logs** | [`relatorio_configuracao_linux.md`](../01_Entrega_1/relatorio_configuracao_linux.md) | Capturas 06, 07, 09 em `Ubuntu_evidencias(1).docx` | **CONCLUÍDO E COMPROVADO** | Serviço Docker ativo via `systemctl` e inspeção de logs com `journalctl -n 15`. |
| **5. Conteinerização Docker e Proxy Nginx** | [`Dockerfile.backend`](../05_Configuracoes/Dockerfile.backend), [`Dockerfile.frontend`](../05_Configuracoes/Dockerfile.frontend), [`nginx.azure.conf`](../05_Configuracoes/nginx.azure.conf), [`nginx.conf`](../05_Configuracoes/nginx.conf) | Capturas 10, 11 em `Ubuntu_evidencias(1).docx` | **CONCLUÍDO E COMPROVADO** | Cópias fiéis dos Dockerfiles e arquivos de configuração Nginx (`nginx.azure.conf` e `nginx.conf`) incluídas no pacote. |
| **6. Orquestração Multicontêiner Sanitizada** | [`docker-compose.yml`](../05_Configuracoes/docker-compose.yml), [`docker-compose.azure.yml`](../05_Configuracoes/docker-compose.azure.yml) | Capturas 13, 14, 15 em `Ubuntu_evidencias(1).docx` | **CONCLUÍDO E COMPROVADO** | Versões sanitizadas sem credenciais fixas (`${POSTGRES_PASSWORD}`) e sem publicação enganosa da porta 443. |
| **7. Implantação em Nuvem (Azure)** | [`relatorio_arquitetura_nuvem_docker.md`](../02_Entrega_2/relatorio_arquitetura_nuvem_docker.md) | Capturas 16, 17, 18 em `Ubuntu_evidencias(1).docx` | **CONCLUÍDO E COMPROVADO** | VM Standard_B2s em `brazilsouth`, IP `191.233.19.182`, FQDN `vm-fecap-secretaria.brazilsouth.cloudapp.azure.com`. Atualmente desalocada para economia de créditos. |
| **8. Portas, Rede e Segurança (NSG)** | [`relatorio_arquitetura_nuvem_docker.md`](../02_Entrega_2/relatorio_arquitetura_nuvem_docker.md) | Capturas 19, 20 em `Ubuntu_evidencias(1).docx` | **CONCLUÍDO E COMPROVADO** | NSG restrito a portas 22 (SSH chave RSA), 80 (HTTP) e 8000. Opera em HTTP puro (sem HTTPS/443 ativo). |
| **9. Monitoramento de Recursos (`docker stats`)** | [`RELATORIO_2_ENTREGA_FINAL.md`](./RELATORIO_2_ENTREGA_FINAL.md) | Capturas 21, 22, 23 em `Ubuntu_evidencias(1).docx` | **CONCLUÍDO E COMPROVADO** | Telemetria real: Backend com 412,6–436,2 MiB (5,24%–5,54% RAM), Frontend com 5,84–9,13 MiB (0,07%–0,12% RAM). |
| **10. Teste de Carga e Avaliação de Latência** | [`load_test_results.json`](../03_Evidencias/load_test_results.json) | Captura 24 e JSON de resultados | **CONCLUÍDO E COMPROVADO** | **150 requisições reais** em 5 cenários (concorrência máx. 5, 100% sucesso). Latência P95 de 32,77 ms (`/health`) até 7.740,53 ms (`RAG C=5`). |
| **11. Rotina de Backup Automatizado** | [`backup.sh`](../05_Configuracoes/backup.sh) | Capturas 25, 26 em `Ubuntu_evidencias(1).docx` | **CONCLUÍDO E COMPROVADO** | Snapshot atômico de SQLite (`sqlite3.backup()`), ChromaDB e base textual com manifesto SHA-256 e caminhos relativos autodetectáveis. |
| **12. Procedimento de Restauração — SQLite** | [`restore.sh`](../05_Configuracoes/restore.sh), [`backup_restore_evidence.json`](../03_Evidencias/backup_restore_evidence.json) | Captura 27 e JSON de validação | **CONCLUÍDO E COMPROVADO** | Restauração validada em diretório isolado: SHA-256 idêntico (`85e89ffa45...`), `PRAGMA integrity_check = ok` e 0 violações de chave. |
| **13. Procedimento de Restauração — ChromaDB** | [`restore.sh`](../05_Configuracoes/restore.sh), [`backup_restore_evidence.json`](../03_Evidencias/backup_restore_evidence.json) | Validação em diretório temporário isolado (`.venv` com `chromadb 1.5.9`) | **CONCLUÍDO E COMPROVADO** | `chroma.sqlite3` com SHA-256 idêntico (`a0187c3774...`), `PRAGMA integrity_check = ok` e coleção `fecap_knowledge` íntegra com **55 embeddings**. |
| **14. Relatório Acadêmico Entrega 1 (Parcial)** | [`RELATORIO_1_ENTREGA_PARCIAL.md`](./RELATORIO_1_ENTREGA_PARCIAL.md) | Capturas 01 a 15 em `Ubuntu_evidencias(1).docx` | **CONCLUÍDO E COMPROVADO** | Documentação formal de Linux, usuários, permissões, serviços e processos. |
| **15. Relatório Acadêmico Entrega 2 (Final)** | [`RELATORIO_2_ENTREGA_FINAL.md`](./RELATORIO_2_ENTREGA_FINAL.md) | Capturas 16 a 27 e artefatos JSON | **CONCLUÍDO E COMPROVADO** | Documentação consistente em todos os números (150 req, 5 cenários, P95 7.740,53 ms, SQLite + ChromaDB validados). |
| **16. Diagrama de Infraestrutura** | [`arquitetura_infraestrutura_nuvem.mmd`](../04_Diagramas/arquitetura_infraestrutura_nuvem.mmd) | Diagrama Mermaid | **CONCLUÍDO E COMPROVADO** | Topologia fiel indicando HTTP Porta 80, rede privada `fecap_azure_net` e volumes persistentes. |

---

## 2. Inventário Completo dos Arquivos no Pacote Final

1. `01_Entrega_1/relatorio_configuracao_linux.md`
2. `02_Entrega_2/relatorio_arquitetura_nuvem_docker.md`
3. `03_Evidencias/Ubuntu_evidencias(1).docx`
4. `03_Evidencias/load_test_results.json`
5. `03_Evidencias/backup_restore_evidence.json`
6. `04_Diagramas/arquitetura_infraestrutura_nuvem.mmd`
7. `05_Configuracoes/Dockerfile.backend`
8. `05_Configuracoes/Dockerfile.frontend`
9. `05_Configuracoes/docker-compose.yml`
10. `05_Configuracoes/docker-compose.azure.yml`
11. `05_Configuracoes/nginx.azure.conf`
12. `05_Configuracoes/nginx.conf`
13. `05_Configuracoes/backup.sh`
14. `05_Configuracoes/restore.sh`
15. `06_Relatorios/RELATORIO_1_ENTREGA_PARCIAL.md`
16. `06_Relatorios/RELATORIO_2_ENTREGA_FINAL.md`
17. `06_Relatorios/CHECKLIST_FINAL_FECAP.md`

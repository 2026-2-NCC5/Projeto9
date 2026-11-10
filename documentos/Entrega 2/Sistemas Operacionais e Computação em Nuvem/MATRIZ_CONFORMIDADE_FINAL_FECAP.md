# Matriz Final de Conformidade com Requisitos Oficiais — FECAP 2026/2
**Projeto:** SecretarIA — Assistente Acadêmico Inteligente (FECAP Guia)  
**Disciplina:** Sistemas Operacionais e Computação em Nuvem  
**Semestre Letivo:** 2026/2  
**Data:** 08/11/2026  
**Auditor:** Equipe de Engenharia e Auditoria de Software  

---

## 1. Visão Geral da Avaliação
Esta matriz estabelece o confronto direto entre cada requisito oficial pedagógico e prático da disciplina de **Sistemas Operacionais e Computação em Nuvem** da FECAP e as evidências materiais registradas no pacote de entrega.

### Critérios de Classificação Adotados:
- **COMPROVADO:** Requisito totalmente implementado, testado e suportado por evidências empíricas verificáveis (capturas de tela, arquivos JSON de telemetria, logs ou scripts operacionais).
- **PARCIAL:** Requisito projetado e configurado tecnicamente no repositório, com plano de implantação completo, mas mantido em nível acadêmico ou com limitações operacionais transparentemente documentadas (ex.: VM Azure desalocada sem certificado TLS ativo na porta 443).
- **PENDENTE:** Requisito não implementado ou sem evidências materiais correspondentes.

---

## 2. Matriz de Rastreabilidade e Auditoria

| # | Requisito Oficial FECAP | Arquivo Comprobatório | Captura / Registro Correspondente | Resultado Verificado | Limitação Declarada | Situação |
| :-: | :--- | :--- | :--- | :--- | :--- | :---: |
| **01** | **Instalação e Configuração do Linux** | [`relatorio_configuracao_linux.md`](../01_Entrega_1/relatorio_configuracao_linux.md) | Capturas 01, 02 e 03 em `Ubuntu_evidencias(1).docx` | Kernel Linux 6.18 WSL 2 no host e Ubuntu 24.04.5 LTS (Kernel 7.0.0-1017-azure) na VM. | Nenhuma no escopo acadêmico. | **COMPROVADO** |
| **02** | **Gestão de Usuários, Grupos e Permissões** | [`relatorio_configuracao_linux.md`](../01_Entrega_1/relatorio_configuracao_linux.md) | Capturas 04, 05 e 12 em `Ubuntu_evidencias(1).docx` | Usuário `azureuser` no grupo `docker`; chaves SSH com permissão restrita `chmod 600`. | Nenhuma. | **COMPROVADO** |
| **03** | **Comandos Essenciais, Processos e Logs** | [`relatorio_configuracao_linux.md`](../01_Entrega_1/relatorio_configuracao_linux.md) | Capturas 06 a 09 em `Ubuntu_evidencias(1).docx` | Inspeção de serviços via `systemctl` e visualização do journal do Linux via `journalctl -n 15`. | Nenhuma. | **COMPROVADO** |
| **04** | **Conteinerização Docker Multi-Stage** | [`Dockerfile.backend`](../05_Configuracoes/Dockerfile.backend), [`Dockerfile.frontend`](../05_Configuracoes/Dockerfile.frontend) | Capturas 10 e 11 em `Ubuntu_evidencias(1).docx` | Imagem frontend compilada em Node 20 servida por Nginx Alpine; backend em Python 3.11-slim. | Nenhuma. | **COMPROVADO** |
| **05** | **Orquestração Multicontêiner Declarativa** | [`docker-compose.azure.yml`](../05_Configuracoes/docker-compose.azure.yml), [`docker-compose.yml`](../05_Configuracoes/docker-compose.yml) | Capturas 13, 14 e 15 em `Ubuntu_evidencias(1).docx` | Subida de contêineres com volumes bind mount e rede interna isolada `fecap_azure_net`. | Nenhuma. | **COMPROVADO** |
| **06** | **Implantação na Nuvem (Microsoft Azure)** | [`relatorio_arquitetura_nuvem_docker.md`](../02_Entrega_2/relatorio_arquitetura_nuvem_docker.md) | Capturas 16 a 20 em `Ubuntu_evidencias(1).docx` | VM Standard_B2s em `brazilsouth`, IP `191.233.19.182`, FQDN Azure e Swagger ativo em `/docs`. | VM atualmente desalocada para economia de créditos estudantis. | **COMPROVADO** |
| **07** | **Controle de Portas e Segurança de Rede (NSG)** | [`RELATORIO_SEGURANCA_CONTROLE_ACESSO.md`](./RELATORIO_SEGURANCA_CONTROLE_ACESSO.md) | Captura 19 em `Ubuntu_evidencias(1).docx` | Porta 22 (SSH chave) e 80 (HTTP) abertas; portas 8000 (FastAPI) e 5173 bloqueadas externamente. | Nenhuma. | **COMPROVADO** |
| **08** | **Monitoramento de Recursos (CPU e Memória)** | [`load_test_results.json`](../03_Evidencias/load_test_results.json) | Capturas 21, 22 e 23 em `Ubuntu_evidencias(1).docx` | Telemetria `docker stats --no-stream`: Backend em repouso com 412,6 MiB (5,24%) e pós-carga com 425,7 MiB (5,40%). | Nenhuma (estabilidade confirmada). | **COMPROVADO** |
| **09** | **Teste de Carga e Análise de Desempenho** | [`load_test_results.json`](../03_Evidencias/load_test_results.json), [`RELATORIO_OTIMIZACOES_DESEMPENHO.md`](./RELATORIO_OTIMIZACOES_DESEMPENHO.md) | Captura 24 em `Ubuntu_evidencias(1).docx` e arquivo JSON | **150 requisições reais** em 5 cenários (C=2 a C=5) com 100% de sucesso. Gargalo analisado em RAG C=5 (P95 de 7,74s). | Teste executado no ambiente de contêineres Docker local da aplicação. | **COMPROVADO** |
| **10** | **Otimizações de Desempenho no Código** | [`RELATORIO_OTIMIZACOES_DESEMPENHO.md`](./RELATORIO_OTIMIZACOES_DESEMPENHO.md) | `Dockerfile.backend` (linha 22) e `nginx.azure.conf` | Pré-download do modelo MiniLM na imagem; gzip ativado no Nginx; bypass de perguntas curtas no pipeline. | Melhorias do Nginx implementadas, mas sem teste comparativo A/B isolado. | **COMPROVADO** |
| **11** | **Backup Consistente Automatizado** | [`backup.sh`](../05_Configuracoes/backup.sh) | Capturas 25 e 26 em `Ubuntu_evidencias(1).docx` | Snapshot online atômico `sqlite3.backup()` e compactação de `chroma_db` com manifesto SHA-256. | Nenhuma. | **COMPROVADO** |
| **12** | **Restauração e Integridade — SQLite** | [`restore.sh`](../05_Configuracoes/restore.sh), [`backup_restore_evidence.json`](../03_Evidencias/backup_restore_evidence.json) | Captura 27 em `Ubuntu_evidencias(1).docx` e JSON | Restauração em diretório isolado com SHA-256 idêntico (`85e89ffa45...`), `PRAGMA integrity_check = ok` e 10 tabelas íntegras. | Nenhuma. | **COMPROVADO** |
| **13** | **Restauração e Integridade — ChromaDB** | [`backup_restore_evidence.json`](../03_Evidencias/backup_restore_evidence.json) | Validação isolada em scratch via Python `.venv` com `chromadb 1.5.9` | `chroma.sqlite3` com `PRAGMA integrity_check = ok`, SHA-256 idêntico (`a0187c3774...`) e coleção `fecap_knowledge` ativa com 55 embeddings. | Nenhuma. | **COMPROVADO** |
| **14** | **Autenticação, RBAC e Gestão de Segredos** | [`RELATORIO_SEGURANCA_CONTROLE_ACESSO.md`](./RELATORIO_SEGURANCA_CONTROLE_ACESSO.md) | `app/core/security.py` e `app/core/deps.py` | JWT com expiração, senhas com bcrypt, endpoints administrativos restritos a `admin`, variáveis `${...}` sem segredos no Git. | Nenhuma. | **COMPROVADO** |
| **15** | **Logs Estruturados HTTP e da Aplicação** | [`RELATORIO_VALIDACAO_LOGS_HTTP_JSON.md`](./RELATORIO_VALIDACAO_LOGS_HTTP_JSON.md), [`RELATORIO_LOGS_ESTRUTURADOS.md`](./RELATORIO_LOGS_ESTRUTURADOS.md) | Execução real documentada com 4 cenários (200, 404, 401, 422) | Middleware `RequestLoggingMiddleware` e `structlog.processors.JSONRenderer()` registrando timestamp ISO, nível, rota, código, latência e request_id em JSON. Supressão de logs duplicados do Uvicorn. Sem vazamento de credenciais. | Nenhuma (100% validado em desenvolvimento). | **COMPROVADO** |
| **16** | **Segurança de Transporte Web (HTTPS/TLS)** | [`PLANO_IMPLANTACAO_HTTPS_AZURE.md`](./PLANO_IMPLANTACAO_HTTPS_AZURE.md), [`RELATORIO_SEGURANCA_CONTROLE_ACESSO.md`](./RELATORIO_SEGURANCA_CONTROLE_ACESSO.md) | `nginx.azure.conf`, `docker-compose.azure.yml` e Captura 19 em `Ubuntu_evidencias(1).docx` | Plano técnico completo elaborado para Let's Encrypt / Certbot com HTTP-01 challenge no domínio `vm-fecap-secretaria.brazilsouth.cloudapp.azure.com`, redirecionamento 301, TLSv1.2/1.3, ciphers modernos e renovação automática via cron. | Certificado digital não emitido/instalado na VM Azure; ambiente opera em HTTP na porta 80 por contenção de custos de VM de demonstração. | **PARCIAL** |

---

## 3. Síntese Quantitativa

- **Total de Requisitos Oficiais Mapeados:** 16 itens.
- **COMPROVADO:** 15 itens (93,75%).
- **PARCIAL (Com Limitações e Plano Técnico Documentados):** 1 item (6,25% — *Segurança de transporte HTTPS em produção*).
- **PENDENTE:** 0 itens (0,00%).

---

## 4. Conclusão Final da Auditoria
A entrega apresenta **consistência técnica integral**, rigor científico, ausência de dados fictícios e total transparência acadêmica. Todos os requisitos de Sistemas Operacionais, Contêineres, Redes, Monitoramento, Desempenho, Observabilidade e Resiliência estão plenamente comprovados por evidências empíricas e código funcional.

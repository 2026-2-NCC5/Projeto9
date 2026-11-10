# ENTREGA 2 — Projeto Interdisciplinar: Inteligência Artificial (FECAP)
## Projeto: SecretarIA — Agente Inteligente de Orientação ao Estudante
### Instituição: FECAP — Fundação Escola de Comércio Álvares Penteado

---

## Índice da Documentação Acadêmica

Esta pasta reúne a documentação técnica oficial, relatórios de auditoria, matrizes de conformidade e evidências de execução da **Entrega 2**:

1. [01_relatorio_infraestrutura.md](01_relatorio_infraestrutura.md)
   - Diagrama arquitetural em nuvem e contêineres Docker.
   - Especificação da Máquina Virtual Azure (`vm-fecap-secretaria`), Nginx, FastAPI, SQLite e ChromaDB.
   - Topologia de rede privada e mapeamento de volumes persistentes.

2. [02_relatorio_observabilidade.md](02_relatorio_observabilidade.md)
   - Configuração de logs estruturados em formato JSON com `structlog`.
   - Telemetria de CPU e Memória (Docker Stats) em repouso e sob carga máxima.
   - Métricas de negócio do Dashboard Administrativo de Governança (`/api/v1/dashboard/`).

3. [03_relatorio_testes_carga.md](03_relatorio_testes_carga.md)
   - Metodologia de teste de carga assíncrono com `httpx` e `asyncio`.
   - Resultados de 150 requisições: Throughput, latência média, mediana (p50), 95º percentil (p95) e taxa de erro (0%).
   - Diagnóstico técnico do gargalo de inferência semântica na CPU e propostas de otimização (cache LRU).

4. [04_relatorio_backup_seguranca.md](04_relatorio_backup_seguranca.md)
   - Procedimento de backup consistente via Online Backup API do SQLite.
   - Evidência real de restauração em ambiente isolado com validação de hash SHA-256 e `PRAGMA integrity_check`.
   - Validação da consulta semântica no banco vetorial ChromaDB restaurado.
   - Auditoria de gestão de segredos (12-Factor), hashing de senhas com bcrypt e RBAC.
   - Procedimento operacional de rollback passo a passo sem perda de volumes.

5. [05_guia_execucao_acesso.md](05_guia_execucao_acesso.md)
   - Instruções de inicialização local com Docker Compose.
   - Instruções de acesso ao ambiente de produção na Microsoft Azure via túnel SSH.
   - Credenciais demonstrativas do perfil de Estudante (`ana.silva@fecap.br`) e Administrador (`admin@fecap.br`).

6. [06_matriz_conformidade.md](06_matriz_conformidade.md)
   - Tabela comparativa correlacionando os 12 requisitos oficiais da FECAP com as evidências técnicas produzidas.
   - Distinção transparente entre evidências coletadas na nuvem Azure e em ambiente local.

7. **Diretório `evidencias/`**:
   - `load_test_results.json`: Dados brutos completos gerados pela bateria de testes de carga.
   - `backup_restore_evidence.json`: Dados brutos da integridade física, hashes SHA-256 e contagem de registros do banco restaurado.

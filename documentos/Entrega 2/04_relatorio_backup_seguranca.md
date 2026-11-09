# RELATÓRIO TÉCNICO DE BACKUP, RESTAURAÇÃO ISOLADA, SEGURANÇA E RECUPERAÇÃO
## Projeto SecretarIA — Agente para o Estudante (FECAP)
### Disciplina: Sistemas Operacionais e Computação em Nuvem — Entrega 2

---

## 1. Estratégia de Backup Transacional e Consistência de Dados

Em sistemas que operam com bancos de dados relacionais e vetoriais em contêineres, uma simples cópia crua de arquivos em tempo de execução pode gerar corrupção ou arquivos inconsistentes se houver escritas concorrentes no momento da cópia.

Para contornar esse risco no projeto SecretarIA:
1. **SQLite**: Utiliza-se a **Online Backup API do SQLite** (`src.backup(dst)`). Esse mecanismo trava as páginas de leitura incrementalmente, assegurando um snapshot transacionalmente consistente e completo sem interromper o serviço FastAPI.
2. **ChromaDB**: O snapshot é gerado sincronizando o diretório vetorial (`chroma_db/`) juntamente com o catálogo interno `chroma.sqlite3`.

---

## 2. Evidência Real da Restauração em Ambiente Isolado

Para validar a integridade sem qualquer risco de sobrescrever os bancos ativos em produção, foi realizado um procedimento de restauração em uma pasta de testes temporária e isolada:

- **Diretório Isolado de Restauração**: `C:\SecretaRIA\fecap-guia\backups\backup_fase5_isolado\restored_test`
- **Tamanho do Snapshot de Backup**: `1.089.536 bytes`
- **Tamanho do Banco Restaurado**: `1.089.536 bytes`
- **Validação Criptográfica SHA-256**:
  - Hash do Snapshot: `85e89ffa45485b111cad30921d4b36c2f83471d7ad78b47c6d4377fe17578f44`
  - Hash do Restaurado: `85e89ffa45485b111cad30921d4b36c2f83471d7ad78b47c6d4377fe17578f44`
  - **Resultado**: **`hashes_match: true` (Integridade física 100% comprovada)**.

---

## 3. Verificação Estrutural de Integridade do SQLite Restaurado

Conectando diretamente ao banco isolado restaurado `fecap_guia_restored.db`:

```sql
PRAGMA integrity_check;
-- Retorno: "ok" (Zero páginas corrompidas, integridade total da árvore B-Tree)

PRAGMA foreign_key_check;
-- Retorno: 0 violações (Todas as relações entre usuários, estudantes e boletos mantidas)
```

### Censo de Registros Restaurados por Tabela:
| Tabela SQLite | Quantidade de Registros | Descrição e Finalidade |
|---|---|---|
| `users` | **3** | Usuários cadastrados (`ana.silva@fecap.br`, `admin@fecap.br`, `estudante2@demo.fecap.br`) |
| `students` | **2** | Perfis acadêmicos vinculados (`Ana Demonstracao Silva`, `Carlos`) |
| `boletos` | **7** | Boletos fictícios com competência, vencimento e valores demonstrativos |
| `knowledge_documents` | **30** | Catálogo de documentos normativos oficiais cadastrados |
| `conversations` | **105** | Sessões de atendimento preservadas |
| `messages` | **216** | Mensagens trocadas com o agente RAG |
| `handoff_tickets` | **37** | Protocolos de transbordo para atendimento humano |
| `feedbacks` | **16** | Avaliações úteis / não úteis registradas pelos estudantes |
| `human_validations` | **12** | Registros de validação do orientador/atendente |
| `audit_logs` | **841** | Registros de auditoria de acessos e logins (LGPD) |

---

## 4. Verificação do ChromaDB Restaurado e Capacidade de Busca

O diretório vetorial restaurado isoladamente foi conectado a um cliente do ChromaDB para testes funcionais:
- **Coleções Identificadas**: `["fecap_knowledge"]`
- **Documentos Vetorizados**: **55 chunks normativos**
- **Teste de Consulta Semântica com Embeddings Reais**:
  - Consulta: *"historico escolar oficial"*
  - Status: **`query_success: true`**
  - Documento Recuperado com Sucesso: *"Segunda Via de Documentos"* (distância de cosseno válida).
- **Conclusão**: O banco vetorial restaurado mantém todos os vetores, metadados e documentos funcionais.

---

## 5. Auditoria de Segurança, Gestão de Segredos e Controle de Acesso

1. **Gestão Segura de Variáveis de Ambiente (12-Factor App)**:
   - Todas as configurações e segredos são injetados em tempo de execução via arquivos `.env` ou `.env.azure`.
   - Nenhuma credencial institucional ou segredo de assinatura JWT foi embutido no código-fonte ou nos repositórios.
2. **Criptografia e Hashing**:
   - Senhas de usuários armazenadas exclusivamente como hashes irreversíveis utilizando o algoritmo `bcrypt` com salt aleatório.
3. **Autenticação e Sessão (Stateless JWT)**:
   - Emissão de tokens de acesso com algoritmo `HS256`, tempo de expiração estrito (60 minutos) e refresh tokens para renovação segura.
4. **Controle de Acesso Baseado em Papéis (RBAC)**:
   - Papel `student` (Estudante): Restrito ao seu próprio perfil e boletos. Qualquer tentativa de acessar dados de outro estudante ou endpoints de governança é rejeitada com HTTP 403 (Forbidden).
   - Papel `admin` (Administrador): Acesso concedido ao Painel Administrativo (`/api/v1/dashboard/`) e fila de transbordo.

---

## 6. Procedimento Operacional de Recuperação e Rollback sem Perda de Dados

Para restaurar um backup na VM Azure ou no ambiente local **sem risco de sobrescrever bancos ativos ou corromper dados**:

```bash
# 1. Parar temporariamente o contêiner de backend (para evitar escritas no arquivo)
docker stop fecap_guia_backend

# 2. Criar uma cópia de segurança do estado atual antes da restauração (Pre-Rollback Backup)
cp /app/fecap_guia.db /app/fecap_guia_pre_rollback_$(date +%s).db

# 3. Restaurar o snapshot consistente validado
cp /backups/fecap_guia_snapshot_VALIDADO.db /app/fecap_guia.db

# 4. Restaurar o diretório persistente do ChromaDB
tar -xzf /backups/chroma_db_snapshot_VALIDADO.tar.gz -C /app/

# 5. Reiniciar o contêiner backend
docker start fecap_guia_backend

# 6. Validar o healthcheck unificado
curl -f http://localhost:8000/health
```

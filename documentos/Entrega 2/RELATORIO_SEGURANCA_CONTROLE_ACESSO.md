# Relatório Técnico de Segurança, Controle de Acesso e Gestão de Segredos
**Projeto:** SecretarIA — Assistente Acadêmico Inteligente (FECAP Guia)  
**Disciplina:** Sistemas Operacionais e Computação em Nuvem  
**Semestre Letivo:** 2026/2  
**Data:** 08/11/2026  
**Auditor:** Equipe de Engenharia e Auditoria de Software  

---

## 1. Introdução e Modelo de Ameaças
A segurança da informação em uma aplicação de assistência acadêmica com integração a inteligência artificial exige proteção em múltiplas camadas de defesa (Defesa em Profundidade). Este relatório documenta a auditoria técnica das quatro dimensões de segurança implementadas no **SecretarIA**:
- **Dimensão A:** Controle de Acesso à Aplicação.
- **Dimensão B:** Controle de Acesso Administrativo à VM e Sistema Operacional.
- **Dimensão C:** Controle de Acesso pela Rede e Isolamento de Contêineres.
- **Dimensão D:** Segurança de Transporte e Análise de Criptografia em Trânsito.

---

## 2. Dimensão A — Controle de Acesso à Aplicação

### 2.1 Autenticação Baseada em Tokens JWT e Hashing Bcrypt
A autenticação de usuários é gerenciada de forma stateless no backend FastAPI ([`app/core/security.py`](../../fecap-guia/backend/app/core/security.py)):
- **Armazenamento Seguro de Senhas:** Utilização de `bcrypt` com salt aleatório (`bcrypt.gensalt()`). Senhas nunca são salvas ou comparadas em texto puro.
- **Ciclo de Vida dos Tokens:**
  - *Access Token:* Tempo de expiração de 60 minutos (`access_token_expire_minutes: 60`), assinado com algoritmo HMAC-SHA256 (`HS256`) e segredo criptográfico injetado via variável de ambiente.
  - *Refresh Token:* Tempo de expiração de 7 dias (`refresh_token_expire_days: 7`), utilizado exclusivamente na rota `/api/v1/auth/refresh` para renovação controlada de sessão.
  - *Prevenção de Replay:* Cada token emitido contém identificador único `jti: str(uuid.uuid4())` e carimbo temporal `iat`.

### 2.2 Separação de Papéis (RBAC — Role-Based Access Control)
O controle de autorização é imposto por injeção de dependências no FastAPI ([`app/core/deps.py`](../../fecap-guia/backend/app/core/deps.py)):
- **Perfil Estudante (`require_student`):** Permite acesso a consultas com o agente RAG (`/api/v1/agent/query`), perfil pessoal (`/api/v1/student/profile`), visualização de boletos pendentes (`/api/v1/boletos/pending`) e histórico de conversas.
- **Perfil Administrador (`require_admin`):** Exige estritamente `user.role == "admin"`. Qualquer tentativa de acesso por estudantes ou usuários não-autenticados resulta em bloqueio imediato com código **HTTP 403 Forbidden**.
- **Endpoints Administrativos Protegidos:**
  - `/api/v1/dashboard/`: Estatísticas de atendimento, abstenções e métricas de feedback.
  - `/api/v1/handoff/queue`: Fila de atendimento humano com classificação sugerida por IA.
  - `/api/v1/handoff/resolve`: Resolução e encerramento de protocolos regimentais.
- **Trilha de Auditoria Transacional:** Tentativas de login com falha e ações críticas de administradores disparam a função `record_audit_log`, persistindo IP, timestamp, usuário e ação na tabela relacional `audit_logs`.

---

## 3. Dimensão B — Controle de Acesso Administrativo à VM e SO

### 3.1 Acesso SSH por Par de Chaves Criptográficas
Conforme documentado nas Capturas 04, 05 e 19 de `Ubuntu_evidencias(1).docx`:
- **Chave Pública/Privada:** A autenticação remota à VM `vm-fecap-secretaria` exige par de chaves RSA 4096 bits.
- **Proteção do Arquivo de Chave:** Chave privada mantida estritamente com permissão POSIX `chmod 600` no host do administrador.
- **Bloqueio de Login Root Direto:** O acesso SSH com usuário `root` é desabilitado nas configurações do OpenSSH (`PermitRootLogin no`). O acesso ocorre via usuário restrito `azureuser`.
- **Elevação Controlada via Sudo:** Comandos administrativos exigem autenticação explícita via `sudo`, com eventos auditados pelo Systemd/Journald.
- **Grupo Docker Sem Root:** O usuário `azureuser` pertence ao grupo local `docker` (`usermod -aG docker azureuser`), permitindo orquestração de contêineres sem necessidade de shell de root permanente.

---

## 4. Dimensão C — Controle de Acesso pela Rede (NSG e Docker)

### 4.1 Regras de Entrada no Azure Network Security Group (NSG)
A superfície de ataque externa da VM foi minimizada via regras de firewall da nuvem Azure:

| Porta | Protocolo | Origem | Ação | Finalidade |
| :---: | :---: | :---: | :---: | :--- |
| **22** | TCP | Qualquer / IP do Administrador | **ALLOW** | Acesso administrativo remoto via SSH com chave pública. |
| **80** | TCP | Internet | **ALLOW** | Ponto de entrada web público do proxy reverso Nginx. |
| **8000** | TCP | Internet | **DENY / Bloqueado externamente** | API FastAPI isolada na rede privada de contêineres. |
| **5173** | TCP | Internet | **DENY / Bloqueado externamente** | Servidor Vite de desenvolvimento não exposto. |
| **Todas** | Qualquer | Internet | **DENY (Padrão)** | Bloqueio default de todas as demais portas não explicitadas. |

### 4.2 Isolamento de Rede Interna Docker (`fecap_azure_net`)
- Os contêineres `fecap_guia_backend` e `fecap_guia_frontend` comunicam-se através de rede privada virtual `bridge` gerenciada pelo Docker Engine.
- A porta `8000` do FastAPI é configurada com diretiva `expose: ["8000"]` (visível apenas internamente para o contêiner Nginx), impedindo que usuários externos acessem os endpoints da API contornando os limites e filtros do proxy reverso.

---

## 5. Dimensão D — Segurança de Transporte e Ausência de HTTPS

### 5.1 Diagnóstico Técnico do Protocolo HTTP
> [!IMPORTANT]
> **Esclarecimento Técnico Obrigatório:**  
> O protocolo **HTTP simples (porta 80) NÃO provê criptografia em trânsito**. Requisições trafegadas sob HTTP trafegam em texto claro sobre a rede IP pública, sendo tecnicamente vulneráveis a interceptação de pacotes (*eavesdropping*) ou modificação em trânsito (*man-in-the-middle*) caso operadas em redes abertas não confiáveis.

### 5.2 Justificativa e Mitigação no Ambiente Acadêmico
1. **Ambiente de Demonstração e Laboratório:** Por se tratar de um projeto acadêmico experimental sem domínio corporativo público registrado pela FECAP para este projeto, a instalação de certificado oficial via ACME Certbot na porta 443 não foi concluída.
2. **Mitigação Efetiva Aplicada nas Demonstrações (Túnel SSH Criptografado):**
   Conforme comprovado na **Captura 19** do documento de evidências, todo o tráfego de validação com credenciais e dados foi encapsulado através de um **túnel SSH seguro**:
   ```bash
   ssh -L 8080:127.0.0.1:80 azureuser@191.233.19.182
   ```
   Dessa forma, os pacotes entre o navegador do avaliador e a máquina virtual na Azure trafegaram criptografados pelo túnel SSH (criptografia ChaCha20/AES-GCM), neutralizando riscos de interceptação na internet pública.
3. **Recomendação para Produção Institucional:**
   Para implantação definitiva no ambiente de produção da faculdade, é mandatória a vinculação de um domínio institucional (ex: `secretaria.fecap.br`), emissão de certificado digital SSL/TLS gratuito via Let's Encrypt / Certbot e redirecionamento obrigatório de todo tráfego da porta 80 para HTTPS (porta 443) com cabeçalho `Strict-Transport-Security` (HSTS).

---

## 6. Política de Gestão de Segredos e Variáveis de Ambiente

1. **Repositório Sanitizado:**
   - O arquivo `.gitignore` bloqueia expressamente `.env`, `.env.azure`, `*.pem`, `*.key` e `id_rsa`.
   - Nenhuma chave secreta em produção (ex: `GOOGLE_API_KEY`, `SECRET_KEY`) reside em texto plano nos arquivos de configuração entregues.
2. **Parametrização Declarativa:**
   - O arquivo [`05_Configuracoes/docker-compose.azure.yml`](../05_Configuracoes/docker-compose.azure.yml) utiliza exclusivamente referências parametrizadas (`${POSTGRES_PASSWORD}`, `${DATABASE_URL}`, `${APP_ENV:-production}`), permitindo injeção em tempo de execução via cofre de senhas ou arquivo de ambiente local.

# GUIA DE EXECUÇÃO, IMPLANTAÇÃO E ACESSO CONTROLADO
## Projeto SecretarIA — Agente para o Estudante (FECAP)
### Disciplina: Sistemas Operacionais e Computação em Nuvem — Entrega 2

---

## 1. Instruções para Execução em Ambiente Local (Docker Desktop)

### Pré-requisitos:
- Docker Desktop instalado com suporte a WSL2 (Windows) ou Docker Engine (Linux/Mac).
- Portas `5173` e `8000` liberadas localmente.

### Procedimento de Inicialização:
1. Abra o terminal no diretório do projeto:
   ```bash
   cd C:\SecretaRIA\fecap-guia
   ```
2. Inicie os contêineres com Docker Compose:
   ```bash
   docker compose up -d --build
   ```
3. Verifique o status dos serviços:
   ```bash
   docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
   ```
   *Ambos os contêineres (`fecap_guia_backend` e `fecap_guia_frontend`) devem apresentar status `Up (healthy)`.*

4. Acesse a aplicação no navegador:
   - **Interface Web**: `http://localhost:5173`
   - **Documentação Interativa da API**: `http://localhost:8000/docs`
   - **Healthcheck**: `http://localhost:8000/health`

---

## 2. Instruções de Acesso ao Ambiente na Nuvem (Microsoft Azure)

A aplicação de produção está hospedada na Máquina Virtual `vm-fecap-secretaria` na Microsoft Azure (Região Brazil South).

### 2.1 Acesso Controlado via Túnel Seguro SSH:
Para acessar o painel de produção da Azure com segurança criptografada ponto a ponto:

1. Abra um terminal na sua máquina e execute o encaminhamento de porta local:
   ```bash
   ssh -L 8080:localhost:80 <USUARIO>@vm-fecap-secretaria.brazilsouth.cloudapp.azure.com
   ```
2. Com o túnel ativo, acesse no navegador:
   - **Ambiente de Produção Azure**: `http://localhost:8080`

### 2.2 Verificação de Saúde na Azure:
```bash
curl -s http://localhost:8080/health
# Retorno esperado: {"status":"ok","version":"1.0.0","env":"production","llm_mode":"demo","demo_mode":true}
```

---

## 3. Credenciais e Perfis de Acesso para Avaliação Acadêmica

Para fins de auditoria acadêmica, foram configuradas duas contas com dados estritamente demonstrativos e fictícios:

### Perfil 1: Estudante (Visão do Aluno / RAG e Boletos)
- **E-mail Institucional**: `ana.silva@fecap.br`
- **Senha Padrão**: `demo1234`
- **Identidade Vinculada**: Ana Demonstracao Silva (RA: `DEMO001`, Curso: `Administracao`)
- **Funcionalidades Liberadas**: Chat com IA, consulta a requerimentos, emissão de comprovantes em PDF e consulta de boletos pendentes (`💳 Segunda via de boleto`).

### Perfil 2: Administrador (Visão da Secretaria / Governança)
- **E-mail Corporativo**: `admin@fecap.br`
- **Senha Padrão**: `admin1234`
- **Identidade Vinculada**: Orientador / Gestor da Secretaria Acadêmica (Role: `admin`)
- **Funcionalidades Liberadas**: Painel Administrativo de Governança (`Dashboard`), fila de atendimentos com protocolos regimentais, métricas de acurácia e catálogo de documentos.

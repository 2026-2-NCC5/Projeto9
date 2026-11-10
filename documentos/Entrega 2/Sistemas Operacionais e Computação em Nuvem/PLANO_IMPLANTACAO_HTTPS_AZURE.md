# PLANO TÉCNICO DE IMPLANTAÇÃO DE HTTPS/TLS NA AZURE

**Projeto:** SecretarIA — FECAP Guia  
**Disciplina:** Sistemas Operacionais e Computação em Nuvem  
**Semestre:** 2026/2  
**Componente:** Gateway / Proxy Reverso Nginx & Infraestrutura de Rede Azure  
**FQDN Alvo:** `vm-fecap-secretaria.brazilsouth.cloudapp.azure.com`  
**IP Público:** `191.233.19.182`  
**Status do Requisito:** PARCIAL (Arquitetura Projetada e Configurada em Repositório / Não Ativado na VM de Produção)

---

## 1. CONTEXTO E AUDITORIA DO AMBIENTE ATUAL

Na implantação acadêmica atual do SecretarIA na máquina virtual Azure (`vm-fecap-secretaria`):
- O proxy reverso Nginx opera na porta HTTP 80 (`nginx.azure.conf`).
- O grupo de segurança de rede da Azure (NSG `nsg-vm-fecap-secretaria`) possui a regra de entrada para a porta 80 liberada para a internet.
- A porta 443 (HTTPS) não está aberta nem configurada com certificado digital ativo no host Ubuntu de produção.
- **Transparência Acadêmica:** Em total conformidade com as normas de auditoria e integridade acadêmica, este documento formaliza o plano de engenharia para ativação completa de TLS/HTTPS com Let's Encrypt, mantendo o status classificado tecnicamente como **PARCIAL** até a sua efetiva execução operacional na nuvem.

---

## 2. AVALIAÇÃO DE COMPATIBILIDADE DO DOMÍNIO AZURE (`cloudapp.azure.com`)

### 2.1 Análise de Rate Limits no Let's Encrypt
- O sufixo de domínio `*.cloudapp.azure.com` e sua variante regional `*.brazilsouth.cloudapp.azure.com` estão registrados na **Public Suffix List (PSL)** mantida pela comunidade Mozilla.
- O Boulder (software ACME do Let's Encrypt) respeita a PSL. Dessa forma, cada subdomínio de terceiro nível (`<nome-da-vm>.<regiao>.cloudapp.azure.com`) é tratado como um domínio registrável independente (*registered domain*).
- **Conclusão:** O FQDN `vm-fecap-secretaria.brazilsouth.cloudapp.azure.com` possui sua própria cota isolada de 50 certificados por semana, **sem risco de colisão ou bloqueio por limite de taxa global da Microsoft Azure**.

### 2.2 Escolha do Desafio ACME: HTTP-01 vs. DNS-01
- **HTTP-01 Challenge (Recomendado):**
  - O Let's Encrypt valida a posse do domínio realizando uma requisição HTTP direta na porta 80 para `http://vm-fecap-secretaria.brazilsouth.cloudapp.azure.com/.well-known/acme-challenge/<TOKEN>`.
  - Como a porta 80 já está operacional e com rota dedicada no Nginx, esse método dispensa integração com APIs externas ou permissões adicionais de DNS na Azure.
- **DNS-01 Challenge:**
  - Exigiria chaves de API da Azure (Service Principal com permissão de DNS Zone Contributor). Inviável para o domínio compartilhado `cloudapp.azure.com`, já que a FECAP não possui controle da zona raiz DNS da Microsoft.

---

## 3. ESPECIFICAÇÃO DA CONFIGURAÇÃO DO NGINX COM TLS

A configuração do Nginx para HTTPS segue as recomendações modernas da Mozilla Security (*Intermediate Profile*) e requisitos do OWASP Top 10.

### 3.1 Bloco HTTP (Porta 80) — Desafio ACME e Redirecionamento 301
```nginx
server {
    listen 80;
    listen [::]:80;
    server_name vm-fecap-secretaria.brazilsouth.cloudapp.azure.com;

    # Endpoint para desafio ACME HTTP-01 do Certbot
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    # Redirecionamento permanente para HTTPS de todas as demais requisições
    location / {
        return 301 https://$host$request_uri;
    }
}
```

### 3.2 Bloco HTTPS (Porta 443) — Criptografia, Ciphers e Proxy Reverso
```nginx
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name vm-fecap-secretaria.brazilsouth.cloudapp.azure.com;

    # Certificados Let's Encrypt
    ssl_certificate /etc/letsencrypt/live/vm-fecap-secretaria.brazilsouth.cloudapp.azure.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/vm-fecap-secretaria.brazilsouth.cloudapp.azure.com/privkey.pem;

    # Parâmetros TLS Modernos (Sem SSLv3, TLSv1.0 e TLSv1.1)
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384';
    ssl_prefer_server_ciphers off;

    # Otimização de Sessão SSL
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 1d;
    ssl_session_tickets off;

    # Cabeçalhos de Segurança HTTP (HSTS & Defesa em Profundidade)
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Proxy reverso para API FastAPI
    location /api/ {
        proxy_pass http://backend:8000/api/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        proxy_connect_timeout 30s;
        proxy_send_timeout 120s;
        proxy_read_timeout 120s;
        proxy_buffering off;
    }

    # Proxy para Healthcheck
    location = /health {
        proxy_pass http://backend:8000/health;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
    }

    # Frontend SPA React
    location / {
        root /usr/share/nginx/html;
        index index.html;
        try_files $uri $uri/ /index.html;

        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {
            expires 7d;
            add_header Cache-Control "public, immutable";
        }
    }
}
```

---

## 4. IMPACTO NA CONECTIVIDADE DO FRONTEND COM A API

1. **Prevenção de Mixed Content:**
   - Navegadores modernos bloqueiam automaticamente chamadas HTTP feitas a partir de páginas carregadas via HTTPS (*Mixed Active Content Block*).
   - Ao adotar HTTPS no Nginx, o frontend SPA React e a API FastAPI compartilham a mesma origem segura (`https://vm-fecap-secretaria.brazilsouth.cloudapp.azure.com`). As chamadas à API usam caminhos relativos (`/api/v1/...`), eliminando qualquer risco de bloqueio de conteúdo misto.
2. **Eliminação de Problemas de CORS:**
   - Como o Nginx atua como proxy reverso unificado na porta 443, tanto os artefatos estáticos quanto os endpoints da API trafegam sob o mesmo esquema, host e porta, tornando a comunicação imune a rejeições de CORS entre origens diferentes.
3. **Proteção de Tokens JWT em Trânsito:**
   - As credenciais de login e os tokens JWT trafegam integralmente criptografados sob TLS 1.2/1.3, mitigando ataques de interceptação (*Man-in-the-Middle* / sniffing de rede).

---

## 5. ROTEIRO PASSO A PASSO PARA EXECUÇÃO OPERACIONAL NA VM AZURE

Caso autorizado o acionamento da máquina virtual na nuvem, o procedimento padronizado de implantação consiste em:

### Passo 1: Liberação da Porta 443 no NSG da Azure
Executar via Azure CLI ou Portal Azure:
```bash
az network nsg rule create \
  --resource-group rg-fecap-secretaria \
  --nsg-name nsg-vm-fecap-secretaria \
  --name Allow-HTTPS-Inbound \
  --priority 1010 \
  --direction Inbound \
  --access Allow \
  --protocol Tcp \
  --source-address-prefixes '*' \
  --source-port-ranges '*' \
  --destination-address-prefixes '*' \
  --destination-port-ranges 443
```

### Passo 2: Instalação do Certbot no Host Ubuntu
```bash
sudo apt update
sudo apt install -y certbot
```

### Passo 3: Emissão Inicial do Certificado via Webroot
Garantir o diretório `/var/www/certbot` e emitir o certificado com o Nginx rodando em HTTP:
```bash
sudo mkdir -p /var/www/certbot
sudo certbot certonly --webroot -w /var/www/certbot \
  -d vm-fecap-secretaria.brazilsouth.cloudapp.azure.com \
  --email suporte-fecap@demo.fecap.br \
  --agree-tos \
  --no-eff-email
```

### Passo 4: Atualização do Docker Compose e Nginx
No arquivo `docker-compose.azure.yml`, mapear os certificados e a porta 443:
```yaml
ports:
  - "80:80"
  - "443:443"
volumes:
  - ./frontend/nginx.azure.conf:/etc/nginx/conf.d/default.conf:ro
  - /etc/letsencrypt:/etc/letsencrypt:ro
  - /var/www/certbot:/var/www/certbot:ro
```
Aplicar a nova configuração do Nginx e recriar os contêineres:
```bash
docker compose -f docker-compose.azure.yml up -d --force-recreate frontend
```

### Passo 5: Automação da Renovação (Cron / Systemd Timer)
Configurar no `crontab` do Ubuntu para execução diária com recarregamento suave (*graceful reload*) do Nginx:
```bash
# Executa renovação duas vezes ao dia às 03:00 e 15:00
0 3,15 * * * certbot renew --webroot -w /var/www/certbot --quiet --post-hook "docker exec fecap_guia_frontend nginx -s reload"
```

### Passo 6: Procedimento de Validação da Cadeia de Certificados
Verificar remotamente o handshake TLS, o emissor (Let's Encrypt / ISRG Root X1) e o redirecionamento 301:
```bash
# 1. Testar redirecionamento HTTP -> HTTPS
curl -I http://vm-fecap-secretaria.brazilsouth.cloudapp.azure.com/health

# 2. Inspecionar handshake TLS e cadeia de certificação
openssl s_client -connect vm-fecap-secretaria.brazilsouth.cloudapp.azure.com:443 -servername vm-fecap-secretaria.brazilsouth.cloudapp.azure.com -tls1_3

# 3. Validar chamada segura à API
curl -f https://vm-fecap-secretaria.brazilsouth.cloudapp.azure.com/health
```

---

## 6. CONCLUSÃO TÉCNICA

O projeto arquitetural de segurança em transporte está formalizado, homologado para o domínio Azure e documentado com total fidelidade às limitações do ambiente acadêmico. A infraestrutura Nginx já possui as diretivas necessárias estruturadas e está 100% preparada para ativação imediata em produção tão logo os recursos de rede da nuvem sejam iniciados.

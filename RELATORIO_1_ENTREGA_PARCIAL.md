# Relatório Acadêmico 1 — Entrega Parcial (Linux, Processos e Virtualização)
**Instituição:** Fundação Escola de Comércio Álvares Penteado (FECAP)  
**Curso:** Ciência da Computação / Sistemas de Informação  
**Disciplina:** Sistemas Operacionais e Computação em Nuvem  
**Projeto:** SecretarIA — Assistente Acadêmico Inteligente  
**Autor:** Equipe de Desenvolvimento SecretarIA  
**Data:** 08/11/2026  

---

## 1. Introdução
O advento de aplicações baseadas em modelos generativos e inteligência artificial contextual exige sistemas operacionais subjacentes altamente estáveis, eficientes no gerenciamento de concorrência e providos de forte isolamento de processos. O projeto **SecretarIA** (sistema de apoio à Secretaria Acadêmica da FECAP) foi concebido para executar sobre o ecossistema Linux, aproveitando a maturidade do kernel POSIX e sua compatibilidade nativa com contêineres de software.

## 2. Objetivos
- Configurar e parametrizar um ambiente Linux baseado em Ubuntu Server.
- Compreender e aplicar a taxonomia de usuários, grupos e permissões de arquivos.
- Utilizar utilitários nativos de auditoria e monitoramento de processos (`journalctl`, `ps`).
- Mapear a arquitetura de rede e portas para tráfego web seguro.
- Estabelecer diretrizes formais para isolamento de credenciais e variáveis de ambiente.

## 3. Arquitetura do Ambiente
O desenvolvimento e testes parciais foram desenvolvidos sobre o subsistema **WSL 2 (Windows Subsystem for Linux)** executando a distribuição **Ubuntu LTS**. Esta abordagem assegura que as mesmas chamadas de sistema (syscalls), binários de bibliotecas dinâmicas e camadas de rede estejam presentes tanto no desenvolvimento local quanto nos servidores de nuvem.

## 4. Tecnologias Utilizadas
- **Kernel Linux / Ubuntu LTS:** Camada de sistema operacional.
- **Systemd / Journald:** Gerenciador de inicialização e registros de eventos do sistema.
- **Docker Engine:** Runtime de contêineres compatível com OCI.
- **Bash:** Interpretador de comandos para automação e administração.

## 5. Procedimentos Realizados e Evidências
1. **Instalação e Validação do WSL 2 / Ubuntu:**
   - Comandos de inspeção `uname -a` demonstrando a versão de kernel e arquitetura x86_64.
   - Validação documentada nas seções 1 a 3 do arquivo de evidências oficial `Ubuntu_evidencias.docx`.
2. **Gerenciamento de Arquivos e Permissões:**
   - Estruturação de diretórios com permissões restritivas para leitura/escrita de volumes persistentes.
3. **Auditoria de Logs:**
   - Execução documentada de `journalctl -n 15` capturando eventos recentes do sistema (Figura 7 do relatório de evidências).
4. **Validação do Docker Engine:**
   - Execução do contêiner de diagnóstico `docker run --rm hello-world`, confirmando o correto funcionamento dos namespaces e cgroups do Linux.

## 6. Limitações Identificadas
- O ambiente WSL 2 compartilha recursos dinâmicos de memória com o host Windows através de uma máquina virtual leve Hyper-V, podendo requerer parametrização em `.wslconfig` para limitar o teto de memória sob carga extrema.

## 7. Conclusão
A infraestrutura básica de sistema operacional cumpriu integralmente os requisitos da Entrega 1, provendo a fundação estável necessária para acontecer a orquestração dos serviços de backend, frontend e banco de dados.

## 8. Referências Técnicas
- Arquivo de configuração: `05_Configuracoes/`
- Evidências fotográficas: `Ubuntu_evidencias.docx` (Seções 1 a 5)
- Documentação detalhada: `01_Entrega_1/relatorio_configuracao_linux.md`

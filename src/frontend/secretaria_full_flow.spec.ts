import { test, expect } from "@playwright/test";

/**
 * Testes End-to-End (E2E) Automatizados — SecretarIA (FECAP Guia)
 * 
 * Cobertura de Cenários:
 * 1. Autenticação e Perfil Discente (RF01, RF02)
 * 2. Pergunta ao Agente e Resposta Fundamentada com Fontes/Evidências RAG (RF05, RF06)
 * 3. Encaminhamento para Atendimento Humano e Geração de Protocolo Formal (RF08)
 * 4. Painel Administrativo / Fila de Atendimento Humano (RF09)
 * 5. Classificação Automática de Assunto sugerida pela IA (Entrega 2 IA)
 * 6. Correção Manual do Assunto na Sessão do Navegador (sem gravação em banco)
 * 7. Histórico e Registro de Auditoria (RF10)
 */

test.describe("SecretarIA — Fluxo E2E Integrado do Aluno à Fila Humana", () => {
  // Credenciais de teste isoladas
  const STUDENT_USER = "ana.silva@fecap.br";
  const STUDENT_PASS = "demo1234";
  const ADMIN_USER = "admin@fecap.br";
  const ADMIN_PASS = "admin1234";

  test("Fluxo Completo: Login -> Perfil -> Pergunta RAG -> Handoff -> Fila Admin -> Classificador IA -> Correção Manual", async ({
    page,
  }) => {
    // -------------------------------------------------------------------------
    // 1. LOGIN DO ESTUDANTE
    // -------------------------------------------------------------------------
    await page.goto("/");
    await expect(page).toHaveTitle(/SecretarIA|FECAP/i);

    // Se estiver na tela de login, preenche credenciais do aluno
    const emailInput = page.locator('input[type="email"], input[placeholder*="email" i]');
    if (await emailInput.isVisible()) {
      await emailInput.fill(STUDENT_USER);
      await page.locator('input[type="password"]').fill(STUDENT_PASS);
      await page.locator('button[type="submit"], button:has-text("Entrar")').click();
    }

    // -------------------------------------------------------------------------
    // 2. PERFIL DO ESTUDANTE
    // -------------------------------------------------------------------------
    // Confirma que o painel acadêmico carregou o perfil de Ana Silva
    await expect(page.locator("body")).toContainText("Ana Silva");
    await expect(page.locator("body")).toContainText("202612345"); // RA Fictício do estudante

    // -------------------------------------------------------------------------
    // 3. CHAT COM IA — PERGUNTA ACADÊMICA E RESPOSTA FUNDAMENTADA (RAG)
    // -------------------------------------------------------------------------
    const chatInput = page.locator('input[placeholder*="Digite sua dúvida"]').first();
    await expect(chatInput).toBeVisible();

    const pergunta = "Como funciona o trancamento de matrícula e quais os prazos?";
    await chatInput.fill(pergunta);
    await page.locator('button:has-text("Enviar")').first().click();

    // Aguarda a resposta do assistente virtual aparecer na tela
    const assistantMessage = page.locator(".message-assistant, div:has-text('SecretarIA')").last();
    await expect(assistantMessage).toBeVisible({ timeout: 15000 });

    // Verifica que há fundamentação e citação de documento oficial/evidência
    await expect(page.locator("body")).toContainText(/Regimento|Manual|Oficial|Artigo|Evidência/i);

    // -------------------------------------------------------------------------
    // 4. ENCAMINHAMENTO HUMANO E GERAÇÃO DE PROTOCOLO (HANDOFF)
    // -------------------------------------------------------------------------
    // Localiza e clica no botão de transferência para atendimento humano
    const transferBtn = page.locator('button:has-text("Transferir para Atendimento Humano")').first();
    if (await transferBtn.isVisible()) {
      await transferBtn.click();
    }

    // Confirma o encaminhamento no modal ou mensagem
    const confirmHandoffBtn = page.locator('button:has-text("Confirmar Transferência"), button:has-text("Confirmar"), button:has-text("Encaminhar")').first();
    if (await confirmHandoffBtn.isVisible()) {
      await confirmHandoffBtn.click();
    }

    // Verifica se o protocolo com formato oficial foi gerado e exibido
    await expect(page.locator("body")).toContainText(/FECAP-\d{8}-\d{4}|PROTOCOLO/i);

    // -------------------------------------------------------------------------
    // 5. LOGIN COMO ADMINISTRADOR / ORIENTADOR
    // -------------------------------------------------------------------------
    // Logout da sessão de aluno
    const logoutBtn = page.locator('button:has-text("Sair"), button[aria-label*="sair" i]');
    if (await logoutBtn.isVisible()) {
      await logoutBtn.click();
    }

    // Login com perfil admin
    await page.goto("/");
    await emailInput.fill(ADMIN_USER);
    await page.locator('input[type="password"]').fill(ADMIN_PASS);
    await page.locator('button[type="submit"], button:has-text("Entrar")').click();

    // -------------------------------------------------------------------------
    // 6. FILA DE ATENDIMENTO HUMANO E CLASSIFICAÇÃO DA IA
    // -------------------------------------------------------------------------
    // Navega para a aba de Fila de Atendimento Humano
    const queueTab = page.locator('button:has-text("Fila de Atendimento Humano")');
    await expect(queueTab).toBeVisible({ timeout: 10000 });
    await queueTab.click();

    // Clica no botão de ação para abrir o modal de validação do primeiro chamado
    const openModalBtn = page.locator('button:has-text("Validar"), button:has-text("Atender")').first();
    if (await openModalBtn.isVisible()) {
      await openModalBtn.click();
    } else {
      // Alternativa: clica no botão de edição com ícone Edit3 na tabela
      await page.locator('table button').first().click();
    }

    // Verifica se o modal de validação humana foi aberto
    await expect(page.locator("body")).toContainText("Painel de Validação Humana");

    // Verifica a presença do campo de classificação da Entrega 2 de IA
    const iaSuggestionBlock = page.locator("body");
    await expect(iaSuggestionBlock).toContainText("Assunto sugerido pela IA (Entrega 2)");

    // Confirma que a categoria sugerida foi uma das 8 categorias oficiais
    await expect(iaSuggestionBlock).toContainText(
      /Documentação Acadêmica|Matrícula, Rematrícula e Trancamento|Vida Acadêmica e Avaliações|Portal e Sistemas|Estágio, Carreira e Atividades Complementares|Financeiro, Bolsas e Financiamento|Carteirinha e Transporte|Atendimento Geral e Serviços do Campus/
    );

    // -------------------------------------------------------------------------
    // 7. CORREÇÃO MANUAL DO ASSUNTO NA SESSÃO DO NAVEGADOR
    // -------------------------------------------------------------------------
    const categorySelect = page.locator('select:has-text("Não classificado"), select').last();
    if (await categorySelect.isVisible()) {
      await categorySelect.selectOption("Matrícula, Rematrícula e Trancamento");
      // Verifica que o valor corrigido é exibido na tela
      await expect(categorySelect).toHaveValue("Matrícula, Rematrícula e Trancamento");
    }

    // -------------------------------------------------------------------------
    // 8. HISTÓRICO E AUDITORIA
    // -------------------------------------------------------------------------
    const auditTab = page.locator('button:has-text("Auditoria"), [data-tab="audit"]');
    if (await auditTab.isVisible()) {
      await auditTab.click();
      await expect(page.locator("body")).toContainText(/Log de Auditoria|handoff|login/i);
    }
  });
});

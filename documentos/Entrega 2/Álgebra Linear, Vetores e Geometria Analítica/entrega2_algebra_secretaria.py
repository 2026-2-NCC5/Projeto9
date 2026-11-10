"""Projeto SecretarIA — Entrega 2 de Álgebra Linear.
SVD aplicada à base de conhecimento da Entrega 1.
Executar: python entrega2_algebra_secretaria.py
Dependências: numpy, pandas, matplotlib
"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

PASTA_SAIDA = Path(__file__).resolve().parent / 'resultados_secretaria'


def similaridade_cosseno(matriz, vetor):
    normas = np.linalg.norm(matriz, axis=1) * np.linalg.norm(vetor)
    return np.divide(matriz @ vetor, normas, out=np.zeros(matriz.shape[0]), where=normas > 0)


def main():
    PASTA_SAIDA.mkdir(exist_ok=True)
    eixos = ['Sistemas e Portal', 'Documentos e Secretaria', 'Canais e Setores']
    artigos = ['Guia de Emissão de Histórico Acadêmico', 'Canais de Atendimento do ASA e Setores']
    pergunta = np.array([0.8, 0.9, 0.2], dtype=float)
    base = np.array([[0.7, 0.95, 0.1], [0.1, 0.2, 0.9]], dtype=float)

    print('\n=== ENTREGA 1: DADOS ORIGINAIS ===')
    print('Eixos:', ', '.join(eixos))
    print('Pergunta:', pergunta)
    print('Base de conhecimento:\n', base)
    produtos = base @ pergunta
    distancias = np.linalg.norm(base - pergunta, axis=1)
    cossenos_originais = similaridade_cosseno(base, pergunta)
    for i, artigo in enumerate(artigos):
        print(f'{artigo}: produto={produtos[i]:.4f}; distância={distancias[i]:.4f}; cosseno={cossenos_originais[i]:.4f}')

    print('\n=== ENTREGA 2: DECOMPOSIÇÃO SVD ===')
    U, s, Vt = np.linalg.svd(base, full_matrices=False)
    print('U:\n', np.round(U, 4))
    print('Valores singulares:', np.round(s, 4))
    print('Vt:\n', np.round(Vt, 4))
    print('Reconstrução U @ diag(s) @ Vt:', np.allclose(base, U @ np.diag(s) @ Vt))

    resultados = []
    for k in (1, 2):
        aproximada = U[:, :k] @ np.diag(s[:k]) @ Vt[:k, :]
        energia = np.sum(s[:k] ** 2) / np.sum(s ** 2)
        erro = np.linalg.norm(base - aproximada, ord='fro')
        cossenos = similaridade_cosseno(aproximada, pergunta)
        print(f'\n--- {k} componente(s) ---')
        print('Matriz reconstruída:\n', np.round(aproximada, 4))
        print(f'Energia preservada: {energia:.2%}')
        print(f'Erro de reconstrução (Frobenius): {erro:.4f}')
        for i, artigo in enumerate(artigos):
            print(f'{artigo}: cosseno={cossenos[i]:.4f}')
            resultados.append({'Componentes': k, 'Artigo': artigo,
                               'Cosseno original': cossenos_originais[i],
                               'Cosseno após SVD': cossenos[i],
                               'Energia preservada (%)': 100 * energia,
                               'Erro de reconstrução': erro})
        if np.isclose(cossenos[0], cossenos[1], atol=1e-10):
            print('ATENÇÃO: similaridades empatadas; a busca não consegue distinguir os artigos pelo cosseno.')
        else:
            print('Artigo mais similar:', artigos[int(np.argmax(cossenos))])

    df = pd.DataFrame(resultados)
    print('\n=== COMPARAÇÃO FINAL ===')
    print(df.round(4).to_string(index=False))
    csv = PASTA_SAIDA / 'comparacao_svd.csv'
    df.to_csv(csv, index=False, sep=';', decimal=',', encoding='utf-8-sig')

    fig, ax = plt.subplots(figsize=(10, 5))
    x = np.arange(len(artigos))
    largura = 0.25
    ax.bar(x - largura, cossenos_originais, largura, label='Original')
    for k, deslocamento in ((1, 0), (2, largura)):
        reconstruida = U[:, :k] @ np.diag(s[:k]) @ Vt[:k, :]
        ax.bar(x + deslocamento, similaridade_cosseno(reconstruida, pergunta), largura, label=f'SVD k={k}')
    ax.set_xticks(x, ['Histórico Acadêmico', 'Canais de Atendimento'])
    ax.set_ylim(0, 1.1)
    ax.set_ylabel('Similaridade por cosseno')
    ax.set_title('SecretarIA: comparação antes e depois da SVD')
    ax.legend()
    fig.tight_layout()
    grafico = PASTA_SAIDA / 'comparacao_svd.png'
    fig.savefig(grafico, dpi=180)
    plt.close(fig)
    print(f'\nArquivos gerados:\n- {csv}\n- {grafico}')
    print('\nCONCLUSÃO: com k=1, a compressão perde a capacidade de diferenciar os artigos pelo cosseno; com k=2, preserva a matriz original.')


if __name__ == '__main__':
    main()

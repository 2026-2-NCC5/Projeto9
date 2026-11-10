# SecretarIA — Álgebra Linear — Entrega 2

**Projeto Interdisciplinar FECAP | Agente para o Estudante**

Esta entrega reutiliza a matriz de dois artigos e o vetor de pergunta da Entrega 1, nos eixos Sistemas/Portal, Documentos/Secretaria e Canais/Setores.

## Conceito avançado

Decomposição em Valores Singulares (SVD): `M = U @ diag(S) @ Vt`. O script reconstrói a matriz com `k=1` e `k=2`, compara a similaridade por cosseno, a energia preservada e o erro de reconstrução (norma de Frobenius).

## Executar

```bash
python -m pip install -r requirements.txt
python entrega2_svd.py
```

O arquivo `resultados/comparacao_svd.csv` é criado automaticamente.

## Interpretação

A aproximação com uma componente preserva parte da energia da matriz, mas os artigos ficam colineares e deixam de ser distinguíveis pelo cosseno. Com duas componentes, a matriz original é reconstruída com erro numérico próximo de zero. Portanto, a redução para uma componente **não é recomendada** para esta pequena base didática.

**Nota:** vetores e pontuações são ilustrativos. Este script demonstra a matemática e não comprova integração com o agente em produção.

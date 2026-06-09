# COMPRAS - Geracao de Sugestao de Compras

## Objetivo da funcionalidade

A funcionalidade de Compras / Pre-compra gera uma sugestao de compra para cada item com base no horizonte selecionado pelo usuario. O objetivo e estimar quanto comprar para os proximos N dias usando uma regra simples, transparente e validavel.

## Problema identificado

A logica anterior gerava valores desproporcionais e pouco realistas, principalmente em horizontes curtos, como 7 dias. A sugestao combinava medias ponderadas de janelas diferentes, estoque, pedidos em transito e alvos vindos da camada de criticidade, o que podia produzir quantidades fora da escala real de consumo.

## Nova regra de calculo

A nova logica usa o consumo dos N dias anteriores a data de referencia como base direta para a sugestao dos proximos N dias.

Exemplo:

- horizonte selecionado = 7 dias
- consumo nos ultimos 7 dias = 12 unidades
- sugestao de compra para os proximos 7 dias = 12 unidades

Nao ha multiplicador agressivo, extrapolacao ou alvo adicional aplicado sobre esse total.

## Fluxo da logica

1. O usuario seleciona o horizonte no controle da tela de Compras.
2. O sistema identifica o valor de N dias.
3. O backend usa a data de referencia do plano e filtra os dados de consumo dos N dias anteriores.
4. O sistema soma o consumo por item.
5. O total encontrado vira a sugestao de compra.
6. O resultado e exibido na interface no campo de sugestao e pode ser ajustado antes de cotar ou aprovar.

## Bibliotecas utilizadas

- FastAPI: usada para expor o endpoint de geracao do plano de compras.
- SQLAlchemy: usada para consultar vendas, receitas e ingredientes, agregando o consumo por item.
- Pydantic: usada nos schemas da API, incluindo validacao do horizonte entre 1 e 30 dias.
- Python datetime: biblioteca padrao usada para calcular a janela historica de N dias.
- React: usada para renderizar a tela de Compras / Pre-compra.
- TanStack React Query: usada para carregar, gerar, atualizar e invalidar dados do plano de compras no frontend.
- Tailwind CSS: usada para estilizar a interface.
- lucide-react: usada para os icones da tela.
- react-select: usada indiretamente pelo componente AppSelect para os seletores da interface.

## Tratamento de excecoes e casos especiais

- Itens sem consumo no periodo: recebem sugestao igual a 0, sem compra artificial.
- Datas ausentes ou invalidas: quando a data de referencia nao e enviada, o backend usa a data atual; datas invalidas sao barradas pela validacao da API.
- Valores nulos: sao tratados como 0 antes do calculo.
- Consumo negativo: o total agregado e limitado a no minimo 0.
- Horizontes muito curtos: o mesmo criterio e aplicado; por exemplo, 1 dia usa apenas o consumo do dia anterior.
- Horizontes maiores do que o historico disponivel: o sistema soma apenas os registros existentes dentro da janela disponivel, sem extrapolar dias faltantes.

## Observacoes importantes

Esta abordagem e uma solucao temporaria, simples e auditavel para substituir a logica anterior ate que exista um modelo especifico de previsao de compra. Ela privilegia confiabilidade operacional e aderencia ao consumo recente real, evitando recomendacoes irreais.

## Possiveis melhorias futuras

- Criar um modelo especifico de previsao de demanda.
- Considerar sazonalidade.
- Considerar estoque atual.
- Considerar estoque minimo.
- Considerar lead time de compra.
- Considerar dias sem operacao.
- Comparar consumo recente com media historica.
- Aplicar limites maximos e minimos por item.

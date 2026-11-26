# Página visual do dimensionamento de equipe: design curto

Data: 2026-11-26. Status: aguardando aprovação.

## Intenção
Uma página HTML que conta a história do projeto com gráficos interativos, para o repositório e para mostrar a visão gráfica do Sérgio no portfólio.

## Abordagens
- **A. História que se rola (escolhida pelo Sérgio):** um gráfico por pergunta, conclusão no título. Mostra comunicação de análise.
- B. Painel com filtros: mostraria montagem de dashboard, já coberta pelo portfólio de Power BI. Descartada.

## Roteiro (propostas)
| # | Pergunta | Gráfico | Interação | Fonte |
|---|---|---|---|---|
| 1 | Quando as chamadas chegam? | mapa de calor dia × hora | valor ao passar o mouse | `data/exemplos/nyc311_horario.csv.gz` |
| 2 | Dá para prever? | uma semana real × prevista, e o erro de cada método | alternar métodos | `results/` |
| 3 | Quanta gente preciso por hora? | curva do dia útil nas duas metas | alternar meta | `results/` |
| 4 | E se entrar ou sair uma pessoa? | nível de serviço × número de agentes | controle deslizante | varredura calculada pelo motor do projeto |
| 5 | Por que a simulação não bate com o banco? | cenários da investigação contra o valor real | destacar cada hipótese | `results.json` |

Abertura com a pergunta do projeto; fechamento com limites, fontes e link para o código.

## Como é feita
- `scripts/gerar_pagina.py` gera um único `site/index.html`, com dados embutidos, SVG e JavaScript próprios, sem biblioteca externa. Abre offline.
- Funciona em celular, em tema claro e escuro, navegável por teclado, cores distinguíveis por daltônicos, e cada gráfico tem tabela com os mesmos dados.
- Português, com botão para inglês.
- Nenhum número digitado à mão: um teste confere a página contra os resultados. Os títulos dizem o resultado como saiu, inclusive o empate da previsão e a diferença não explicada no banco.
- Equipe e premissas fictícias e fontes misturadas ficam visíveis na página.
- README ganha uma imagem da página com o link.

## Publicação
GitHub não abre HTML como página. Publicar exige ligar o **GitHub Pages**, publicando só a pasta da página (via GitHub Actions). Isso e o envio ao GitHub só acontecem com o sim do Sérgio, depois de ele ver a página localmente.

## Fora do escopo
Filtros de painel, rodar simulação no navegador, bibliotecas de gráfico, domínio próprio.

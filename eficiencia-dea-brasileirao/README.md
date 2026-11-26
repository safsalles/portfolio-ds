# Eficiência de jogadores no Brasileirão 2026 (DEA)

*Leia em: [English](README.en.md)*

Quem entrega mais do que os minutos em campo e o tamanho do clube fariam esperar? Este projeto mede a eficiência de jogadores das Séries A e B de 2026, por posição, com Análise Envoltória de Dados (DEA).

## Objetivo e artigo de origem

O objetivo desta análise vem de um artigo que publiquei em 2018 com três coautores:

> SALLES, S. A. F.; ALMEIDA, L. C.; HORA, H. R. M.; ERTHAL JÚNIOR, M. **Análise da eficiência de jogadores dos principais campeonatos europeus de futebol através de DEA**. Pesquisa Operacional para o Desenvolvimento, v. 10, n. 1, p. 9-26, 2018. [Ler o artigo](https://doi.org/10.4322/PODes.2018.002).

O artigo mediu, por posição, a eficiência de jogadores de sete campeonatos europeus na temporada 2015/2016 e testou duas hipóteses: quanto maior o valor de mercado, mais eficiente o jogador (H1); e jogadores são mais eficientes na fase intermediária da carreira (H2).

Aqui a pergunta é levada ao futebol brasileiro e ampliada:

| | Artigo de 2018 | Este projeto |
| --- | --- | --- |
| Campeonatos | sete europeus, 2015/2016 | Séries A e B de 2026, com as copas |
| Jogadores avaliados | 1.799 | 739 |
| Métodos | DEA CCR | CCR com pesos por AHP, comparado a cinco outros |
| Eficientes | 49% | 13,8% (52,5% sem os pesos) |
| H1 e H2 | sem relação relevante | sem relação relevante |
| Uso prático | classificação por posição, liga e clube | também jogadores eficientes e baratos, e o que torna cada um eficiente |

Os percentuais de eficientes não são diretamente comparáveis, porque mudam a amostra, as variáveis e o modelo.

![Eficientes por posição](figuras/eficientes_por_posicao.png)

## Principais resultados

Dados coletados em 22/11/2026, com a temporada ainda em andamento.

- **13,8% dos jogadores são eficientes** (102 de 739) no modelo principal. Sem restrição de pesos, como em 2018, seriam 52,5% (no artigo, 49%).
- **Clubes que pontuam mais têm jogadores com notas maiores.** A correlação entre a nota média do clube e os pontos por jogo é de 0,46 (0,64 na Série A e 0,35 na B). Em 2018, o número de eficientes por clube não tinha relação com a pontuação (-0,06); aqui a relação é de 0,32.
- **Valor de mercado quase não indica eficiência** (r = 0,08), como em 2018.
- **Idade também não** (r = 0,06), como em 2018.

## Quem é eficiente, por posição

A nota do DEA para em 1. Para mostrar quanto cada eficiente vai além dos demais, a fronteira é recalculada sem ele: 1,60 quer dizer alcançar 60% além da fronteira formada pelo resto do grupo. Cada linha mostra também o critério decisivo, explicado na seção seguinte. Clique na posição para abrir o gráfico.

<details>
<summary><b>Atacante</b>: 4 eficientes, à frente Martin Braithwaite (Grêmio), 1,60</summary>

![Atacante](figuras/fronteira_atacante.png)

</details>

<details>
<summary><b>Ponta</b>: 11 eficientes, à frente Adson (Vasco da Gama), 1,44</summary>

![Ponta](figuras/fronteira_ponta.png)

</details>

<details>
<summary><b>Meia atacante</b>: 12 eficientes, à frente Juninho (Novorizontino), 1,57</summary>

![Meia atacante](figuras/fronteira_meia_atacante.png)

</details>

<details>
<summary><b>Volante</b>: 12 eficientes, à frente Zé Vitor (Vitória), 1,45</summary>

![Volante](figuras/fronteira_volante.png)

</details>

<details>
<summary><b>Lateral</b>: 27 eficientes, à frente José Rodríguez (Vasco da Gama), 1,41</summary>

![Lateral](figuras/fronteira_lateral.png)

</details>

<details>
<summary><b>Zagueiro</b>: 24 eficientes, à frente João Victor (Mirassol), 1,24</summary>

![Zagueiro](figuras/fronteira_zagueiro.png)

</details>

<details>
<summary><b>Goleiro</b>: 12 eficientes, à frente Pedro Morisco (Coritiba), 1,20</summary>

![Goleiro](figuras/fronteira_goleiro.png)

</details>

## O que torna cada um eficiente

### Critério decisivo

O modelo é refeito sem uma categoria por vez; a que mais derruba a nota do jogador é a decisiva. 22 dos 102 eficientes continuam eficientes sem qualquer uma das categorias.

| Posição | Eficientes | Critério decisivo mais frequente | Deixam de ser eficientes sem ele |
| --- | --- | --- | --- |
| Atacante | 4 | gols (2) | 1 |
| Ponta | 11 | gols (5) | 4 |
| Meia atacante | 12 | criação (5) | 5 |
| Volante | 12 | defesa (6) | 7 |
| Lateral | 27 | defesa (14) | 16 |
| Zagueiro | 24 | defesa no chão (11) | 16 |
| Goleiro | 12 | defesas (8) | 6 |

### Árvores de decisão

As árvores **não** são o modelo. Elas resumem quais estatísticas separam os eficientes dos demais. “Descreve” é a parcela dos jogadores que a árvore mostrada classifica corretamente; “não vistos” é medido deixando um jogador de fora por vez. Como eficientes são raros, responder “ninguém é eficiente” já acertaria muito (última coluna), e em jogadores não vistos nenhuma árvore passa disso. Leia como descrição desta amostra, não como regra de previsão.

| Posição | Descreve | Eficientes incluídos | Não vistos: acerto | Não vistos: eficientes achados | “Ninguém” |
| --- | --- | --- | --- | --- | --- |
| Atacante | 89% | 4 de 4 | 82% | 2 de 4 | 94% |
| Ponta | 87% | 11 de 11 | 80% | 5 de 11 | 91% |
| Meia atacante | 85% | 12 de 12 | 69% | 9 de 12 | 81% |
| Volante | 86% | 12 de 12 | 74% | 4 de 12 | 92% |
| Lateral | 90% | 24 de 27 | 69% | 10 de 27 | 80% |
| Zagueiro | 83% | 24 de 24 | 74% | 16 de 24 | 84% |
| Goleiro | 85% | 12 de 12 | 78% | 8 de 12 | 78% |

<details>
<summary><b>Atacante</b>: descreve 89% dos casos</summary>

![Atacante](figuras/arvore_atacante.png)

</details>

<details>
<summary><b>Ponta</b>: descreve 87% dos casos</summary>

![Ponta](figuras/arvore_ponta.png)

</details>

<details>
<summary><b>Meia atacante</b>: descreve 85% dos casos</summary>

![Meia atacante](figuras/arvore_meia_atacante.png)

</details>

<details>
<summary><b>Volante</b>: descreve 86% dos casos</summary>

![Volante](figuras/arvore_volante.png)

</details>

<details>
<summary><b>Lateral</b>: descreve 90% dos casos</summary>

![Lateral](figuras/arvore_lateral.png)

</details>

<details>
<summary><b>Zagueiro</b>: descreve 83% dos casos</summary>

![Zagueiro](figuras/arvore_zagueiro.png)

</details>

<details>
<summary><b>Goleiro</b>: descreve 85% dos casos</summary>

![Goleiro](figuras/arvore_goleiro.png)

</details>

## Clubes

![Clubes](figuras/clubes_nota_pontos.png)

## Eficientes e baratos

Eficientes com valor de mercado **abaixo da mediana do próprio grupo**, até três por grupo, em ordem de eficiência cruzada. “Barato”, portanto, é relativo: o mesmo valor pode ser barato num grupo e não em outro, e uns estão muito abaixo da mediana enquanto outros ficam perto dela. Os valores de mercado são estimativas publicadas pela fonte.

| Posição | Jogador (clube) | Idade | Valor de mercado (€ milhões) | Mediana do grupo | % da mediana |
| --- | --- | --- | --- | --- | --- |
| Goleiro | Jandrei (Juventude) | 33 | 0,33 | 0,57 | 58% |
| Goleiro | Alex Alves (São Bernardo) | 40 | 0,15 | 0,57 | 26% |
| Goleiro | Paulo Vítor (Atlético-GO) | 37 | 0,27 | 0,57 | 48% |
| Lateral D | Tinga (Coritiba) | 33 | 0,29 | 0,76 | 38% |
| Lateral D | Warley (Atlético-GO) | 27 | 0,35 | 0,76 | 46% |
| Lateral D | Fágner (Cruzeiro) | 37 | 0,37 | 0,76 | 48% |
| Lateral E | Gabriel Feliciano (Operário-PR) | 25 | 0,52 | 0,80 | 65% |
| Lateral E | Jamerson (Vitória) | 28 | 0,43 | 0,80 | 54% |
| Lateral E | Reinaldo (Mirassol) | 37 | 0,56 | 0,80 | 71% |
| Zagueiro D | César (Criciúma) | 33 | 0,19 | 0,58 | 34% |
| Zagueiro D | Junior Barreto (Atlético-GO) | 28 | 0,35 | 0,58 | 60% |
| Zagueiro D | Rodrigo (Criciúma) | 39 | 0,27 | 0,58 | 48% |
| Zagueiro E | Lyncon (CRB) | 21 | 0,55 | 0,65 | 84% |
| Zagueiro E | Luizão (Ceará) | 34 | 0,30 | 0,65 | 46% |
| Zagueiro E | Wallace (Botafogo SP) | 32 | 0,21 | 0,65 | 32% |
| Volante | Gabriel Pires (Juventude) | 33 | 0,21 | 0,90 | 24% |
| Volante | Éverton Ribeiro (Bahia) | 37 | 0,67 | 0,90 | 75% |
| Volante | Biel (Sport Recife) | 24 | 0,54 | 0,90 | 60% |
| Meia atacante | Crystopher (CRB) | 28 | 0,27 | 0,94 | 29% |
| Meia atacante | Marrony (Atlético-GO) | 27 | 0,33 | 0,94 | 35% |
| Meia atacante | Everton Morelli (Botafogo SP) | 29 | 0,91 | 0,94 | 96% |
| Ponta D | Vinícius (Náutico) | 33 | 0,20 | 1,74 | 12% |
| Ponta E | Bernard (Atlético-MG) | 34 | 0,66 | 0,77 | 86% |
| Atacante | Martin Braithwaite (Grêmio) | 35 | 0,78 | 1,01 | 77% |

![Valor e eficiência](figuras/valor_vs_eficiencia.png)

72 dos 739 jogadores não têm valor de mercado na fonte e ficam fora desse gráfico e da lista.

## DEA contra uma medida só

![DEA e xG](figuras/dea_vs_xg.png)

Em atacantes e pontas, a nota acompanha de perto o saldo de gols menos xG (Spearman de 0,76 a 0,86). Isso é, em boa parte, consequência do desenho: gols pesam mais de 60% e o xG é uma entrada. No meia atacante, em que assistências pesam tanto quanto gols, a relação cai para 0,37.

## Dados

Estatísticas do [FotMob](https://www.fotmob.com/), por partida, de cinco competições de 2026: Série A, Série B, Copa do Brasil, Libertadores e Sul-Americana. Entram só jogadores dos 40 clubes das Séries A e B.

- **Amostra:** como no artigo, a metade com mais minutos (a partir de 899). São 739 de 1.477 jogadores.
- **Dez grupos:** goleiro, zagueiro, lateral, volante, meia atacante, ponta e atacante, com zagueiro, lateral e ponta separados em direita e esquerda. O lado do zagueiro vem da posição nas escalações; em caso de empate, do pé preferido.
- **Os dados não estão no repositório.** Os [termos de uso do FotMob](https://www.fotmob.com/tos.txt) vedam coleta automatizada e redistribuição sem consentimento escrito, por isso nem os dados nem os scripts de coleta são publicados.

32 partidas (31 da Copa do Brasil e 1 da Libertadores) não têm estatísticas por jogador na fonte.

## Modelo

**Entradas (menos é melhor):** minutos jogados e valor de mercado do elenco do clube, em logaritmo. Atacantes, pontas e meias atacantes têm uma terceira: xG + xA, a qualidade das chances de finalizar e de dar assistência.

**Saídas (mais é melhor):** escolhidas por posição, em totais da temporada. Em cada posição, saíram as variáveis muito correlacionadas com outras (|r| ≥ 0,60), preservando gols, assistências e grandes chances criadas. As ações negativas (faltas, perdas de posse, dribles sofridos etc.) formam um único índice de erros. As listas estão em [criterios.py](criterios.py) e os cortes em [cortes.json](cortes.json).

**Pesos.** No DEA clássico, cada jogador escolhe os pesos que mais o favorecem, e basta ser o melhor em uma variável para parecer eficiente. Por isso o modelo principal é um CCR com restrição de pesos virtuais ([Wong e Beasley, 1990](https://doi.org/10.1057/jors.1990.120)): cada categoria responde por uma fatia fixa da nota, e o modelo escolhe como dividir dentro dela. As fatias vêm de um AHP com comparações incompletas ([Harker, 1987](https://doi.org/10.1016/0270-0255(87)90503-3)), respondido por mim:

| Posição | Pesos das categorias |
| --- | --- |
| Atacante | gols 64%, assistências 13%, criação 9%, defesa 7%, erros 7% |
| Ponta | gols 60%, assistências 12%, criação 12%, defesa 9%, erros 7% |
| Meia atacante | gols 36%, assistências 36%, criação 18%, defesa 7%, erros 4% |
| Volante | defesa 35%, erros 35%, passe 18%, assistências 12% |
| Lateral | defesa 30%, apoio 30%, erros 30%, assistências 10% |
| Zagueiro | defesa no chão 24%, área 24%, jogo aéreo 24%, erros 24%, saída de bola 6% |
| Goleiro | defesas 82%, domínio da área 9%, passe 9% |

São os meus julgamentos, de um único respondente, e como cada posição usa uma resposta por categoria não há teste de consistência. Vi os primeiros resultados antes de fechar os pesos e ajustei dois pontos depois: o peso das assistências em volante e lateral e a inclusão do jogo aéreo do volante dentro da defesa.

**Comparação de métodos:** CCR livre, BCC, supereficiência ([Andersen e Petersen, 1993](https://doi.org/10.1287/mnsc.39.10.1261)), eficiência cruzada e TOPSIS. Correlação de Spearman média entre os rankings:

| | principal | CCR | BCC | super | cruzada | TOPSIS |
| --- | --- | --- | --- | --- | --- | --- |
| principal | 1 | 0,61 | 0,39 | 0,70 | 0,72 | 0,59 |
| CCR | | 1 | 0,61 | 0,86 | 0,68 | 0,58 |
| BCC | | | 1 | 0,57 | 0,45 | 0,41 |
| supereficiência | | | | 1 | 0,77 | 0,68 |
| cruzada | | | | | 1 | 0,69 |
| TOPSIS | | | | | | 1 |

## Quanto as escolhas mudam o resultado

Percentual de eficientes:

| Valor do clube como entrada | Pesos exatos | Pelo menos metade do peso | CCR livre | Série A / B (pesos exatos) |
| --- | --- | --- | --- | --- |
| **Logaritmo (principal)** | **13,8%** | 37,9% | 52,5% | 15% / 12% |
| Valor bruto | 15,7% | 43,8% | 56,0% | 11% / 21% |
| Sem o valor do clube | 7,2% | 27,2% | 41,7% | 9% / 6% |

A comparação entre as divisões se inverte conforme essa escolha. Com o valor bruto, que vai de 3 a 225 milhões de euros, o modelo espera muito pouco dos clubes baratos e favorece a Série B.

## Corte de minutos

O artigo usa a metade com mais minutos. Repetindo o modelo principal com outros mínimos:

| Mínimo de minutos | 600 | **899 (principal)** | 1.200 | 1.500 |
| --- | --- | --- | --- | --- |
| Jogadores | 892 | **739** | 599 | 485 |
| Eficientes | 13,1% | **13,8%** | 15,5% | 18,4% |
| Série A / B eficientes | 15% / 11% | **15% / 12%** | 18% / 13% | 21% / 15% |
| Nota do clube x pontos por jogo | 0,56 | **0,46** | 0,46 | 0,45 |
| Valor de mercado x nota | 0,10 | **0,08** | 0,05 | 0,04 |
| Idade x nota | 0,03 | **0,06** | 0,06 | 0,10 |
| Ordem dos jogadores (Spearman com o principal) | 0,99 | **1** | 0,99 | 0,98 |
| Eficientes do principal que continuam | 101 de 102 | **—** | 87 de 89 | 79 de 82 |

As conclusões se mantêm. O percentual de eficientes sobe com cortes mais altos porque os grupos ficam menores (o menor passa de 55 para 31 jogadores em 1.500 minutos). Da lista de oportunidades, só Jandrei e Wallace deixam de ser eficientes, a partir de 1.200 minutos. Com esses cortes mais altos, os pontas ficam abaixo do tamanho mínimo usual para o DEA (três jogadores por variável): a ponta esquerda em 1.200 minutos e as duas em 1.500.

## Limitações

- **Eficiente não é o mesmo que melhor.** A nota compara a produção com minutos, clube e, no ataque, qualidade das chances, só entre jogadores do mesmo grupo.
- **Competições misturadas.** Gols na Série B ou nas fases iniciais das copas contam como os da Série A.
- **Valores extremos pesam.** Um jogador muito acima dos demais em uma variável vira referência de quase todo o grupo.
- **Grupos de tamanhos diferentes** (55 a 147) não têm percentuais diretamente comparáveis.

## Como rodar

```bash
pip install -r requirements.txt
```

Os scripts rodam nesta pasta e esperam uma base em `../../dados-fotmob`, que não é distribuída. Sem ela, o código serve como documentação do método.

| Script | O que faz |
| --- | --- |
| `01_base_analise.py` | Uma linha por jogador, com posição, lado e estatísticas somadas |
| `02_correlacao.py` | Cortes de variáveis redundantes por posição |
| `03_rodar_dea.py` | Os seis métodos; aceita as variantes `log`, `valor` e `sem` |
| `04_analises.py` | Métodos, xG, hipóteses, clubes e oportunidades |
| `05_graficos.py` | Gráficos deste README |
| `06_sensibilidade_minutos.py` | Repete o modelo com outros cortes de minutos |
| `07_explicacao.py` | Quanto cada um passa da fronteira, critério decisivo e árvores de decisão |

Os modelos estão em [dea.py](dea.py) e os pesos em [ahp.py](ahp.py) e [ahp_respostas.json](ahp_respostas.json).

# MEM-GA

*Leia em: [English](README.en.md)*

Monta um time de futebol a partir das estatísticas dos jogadores, combinando o Método de Escolha Múltipla (MEM) com um algoritmo genético. A pessoa escolhe a formação tática, e o programa procura os jogadores que se complementam melhor.

O projeto nasceu na minha dissertação de mestrado e usa dados do Campeonato Brasileiro de 2017, com 317 jogadores de linha e 26 goleiros.

![Times por formação](images/times.png)

A [análise completa](analise.ipynb) mostra os times de cada formação e por que o time mais complementar não é o dos 10 jogadores mais fortes.

## O método

1. **Prepara os dados.** Entram os jogadores com pelo menos 850 minutos, cerca de 25% do campeonato. Cada estatística é convertida para valor por 90 minutos e vira 0 ou 1 com um corte que deixa cerca de 20% dos jogadores acima dele. Nos critérios de custo, como faltas e cartões, a escala é invertida, então 1 sempre é o melhor desempenho.
2. **Define a complementaridade.** Uma matriz diz o quanto cada par de critérios se complementa, de 0 a 1.
3. **Monta as combinações.** O método gera todas as combinações de 10 dos 18 critérios, 43.758 no total.
4. **Calcula o valor do time em cada combinação.** O valor é o desempenho médio dos jogadores naqueles critérios, multiplicado pelo peso e pela complementaridade média da combinação.
5. **Calcula a nota do time.** A nota é a fração das combinações em que o valor alcança o tau, o corte do grupo.
6. **Procura o melhor time.** O algoritmo genético sorteia 60 times e repete 10.000 iterações:
   - Cruza dois times e sorteia um novo entre os jogadores deles, respeitando as quotas da formação.
   - Coloca o novo time na população e retira o pior.
   - Depois de 14 iterações sem melhora, tenta até 7 mutações, trocando um jogador do melhor time por outro da mesma posição.
7. **Escolhe o goleiro.** Como as estatísticas dele são outras, o goleiro fica fora das combinações. O escolhido é o de maior aproveitamento: defesas divididas pela soma de defesas e gols sofridos.

Em caso de empate na nota, vence o time com maior valor médio. Isso dá uma direção ao algoritmo no início, quando quase todo time sorteado tem nota zero.

Como a nota é calculada para o grupo, um time com pontos fracos falha em toda combinação que inclui esses pontos. Um jogador vale mais quando cobre o que falta aos outros, e não só pelo que faz sozinho.

O tau padrão é 0,36. Até cerca de 0,30, o melhor time alcança todas as combinações, e a nota deixa de diferenciar os times.

## Como rodar

Na pasta `mem-ga`, instale as dependências:

```bash
pip install -r requirements.txt
```

Depois, execute:

```bash
python mem_ga.py
```

O programa pergunta a formação. Aceita um atalho, uma formação montada por você ou nada, para o time livre:

```text
Qual formação você quer? 4-3-3
Qual formação você quer? zag=3,le=1,ld=1,vol=3,mei=1,ata=1
```

Os atalhos ficam em `PRESETS`, no arquivo `mem_ga.py`:

| Formação | ZAG | LE | LD | VOL | MEI | ATA |
| --- | --- | --- | --- | --- | --- | --- |
| 4-4-2 | 2 | 1 | 1 | 2 | 2 | 2 |
| 4-3-3 | 2 | 1 | 1 | 1 | 2 | 3 |
| 4-2-3-1 | 2 | 1 | 1 | 2 | 3 | 1 |
| 3-5-2 | 3 | 1 | 1 | 2 | 1 | 2 |

A formação define os 10 jogadores de linha, e o goleiro é escolhido à parte.

Durante a execução, uma barra mostra a iteração atual e a melhor nota. No fim, o resultado aparece em formato de escalação, seguido da lista com a posição de cada jogador e quantos critérios ele atingiu:

```text
+---------------------------------[     ]----------------------------------+
|                                                                          |
|                  Luan (GRE)                  Dudu (PAL)                  |
|                                                                          |
|           Hernanes (SAO)           Giorgian de Arrascaeta (CRU)          |
|                                                                          |
|------------------------------------o-------------------------------------|
|                                                                          |
|                 Juninho (BAH)                Michel (GRE)                |
|                                                                          |
|  Thiago Carleto (CTB)  Réver (FLA)  Reginaldo (FLU)  Nino Paraíba (PON)  |
|                                                                          |
|                              Vanderlei (SAN)                             |
|                                                                          |
+---------------------------------[     ]----------------------------------+
```

Cada execução leva cerca de 5 segundos. Para pular a pergunta e repetir um resultado, use `--formation` e `--seed`. Para mudar o corte do grupo, use `--tau`, e para mudar o mínimo de minutos, use `--min-minutes`. As demais opções aparecem em `python mem_ga.py --help`.

Para rodar os testes:

```bash
python -m pytest
```

## Formato dos dados

O programa lê os arquivos CSV em UTF-8 da pasta `data/`. Para usar outros dados, crie uma pasta com os mesmos arquivos e rode `python mem_ga.py --data minha_pasta`.

### `players.csv`

Uma linha por jogador.

| Coluna | Conteúdo |
| --- | --- |
| `player` | Nome do jogador |
| `team` | Sigla do clube, mostrada entre parênteses ao lado do nome |
| `position` | Código da posição, usado nas quotas da formação |
| `minutes` | Minutos jogados na temporada |
| uma coluna por critério | Total da temporada, com o mesmo nome usado em `criteria.csv`. O programa converte para valor por 90 minutos |

```csv
player,team,position,minutes,Tackles,Interception,...
Alecsandro,CTB,ATA,827,15,5,...
```

### `criteria.csv`

Uma linha por critério.

| Coluna | Conteúdo |
| --- | --- |
| `criterion` | Nome do critério |
| `direction` | `1` quando mais é melhor e `0` quando mais é pior |
| `weight` | Peso do critério |
| `cut` | Corte sobre o valor por 90 minutos. Valores iguais ou maiores viram 1. Em branco, o critério é apenas normalizado entre 0 e 1 |

```csv
criterion,direction,weight,cut
Tackles,1,1,2.266
Fouls,0,1,2.019
```

### `matrix_c.csv`

Matriz quadrada com a complementaridade entre os critérios, com os mesmos nomes nas linhas e nas colunas. Só os valores acima da diagonal são usados; a diagonal e a parte de baixo podem ficar em branco.

```csv
criterion,Tackles,Interception,Fouled
Tackles,,0.15,0.19
Interception,,,0.55
Fouled,,,
```

### `goalkeepers.csv`

Arquivo opcional, com uma linha por goleiro. Sem ele, o time sai só com os jogadores de linha.

| Coluna | Conteúdo |
| --- | --- |
| `player` | Nome do goleiro |
| `team` | Sigla do clube |
| `minutes` | Minutos jogados na temporada |
| `saves` | Defesas |
| `goals_conceded` | Gols sofridos |

```csv
player,team,minutes,saves,goals_conceded
Aranha,PON,3330,123,51
```

### Regras

- A formação precisa somar o tamanho do time, definido por `--team-size`, que por padrão é 10.
- O tamanho do time também define quantos critérios entram em cada combinação. Por isso, ele precisa estar entre 2 e o número de critérios.
- Com outros códigos de posição, os atalhos e o campinho deixam de valer. Basta escrever a formação no formato `posição=quantidade`, e o resultado sai só em lista.
- Com outros dados, os cortes e o tau precisam ser calibrados de novo.

## Resultados

Melhor nota com os dados de 2017, usando o tau de 0,36. Nas 30 execuções de cada formação, com sementes diferentes, o algoritmo chegou sempre à mesma nota:

| Formação | Nota |
| --- | --- |
| Livre | 0,8997 |
| 4-3-3 | 0,8654 |
| 4-4-2 | 0,8619 |
| 4-2-3-1 | 0,8382 |
| 3-5-2 | 0,8165 |

A repetição indica um resultado estável, mas não prova que seja o máximo. Para comparar, os 10 jogadores que atingem mais critérios individualmente têm nota 0,8567, abaixo do time livre.

## Fontes

As estatísticas dos jogadores foram coletadas manualmente do [WhoScored](https://www.whoscored.com/) em 2017, com autorização do site para uso na pesquisa.

O projeto parte da dissertação *MEM-GA: Método de Escolha Múltipla com Algoritmo Genético aplicado à formação de equipes de futebol*, de Sérgio Augusto Faria Salles, no Instituto Federal Fluminense (2018). O MEM foi proposto por da Hora e Costa (2015).

## Limitações

O time só considera a temporada de 2017, e o goleiro é escolhido por uma regra simples, fora da análise de complementação. A nota depende do tau escolhido, e os cortes transformam as estatísticas em 0 ou 1, o que descarta a diferença entre jogadores do mesmo lado do corte.

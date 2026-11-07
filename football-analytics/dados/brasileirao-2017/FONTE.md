# Brasileirão 2017

*English: see [FONTE.en.md](FONTE.en.md).*

Estatísticas da temporada de 2017 do Campeonato Brasileiro, coletadas manualmente do [WhoScored](https://www.whoscored.com/) em 2017, com autorização do site para uso na pesquisa da dissertação. Ao usar estes dados, cite o WhoScored como fonte.

São 4 arquivos: `players.csv` (jogadores de linha), `criteria.csv` (os 18 critérios), `goalkeepers.csv` e `clubs.csv`. Os programas usam os jogadores com pelo menos 850 minutos: 317 jogadores de linha e 25 goleiros.

Os dois programas leem os arquivos CSV em UTF-8 desta pasta. Para usar outros dados, crie uma pasta ao lado, em `dados/`, com os mesmos arquivos e rode, por exemplo, `python -m escalacao --data dados/minha_pasta`.

## `players.csv`

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

## `criteria.csv`

Uma linha por critério.

| Coluna | Conteúdo |
| --- | --- |
| `criterion` | Nome do critério |
| `direction` | `1` quando mais é melhor e `0` quando mais é pior |
| `weight` | Peso base do critério, aplicado junto com o peso da posição. Use 1 para deixar só o peso da posição |

```csv
criterion,direction,weight
Tackles,1,1
Fouls,0,1
```

## `goalkeepers.csv`

Arquivo opcional, com uma linha por goleiro. Sem ele, o time sai só com os jogadores de linha.

| Coluna | Conteúdo |
| --- | --- |
| `player` | Nome do goleiro |
| `team` | Sigla do clube |
| `minutes` | Minutos jogados na temporada |
| `saves` | Defesas |
| `goals_conceded` | Gols sofridos |
| `long_passes_accurate` | Passes longos certos |
| `long_passes_inaccurate` | Passes longos errados |
| `clearances` | Bolas afastadas |

```csv
player,team,minutes,saves,goals_conceded,long_passes_accurate,long_passes_inaccurate,clearances
Aranha,PON,3330,123,51,187,384,58
```

## `clubs.csv`

Arquivo opcional, usado pelo GA-MEM para mostrar o nome dos clubes. Sem ele, a lista mostra só as siglas.

```csv
code,name
SAN,Santos
```

## Regras

- A formação precisa somar o tamanho do time, definido por `--team-size`, que por padrão é 10.
- Com outros códigos de posição, os atalhos e o campinho deixam de valer. Basta escrever a formação no formato `posição=quantidade`, e o resultado sai só em lista.
- Com outros dados, o tau precisa ser calibrado de novo.

# Exemplo grande: equipe de 4 entre 300 candidatos

*English: see the [main README](../../README.en.md#large-example-a-team-of-4-out-of-300-candidates).*

Uma equipe de projeto com 2 analistas, 1 engenheiro e 1 gestor, escolhida entre 300 candidatos fictícios com notas em 8 critérios. Testar todas as equipes seria inviável, então a busca é feita pelo algoritmo genético, com as duas regras.

## Como rodar

Com o pacote instalado (veja o [README principal](../../README.md#instalação)):

```bash
python exemplo.py
python exemplo.py --seed 1 --radar radar.png --no-plot
```

`--seed` muda a semente do algoritmo genético, `--iterations` a quantidade de iterações e `--data` a pasta dos dados. A execução leva cerca de 20 segundos.

## Os dados

`gerar_dados.py` gera os dois arquivos de `data/` com semente fixa (2026), então rodar de novo dá os mesmos arquivos:

```bash
python gerar_dados.py
```

- 150 analistas, 90 engenheiros e 60 gestores.
- 8 critérios, de 0 a 10, todos em que mais é melhor e com peso 1: `sql`, `estatistica`, `visualizacao`, `programacao`, `comunicacao`, `lideranca`, `negociacao` e `organizacao`.
- Cada cargo tem um perfil próprio: analistas mais fortes em dados, engenheiros em programação, gestores em liderança e negociação.
- Os critérios andam juntos ou em sentidos opostos. Os técnicos sobem juntos, e vão no sentido oposto ao da negociação e da liderança. Cada cargo tem a própria matriz de correlação.

Não há `complementarity.csv`: a complementação é calculada dos dados, como 1 menos a correlação em módulo, dentro de cada cargo. E cada cargo pesa mais os critérios em que se destaca.

## O tau

Com o tau baixo demais, toda equipe passa em todos os grupos de critérios e a nota não separa ninguém; alto demais, ninguém passa. Para cada regra, testamos o tau de 0,01 a 1,00, de 0,01 em 0,01, e ficamos com o valor em que a escolha tradicional chega mais perto de 50% dos grupos: 0,63 na regra `media` e 0,54 na `minimo`. Assim sobra espaço para a busca mostrar se acha uma equipe melhor.

O resultado e a comparação das três equipes estão no [README principal](../../README.md#exemplo-grande-equipe-de-4-entre-300-candidatos).

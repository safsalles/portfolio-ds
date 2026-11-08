# Exemplo pequeno: 2 de 8 candidatos

*English: see the [main README](../../README.en.md#small-example-2-of-8-candidates).*

O MEM como a tese de da Hora descreve: a busca testa todas as combinações e mostra a ordem completa. Os dados são fictícios e pequenos, para dar para acompanhar a conta, e seguem a ideia do problema de recrutamento da tese: escolher 2 de 8 candidatos, com notas em 6 critérios.

## Como rodar

Com o pacote instalado (veja o [README principal](../../README.md#instalação)):

```bash
python exemplo.py
python exemplo.py --regra minimo
python exemplo.py --choices 3 --tau 0.24 --top 5
python exemplo.py --radar radar.png --no-plot
```

`--choices` muda a quantidade de escolhas, `--tau` o corte, `--top` o tamanho da lista e `--data` a pasta dos dados. No final, o gráfico de radar abre em outra janela. `--radar` salva o gráfico num arquivo e `--no-plot` não abre a janela.

## A conta, passo a passo

Os números das equações são os da tese. Com a regra `media`:

1. **Normaliza a matriz de pagamentos (Equação 3.1).** Cada critério vai para a faixa de 0 a 1. Em `Faltas`, menos é melhor, então o sentido se inverte.
2. **Forma os conjuntos (Equações 3.2 e 3.3).** As alternativas e os critérios são combinados `n` a `n`, em que `n` é a quantidade de escolhas. Com 8 alternativas, 6 critérios e `n` igual a 2, são 28 conjuntos e 15 grupos de critérios, ou 420 avaliações.
3. **Calcula a matriz B' (Equações 3.4 e 3.5).** Cada avaliação é a média das notas do conjunto nos critérios do grupo, vezes a média dos pesos, vezes a complementação média entre esses critérios.
4. **Aplica o tau de corte (Equação 3.8)** e **ordena os conjuntos (Equação 3.9)** pela fração dos grupos que alcançam o tau. Empates ficam na mesma posição.

O tau padrão é 0,24. Ele usa a regra da tese: um desempenho de 50%, vezes a média dos pesos (0,75), vezes a média da complementação (0,647), dá 0,243.

## Dados

Em `data/`: `alternatives.csv` (as notas), `criteria.csv` (direção e peso de cada critério) e `complementarity.csv` (a matriz C, informada à mão, como na tese).

O resultado e a comparação entre as duas regras estão no [README principal](../../README.md#exemplo-pequeno-2-de-8-candidatos).

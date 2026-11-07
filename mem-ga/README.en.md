# mem-ga

*Read in: [Português](README.md)*

The Multiple Choice Method (MEM, from the Portuguese *Método de Escolha Múltipla*) picks a set of alternatives that complement each other, instead of taking the best ones one by one. It fits any choice where the group matters more than each part: teams, portfolios, committees.

This repository packages the method as a Python package, `mem`, with:

- two scoring rules: the one from the thesis that proposed the MEM (`media`, mean) and the adaptation from my master's dissertation (`minimo`, minimum), with the same interface;
- two searches: trying every combination, for small problems, and a genetic algorithm (MEM-GA), for large ones;
- quotas per group (for example, 2 analysts and 1 manager), complementarity and weights computed from the data, and a radar chart.

Two fictional hiring examples show how to use it: a small one, to follow the math, and a large one, with 300 candidates. The football application, with data from the 2017 Brazilian league, lives in the [football-analytics](https://github.com/safsalles/football-analytics) repository.

The code is in English; messages, comments, column names and example data are in Portuguese.

## Installation

```bash
pip install git+https://github.com/safsalles/mem-ga@v1.0
```

To work on the code and run the tests, clone the repository and, inside it:

```bash
pip install -e ".[test]"
python -m pytest
```

## Usage

With the repository cloned, from its folder (the example data does not come with `pip install`):

```python
from mem.busca import run_ga
from mem.problema import load_problem
from mem.regras import build_rule

problem = load_problem("exemplos/recrutamento-grande/data")
rule = build_rule(problem, "minimo", tau=0.54)
vagas = {"analista": 2, "engenheiro": 1, "gestor": 1}
result = run_ga(rule, problem.groups, vagas, size=4, seed=2026)
print(sorted(problem.alternatives[i] for i in result.team), result.score)
# ['P007', 'P038', 'P192', 'P276'] 0.6785714285714286
```

| Module | What it does |
| --- | --- |
| `mem.problema` | `Problem` (alternatives, criteria, direction, weights, groups), `load_problem` to read the CSVs, and `normalize` |
| `mem.pesos` | Complementarity computed from the data (1 − \|r\|, as in CRITIC, within each group) and per-group weights |
| `mem.regras` | The two rules, `mean_rule` and `minimum_rule`, and `build_rule` to build either from a `Problem` |
| `mem.busca` | `exhaustive` (every combination), `run_ga` (genetic algorithm) and `traditional_choice` (the best of each group, for comparison) |
| `mem.radar` | Radar chart with one panel per set |

## The method

1. **Normalize the ratings.** Each criterion goes to the 0 to 1 range, with 1 for the best rating. Where less is better, the scale is flipped.
2. **Rate the set on groups of criteria.** For each group of criteria, combine the set's performance, the weights and the complementarity between those criteria into one value.
3. **Apply the tau cutoff.** A group of criteria counts as 1 if its value reaches tau, and 0 otherwise. This cutoff keeps a very high result from paying for a low one elsewhere: the method is non-compensatory.
4. **Score.** The score is the share of groups of criteria that reach tau.

With groups of alternatives (roles, positions), complementarity is computed within each group, and each group weighs more the criteria it stands out in.

## The two rules

Both take a set and return `(score, tie_break)`, so any search works with any rule.

| | `media` (thesis) | `minimo` (adaptation) |
| --- | --- | --- |
| Criteria | Combined n at a time, n = set size | Combined in pairs |
| Within the group of criteria | Mean performance (Equation 3.4 of the thesis) | Minimum performance |
| Score | Share of groups of criteria reaching tau | Share of pairs reaching tau |
| Tie-break | Mean of `min(value, tau)` over the groups | Mean of `min(value, tau)` over the pairs |

**Why the adaptation.** In the thesis, criteria are combined as many at a time as alternatives chosen. In a large set, such as 10 of 18 criteria, each combination ends up close to the set's overall mean, and differences between sets fade. With criteria in pairs, each pair still shows what the set has and what it lacks. And with the minimum instead of the mean, a strong criterion does not cover a weak one within the pair, so the method stays non-compensatory there too.

**The tie-break of the `media` rule is new.** In the thesis it only ran by trying every combination, and ties shared a position. The genetic algorithm needs a tie-break to have a direction among sets with the same score, so the `media` rule uses the same tie-break as `minimo`: how far, on average, the groups are from reaching tau.

**Limit of the `media` rule.** The number of groups of criteria is C(criteria, n). With 18 criteria and a set of 10, that is 43,758 groups per evaluation, too slow for the genetic algorithm. Above 10,000 groups (`MAX_MEAN_GROUPS`), the rule refuses the problem with a message stating the numbers and suggesting the `minimo` rule. Trying every combination has a limit too: above 20 million evaluations, the exhaustive search refuses the problem.

## Small example: 2 of 8 candidates

```bash
python exemplos/recrutamento-pequeno/exemplo.py
python exemplos/recrutamento-pequeno/exemplo.py --regra minimo
```

There are 8 candidates rated on 6 criteria, and the search tries all 28 pairs. Candidates A1 and A2 have the best averages, but they are alike: strong in planning, logistics and quality, and average in costs and people. A3 is the opposite.

| Rank | Weighted mean | MEM, `media` rule | % of groups | MEM, `minimo` rule | % of pairs |
| --- | --- | --- | --- | --- | --- |
| 1st | A1 | A1, A3 | 66.7% | A1, A3 | 46.7% |
| 1st | | A2, A3 | 66.7% | A2, A3 | 46.7% |
| 3rd | A2 | A1, A2 | 60.0% | A1, A2 | 33.3% |

The traditional choice takes A1 and A2, the top two by weighted mean. Under both rules that pair ranks 3rd, and the best pairs join one of them with A3, who covers what is missing. With tau 0.24 both rules agree at the top. The `minimo` rule gives lower scores, because each pair is worth its weaker criterion.

In the radar chart, each colored line is a candidate and the gray area is the pair's mean. On the left, A1 and A2 nearly overlap. On the right, A1 and A3 complement each other.

![Radar of the pairs A1, A2 and A1, A3](images/radar_pequeno.png)

The result depends on tau. With the `media` rule and tau of 0.27 or more, the cutoff is high enough that only the very high ratings of A1 and A2 pass, and that pair moves back to 1st place. That is why the program shows what changes with tau slightly above and below. More in [exemplos/recrutamento-pequeno](exemplos/recrutamento-pequeno/).

## Large example: a team of 4 out of 300 candidates

```bash
python exemplos/recrutamento-grande/exemplo.py
```

There are 300 fictional candidates (150 analysts, 90 engineers and 60 managers) rated on 8 criteria, for a team of 2 analysts, 1 engineer and 1 manager. That is over 60 million possible teams, so the search uses the genetic algorithm. A run takes about 20 seconds.

| Team | People | `media` score | `minimo` score |
| --- | --- | --- | --- |
| `media` rule | P050, P110 (analysts), P218 (engineer), P276 (manager) | **50.0%** | 32.1% |
| `minimo` rule | P007, P038 (analysts), P192 (engineer), P276 (manager) | 24.3% | **67.9%** |
| Traditional choice | P038, P110 (analysts), P218 (engineer), P276 (manager) | 48.6% | 53.6% |

The traditional choice takes the strongest people in each role. Each rule finds a team that beats it on its own score, and the two rules pick different teams: `media` swaps one analyst and stays close to the traditional team, while `minimo` swaps one analyst and the engineer. The `minimo` team loses a little in data and programming and gains in communication, negotiation and organization: it is more balanced, because each pair of criteria is worth the weaker of the two. The manager is the same in all three.

![Radar of the three teams](images/radar_grande.png)

Each rule's tau was chosen so the score does not saturate: with tau too low, every team passes everything; too high, no one passes. Trying 0.01 to 1.00, we kept the value where the traditional choice comes closest to 50% (0.63 for `media` and 0.54 for `minimo`). More, including how the data was generated, in [exemplos/recrutamento-grande](exemplos/recrutamento-grande/).

## Data format

`load_problem` reads a folder with these files:

- `criteria.csv`: `criterion`, `direction` (1 when more is better and 0 when more is worse) and `weight`.
- `alternatives.csv`: the `alternative` column, one column per criterion and, if there are quotas per group, the `group` column.
- `complementarity.csv` (optional): the complementarity matrix between criteria, with an empty diagonal. Without it, complementarity is computed from the data.

## Check against the thesis

The `media` rule, with exhaustive search, was checked against the thesis's numerical application, whose data is not in this repository. For a choice of 2 with tau 0.20, all 45 pairs in Table 3.9 matched. With tau 0.19 and 0.21, 44 of 45 matched in Tables 3.10 and 3.11, and the differing pair (A1, A8) has one group of criteria more or less. For a choice of 3, the 40 legible sets in Table 3.15 matched. The tests store the small example's ranking so it cannot change silently.

## Source

The MEM was proposed in the doctoral thesis *Método de Escolha Múltipla: uma proposta multicritério para seleção em conjunto de mais de uma alternativa*, by Henrique Rego Monteiro da Hora (Universidade Federal Fluminense, 2013). The `minimo` rule and the genetic algorithm come from the master's dissertation *MEM-GA: Método de Escolha Múltipla com Algoritmo Genético aplicado à formação de equipes de futebol*, by Sérgio Augusto Faria Salles (Instituto Federal Fluminense, 2018), written in MATLAB and ported here to Python.

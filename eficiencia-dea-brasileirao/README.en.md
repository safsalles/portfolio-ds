# Player efficiency in the 2026 Brazilian Championship (DEA)

*Read in: [Português](README.md)*

Who delivers more than their minutes on the pitch and the size of their club would suggest? This project measures the efficiency of players from the 2026 Brazilian first (Série A) and second (Série B) divisions, by position, using Data Envelopment Analysis (DEA).

It revisits a 2018 paper of mine that applied DEA to seven European leagues ([Salles et al., 2018](https://doi.org/10.4322/PODes.2018.002), in Portuguese), now with Brazilian data, more methods and weights that reflect the role of each position. The charts are labelled in Portuguese.

![Efficient players by position](figuras/eficientes_por_posicao.png)

## Main results

Data collected on 22 November 2026, with the season still in progress.

- **13.8% of players are efficient** (102 of 739) in the main model. Without weight restrictions, as in 2018, it would be 52.5% (49% in the paper).
- **Clubs that earn more points have players with higher scores.** The correlation between a club's mean score and its points per match is 0.46 (0.64 in Série A and 0.35 in Série B). In 2018 the number of efficient players per club was unrelated to points (-0.06); here the correlation is 0.32.
- **Market value says little about efficiency** (r = 0.08), as in 2018.
- **Neither does age** (r = 0.06), as in 2018.

![Clubs](figuras/clubes_nota_pontos.png)

## Data

Match-level statistics from [FotMob](https://www.fotmob.com/) for five 2026 competitions: Série A, Série B, Copa do Brasil, Copa Libertadores and Copa Sudamericana. Only players from the 40 Série A and B clubs are included.

- **Sample:** as in the paper, the half with the most minutes (899 or more). That is 739 of 1,477 players.
- **Ten groups:** goalkeeper, centre-back, full-back, defensive/central midfielder, attacking midfielder, winger and striker, with centre-backs, full-backs and wingers split into right and left. A centre-back's side comes from the lineup positions; in case of a tie, from the preferred foot.
- **The data are not in the repository.** [FotMob's terms of use](https://www.fotmob.com/tos.txt) forbid automated collection and redistribution without written consent, so neither the data nor the collection scripts are published.

32 matches (31 from Copa do Brasil and 1 from Libertadores) have no player statistics at the source.

## Model

**Inputs (less is better):** minutes played and the market value of the club's squad, on a log scale. Strikers, wingers and attacking midfielders have a third one: xG + xA, the quality of their chances to score and to assist.

**Outputs (more is better):** chosen by position, as season totals. Within each position, variables highly correlated with others (|r| ≥ 0.60) were removed, always keeping goals, assists and big chances created. Negative actions (fouls, possession lost, times dribbled past and so on) form a single error index. The lists are in [criterios.py](criterios.py) and the removals in [cortes.json](cortes.json).

**Weights.** In classic DEA each player picks the weights that favour them most, so being the best in one variable is enough to look efficient. The main model is therefore a CCR model with virtual weight restrictions ([Wong and Beasley, 1990](https://doi.org/10.1057/jors.1990.120)): each category accounts for a fixed share of the score, and the model chooses how to split it inside the category. The shares come from an AHP with incomplete pairwise comparisons ([Harker, 1987](https://doi.org/10.1016/0270-0255(87)90503-3)), which I answered:

| Position | Category weights |
| --- | --- |
| Striker | goals 64%, assists 13%, creation 9%, defence 7%, errors 7% |
| Winger | goals 60%, assists 12%, creation 12%, defence 9%, errors 7% |
| Attacking midfielder | goals 36%, assists 36%, creation 18%, defence 7%, errors 4% |
| Defensive/central midfielder | defence 35%, errors 35%, passing 18%, assists 12% |
| Full-back | defence 30%, attacking support 30%, errors 30%, assists 10% |
| Centre-back | ground defending 24%, box defending 24%, aerial duels 24%, errors 24%, build-up 6% |
| Goalkeeper | saves 82%, command of the area 9%, passing 9% |

These are my own judgements, from a single respondent, and since each position uses one answer per category there is no consistency test. I saw the first results before settling the weights and changed two things afterwards: the weight of assists for defensive midfielders and full-backs, and moving the midfielders' aerial duels into defence.

**Method comparison:** unrestricted CCR, BCC, super-efficiency ([Andersen and Petersen, 1993](https://doi.org/10.1287/mnsc.39.10.1261)), cross-efficiency and TOPSIS. Mean Spearman correlation between rankings:

| | main | CCR | BCC | super | cross | TOPSIS |
| --- | --- | --- | --- | --- | --- | --- |
| main | 1 | 0.61 | 0.39 | 0.70 | 0.72 | 0.59 |
| CCR | | 1 | 0.61 | 0.86 | 0.68 | 0.58 |
| BCC | | | 1 | 0.57 | 0.45 | 0.41 |
| super-efficiency | | | | 1 | 0.77 | 0.68 |
| cross-efficiency | | | | | 1 | 0.69 |
| TOPSIS | | | | | | 1 |

## How much the choices change the result

Share of efficient players:

| Club value as input | Exact weights | At least half of each weight | Unrestricted CCR | Série A / B (exact weights) |
| --- | --- | --- | --- | --- |
| **Log (main)** | **13.8%** | 37.9% | 52.5% | 15% / 12% |
| Raw value | 15.7% | 43.8% | 56.0% | 11% / 21% |
| No club value | 7.2% | 27.2% | 41.7% | 9% / 6% |

The comparison between divisions flips with this choice. With the raw value, which ranges from 3 to 225 million euros, the model expects very little from the cheaper clubs and favours Série B.

## Minutes cut-off

The paper keeps the half with the most minutes. Running the main model again with other minimums:

| Minimum minutes | 600 | **899 (main)** | 1,200 | 1,500 |
| --- | --- | --- | --- | --- |
| Players | 892 | **739** | 599 | 485 |
| Efficient | 13.1% | **13.8%** | 15.5% | 18.4% |
| Série A / B efficient | 15% / 11% | **15% / 12%** | 18% / 13% | 21% / 15% |
| Club score vs. points per match | 0.56 | **0.46** | 0.46 | 0.45 |
| Market value vs. score | 0.10 | **0.08** | 0.05 | 0.04 |
| Age vs. score | 0.03 | **0.06** | 0.06 | 0.10 |
| Player order (Spearman with main) | 0.99 | **1** | 0.99 | 0.98 |
| Main-model efficient players kept | 101 of 102 | **—** | 87 of 89 | 79 of 82 |

The conclusions hold. The share of efficient players rises with higher cut-offs because the groups get smaller (the smallest goes from 55 to 31 players at 1,500 minutes). In the shortlist below, only Jandrei and Wallace stop being efficient, from 1,200 minutes on. At these higher cut-offs the winger groups fall below the usual minimum size for DEA (three players per variable): the left side at 1,200 minutes and both sides at 1,500.

## DEA against a single measure

![DEA and xG](figuras/dea_vs_xg.png)

For strikers and wingers the score closely follows goals minus xG (Spearman from 0.76 to 0.86). This is largely a consequence of the design: goals weigh more than 60% and xG is an input. For attacking midfielders, where assists weigh as much as goals, the correlation drops to 0.37.

## Efficient and low-priced

Efficient players with a market value below their group's median, up to three per position, ordered by cross-efficiency:

| Position | Players (club) |
| --- | --- |
| Goalkeeper | Jandrei (Juventude), Alex Alves (São Bernardo), Paulo Vítor (Atlético-GO) |
| Right-back | Tinga (Coritiba), Warley (Atlético-GO), Fágner (Cruzeiro) |
| Left-back | Gabriel Feliciano (Operário-PR), Jamerson (Vitória), Reinaldo (Mirassol) |
| Right centre-back | César (Criciúma), Junior Barreto (Atlético-GO), Rodrigo (Criciúma) |
| Left centre-back | Lyncon (CRB), Luizão (Ceará), Wallace (Botafogo-SP) |
| Defensive/central midfielder | Gabriel Pires (Juventude), Éverton Ribeiro (Bahia), Biel (Sport) |
| Attacking midfielder | Crystopher (CRB), Marrony (Atlético-GO), Everton Morelli (Botafogo-SP) |
| Right winger | Vinícius (Náutico) |
| Left winger | Bernard (Atlético-MG) |
| Striker | Martin Braithwaite (Grêmio) |

![Value and efficiency](figuras/valor_vs_eficiencia.png)

72 of the 739 players have no market value at the source and are left out of this chart and the list.

## Limitations

- **Efficient does not mean best.** The score compares output with minutes, club and, in attack, chance quality, only among players in the same group.
- **Mixed competitions.** Goals in Série B or in early cup rounds count the same as goals in Série A.
- **Extreme values matter.** A player far above everyone else in one variable becomes the benchmark for almost the whole group.
- **Groups of different sizes** (55 to 147) do not have directly comparable percentages.

## How to run

```bash
pip install -r requirements.txt
```

The scripts run from this folder and expect a dataset in `../../dados-fotmob`, which is not distributed. Without it, the code serves as documentation of the method.

| Script | What it does |
| --- | --- |
| `01_base_analise.py` | One row per player, with position, side and aggregated statistics |
| `02_correlacao.py` | Removes redundant variables by position |
| `03_rodar_dea.py` | The six methods; accepts the `log`, `valor` (raw) and `sem` (no club value) variants |
| `04_analises.py` | Methods, xG, hypotheses, clubs and shortlist |
| `05_graficos.py` | Charts in this README |
| `06_sensibilidade_minutos.py` | Runs the model again with other minute cut-offs |

The models are in [dea.py](dea.py) and the weights in [ahp.py](ahp.py) and [ahp_respostas.json](ahp_respostas.json).

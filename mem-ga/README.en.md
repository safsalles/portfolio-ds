# MEM-GA

*Read in: [Português](README.md)*

Builds a football team from player statistics by combining the Multiple Choice Method (MEM) with a genetic algorithm. You choose a tactical formation, and the program searches for the players who complement each other best.

The project began in my master's dissertation and uses data from the 2017 Brazilian Championship, with 317 outfield players with at least 850 minutes and 25 goalkeepers with 850 minutes or more.

![Teams by formation](images/times.png)

The [mem](../mem/README.en.md) folder holds the pure method, without a genetic algorithm, with a small fictional example. The project also includes [GA-MEM](#ga-mem), which suggests signings for a club. The [full analysis](analise.ipynb), in Portuguese, shows the team for each formation and why the most complementary team is not the 10 strongest players.

## The method

1. **Prepare the data.** Players with at least 850 minutes enter, about 25% of the championship. Each statistic is converted to a per-90-minutes value and normalized from 0 to 1, from the worst to the best player on that criterion. For cost criteria, such as fouls and cards, the scale is inverted, so 1 is always the best performance.
2. **Calculate complementarity between criteria.** It is 1 minus the absolute correlation between two criteria, calculated within each position. Criteria that move together, such as shots on target and goals, complement each other little.
3. **Calculate position weights.** Each criterion starts at 1 and gains as much as the position does it more than the others. Clearances weigh more for center-backs, and goals in the box for forwards.
4. **Build the criteria pairs.** The method generates every pair of the 18 criteria, 153 in total.
5. **Calculate the team's value in each pair.** First, it takes the team's average on each criterion, using each player's position weights. The pair's value is the lower of the two averages, multiplied by the average weight of the two criteria and by the complementarity between them.
6. **Calculate the team's score.** A pair passes when its value reaches tau, the group threshold. The score is the share of the 153 pairs that pass.
7. **Search for the best team.** The genetic algorithm draws 60 teams and repeats 15,000 iterations:
   - It crosses two teams and draws a new one from their players, respecting the formation's quotas.
   - It adds the new team to the population and removes the worst.
   - After 14 iterations without improvement, it runs a mutation round, with up to 7 attempts to swap a player on the best team for another in the same position.
   - Every 5 mutation rounds, it runs a strong mutation: it swaps 3 players at once and then climbs swap by swap, changing one player at a time while the score improves. This takes the search out of teams where no single swap improves the score.
8. **Choose the goalkeeper.** Goalkeepers have different statistics, so they stay out of the criteria pairs. They are judged on three criteria: save rate, long pass accuracy, and clearances per 90 minutes. The winner reaches the most criteria by ranking in the top 20% of each, with ties broken by save rate.

As a formula, for each pair of criteria `(j, j')`:

```text
mean(j)     = average, over the team's players, of performance on j x position weight on j
value(j,j') = minimum(mean(j), mean(j')) x (weight[j] + weight[j']) / 2 x complementarity[j, j']
pass(j,j')  = 1 if value(j,j') >= tau, otherwise 0
score       = sum of pass / 153
```

Here, `weight` is the criterion's base weight, in `criteria.csv`.

When scores tie, the team that gets closest to tau on the pairs that do not pass yet wins. The tiebreak is the average of the 153 values, with each value capped at tau. This gives the algorithm a direction, because the score only changes when a whole pair passes. Different teams can have the same score, and the program shows the best one by the tiebreak.

A pair only passes if the team is good on both criteria, so a strong criterion does not make up for a weak one. Below tau, reinforcing the pair's weak criterion helps, even if the reinforcement comes from someone who repeats what a teammate already does. Above tau, more of the same adds nothing. So a player's value depends on the team they join: they are worth more when covering what the others lack, not only for what they do alone.

The default tau is 0.24. With it, the median club's starters pass 0.458 of the pairs, and the best team found reaches 0.9739, so the score still separates teams. With other data, tau needs recalibrating, and the [results](#results) show what changes with it.

### Adaptations from the MEM thesis

MEM was proposed in da Hora's doctoral thesis (2013). From it come the normalized performance matrix, the complementarity between criteria, the weights, and the tau applied to the group (Equation 3.8), which makes the method non-compensatory. This project makes two adaptations:

- **Criteria two by two, instead of n by n.** Equation 3.3 and the code in Annex III combine criteria in the same number as the alternatives chosen, n by n, although step 5 of the method says "two by two". The two readings match when 2 alternatives are chosen. Here there are 10 players, and combining 10 of the 18 criteria keeps each combination close to the team's overall average, which erases the differences between teams. Two by two, each pair still shows what the team has and what it lacks.
- **Minimum, instead of average, within the pair.** Equation 3.4 uses the average, so a strong criterion makes up for a weak one within the pair. With the minimum, the pair's value depends on the weaker criterion, and the method stays non-compensatory within the pair too.

## How to run

From the `mem-ga` folder, install the dependencies:

```bash
pip install -r requirements.txt
```

Then run:

```bash
python mem_ga.py
```

The program asks for the formation. It accepts a shortcut, a formation you build yourself, or nothing, for a free team:

```text
Qual formação você quer? 4-3-3
Qual formação você quer? zag=3,le=1,ld=1,vol=3,mei=1,ata=1
```

The prompts and output are in Portuguese. The position codes are ZAG (center-back), LE (left-back), LD (right-back), VOL (defensive midfielder), MEI (attacking midfielder), and ATA (forward).

The shortcuts live in `PRESETS`, in `mem_ga.py`:

| Formation | ZAG | LE | LD | VOL | MEI | ATA |
| --- | --- | --- | --- | --- | --- | --- |
| 4-4-2 | 2 | 1 | 1 | 2 | 2 | 2 |
| 4-3-3 | 2 | 1 | 1 | 1 | 2 | 3 |
| 4-2-3-1 | 2 | 1 | 1 | 2 | 3 | 1 |
| 4-1-4-1 | 2 | 1 | 1 | 1 | 4 | 1 |
| 3-5-2 | 3 | 0 | 0 | 2 | 3 | 2 |
| 3-4-3 | 3 | 0 | 0 | 2 | 2 | 3 |
| 3-6-1 | 3 | 0 | 0 | 3 | 3 | 1 |
| 5-3-2 | 3 | 1 | 1 | 2 | 1 | 2 |
| 5-4-1 | 3 | 1 | 1 | 2 | 2 | 1 |

With three at the back, the team uses no full-backs. With five, it uses three center-backs and two full-backs. You can also type without hyphens, such as `4141`.

The formation sets the 10 outfield players, and the goalkeeper is chosen separately.

While it runs, a bar shows the current iteration and the best score. At the end, the result appears as a lineup, followed by a list with each player's position and the sum of their performance on the 18 criteria, from 0 to 18:

```text
+-------------------------------[     ]--------------------------------+
|                                                                      |
|              Dudu (PAL)              Túlio de Melo (CHA)             |
|                                                                      |
|             Hernanes (SAO)             Rómulo Otero (CAM)            |
|                                                                      |
|----------------------------------o-----------------------------------|
|                                                                      |
|          Lucas Marques (CHA)          Matheus Rossetto (CAP)         |
|                                                                      |
|  Thiago Carleto (CTB)  Paulo André (CAP)  Fred (VIT)  Rodinei (FLA)  |
|                                                                      |
|                             Cássio (COR)                             |
|                                                                      |
+-------------------------------[     ]--------------------------------+
```

Each run takes about 10 to 25 seconds for formations and about 40 seconds for the free team, on an idle machine. With other heavy processes running, it takes longer and can go past 60 seconds. To skip the question and repeat a result, use `--formation` and `--seed`. To change the group threshold, use `--tau`, and to change the minimum minutes, use `--min-minutes`. The other options are listed by `python mem_ga.py --help`.

At the end, the team's radar chart opens in a separate window, and the program ends when you close it. To save the chart to a file, use `--radar`, as in `python mem_ga.py --formation 4-4-2 --seed 1 --radar radar.png`. To skip the window, use `--no-plot`.

Raising `--iterations` to 20,000 or more can make a run much slower in some formations. The 4-1-4-1 reached 105 seconds with 20,000 iterations and 357 seconds with 30,000, in 10 parallel processes.

To run the tests:

```bash
python -m pytest
```

## Data format

The program reads UTF-8 CSV files from the `data/` folder. To use other data, create a folder with the same files and run `python mem_ga.py --data my_folder`.

### `players.csv`

One row per player.

| Column | Content |
| --- | --- |
| `player` | Player name |
| `team` | Club code, shown in parentheses next to the name |
| `position` | Position code, used by the formation quotas |
| `minutes` | Minutes played in the season |
| one column per criterion | Season total, with the same name used in `criteria.csv`. The program converts it to a per-90-minutes value |

```csv
player,team,position,minutes,Tackles,Interception,...
Alecsandro,CTB,ATA,827,15,5,...
```

### `criteria.csv`

One row per criterion.

| Column | Content |
| --- | --- |
| `criterion` | Criterion name |
| `direction` | `1` when more is better and `0` when more is worse |
| `weight` | Base criterion weight, applied together with the position weight. Use 1 to keep only the position weight |

```csv
criterion,direction,weight
Tackles,1,1
Fouls,0,1
```

### `goalkeepers.csv`

Optional file, with one row per goalkeeper. Without it, the team has only outfield players.

| Column | Content |
| --- | --- |
| `player` | Goalkeeper name |
| `team` | Club code |
| `minutes` | Minutes played in the season |
| `saves` | Saves |
| `goals_conceded` | Goals conceded |
| `long_passes_accurate` | Accurate long passes |
| `long_passes_inaccurate` | Inaccurate long passes |
| `clearances` | Clearances |

```csv
player,team,minutes,saves,goals_conceded,long_passes_accurate,long_passes_inaccurate,clearances
Aranha,PON,3330,123,51,187,384,58
```

### `clubs.csv`

Optional file, used by GA-MEM to show club names. Without it, the list shows only the codes.

```csv
code,name
SAN,Santos
```

### Rules

- The formation must add up to the team size, set by `--team-size`, which defaults to 10.
- With other position codes, the shortcuts and the lineup drawing no longer apply. Write the formation as `position=amount`, and the result appears only as a list.
- With other data, tau needs to be calibrated again.

## Results

Best known score with the 2017 data, using a tau of 0.24. Each formation ran 60 times, with different seeds, and the table counts how many runs reached that score. Seeds 0 to 29 were used to choose the search configuration. Seeds 30 to 59 only ran after that choice, so they are the honest check.

| Formation | Score | Pairs passed | Hits, seeds 0 to 29 | Hits, seeds 30 to 59 | Worst score |
| --- | --- | --- | --- | --- | --- |
| Free | 0.9739 | 149 of 153 | 30 of 30 | 30 of 30 | 0.9739 |
| 4-2-3-1 | 0.9673 | 148 of 153 | 30 of 30 | 30 of 30 | 0.9673 |
| 3-5-2 | 0.9673 | 148 of 153 | 28 of 30 | 29 of 30 | 0.9608 |
| 4-4-2 | 0.9608 | 147 of 153 | 30 of 30 | 30 of 30 | 0.9608 |
| 4-1-4-1 | 0.9608 | 147 of 153 | 30 of 30 | 30 of 30 | 0.9608 |
| 3-4-3 | 0.9477 | 145 of 153 | 30 of 30 | 30 of 30 | 0.9477 |
| 4-3-3 | 0.9412 | 144 of 153 | 29 of 30 | 30 of 30 | 0.9346 |
| 3-6-1 | 0.9346 | 143 of 153 | 30 of 30 | 30 of 30 | 0.9346 |
| 5-4-1 | 0.9216 | 141 of 153 | 30 of 30 | 29 of 30 | 0.9150 |
| 5-3-2 | 0.9085 | 139 of 153 | 27 of 30 | 28 of 30 | 0.8693 |

In total, the search reached the best known score in 294 of 300 runs on seeds 0 to 29, and in 296 of 300 on the new seeds. The largest drop is in the 5-3-2: the run that fails stops at 0.8693, against the best of 0.9085. This happened in 3 of 30 runs, and in 2 of 30 on the new seeds. So it is worth repeating the formation with other seeds.

The best known score is the highest found in these runs, in another 30 from a different search configuration, and in 200 swap-by-swap climbs from random teams. Those climbs, without the genetic algorithm, reached the same score in 8 of the 10 formations and fell short in the 4-3-3 and the 5-4-1. The global optimum was not proven, so a team with a higher score may exist.

### Traditional choice and group formation

To show what group formation changes, the MEM-GA team is compared with the traditional choice: rating each player alone and keeping the best ones. In that choice, each player gets a summed performance:

1. **Normalize each criterion.** Each of the 18 criteria goes from 0 to 1 across the 317 outfield players: the league's best on that criterion gets 1 and the worst gets 0. For criteria where less is better, such as fouls, cards, and lost balls, the scale flips, so 1 is still the best.
2. **Add up the 18 grades.** The sum has no weights and no position adjustment, and goes from 0 to 18. Hernanes, for example, sums 8.96.
3. **Fill the slots.** Each slot in the formation takes the players with the highest sum in that position. In the 4-4-2, that means the 2 best center-backs, the best full-back on each side, the 2 best defensive midfielders, the 2 best midfielders, and the 2 best forwards. In the free team, it is the 10 highest sums, regardless of position.

No step looks at what the other players already cover. Group formation does the opposite: a player's value depends on the rest of the team.

| Formation | Traditional choice | MEM-GA |
| --- | --- | --- |
| Free | 0.6863 | 0.9739 |
| 4-4-2 | 0.8039 | 0.9608 |

The radar chart shows this difference in the 4-4-2. Each axis is a criterion, and each line is the average of the team's 10 players, using the values the score uses, already adjusted by position. The orange line is the traditional choice, the blue area is MEM-GA, and the dashed line is the league average. The chart labels are in Portuguese, like the program's output.

![Radar chart of the MEM-GA team in the 4-4-2](images/radar_mem_ga.png)

The traditional choice has higher averages in tackles, passes, and assists, but stays low in goals from outside the box (0.12) and aerial duels (0.27). That happens because a high sum can hide a weak spot. Luan (GRE) sums 7.63 and gets a forward slot, but barely wins anything in the air (0.03). MEM-GA puts Túlio de Melo (CHA) in his place, with a lower sum of 6.71 and 0.92 in aerial duels. In the same way, it swaps Gustavo Scarpa (FLU), with 0.09 in goals from outside the box, for Rómulo Otero (CAM), with 1.22. The two teams share only 3 players.

As a result, MEM-GA gives up part of the peaks and raises the weak spots to 0.30 in goals from outside the box and 0.36 in aerial duels. Since the score looks at the weaker criterion of each pair, that is worth more than high numbers where the team is already good.

### Tau sensitivity

The table shows what changes between 0.22 and 0.26. Changes are the players who differ from the team at 0.24, and the club columns use the score of the starters of the 20 clubs.

| Tau | 4-4-2 score | 4-4-2 changes | Free score | Free changes | Median club | Worst club | Best club |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0.22 | 0.9869 | 4 | 0.9935 | 4 | 0.542 | 0.359 | 0.725 |
| 0.23 | 0.9804 | 4 | 0.9869 | 4 | 0.484 | 0.294 | 0.667 |
| 0.24 | 0.9608 | 0 | 0.9739 | 0 | 0.458 | 0.281 | 0.608 |
| 0.25 | 0.9346 | 1 | 0.9608 | 4 | 0.408 | 0.242 | 0.569 |
| 0.26 | 0.9085 | 1 | 0.9412 | 3 | 0.373 | 0.216 | 0.562 |

In this range, no score reaches 1 and the best team changes up to 4 of its 10 players. Values other than 0.24 are the best score from 10 seeds and 200 climbs, with no convergence measure. The search was calibrated only at 0.24, so those teams may not be the best for that tau. At 0.26, in the 4-4-2, only 5 of the 10 seeds reached 0.9085, and the others stayed at 0.8693.

## GA-MEM

GA-MEM is a variation that works the other way around: instead of building a team from scratch, it starts from a club and suggests the signings that most improve its complementarity.

```bash
python ga_mem.py
```

The program shows the list of clubs and asks three questions, in Portuguese:

1. **Club:** it accepts the list number, the name, or the code.
2. **Option:** choose the signing's position or let the method suggest any position.
3. **Amount:** how many options to show. Pressing Enter shows 5.

The result shows the score before and after the best option, the lineup with it, and the list of options, with the gain of each one. Each option is a single signing, not a package. If no option improves the team, the program says so, keeps the current team on the pitch, and lists the ones that hurt it least. Across the 20 clubs and 6 positions, this only happens with Vasco's right back. To skip the questions, use `--club`, `--position`, and `--options`.

**How the method decides:**

- The current team is the club's 10 outfield players with the most minutes, with at least one in each position. If the club has fewer than 10 outfield players with the minimum minutes, the program warns how many players the score used, and it is not comparable with the score of a 10-player team.
- Candidates are players from other clubs with at least 850 minutes.
- Swaps are always position by position: a forward only replaces a forward. Among the starters in that position, the one whose exit most improves the score leaves.
- The method tests every candidate, so the list is exact. With one signing at a time there are few cases, and the genetic algorithm is not needed here.
- The default tau is 0.24, the same as in MEM-GA.
- The goalkeeper shown is the one who played most for the club. They do not count toward the score.

Examples of the best option from any position:

| Club | Current score | With the signing | Leaves | Arrives |
| --- | --- | --- | --- | --- |
| Grêmio | 0.5686 | 0.6667 | Ramiro | Agustín Allione (BAH) |
| Santos | 0.6078 | 0.7582 | Ricardo Oliveira | Dudu (PAL) |
| Corinthians | 0.5163 | 0.6667 | Rodriguinho | Agustín Allione (BAH) |
| Vasco | 0.4444 | 0.5229 | Andrés Ríos | Túlio de Melo (CHA) |

The radar chart shows Vasco's signing. On the right, Túlio de Melo is much stronger than Andrés Ríos in goals inside the box and shots on target, and also in aerial duels, but falls behind in fouls suffered and dribbles. On the left, the team's average barely changes, because he is one player out of 10, but the gain falls on criteria where the team was weak, and that is enough to raise the score from 0.4444 to 0.5229.

![Radar chart of Vasco signing Túlio de Melo](images/radar_ga_mem.png)

At the end, the radar chart of the best option opens in a separate window. To save it, use `--radar` with the file name, as in `python ga_mem.py --club VAS --position ata --options 3 --radar radar.png`, and to skip the window, use `--no-plot`.

The best option changes from club to club, because a player's value depends on what the team already has. Across the 20 clubs, 14 different names appear, and the most repeated is Agustín Allione, at 3 clubs. The method ignores price and availability, so it is worth checking the other options on the list.

## Sources

The player statistics were collected manually from [WhoScored](https://www.whoscored.com/) in 2017, with the site's permission to use them in the research.

The position weights draw on the idea that indicators are nearly the same across positions, and what changes is the priority of each one (Hughes et al., 2012). Complementarity uses the conflict measure of the [CRITIC](https://doi.org/10.1016/0305-0548(94)00059-H) method (Diakoulaki, Mavrotas and Papayannakis, 1995).

The project builds on the dissertation *MEM-GA: Método de Escolha Múltipla com Algoritmo Genético aplicado à formação de equipes de futebol*, by Sérgio Augusto Faria Salles, at the Instituto Federal Fluminense (2018). MEM was proposed in the thesis *Método de Escolha Múltipla: uma proposta multicritério para seleção em conjunto de mais de uma alternativa*, by Henrique Rego Monteiro da Hora, at the Universidade Federal Fluminense (2013), and also appears in da Hora and Costa (2015).

## Limitations

The global optimum was not proven. The scores are the best known, and the search does not always reach them. There is also no validation that these teams would win more matches, because the score measures complementarity in the statistics, not results on the pitch.

The weight shows what each position does most, which does not prove it decides matches. The team only considers the 2017 season, and the goalkeeper stays outside the complementarity analysis. The data also does not measure how hard the shots they faced were. The score depends on the chosen tau, and the best team changes with it.

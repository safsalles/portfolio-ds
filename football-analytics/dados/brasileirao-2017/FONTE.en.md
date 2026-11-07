# Brazilian league 2017

*Português: veja o [FONTE.md](FONTE.md).*

Statistics from the 2017 season of the Brazilian Championship, collected by hand from [WhoScored](https://www.whoscored.com/) in 2017, with the site's permission for use in the dissertation research. If you use this data, cite WhoScored as the source.

There are 4 files: `players.csv` (outfield players), `criteria.csv` (the 18 criteria), `goalkeepers.csv` and `clubs.csv`. The programs use players with at least 850 minutes: 317 outfield players and 25 goalkeepers.

Both programs read the UTF-8 CSV files in this folder. To use other data, create a folder next to it, in `dados/`, with the same files and run, for example, `python -m escalacao --data dados/my_folder`.

## `players.csv`

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

## `criteria.csv`

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

## `goalkeepers.csv`

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

## `clubs.csv`

Optional file, used by GA-MEM to show club names. Without it, the list shows only the codes.

```csv
code,name
SAN,Santos
```

## Rules

- The formation must add up to the team size, set by `--team-size`, which defaults to 10.
- With other position codes, the shortcuts and the lineup drawing no longer apply. Write the formation as `position=amount`, and the result appears only as a list.
- With other data, tau needs to be calibrated again.

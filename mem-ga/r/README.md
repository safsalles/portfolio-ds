# memga

Selects a set of alternatives that complement each other, instead of ranking
the alternatives one by one. It implements the Multiple Choice Method (MEM) of
da Hora and Costa (2015), plus an adaptation for larger problems, with two
searches: exhaustive (tests every combination) and a genetic algorithm.

The same method is available in Python in the parent folder.

## Install

From R-universe (no compiler needed):

```r
install.packages("memga", repos = c("https://safsalles.r-universe.dev", "https://cloud.r-project.org"))
```

From CRAN, once it is accepted:

```r
install.packages("memga")
```

## Use

```r
library(memga)

# Choose 2 of 8 candidates, testing every pair
result <- memga(recruiting_small, size = 2)
result
plot(result)   # radar chart

# Choose a team of 4 among 300, with vacancies per group, using the genetic algorithm
memga(recruiting_large, method = "ga", tau = 0.54,
      quotas = c(analyst = 2, engineer = 1, manager = 1), seed = 1)
```

The two best candidates one by one are not always the best pair. In
`recruiting_small`, A1 and A2 have the best averages but are alike, so the pair
that adds A3, who covers what is missing, ranks first.

Use your own data with `mem_problem()` (a matrix or data frame with one row per
alternative and one column per criterion) or `read_mem_problem()` (CSV files).

| Argument | Meaning |
| --- | --- |
| `method` | `"exhaustive"` (default) or `"ga"` |
| `rule` | `"mean"` (original method) or `"minimum"` (criteria in pairs, for larger problems) |
| `tau` | The cutoff, 0.24 by default |
| `quotas` | Vacancies per group, such as `c(analyst = 2, manager = 1)` |
| `control` | Genetic algorithm settings, from `ga_control()` |

The genetic algorithm takes about 15 to 20 seconds on `recruiting_large` with
the default settings. It does not prove the best answer, so repeat it with other
seeds.

## Reference

da Hora, H. R. M. and Costa, H. G. (2015). Proposta de um método multicritério
para escolha múltipla. *Production*, 25(2). <https://doi.org/10.1590/0103-6513.084812>

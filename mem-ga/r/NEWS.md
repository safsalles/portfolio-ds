# memga 0.1.0

* First release.
* `memga()` selects a set of alternatives with the Multiple Choice Method, by
  exhaustive search or by a genetic algorithm, with the "mean" rule of the
  original method or the "minimum" rule, and optional vacancies per group.
* `mem_problem()` and `read_mem_problem()` describe a problem; `mem_score()` and
  `traditional_choice()` score a set and give the usual one-by-one choice for
  comparison.
* `memga_radar()` draws a radar chart of the selected set.
* Two simulated data sets: `recruiting_small` and `recruiting_large`.

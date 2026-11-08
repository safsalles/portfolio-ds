# memga for MATLAB and Octave

*Read in: [Português](README.md)*

The Multiple Choice Method (MEM) picks a set of alternatives that complement each other, instead of taking the best ones one by one. This folder brings the method to MATLAB and GNU Octave, with the same options as the [Python](../README.en.md) and [R](../r/) packages: exhaustive search or a genetic algorithm, the two scoring rules, and quotas per group.

It needs MATLAB R2016b or newer (or GNU Octave 7 or newer). It uses no toolbox.

## Installation

Download the `matlab` folder and add it to the MATLAB path:

```matlab
addpath('path/to/mem-ga/matlab')
```

## Usage

```matlab
% 2 of 8 candidates, trying every pair
result = memga(memga_load_example('small'), 2);
memga_print(result)
memga_radar(result)           % radar chart

% A team of 4 among 300, with quotas per group, by the genetic algorithm
result = memga(memga_load_example('large'), [], 'Method', 'ga', 'Tau', 0.54, ...
    'Quotas', struct('analyst', 2, 'engineer', 1, 'manager', 1), 'Seed', 1);
result.team
% {'P007', 'P038', 'P192', 'P276'}, score 0.6786
```

To use your own data, build the problem with `memga_problem(values)`, a matrix with one row per alternative and one column per criterion, or read CSV files with `memga_read_problem(folder)`. The file format is the same as in the Python package.

| `memga` option | What it does |
| --- | --- |
| `'Method'` | `'exhaustive'` (default) tests every combination. `'ga'` uses the genetic algorithm, for large problems. |
| `'Rule'` | `'mean'` (the thesis rule) or `'minimum'` (criteria in pairs). Without the option, the exhaustive search uses `'mean'` and the genetic algorithm uses `'minimum'`. |
| `'Tau'` | The cutoff, 0.24 by default. |
| `'Quotas'` | Vacancies per group, like `struct('analyst', 2, 'manager', 1)`. |
| `'Options'` | Genetic algorithm settings, from `memga_options`. |
| `'Seed'` | A seed to repeat a result. |

Type `help memga` for the full list. The result is a struct with `team`, `score`, `ranking` (exhaustive search), `history` (genetic algorithm) and `traditional`.

The genetic algorithm with the default settings takes about 75 seconds on the large example, in Octave. It does not prove the best answer, so repeat it with other seeds.

## Tests

```matlab
cd tests
run_tests          % quick ones
run_tests('full')  % also runs the full genetic algorithm on the large example
```

The reference values in `tests/ref` come from the Python version, so the versions agree: the ranking of the `'mean'` rule is identical, and the `'minimum'` rule agrees at the top of the ranking (below that, sets that sit exactly at tau can fall on either side because of floating point).

The tests passed on GNU Octave 9.4. They have not been run on MATLAB yet.

## Reference

da Hora, H. R. M. and Costa, H. G. (2015). Proposta de um método multicritério para escolha múltipla. *Production*, 25(2). <https://doi.org/10.1590/0103-6513.084812>

## Test environments

* Local Windows 11, R 4.6.2: `R CMD check --as-cran --no-manual`
* win-builder, R-devel (2026-11-07 r90850 ucrt), Windows Server 2022
* win-builder, R-release (4.6.2 ucrt), Windows Server 2022
* R-hub: to be run before submission

## R CMD check results

0 errors | 0 warnings | 1 note

* The note is "New submission".
* It also lists "Costa" and "da" as possibly misspelled words in DESCRIPTION.
  They are parts of the names of the authors of the cited paper (da Hora and
  Costa, 2015).

(The local run on Windows with R 4.6.2 had no notes, with the remote part of
the incoming checks disabled.)

## Notes

* The package has no compiled code and imports only base R packages (graphics,
  grDevices, stats and utils).
* The tests that run the genetic algorithm with its default settings take about
  a minute, so they are skipped on CRAN with `skip_on_cran()`. The examples use
  few iterations and run in a fraction of a second.

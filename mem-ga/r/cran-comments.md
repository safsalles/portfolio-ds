## Test environments

* Local Windows 11, R 4.6.2: `R CMD check --as-cran --no-manual`
* win-builder (release and devel): to be run before submission
* R-hub: to be run before submission

## R CMD check results

0 errors | 0 warnings | 0 notes

(Local run, with the remote part of the incoming checks disabled.)

This is a new submission.

## Notes

* The package has no compiled code and imports only base R packages (graphics,
  grDevices, stats and utils).
* The tests that run the genetic algorithm with its default settings take about
  a minute, so they are skipped on CRAN with `skip_on_cran()`. The examples use
  few iterations and run in a fraction of a second.

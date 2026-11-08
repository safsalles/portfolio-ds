#' Select a set of alternatives with the Multiple Choice Method
#'
#' Finds the set of alternatives that best complements itself. A set is scored
#' by the share of criteria combinations in which it reaches the cutoff `tau`,
#' so a set whose members are strong in the same criteria scores below a set
#' whose members cover each other's weak points.
#'
#' Two scoring rules are available.
#'
#' * `"mean"` is the rule of the thesis that proposed the method. The criteria
#'   are combined `size` at a time, and the value of a set in a combination is
#'   the average performance of the set in those criteria, times the average
#'   weight, times the average complementarity of the criteria. The number of
#'   combinations grows fast, so it is limited to 10,000 per evaluation.
#' * `"minimum"` is an adaptation for continuous data and larger problems. The
#'   criteria are combined two at a time, and the value of a set in a pair is
#'   the weaker of the two average performances, times the average weight of the
#'   pair, times its complementarity. A strong criterion does not cover a weak
#'   one.
#'
#' Two searches are available.
#'
#' * `"exhaustive"` tests every combination and returns the full ranking. Tied
#'   sets share a position, because the method can point to more than one good
#'   choice. It is limited to 20 million evaluations.
#' * `"ga"` uses a genetic algorithm with a strong mutation, for problems too
#'   large to enumerate. It does not guarantee the best answer, so it is worth
#'   repeating with other seeds.
#'
#' @param problem A [mem_problem()]. A matrix or data frame of values is also
#'   accepted and converted with the default settings.
#' @param size The number of alternatives to select. It can be omitted when
#'   `quotas` is given.
#' @param method `"exhaustive"` (the default) or `"ga"`.
#' @param rule `"mean"` or `"minimum"`. By default, `"mean"` with the exhaustive
#'   search and `"minimum"` with the genetic algorithm.
#' @param tau The cutoff, a number greater than 0. A combination counts when its
#'   value reaches `tau`. The default, 0.24, is the value the thesis obtains for
#'   a performance of 50% with its example weights; see the thesis for how to
#'   choose it for other data.
#' @param quotas Optional. A named vector with the number of alternatives to
#'   select in each group, for example `c(analyst = 2, manager = 1)`. Needs
#'   `groups` in the problem.
#' @param control Settings of the genetic algorithm, from [ga_control()].
#' @param seed Optional. A seed to repeat a genetic algorithm result.
#' @param progress Show a progress bar during the genetic algorithm.
#'
#' @return An object of class `memga`, a list with
#'   \item{team}{The names of the selected alternatives. With the exhaustive
#'     search, the first set of the ranking.}
#'   \item{score}{The score of `team`, between 0 and 1.}
#'   \item{ranking}{With the exhaustive search, a data frame with the columns
#'     `position`, `set` and `score`, and a list column `members`.}
#'   \item{history}{With the genetic algorithm, the best score at each
#'     iteration.}
#'   \item{traditional}{The traditional choice (see [traditional_choice()]) and
#'     its score under the same rule, for comparison.}
#'   \item{problem, size, method, rule, tau, quotas, seed}{The inputs used.}
#'
#' @references
#' da Hora, H. R. M. and Costa, H. G. (2015). Proposta de um método multicritério
#' para escolha múltipla. *Production*, 25(2). \doi{10.1590/0103-6513.084812}
#'
#' da Hora, H. R. M. (2013). *Método de Escolha Múltipla: uma proposta
#' multicritério para seleção em conjunto de mais de uma alternativa*.
#' Doctoral thesis, Universidade Federal Fluminense.
#'
#' @seealso [mem_problem()], [traditional_choice()], [memga_radar()]
#'
#' @examples
#' # Two of eight candidates, testing every pair
#' result <- memga(recruiting_small, size = 2)
#' result
#'
#' # The same problem with the adaptation that scores criteria in pairs
#' memga(recruiting_small, size = 2, rule = "minimum")
#'
#' # A team of 4 among 300 candidates, with vacancies per group, found by
#' # the genetic algorithm (few iterations to keep the example fast)
#' memga(recruiting_large, method = "ga", tau = 0.54,
#'       quotas = c(analyst = 2, engineer = 1, manager = 1),
#'       control = ga_control(iterations = 300), seed = 1)
#' @export
memga <- function(problem, size = NULL, method = c("exhaustive", "ga"), rule = NULL,
                  tau = 0.24, quotas = NULL, control = ga_control(), seed = NULL,
                  progress = FALSE) {
  method <- match.arg(method)
  if (!inherits(problem, "mem_problem")) problem <- mem_problem(problem)
  if (is.null(rule)) rule <- if (method == "exhaustive") "mean" else "minimum"
  rule <- match.arg(rule, c("mean", "minimum"))
  check_tau(tau)
  if (!inherits(control, "memga_ga_control")) {
    stop("`control` must come from ga_control().", call. = FALSE)
  }

  quotas <- check_quotas(quotas, problem)
  if (is.null(size)) {
    if (is.null(quotas)) stop("Give `size`, the number of alternatives to select.", call. = FALSE)
    size <- sum(quotas)
  } else if (!is.numeric(size) || length(size) != 1 || size != round(size) || size < 1) {
    stop("`size` must be a single whole number of at least 1.", call. = FALSE)
  } else if (!is.null(quotas) && size != sum(quotas)) {
    stop("`size` is ", size, " but `quotas` adds up to ", sum(quotas), ".", call. = FALSE)
  }
  if (size > nrow(problem$values)) {
    stop("The set asks for ", size, " alternatives, but the data has only ",
         nrow(problem$values), ".", call. = FALSE)
  }

  fitted <- build_rule(problem, rule, tau, size)
  labels <- if (is.null(quotas)) NULL else problem$groups

  if (!is.null(seed)) {
    if (exists(".Random.seed", envir = globalenv(), inherits = FALSE)) {
      old_seed <- get(".Random.seed", envir = globalenv())
      on.exit(assign(".Random.seed", old_seed, envir = globalenv()), add = TRUE)
    } else {
      on.exit(rm(".Random.seed", envir = globalenv()), add = TRUE)
    }
    set.seed(seed)
  }

  traditional <- traditional_choice(problem, size, quotas)
  traditional_score <- rule_rate(fitted, match(traditional, problem$alternatives))$score

  result <- list(
    problem = problem, size = size, method = method, rule = rule, tau = tau,
    quotas = quotas, seed = seed, fitted = fitted,
    traditional = list(team = traditional, score = traditional_score)
  )

  if (method == "exhaustive") {
    found <- exhaustive_search(fitted, nrow(problem$values), size, labels, quotas)
    members <- lapply(seq_len(ncol(found$sets)), function(i) problem$alternatives[found$sets[, i]])
    ranking <- data.frame(
      position = found$position,
      set = vapply(members, paste, character(1), collapse = ", "),
      score = found$score,
      stringsAsFactors = FALSE
    )
    ranking$members <- members
    result$ranking <- ranking
    result$team <- members[[1]]
    result$score <- found$score[1]
  } else {
    found <- run_ga(fitted, problem$groups, quotas, size, control, progress)
    result$team <- problem$alternatives[found$team]
    result$score <- found$score
    result$history <- found$history
    result$control <- control
  }
  structure(result, class = "memga")
}

check_quotas <- function(quotas, problem) {
  if (is.null(quotas)) return(NULL)
  if (is.null(problem$groups)) {
    stop("`quotas` needs `groups` in the problem.", call. = FALSE)
  }
  if (!is.numeric(quotas) || is.null(names(quotas)) || anyNA(quotas) ||
      any(quotas != round(quotas)) || any(quotas < 0)) {
    stop("`quotas` must be a named vector of whole numbers, like c(analyst = 2).",
         call. = FALSE)
  }
  unknown <- setdiff(names(quotas), problem$groups)
  if (length(unknown) > 0) {
    stop("`quotas` names groups that are not in the problem: ",
         paste(unknown, collapse = ", "), ".", call. = FALSE)
  }
  quotas <- quotas[quotas > 0]
  if (length(quotas) == 0) stop("`quotas` must ask for at least 1 alternative.", call. = FALSE)
  quotas
}

#' The traditional choice
#'
#' The usual choice without the Multiple Choice Method: rate each alternative
#' alone, by the weighted average of its normalised performance, and keep the
#' best ones, respecting the vacancies per group when there are quotas.
#' [memga()] reports it next to the selected set for comparison.
#'
#' @param problem A [mem_problem()].
#' @param size The number of alternatives to select. It can be omitted when
#'   `quotas` is given.
#' @param quotas Optional. A named vector with the number of alternatives to
#'   select in each group.
#'
#' @return The names of the selected alternatives.
#'
#' @examples
#' traditional_choice(recruiting_small, size = 2)
#' traditional_choice(recruiting_large, quotas = c(analyst = 2, engineer = 1, manager = 1))
#' @export
traditional_choice <- function(problem, size = NULL, quotas = NULL) {
  if (!inherits(problem, "mem_problem")) problem <- mem_problem(problem)
  quotas <- check_quotas(quotas, problem)
  if (is.null(size)) {
    if (is.null(quotas)) stop("Give `size`, the number of alternatives to select.", call. = FALSE)
    size <- sum(quotas)
  }
  normalized <- normalize_values(problem$values, problem$direction)
  strengths <- if (sum(problem$weights) > 0) {
    as.vector(normalized %*% problem$weights) / sum(problem$weights)
  } else {
    rowSums(normalized)
  }
  ordered <- order(-strengths)
  if (is.null(quotas)) {
    return(problem$alternatives[ordered[seq_len(size)]])
  }
  chosen <- integer(0)
  for (group in names(quotas)) {
    chosen <- c(chosen, ordered[problem$groups[ordered] == group][seq_len(quotas[[group]])])
  }
  problem$alternatives[chosen]
}

#' Score a set of alternatives
#'
#' Scores a set that you chose yourself, with the same rule used by [memga()].
#'
#' @param problem A [mem_problem()].
#' @param team The names of the alternatives in the set.
#' @param rule `"mean"` or `"minimum"`.
#' @param tau The cutoff, a number greater than 0.
#'
#' @return The score of the set, between 0 and 1.
#'
#' @examples
#' mem_score(recruiting_small, c("A1", "A2"))
#' mem_score(recruiting_small, c("A1", "A3"))
#' @export
mem_score <- function(problem, team, rule = c("mean", "minimum"), tau = 0.24) {
  rule <- match.arg(rule)
  if (!inherits(problem, "mem_problem")) problem <- mem_problem(problem)
  index <- match(team, problem$alternatives)
  if (anyNA(index) || anyDuplicated(index) || length(index) < 1) {
    stop("`team` must name different alternatives of the problem.", call. = FALSE)
  }
  fitted <- build_rule(problem, rule, tau, length(index))
  rule_rate(fitted, index)$score
}

#' Settings of the genetic algorithm
#'
#' Controls the search used by `memga(method = "ga")`. The defaults are the ones
#' used in the original implementation.
#'
#' @param iterations Number of iterations.
#' @param population Number of sets kept in the population.
#' @param stagnation Iterations without improvement before a mutation.
#' @param mutation_attempts Attempts in each mutation.
#' @param kick_size Number of alternatives swapped at once in the strong
#'   mutation.
#' @param climb_every Number of mutations between one strong mutation and the
#'   next.
#'
#' @return A list of class `memga_ga_control`.
#'
#' @examples
#' ga_control(iterations = 2000)
#' @export
ga_control <- function(iterations = 15000, population = 60, stagnation = 14,
                       mutation_attempts = 7, kick_size = 3, climb_every = 5) {
  values <- c(iterations, population, stagnation, mutation_attempts, kick_size, climb_every)
  if (!is.numeric(values) || anyNA(values) || any(values != round(values))) {
    stop("All settings of the genetic algorithm must be whole numbers.", call. = FALSE)
  }
  if (population < 2) {
    stop("The population needs at least 2 sets.", call. = FALSE)
  }
  if (min(iterations, stagnation, mutation_attempts) < 1) {
    stop("`iterations`, `stagnation` and `mutation_attempts` must be at least 1.", call. = FALSE)
  }
  if (min(kick_size, climb_every) < 1) {
    stop("`kick_size` and `climb_every` must be at least 1.", call. = FALSE)
  }
  structure(
    list(iterations = iterations, population = population, stagnation = stagnation,
         mutation_attempts = mutation_attempts, kick_size = kick_size, climb_every = climb_every),
    class = "memga_ga_control"
  )
}

MAX_REDRAWS <- 1000
PROGRESS_STEP <- 100

team_key <- function(team) paste(team, collapse = ",")

# TRUE when a is better than b, comparing the score first and the tie-breaker second.
is_better <- function(a, b) {
  a$score > b$score || (a$score == b$score && a$tie > b$tie)
}

run_ga <- function(rule, groups, quotas, size, control, progress = FALSE) {
  n <- nrow(rule$payment)
  if (is.null(quotas)) {
    if (size < 1) stop("The set needs at least 1 alternative.", call. = FALSE)
    if (size > n) {
      stop("The set asks for ", size, " alternatives, but the data has only ", n, ".",
           call. = FALSE)
    }
    labels <- rep("*", n)
    quotas <- c("*" = size)
  } else {
    labels <- as.character(groups)
    quotas <- quotas[quotas > 0]
  }
  pools <- lapply(names(quotas), function(group) which(labels == group))
  names(pools) <- names(quotas)
  for (group in names(quotas)) {
    if (quotas[[group]] > length(pools[[group]])) {
      stop("Group ", group, " has ", length(pools[[group]]),
           " alternatives, and ", quotas[[group]], " were requested.", call. = FALSE)
    }
  }

  state <- new.env()
  state$teams <- list()
  state$score <- numeric(0)
  state$tie <- numeric(0)
  seen <- new.env(hash = TRUE)

  rate_team <- function(team) rule_rate(rule, team)

  # Draws the alternatives of each group among the candidates.
  pick <- function(candidates) {
    team <- integer(0)
    for (group in names(quotas)) {
      pool <- candidates[labels[candidates] == group]
      team <- c(team, pool[sample.int(length(pool), quotas[[group]])])
    }
    sort(team)
  }

  sort_population <- function() {
    ordered <- order(state$score, state$tie)
    state$teams <- state$teams[ordered]
    state$score <- state$score[ordered]
    state$tie <- state$tie[ordered]
  }
  replace_worst <- function(rated) {
    state$teams[[length(state$teams) + 1]] <- rated$team
    state$score <- c(state$score, rated$score)
    state$tie <- c(state$tie, rated$tie)
    sort_population()
    state$teams <- state$teams[-1]
    state$score <- state$score[-1]
    state$tie <- state$tie[-1]
    # `seen` holds every set that has been in the population, so adding the new one is enough.
    assign(team_key(rated$team), TRUE, envir = seen)
  }
  top <- function() {
    last <- length(state$teams)
    list(score = state$score[last], tie = state$tie[last], team = state$teams[[last]])
  }

  possible <- prod(vapply(names(quotas), function(group) {
    choose(length(pools[[group]]), quotas[[group]])
  }, numeric(1)))
  target <- min(control$population, possible)
  keys <- character(0)
  while (length(state$teams) < target) {
    team <- pick(seq_len(n))
    key <- team_key(team)
    if (!key %in% keys) {
      keys <- c(keys, key)
      rated <- rate_team(team)
      state$teams[[length(state$teams) + 1]] <- team
      state$score <- c(state$score, rated$score)
      state$tie <- c(state$tie, rated$tie)
    }
  }
  sort_population()
  for (team in state$teams) assign(team_key(team), TRUE, envir = seen)

  crossover <- function() {
    parents <- sample.int(length(state$teams), 2, replace = TRUE)
    pick(sort(union(state$teams[[parents[1]]], state$teams[[parents[2]]])))
  }
  new_child <- function() {
    child <- crossover()
    if (exists(team_key(child), envir = seen, inherits = FALSE)) {
      current <- vapply(state$teams, team_key, character(1))
      # The limit avoids an endless loop when the population has converged.
      for (attempt in seq_len(MAX_REDRAWS)) {
        child <- crossover()
        if (!team_key(child) %in% current) break
      }
    }
    child
  }

  mutate <- function(best) {
    eligible <- which(labels %in% names(quotas))
    untested <- setdiff(eligible, best$team)
    for (attempt in seq_len(control$mutation_attempts)) {
      if (length(untested) == 0) break
      newcomer <- untested[sample.int(length(untested), 1)]
      untested <- setdiff(untested, newcomer)
      slots <- which(labels[best$team] == labels[newcomer])
      mutant <- best$team
      mutant[slots[sample.int(length(slots), 1)]] <- newcomer
      rated <- rate_team(mutant)
      # The better set becomes the champion without entering the population.
      if (is_better(rated, best)) return(rated)
      replace_worst(rated)
    }
    best
  }

  # Swaps `kick_size` alternatives at once, each for another of the same group.
  kick <- function(team) {
    spare <- lapply(pools, function(pool) setdiff(pool, team))
    slots <- which(vapply(team, function(member) length(spare[[labels[member]]]) > 0, logical(1)))
    if (length(slots) == 0) return(team)
    chosen <- slots[sample.int(length(slots), min(control$kick_size, length(slots)))]
    for (slot in chosen) {
      group <- labels[team[slot]]
      pool <- spare[[group]]
      # A group with few spare alternatives can run out before `kick_size` swaps.
      if (length(pool) > 0) {
        index <- sample.int(length(pool), 1)
        team[slot] <- pool[index]
        spare[[group]] <- pool[-index]
      }
    }
    sort(team)
  }

  # Swaps one alternative at a time, inside its group, while the score goes up.
  climb <- function(team) {
    best <- rate_team(team)
    improved <- TRUE
    while (improved) {
      improved <- FALSE
      for (slot in seq_along(team)) {
        others <- team[-slot]
        candidates <- setdiff(pools[[labels[team[slot]]]], team)
        if (length(candidates) == 0) next
        base <- colSums(rule$payment[others, , drop = FALSE])
        means <- sweep(rule$payment[candidates, , drop = FALSE], 2, base, "+") / length(team)
        rated <- rule_rate_means(rule, means)
        first <- order(-rated$score, -rated$tie)[1]
        challenger <- list(score = rated$score[first], tie = rated$tie[first])
        if (is_better(challenger, best)) {
          team[slot] <- candidates[first]
          best <- c(challenger, list(team = sort(team)))
          improved <- TRUE
        }
      }
    }
    best
  }

  strong_mutation <- function(best) {
    rated <- climb(kick(best$team))
    if (is_better(best, rated)) return(best)
    # Copies of the same set in the population would lock the crossover in `new_child`.
    if (!team_key(rated$team) %in% vapply(state$teams, team_key, character(1))) {
      replace_worst(rated)
    }
    rated
  }

  best <- top()
  stagnant <- 0
  mutations <- 0
  history <- numeric(control$iterations)
  bar <- NULL
  if (progress) bar <- utils::txtProgressBar(min = 0, max = control$iterations, style = 3)
  for (iteration in seq_len(control$iterations)) {
    replace_worst(rate_team(new_child()))
    leader <- top()
    if (is_better(leader, best)) {
      best <- leader
      stagnant <- 0
    } else {
      stagnant <- stagnant + 1
      if (stagnant == control$stagnation) {
        best <- mutate(best)
        stagnant <- 0
        mutations <- mutations + 1
        if (mutations %% control$climb_every == 0) best <- strong_mutation(best)
      }
    }
    history[iteration] <- best$score
    if (!is.null(bar) && (iteration %% PROGRESS_STEP == 0 || iteration == control$iterations)) {
      utils::setTxtProgressBar(bar, iteration)
    }
  }
  if (!is.null(bar)) close(bar)

  list(team = best$team, score = best$score, history = history)
}

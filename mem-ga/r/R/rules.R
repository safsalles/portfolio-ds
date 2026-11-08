# Normalisation, group weights and the two scoring rules.
#
# A rule receives the average performance of a set on each criterion and returns
# a score (the share of criteria combinations in which the set reaches `tau`) and
# a tie-breaker (the average of min(value, tau), which shows how far the
# combinations that do not pass are from passing).

MAX_MEAN_GROUPS <- 10000
MAX_EVALUATIONS <- 2e7

# Equation 3.1 of the thesis: each criterion goes from 0 to 1, and 1 is the best.
normalize_values <- function(values, direction) {
  high <- apply(values, 2, max)
  low <- apply(values, 2, min)
  benefit <- direction >= 1
  best <- ifelse(benefit, high, low)
  worst <- ifelse(benefit, low, high)
  spread <- ifelse(best == worst, 1, best - worst)
  sweep(sweep(values, 2, worst, "-"), 2, spread, "/")
}

# 1 minus the absolute correlation between criteria, within each group.
complementarity_from_data <- function(values, groups = NULL) {
  centered <- values
  if (is.null(groups)) groups <- rep("*", nrow(values))
  for (group in unique(groups)) {
    members <- groups == group
    centered[members, ] <- sweep(values[members, , drop = FALSE], 2,
                                 colMeans(values[members, , drop = FALSE]), "-")
  }
  correlation <- suppressWarnings(stats::cor(centered))
  correlation[is.na(correlation)] <- 0
  out <- 1 - abs(correlation)
  dimnames(out) <- list(colnames(values), colnames(values))
  out
}

# How much each group does each criterion above the other groups, in standard
# deviations. Every criterion starts at 1, so only the priority changes.
group_weights <- function(values, groups, direction) {
  weights <- matrix(1, nrow(values), ncol(values))
  spread <- apply(values, 2, function(x) sqrt(mean((x - mean(x))^2)))
  spread[spread == 0] <- 1
  for (group in unique(groups)) {
    members <- groups == group
    if (all(members)) next
    lead <- (colMeans(values[members, , drop = FALSE]) -
               colMeans(values[!members, , drop = FALSE])) / spread
    raw <- 1 + pmax(ifelse(direction >= 1, lead, 0), 0)
    weights[members, ] <- matrix(raw / mean(raw), sum(members), ncol(values), byrow = TRUE)
  }
  weights
}

check_tau <- function(tau) {
  if (!is.numeric(tau) || length(tau) != 1 || !is.finite(tau) || tau <= 0) {
    stop("`tau` must be a single finite number greater than 0.", call. = FALSE)
  }
}

build_rule <- function(problem, rule, tau, size = NULL) {
  check_tau(tau)
  payment <- normalize_values(problem$values, problem$direction)
  if (!is.null(problem$groups)) {
    payment <- payment * group_weights(problem$values, problem$groups, problem$direction)
  }
  complementarity <- problem$complementarity
  if (is.null(complementarity)) {
    complementarity <- complementarity_from_data(problem$values, problem$groups)
  }
  weights <- problem$weights
  n_criteria <- ncol(payment)

  if (rule == "minimum") {
    pairs <- utils::combn(n_criteria, 2)
    first <- pairs[1, ]
    second <- pairs[2, ]
    factor <- (weights[first] + weights[second]) / 2 * complementarity[cbind(first, second)]
    return(list(kind = "minimum", payment = payment, first = first, second = second,
                factor = factor, tau = tau, n_combos = length(first)))
  }

  if (is.null(size)) {
    stop("The \"mean\" rule needs the size of the set.", call. = FALSE)
  }
  if (size < 2 || size > n_criteria) {
    stop("With the \"mean\" rule, the set must have from 2 to ", n_criteria,
         " alternatives, and ", size, " was requested.", call. = FALSE)
  }
  total <- choose(n_criteria, size)
  if (total > MAX_MEAN_GROUPS) {
    stop("The \"mean\" rule would have ", format(total, scientific = FALSE),
         " criteria groups per evaluation, above the limit of ", MAX_MEAN_GROUPS,
         ". Use fewer criteria, a smaller set or the \"minimum\" rule.", call. = FALSE)
  }
  groups <- utils::combn(n_criteria, size)
  factor <- apply(groups, 2, function(group) {
    pairs <- utils::combn(group, 2)
    mean(weights[group]) * mean(complementarity[cbind(pairs[1, ], pairs[2, ])])
  })
  membership <- matrix(0, n_criteria, ncol(groups))
  membership[cbind(as.vector(groups), rep(seq_len(ncol(groups)), each = size))] <- 1 / size
  list(kind = "mean", payment = payment, membership = membership, factor = factor,
       tau = tau, n_combos = ncol(groups))
}

# `means` has one row per set and one column per criterion.
rule_values <- function(rule, means) {
  if (rule$kind == "minimum") {
    values <- pmin(means[, rule$first, drop = FALSE], means[, rule$second, drop = FALSE])
  } else {
    values <- means %*% rule$membership
  }
  sweep(values, 2, rule$factor, "*")
}

rule_rate_means <- function(rule, means) {
  values <- rule_values(rule, means)
  # Rounding keeps a value equal to tau from falling below it because of floating point.
  passed <- round(values, 12) >= rule$tau
  list(score = unname(rowMeans(passed)), tie = unname(rowMeans(pmin(values, rule$tau))))
}

rule_rate <- function(rule, team) {
  means <- matrix(colMeans(rule$payment[team, , drop = FALSE]), nrow = 1)
  out <- rule_rate_means(rule, means)
  list(score = out$score, tie = out$tie, team = sort(team))
}

# Exhaustive search: test every combination and rank them all, as in the thesis.

exhaustive_search <- function(rule, n_alternatives, size, labels = NULL, quotas = NULL) {
  total <- choose(n_alternatives, size) * rule$n_combos
  if (total > MAX_EVALUATIONS) {
    stop("That would be ", format(total, scientific = FALSE),
         " evaluations, too many to test one by one. Use method = \"ga\".", call. = FALSE)
  }
  sets <- utils::combn(n_alternatives, size)
  if (!is.null(quotas)) {
    keep <- rep(TRUE, ncol(sets))
    for (group in names(quotas)) {
      inside <- matrix(labels[sets] == group, nrow = size)
      keep <- keep & colSums(inside) == quotas[[group]]
    }
    sets <- sets[, keep, drop = FALSE]
  }

  scores <- numeric(ncol(sets))
  chunk <- 50000
  for (start in seq(1, ncol(sets), by = chunk)) {
    index <- start:min(start + chunk - 1, ncol(sets))
    picked <- sets[, index, drop = FALSE]
    sums <- rule$payment[picked[1, ], , drop = FALSE]
    for (row in seq_len(size)[-1]) {
      sums <- sums + rule$payment[picked[row, ], , drop = FALSE]
    }
    scores[index] <- rule_rate_means(rule, sums / size)$score
  }

  # `order` is stable and `combn` is in lexicographic order, so ties keep that order.
  ordered <- order(-scores)
  scores <- scores[ordered]
  list(sets = sets[, ordered, drop = FALSE], score = scores,
       position = rank(-scores, ties.method = "min"))
}

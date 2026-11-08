# These values were produced by the Python version, so the ports agree.

read_ref <- function(name) {
  utils::read.csv(test_path("ref", name), stringsAsFactors = FALSE)
}

test_that("the exhaustive ranking matches the Python version", {
  for (rule in c("mean", "minimum")) {
    python_rule <- if (rule == "mean") "media" else "minimo"
    for (size in c(2, 3)) {
      ref <- read_ref(sprintf("exhaustive_%s_%d.csv", python_rule, size))
      result <- memga(recruiting_small, size = size, rule = rule, tau = 0.24)
      expect_equal(nrow(result$ranking), nrow(ref))
      # With the "minimum" rule, many sets have a pair that is exactly at tau in exact
      # arithmetic. Python lets floating point push some of them below tau, and the
      # package rounds them in, so below this point the two rankings differ in the
      # sets that sit at the cutoff. The top of the ranking is the same.
      keep <- if (rule == "minimum") c(`2` = 8, `3` = 17)[[as.character(size)]] else nrow(ref)
      rows <- seq_len(keep)
      info <- paste(rule, size)
      expect_equal(result$ranking$position[rows], ref$position[rows], info = info)
      expect_equal(result$ranking$set[rows], gsub(",", ", ", ref$set[rows]), info = info)
      expect_equal(result$ranking$score[rows], ref$score[rows], tolerance = 1e-12, info = info)
    }
  }
})

test_that("scores of random sets match the Python version", {
  ref <- read_ref("ratings.csv")
  problems <- list(small = recruiting_small, large = recruiting_large)
  for (i in seq_len(nrow(ref))) {
    row <- ref[i, ]
    team <- as.integer(strsplit(row$team, " ")[[1]])
    rule_name <- if (row$rule == "media") "mean" else "minimum"
    fitted <- build_rule(problems[[row$data]], rule_name, row$tau, length(team))
    # A value that is exactly tau in exact arithmetic can fall on either side of it in
    # floating point, and the two languages sum in a different order. Skip those teams.
    means <- matrix(colMeans(fitted$payment[team, , drop = FALSE]), nrow = 1)
    if (any(abs(rule_values(fitted, means) - row$tau) < 1e-9)) next
    got <- rule_rate(fitted, team)
    expect_equal(got$score, row$score, tolerance = 1e-12, info = paste(i, row$team))
    expect_equal(got$tie, row$tie, tolerance = 1e-10, info = paste(i, row$team))
  }
})

test_that("the genetic algorithm reaches the best score the Python version finds", {
  skip_on_cran()
  ref <- read_ref("ga_large.csv")
  quotas <- c(analyst = 2, engineer = 1, manager = 1)
  for (i in seq_len(nrow(ref))) {
    rule <- if (ref$rule[i] == "media") "mean" else "minimum"
    scores <- vapply(1:3, function(seed) {
      memga(recruiting_large, method = "ga", rule = rule, tau = ref$tau[i], quotas = quotas,
            seed = seed)$score
    }, numeric(1))
    expect_equal(max(scores), ref$best[i], tolerance = 1e-12, info = rule)
    expect_gte(min(scores), ref$worst[i] - 0.05)
  }
})

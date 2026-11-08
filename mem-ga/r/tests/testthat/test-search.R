test_that("the example prefers a pair that complements itself", {
  result <- memga(recruiting_small, size = 2)
  expect_s3_class(result, "memga")
  expect_true(result$score > 0.6)
  top <- result$ranking$set[result$ranking$position == 1]
  expect_true("A1, A3" %in% top)
  expect_false("A1, A2" %in% top)
  expect_equal(result$traditional$team, c("A1", "A2"))
  expect_lt(result$traditional$score, result$score)
})

test_that("tied sets share a position", {
  ranking <- memga(recruiting_small, size = 2)$ranking
  expect_equal(ranking$position[1:2], c(1, 1))
  expect_equal(ranking$position[3], 3)
  expect_equal(ranking$score, sort(ranking$score, decreasing = TRUE))
})

test_that("a value equal to tau passes despite floating point", {
  problem <- mem_problem(rbind(c(0, 0), c(1, 1)), weights = c(0.1, 0.1),
                         complementarity = matrix(c(0, 3, 3, 0), 2))
  expect_equal(memga(problem, size = 2, tau = 0.15)$score, 1)
})

test_that("quotas restrict the exhaustive search", {
  problem <- mem_problem(
    matrix(c(9, 8, 2, 3, 4, 7, 6, 5, 1, 9, 3, 8), 6,
           dimnames = list(letters[1:6], c("x", "y"))),
    groups = c("p", "p", "p", "q", "q", "q"), complementarity = matrix(c(0, 1, 1, 0), 2))
  result <- memga(problem, quotas = c(p = 1, q = 1), tau = 0.1)
  expect_equal(nrow(result$ranking), 9)
  kinds <- vapply(result$ranking$members, function(members) {
    paste(sort(problem$groups[match(members, problem$alternatives)]), collapse = "")
  }, character(1))
  expect_true(all(kinds == "pq"))
})

test_that("size and quotas are checked", {
  expect_error(memga(recruiting_small), "size")
  expect_error(memga(recruiting_small, size = 20), "only 8")
  expect_error(memga(recruiting_small, size = 1), "from 2")
  expect_error(memga(recruiting_small, size = 2, quotas = c(a = 2)), "groups")
  expect_error(
    memga(recruiting_large, size = 3, quotas = c(analyst = 2, manager = 1, engineer = 1)),
    "adds up"
  )
  expect_error(memga(recruiting_large, quotas = c(pilot = 2), method = "ga"), "not in the problem")
  expect_error(memga(recruiting_small, size = 2, tau = 0), "tau")
  expect_error(memga(recruiting_small, size = 2, tau = NA), "tau")
  expect_error(memga(recruiting_small, size = 2, control = list()), "ga_control")
})

test_that("a problem that is too big for the exhaustive search is refused", {
  expect_error(memga(recruiting_large, size = 4, rule = "minimum"), "too many")
  set.seed(1)
  wide <- mem_problem(matrix(stats::runif(20 * 18), 20, 18))
  expect_error(memga(wide, size = 10, rule = "mean", method = "ga"), "limit")
})

test_that("printing shows the ranking and the traditional choice", {
  expect_output(print(memga(recruiting_small, size = 2)), "A1, A3")
  expect_output(print(memga(recruiting_small, size = 2)), "ranks 3rd")
})

test_that("traditional_choice follows the weighted average and the quotas", {
  expect_equal(traditional_choice(recruiting_small, size = 2), c("A1", "A2"))
  team <- traditional_choice(recruiting_large, quotas = c(analyst = 2, engineer = 1, manager = 1))
  groups <- recruiting_large$groups[match(team, recruiting_large$alternatives)]
  expect_equal(sort(groups), c("analyst", "analyst", "engineer", "manager"))
  expect_error(traditional_choice(recruiting_small), "size")
})

test_that("mem_score scores a chosen set", {
  expect_equal(mem_score(recruiting_small, c("A1", "A3")), 2 / 3)
  expect_lt(mem_score(recruiting_small, c("A1", "A2")), mem_score(recruiting_small, c("A1", "A3")))
  expect_error(mem_score(recruiting_small, c("A1", "Z9")), "different alternatives")
})

quotas <- c(analyst = 2, engineer = 1, manager = 1)
quick <- ga_control(iterations = 200)

test_that("the genetic algorithm respects the quotas", {
  result <- memga(recruiting_large, method = "ga", quotas = quotas, control = quick, seed = 1)
  groups <- recruiting_large$groups[match(result$team, recruiting_large$alternatives)]
  expect_equal(sort(groups), c("analyst", "analyst", "engineer", "manager"))
  expect_equal(anyDuplicated(result$team), 0)
})

test_that("the genetic algorithm works without groups", {
  result <- memga(recruiting_small, size = 3, method = "ga", control = quick, seed = 2)
  expect_length(result$team, 3)
  expect_equal(result$score, mem_score(recruiting_small, result$team, rule = "minimum"))
})

test_that("the history never decreases and has one value per iteration", {
  result <- memga(recruiting_large, method = "ga", quotas = quotas, control = quick, seed = 3)
  expect_length(result$history, 200)
  expect_false(is.unsorted(result$history))
  expect_equal(result$history[200], result$score)
})

test_that("the same seed repeats the result and leaves the user's seed alone", {
  set.seed(10)
  before <- runif(1)
  set.seed(10)
  first <- memga(recruiting_large, method = "ga", quotas = quotas, control = quick, seed = 4)
  expect_equal(runif(1), before)
  second <- memga(recruiting_large, method = "ga", quotas = quotas, control = quick, seed = 4)
  expect_equal(first$team, second$team)
})

test_that("the genetic algorithm finds the exhaustive best on a small problem", {
  exhaustive <- memga(recruiting_small, size = 2, rule = "minimum")
  ga <- memga(recruiting_small, size = 2, method = "ga", rule = "minimum",
              control = ga_control(iterations = 300), seed = 5)
  expect_equal(ga$score, exhaustive$score)
})

test_that("a population larger than the number of possible sets is accepted", {
  result <- memga(recruiting_small, size = 7, method = "ga",
                  control = ga_control(iterations = 20), seed = 1)
  expect_length(result$team, 7)
})

test_that("ga_control validates its settings", {
  expect_error(ga_control(population = 1), "at least 2")
  expect_error(ga_control(iterations = 0), "at least 1")
  expect_error(ga_control(kick_size = 0), "at least 1")
  expect_error(ga_control(iterations = 1.5), "whole")
  expect_equal(ga_control()$iterations, 15000)
})

test_that("asking for more than a group has is an error", {
  expect_error(
    memga(recruiting_large, method = "ga", quotas = c(manager = 61), control = quick),
    "Group manager"
  )
})

test_that("a progress bar can be shown", {
  expect_output(
    memga(recruiting_small, size = 2, method = "ga", control = ga_control(iterations = 100),
          seed = 1, progress = TRUE),
    "100%"
  )
})

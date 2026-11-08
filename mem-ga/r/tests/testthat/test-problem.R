test_that("a problem keeps names, directions and weights", {
  values <- data.frame(a = c(1, 2, 3), b = c(3, 1, 2), row.names = c("x", "y", "z"))
  problem <- mem_problem(values, direction = c("max", "min"), weights = c(1, 0.5))
  expect_s3_class(problem, "mem_problem")
  expect_equal(problem$alternatives, c("x", "y", "z"))
  expect_equal(problem$direction, c(1, 0))
  expect_equal(problem$weights, c(1, 0.5))
  expect_output(print(problem), "3 alternatives, 2 criteria")
})

test_that("numeric directions and single values are recycled", {
  problem <- mem_problem(matrix(c(1, 2, 3, 4, 5, 6), 3), direction = 0, weights = 2)
  expect_equal(problem$direction, c(0, 0))
  expect_equal(problem$weights, c(2, 2))
  expect_equal(problem$alternatives, c("A1", "A2", "A3"))
})

test_that("bad inputs stop with a message", {
  good <- matrix(c(1, 2, 3, 4, 5, 6), 3)
  expect_error(mem_problem(matrix(c("a", "b", "c", "d"), 2)), "numeric")
  expect_error(mem_problem(matrix(c(1, NA, 3, 4), 2)), "missing")
  expect_error(mem_problem(matrix(1:2, 1)), "at least 2")
  expect_error(mem_problem(good, direction = "up"), "max")
  expect_error(mem_problem(good, direction = c("max", "min", "max")), "length")
  expect_error(mem_problem(good, weights = -1), "not negative")
  expect_error(mem_problem(good, groups = c("a", "b")), "one value per alternative")
  expect_error(mem_problem(good, complementarity = matrix(0, 3, 3)), "complementarity")
})

test_that("a criterion with a constant value gets a warning", {
  expect_warning(mem_problem(cbind(c(1, 2, 3), c(5, 5, 5))), "same value")
})

test_that("reading the CSV files gives the packaged data sets", {
  small <- read_mem_problem(system.file("extdata", "recruiting-small", package = "memga"))
  expect_equal(small, recruiting_small)
  large <- read_mem_problem(system.file("extdata", "recruiting-large", package = "memga"))
  expect_equal(large, recruiting_large)
})

test_that("reading reports missing files and columns", {
  expect_error(read_mem_problem(tempfile()), "not found")
  folder <- tempfile()
  dir.create(folder)
  writeLines(c("criterion,direction", "x,1"), file.path(folder, "criteria.csv"))
  expect_error(read_mem_problem(folder), "Missing columns")
})

test_that("the example data sets have the documented shape", {
  expect_equal(dim(recruiting_small$values), c(8L, 6L))
  expect_equal(recruiting_small$direction[recruiting_small$criteria == "Absences"], 0)
  expect_true(isSymmetric(unname(recruiting_small$complementarity)))
  expect_equal(dim(recruiting_large$values), c(300L, 8L))
  counts <- table(recruiting_large$groups)
  expect_equal(as.vector(counts[c("analyst", "engineer", "manager")]), c(150L, 90L, 60L))
})

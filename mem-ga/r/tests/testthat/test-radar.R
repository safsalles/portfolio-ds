test_that("the radar chart draws for both searches", {
  grDevices::pdf(NULL)
  on.exit(grDevices::dev.off())
  exhaustive <- memga(recruiting_small, size = 2)
  expect_no_error(memga_radar(exhaustive))
  expect_no_error(plot(exhaustive, compare = FALSE))
  ga <- memga(recruiting_large, method = "ga", control = ga_control(iterations = 100), seed = 1,
              quotas = c(analyst = 2, engineer = 1, manager = 1))
  expect_no_error(memga_radar(ga))
})

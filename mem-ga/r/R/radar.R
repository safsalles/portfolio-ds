RADAR_COLORS <- c(team = "#2a78d6", traditional = "#eb6834", all = "#898781")

#' Radar chart of the selected set
#'
#' Draws one axis per criterion and compares the average performance of the
#' selected set with the traditional choice and with the average of all
#' alternatives. A set that complements itself has no deep dips: where one
#' member is weak, another is strong.
#'
#' Values are the normalised performances, from 0 (worst) to 1 (best), so for
#' criteria in which less is better the axis is already inverted. When the
#' problem has groups, they are adjusted by group, as in the score, so a value
#' can pass 1.
#'
#' @param x A result from [memga()].
#' @param compare Show the traditional choice (`TRUE`, the default) or only the
#'   selected set (`FALSE`).
#' @param ... Not used.
#'
#' @return `NULL`, invisibly. Called for the chart.
#'
#' @examples
#' result <- memga(recruiting_small, size = 2)
#' memga_radar(result)
#' @export
memga_radar <- function(x, compare = TRUE, ...) {
  stopifnot(inherits(x, "memga"))
  payment <- x$fitted$payment
  index <- function(team) match(team, x$problem$alternatives)
  profiles <- list(`All alternatives` = list(values = colMeans(payment), color = RADAR_COLORS[["all"]],
                                              dash = TRUE, fill = FALSE))
  if (isTRUE(compare)) {
    profiles[["Traditional choice"]] <- list(
      values = colMeans(payment[index(x$traditional$team), , drop = FALSE]),
      color = RADAR_COLORS[["traditional"]], dash = FALSE, fill = FALSE)
  }
  profiles[["Selected set"]] <- list(
    values = colMeans(payment[index(x$team), , drop = FALSE]),
    color = RADAR_COLORS[["team"]], dash = FALSE, fill = TRUE)
  title <- paste0("Selected set: ", paste(x$team, collapse = ", "), " (", percent(x$score), ")")
  draw_radar(x$problem$criteria, profiles, title)
  invisible(NULL)
}

#' @rdname memga_radar
#' @export
plot.memga <- function(x, ...) {
  memga_radar(x, ...)
}

draw_radar <- function(labels, profiles, title) {
  count <- length(labels)
  angles <- pi / 2 - 2 * pi * (seq_len(count) - 1) / count
  top <- max(1, ceiling(max(vapply(profiles, function(p) max(p$values), numeric(1))) * 2) / 2)
  old <- graphics::par(mar = c(4, 1, 3, 1))
  on.exit(graphics::par(old), add = TRUE)
  graphics::plot(NA, xlim = c(-1.5, 1.5), ylim = c(-1.3, 1.3), asp = 1, axes = FALSE,
                 xlab = "", ylab = "", main = title, cex.main = 1)
  grid_color <- "#e1e0d9"
  circle <- seq(0, 2 * pi, length.out = 200)
  for (ring in seq(0.5, top, by = 0.5)) {
    graphics::lines(ring / top * cos(circle), ring / top * sin(circle), col = grid_color)
    graphics::text(0.02, ring / top, format(ring), cex = 0.6, col = "#898781", adj = c(0, -0.2))
  }
  graphics::segments(0, 0, cos(angles), sin(angles), col = grid_color)
  graphics::text(1.17 * cos(angles), 1.17 * sin(angles), labels, cex = 0.75,
                 adj = c(ifelse(abs(cos(angles)) < 0.15, 0.5, ifelse(cos(angles) > 0, 0, 1)), 0.5))
  for (profile in profiles) {
    radius <- profile$values / top
    px <- radius * cos(angles)
    py <- radius * sin(angles)
    fill <- if (profile$fill) grDevices::adjustcolor(profile$color, alpha.f = 0.18) else NA
    graphics::polygon(px, py, border = profile$color, col = fill, lwd = 2,
                      lty = if (profile$dash) 2 else 1)
  }
  graphics::legend("bottom", legend = names(profiles), inset = c(0, -0.1), xpd = TRUE,
                   horiz = FALSE, ncol = length(profiles), bty = "n", cex = 0.8,
                   col = vapply(profiles, function(p) p$color, character(1)),
                   lwd = 2, lty = vapply(profiles, function(p) if (p$dash) 2 else 1, numeric(1)))
}

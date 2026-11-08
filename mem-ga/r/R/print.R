percent <- function(x) sprintf("%.1f%%", 100 * x)

#' @export
print.memga <- function(x, top = 10, ...) {
  search <- if (x$method == "exhaustive") "exhaustive search" else "genetic algorithm"
  rule <- if (x$rule == "mean") "mean rule" else "minimum rule"
  cat("Multiple Choice Method: ", search, ", ", rule, ", tau ", format(x$tau), "\n", sep = "")
  cat(nrow(x$problem$values), " alternatives, ", ncol(x$problem$values),
      " criteria, selecting ", x$size, "\n\n", sep = "")

  if (x$method == "exhaustive") {
    shown <- utils::head(x$ranking, top)
    cat("Best sets (", nrow(x$ranking), " tested):\n", sep = "")
    print(data.frame(position = shown$position, set = shown$set,
                     score = percent(shown$score)), row.names = FALSE, right = FALSE)
    if (nrow(x$ranking) > top) cat("... ", nrow(x$ranking) - top, " more\n", sep = "")
  } else {
    cat("Selected: ", paste(x$team, collapse = ", "), " (", percent(x$score), ")\n", sep = "")
    if (!is.null(x$seed)) cat("Seed: ", x$seed, "\n", sep = "")
  }

  cat("\nTraditional choice (best one by one): ",
      paste(x$traditional$team, collapse = ", "), " (", percent(x$traditional$score), ")\n", sep = "")
  if (x$method == "exhaustive") {
    place <- x$ranking$position[match(
      TRUE, vapply(x$ranking$members, setequal, logical(1), x$traditional$team)
    )]
    if (!is.na(place) && length(x$traditional$team) == x$size) {
      cat("It ranks ", place, if (place == 1) "st" else if (place == 2) "nd" else if (place == 3) "rd" else "th",
          " in the Multiple Choice Method.\n", sep = "")
    }
  }
  invisible(x)
}

#' @export
summary.memga <- function(object, ...) {
  print(object, ...)
}

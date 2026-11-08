#' Define a selection problem
#'
#' Collects the data the Multiple Choice Method needs: how each alternative
#' performs on each criterion, which direction is better for each criterion,
#' how important each criterion is, and how much the criteria complement each
#' other.
#'
#' @param values A numeric matrix or data frame with one row per alternative and
#'   one column per criterion. Row names are used as the names of the
#'   alternatives and column names as the names of the criteria.
#' @param direction Either `"max"` (more is better) or `"min"` (less is better),
#'   one per criterion or a single value for all. Numeric `1` and `0` are
#'   accepted as `"max"` and `"min"`.
#' @param weights A non-negative importance weight for each criterion, or a
#'   single value for all.
#' @param groups Optional. The group of each alternative, for example a job
#'   role or a position. Criteria are then valued differently for each group,
#'   and `quotas` can be used in [memga()].
#' @param complementarity Optional. A symmetric criteria-by-criteria matrix in
#'   which a higher value means that the two criteria complement each other
#'   more. When omitted, it is computed from the data as one minus the absolute
#'   correlation between criteria (the conflict measure of the CRITIC method,
#'   Diakoulaki et al., 1995), within each group when `groups` is given.
#'
#' @return An object of class `mem_problem`.
#'
#' @examples
#' values <- data.frame(
#'   Planning = c(9.5, 9.3, 6.4, 7.6),
#'   Quality  = c(9.0, 8.8, 7.0, 7.8),
#'   Costs    = c(6.2, 6.0, 9.4, 7.4),
#'   Absences = c(2, 3, 4, 5),
#'   row.names = c("A1", "A2", "A3", "A4")
#' )
#' problem <- mem_problem(values, direction = c("max", "max", "max", "min"))
#' problem
#'
#' @references
#' Diakoulaki, D., Mavrotas, G. and Papayannakis, L. (1995). Determining
#' objective weights in multiple criteria problems: the CRITIC method.
#' *Computers & Operations Research*, 22(7), 763-770.
#' @export
mem_problem <- function(values, direction = "max", weights = 1, groups = NULL,
                        complementarity = NULL) {
  values <- as.matrix(values)
  if (!is.numeric(values)) {
    stop("`values` must be numeric.", call. = FALSE)
  }
  if (anyNA(values) || any(!is.finite(values))) {
    stop("`values` must not contain missing or infinite numbers.", call. = FALSE)
  }
  n_alternatives <- nrow(values)
  n_criteria <- ncol(values)
  if (n_alternatives < 2 || n_criteria < 2) {
    stop("The problem needs at least 2 alternatives and 2 criteria.", call. = FALSE)
  }
  alternatives <- rownames(values)
  if (is.null(alternatives)) alternatives <- paste0("A", seq_len(n_alternatives))
  criteria <- colnames(values)
  if (is.null(criteria)) criteria <- paste0("C", seq_len(n_criteria))
  dimnames(values) <- list(alternatives, criteria)
  if (anyDuplicated(alternatives)) {
    stop("The names of the alternatives must be unique.", call. = FALSE)
  }

  direction <- check_direction(direction, n_criteria)
  weights <- check_weights(weights, n_criteria)

  if (!is.null(groups)) {
    if (length(groups) != n_alternatives || anyNA(groups)) {
      stop("`groups` must have one value per alternative and no missing values.",
           call. = FALSE)
    }
    groups <- as.character(groups)
  }
  if (!is.null(complementarity)) {
    complementarity <- as.matrix(complementarity)
    if (!is.numeric(complementarity) || !identical(dim(complementarity), c(n_criteria, n_criteria)) ||
        anyNA(complementarity)) {
      stop("`complementarity` must be a numeric matrix with one row and one column per criterion.",
           call. = FALSE)
    }
    diag(complementarity) <- 0
    dimnames(complementarity) <- list(criteria, criteria)
  }

  constant <- criteria[apply(values, 2, function(x) max(x) == min(x))]
  if (length(constant) > 0) {
    warning("Criteria with the same value in every alternative do not tell the ",
            "alternatives apart: ", paste(constant, collapse = ", "), ".", call. = FALSE)
  }

  structure(
    list(
      values = values, direction = direction, weights = weights, groups = groups,
      complementarity = complementarity, alternatives = alternatives, criteria = criteria
    ),
    class = "mem_problem"
  )
}

check_direction <- function(direction, n_criteria) {
  if (is.character(direction)) {
    if (!all(direction %in% c("max", "min"))) {
      stop("`direction` must be \"max\" or \"min\".", call. = FALSE)
    }
    direction <- as.numeric(direction == "max")
  } else if (is.numeric(direction) || is.logical(direction)) {
    if (!all(direction %in% c(0, 1))) {
      stop("A numeric `direction` must be 1 (more is better) or 0 (less is better).",
           call. = FALSE)
    }
    direction <- as.numeric(direction)
  } else {
    stop("`direction` must be \"max\" or \"min\".", call. = FALSE)
  }
  if (!length(direction) %in% c(1, n_criteria)) {
    stop("`direction` must have length 1 or one value per criterion.", call. = FALSE)
  }
  rep_len(direction, n_criteria)
}

check_weights <- function(weights, n_criteria) {
  if (!is.numeric(weights) || anyNA(weights) || any(!is.finite(weights)) || any(weights < 0)) {
    stop("`weights` must be finite numbers that are not negative.", call. = FALSE)
  }
  if (!length(weights) %in% c(1, n_criteria)) {
    stop("`weights` must have length 1 or one value per criterion.", call. = FALSE)
  }
  rep_len(as.numeric(weights), n_criteria)
}

#' @export
print.mem_problem <- function(x, ...) {
  cat("<mem_problem>", nrow(x$values), "alternatives,", ncol(x$values), "criteria")
  if (!is.null(x$groups)) {
    counts <- table(x$groups)
    cat(", groups:", paste0(names(counts), " (", counts, ")", collapse = ", "))
  }
  cat("\n")
  info <- data.frame(
    direction = ifelse(x$direction == 1, "max", "min"),
    weight = x$weights,
    row.names = x$criteria
  )
  print(info)
  invisible(x)
}

#' Read a problem from CSV files
#'
#' Reads `criteria.csv`, `alternatives.csv` and, when it exists,
#' `complementarity.csv` from a folder.
#'
#' * `criteria.csv` has the columns `criterion`, `direction` (1 when more is
#'   better and 0 when less is better) and `weight`.
#' * `alternatives.csv` has the column `alternative`, one column per criterion
#'   and, optionally, a `group` column.
#' * `complementarity.csv` has the column `criterion` and one column per
#'   criterion. The diagonal is ignored.
#'
#' @param folder The folder with the files.
#'
#' @return An object of class `mem_problem`.
#'
#' @examples
#' folder <- system.file("extdata", "recruiting-small", package = "memga")
#' read_mem_problem(folder)
#' @export
read_mem_problem <- function(folder) {
  read_file <- function(name, required, optional = FALSE) {
    path <- file.path(folder, name)
    if (!file.exists(path)) {
      if (optional) return(NULL)
      stop("File not found: ", name, call. = FALSE)
    }
    data <- utils::read.csv(path, stringsAsFactors = FALSE, check.names = FALSE,
                            fileEncoding = "UTF-8-BOM", strip.white = TRUE)
    missing <- setdiff(required, names(data))
    if (length(missing) > 0) {
      stop("Missing columns in ", name, ": ", paste(missing, collapse = ", "), call. = FALSE)
    }
    data
  }
  criteria_data <- read_file("criteria.csv", c("criterion", "direction", "weight"))
  criteria <- criteria_data$criterion
  alternatives_data <- read_file("alternatives.csv", c("alternative", criteria))
  values <- as.matrix(alternatives_data[, criteria, drop = FALSE])
  rownames(values) <- alternatives_data$alternative
  groups <- if ("group" %in% names(alternatives_data)) alternatives_data$group else NULL

  complementarity <- NULL
  matrix_data <- read_file("complementarity.csv", c("criterion", criteria), optional = TRUE)
  if (!is.null(matrix_data)) {
    rownames(matrix_data) <- matrix_data$criterion
    complementarity <- as.matrix(matrix_data[criteria, criteria, drop = FALSE])
    complementarity[is.na(complementarity)] <- 0
  }

  mem_problem(values, direction = criteria_data$direction, weights = criteria_data$weight,
              groups = groups, complementarity = complementarity)
}

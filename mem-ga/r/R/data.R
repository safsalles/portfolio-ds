#' Small recruiting example
#'
#' A simulated problem for choosing 2 of 8 candidates for two openings, graded
#' from 0 to 10 on six criteria. Candidates A1 and A2 have the best averages
#' but are alike, strong in planning, logistics and quality and average in costs
#' and people, while A3 is the opposite. It is the kind of problem used to
#' present the method: the two best candidates one by one are not the best
#' pair.
#'
#' The criteria are Planning, Logistics, Quality, Costs, People and Absences
#' (less is better). The data is fictional.
#'
#' @format A [mem_problem()] with 8 alternatives and 6 criteria, with weights
#'   and a complementarity matrix.
#'
#' @examples
#' recruiting_small
#' memga(recruiting_small, size = 2)
"recruiting_small"

#' Large recruiting example
#'
#' A simulated problem for building a project team of 4 among 300 candidates:
#' 150 analysts, 90 engineers and 60 managers, graded from 0 to 10 on eight
#' criteria (sql, statistics, visualization, programming, communication,
#' leadership, negotiation and organization). Testing every possible team is
#' not practical, so the search is done with the genetic algorithm. The groups
#' are the job roles, and each role values the criteria differently. The
#' complementarity is computed from the data. The data is fictional.
#'
#' @format A [mem_problem()] with 300 alternatives, 8 criteria and 3 groups.
#'
#' @examples
#' recruiting_large
"recruiting_large"

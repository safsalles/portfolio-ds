# Builds the example data sets of the package from the Portuguese CSV files of the
# Python version, translating the names of criteria and groups.
#
# Run from the package folder: Rscript data-raw/make-data.R

source("R/problem.R")

source_folder <- file.path("..", "exemplos")
criteria_names <- c(
  Planejamento = "Planning", `Logística` = "Logistics", Qualidade = "Quality",
  Custos = "Costs", Pessoas = "People", Faltas = "Absences",
  sql = "sql", estatistica = "statistics", visualizacao = "visualization",
  programacao = "programming", comunicacao = "communication", lideranca = "leadership",
  negociacao = "negotiation", organizacao = "organization"
)
group_names <- c(analista = "analyst", engenheiro = "engineer", gestor = "manager")

translate <- function(x, map) ifelse(x %in% names(map), map[x], x)
read <- function(path) {
  utils::read.csv(path, stringsAsFactors = FALSE, check.names = FALSE, fileEncoding = "UTF-8-BOM")
}

convert <- function(from, to) {
  dir.create(to, recursive = TRUE, showWarnings = FALSE)
  criteria <- read(file.path(from, "criteria.csv"))
  criteria$criterion <- translate(criteria$criterion, criteria_names)
  utils::write.csv(criteria, file.path(to, "criteria.csv"), row.names = FALSE, fileEncoding = "UTF-8")

  alternatives <- read(file.path(from, "alternatives.csv"))
  names(alternatives) <- translate(names(alternatives), criteria_names)
  if ("group" %in% names(alternatives)) alternatives$group <- translate(alternatives$group, group_names)
  utils::write.csv(alternatives, file.path(to, "alternatives.csv"), row.names = FALSE, fileEncoding = "UTF-8")

  matrix_path <- file.path(from, "complementarity.csv")
  if (file.exists(matrix_path)) {
    complementarity <- read(matrix_path)
    names(complementarity) <- translate(names(complementarity), criteria_names)
    complementarity$criterion <- translate(complementarity$criterion, criteria_names)
    utils::write.csv(complementarity, file.path(to, "complementarity.csv"),
                     row.names = FALSE, na = "", fileEncoding = "UTF-8")
  }
}

convert(file.path(source_folder, "recrutamento-pequeno", "data"),
        file.path("inst", "extdata", "recruiting-small"))
convert(file.path(source_folder, "recrutamento-grande", "data"),
        file.path("inst", "extdata", "recruiting-large"))

recruiting_small <- read_mem_problem(file.path("inst", "extdata", "recruiting-small"))
recruiting_large <- read_mem_problem(file.path("inst", "extdata", "recruiting-large"))
save(recruiting_small, file = file.path("data", "recruiting_small.rda"), compress = "xz")
save(recruiting_large, file = file.path("data", "recruiting_large.rda"), compress = "xz")

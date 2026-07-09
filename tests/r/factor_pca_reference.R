#!/usr/bin/env Rscript

args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 1) {
  stop("usage: factor_pca_reference.R <frame.csv>", call. = FALSE)
}
if (!requireNamespace("psych", quietly = TRUE)) {
  stop("The R package 'psych' is required for factor_pca_reference.R", call. = FALSE)
}

frame <- read.csv(args[[1]], check.names = FALSE)
corr <- cor(frame)
n_obs <- nrow(frame)
variables <- colnames(frame)

cat_value <- function(name, value) {
  cat(sprintf("%s=%.17g\n", name, value))
}

kmo <- psych::KMO(corr)
bartlett <- psych::cortest.bartlett(corr, n = n_obs)
eigen_result <- eigen(corr, symmetric = TRUE)
eigenvalues <- eigen_result$values
eigenvectors <- eigen_result$vectors

for (component in seq_len(ncol(eigenvectors))) {
  column <- eigenvectors[, component]
  anchor <- which.max(abs(column))
  if (column[[anchor]] < 0) {
    eigenvectors[, component] <- -column
  }
}
loadings <- sweep(eigenvectors, 2, sqrt(pmax(eigenvalues, 0.0)), `*`)

cat_value("n_obs", n_obs)
cat_value("kmo_overall", kmo$MSA)
for (index in seq_along(variables)) {
  cat_value(paste0("kmo_", variables[[index]]), kmo$MSAi[[index]])
}
cat_value("bartlett_chi_square", bartlett$chisq)
cat_value("bartlett_df", bartlett$df)
cat_value("bartlett_p_value", bartlett$p.value)

for (index in seq_along(eigenvalues)) {
  cat_value(paste0("eigenvalue_", index), eigenvalues[[index]])
}
for (row in seq_along(variables)) {
  for (component in seq_len(ncol(loadings))) {
    cat_value(
      paste0("loading_", variables[[row]], "_PC", component),
      loadings[row, component]
    )
  }
}

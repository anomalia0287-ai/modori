#!/usr/bin/env Rscript

# Reproducible external check for Modori's McDonald's omega fixture.
# psych::omega accepts raw data frames and supports fm="ml"; see:
# https://personality-project.org/r/psych/help/omega.html

if (!requireNamespace("psych", quietly = TRUE)) {
  stop("The R package 'psych' is required for omega_reference.R", call. = FALSE)
}

fixture <- data.frame(
  q1 = c(1, 2, 3, 4, 5, 5, 4, 3),
  q2 = c(1, 2, 3, 4, 4, 5, 4, 3),
  q3 = c(2, 2, 3, 3, 5, 5, 4, 4),
  q4 = c(1, 3, 3, 4, 5, 4, 4, 3)
)

result <- psych::omega(
  fixture,
  nfactors = 1,
  fm = "ml",
  plot = FALSE,
  flip = FALSE
)

cat(sprintf("%.12f\n", result$omega.tot))

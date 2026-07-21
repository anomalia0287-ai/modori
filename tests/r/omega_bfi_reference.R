#!/usr/bin/env Rscript

args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 1) {
  stop("usage: omega_bfi_reference.R <frame.csv>", call. = FALSE)
}
if (!requireNamespace("psych", quietly = TRUE)) {
  stop("The R package 'psych' is required for omega_bfi_reference.R", call. = FALSE)
}

frame <- read.csv(args[[1]], check.names = FALSE)
result <- psych::omega(
  frame,
  nfactors = 1,
  fm = "ml",
  plot = FALSE,
  flip = FALSE
)
alpha <- psych::alpha(frame, warnings = FALSE)

cat(sprintf("omega_total=%.17g\n", result$omega.tot))
cat(sprintf("cronbach_alpha=%.17g\n", alpha$total$raw_alpha))

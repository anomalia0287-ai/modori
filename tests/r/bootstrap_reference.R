#!/usr/bin/env Rscript

args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 4) {
  stop(
    "usage: bootstrap_reference.R <mediation|model7|model14> <frame.csv> <indices.csv> <ci>",
    call. = FALSE
  )
}

model <- args[[1]]
frame <- read.csv(args[[2]], check.names = FALSE)
indices <- as.matrix(read.csv(args[[3]], header = FALSE, check.names = FALSE))
ci_level <- as.numeric(args[[4]])

if (!model %in% c("mediation", "model7", "model14")) {
  stop("unsupported bootstrap reference model", call. = FALSE)
}
if (!is.finite(ci_level) || ci_level <= 0.5 || ci_level >= 1.0) {
  stop("ci must be in (0.5, 1)", call. = FALSE)
}

percentile_ci <- function(values) {
  alpha <- 1.0 - ci_level
  as.numeric(quantile(
    values,
    probs = c(alpha / 2.0, 1.0 - alpha / 2.0),
    type = 7,
    names = FALSE
  ))
}

cat_value <- function(name, value) {
  cat(sprintf("%s=%.17g\n", name, value))
}

coef_value <- function(fit, name) {
  coefficients <- coef(fit)
  coefficient_names <- names(coefficients)
  backtick_name <- paste0("`", name, "`")
  if (name %in% coefficient_names) {
    return(as.numeric(coefficients[[name]]))
  }
  if (backtick_name %in% coefficient_names) {
    return(as.numeric(coefficients[[backtick_name]]))
  }
  if (!name %in% coefficient_names) {
    stop(paste("missing coefficient", name), call. = FALSE)
  }
}

effect_labels <- c("mean_minus_1sd", "mean", "mean_plus_1sd")
effect_points <- function(moderator_sd) {
  c(-moderator_sd, 0.0, moderator_sd)
}

indirect <- c()
index_values <- c()
effects <- list(
  mean_minus_1sd = c(),
  mean = c(),
  mean_plus_1sd = c()
)
moderator_sd <- if (model == "mediation") NA_real_ else sd(frame[["w"]])

for (row_index in seq_len(nrow(indices))) {
  sample <- frame[as.integer(indices[row_index, ]), , drop = FALSE]

  if (model == "mediation") {
    mediator_fit <- lm(m ~ x + c1, data = sample)
    outcome_fit <- lm(y ~ x + m + c1, data = sample)
    indirect <- c(indirect, coef_value(mediator_fit, "x") * coef_value(outcome_fit, "m"))
  } else if (model == "model7") {
    mediator_fit <- lm(
      m ~ x_centered + w_centered + `x_centered:w_centered` + c1,
      data = sample
    )
    outcome_fit <- lm(y ~ x_centered + m + c1, data = sample)
    a1 <- coef_value(mediator_fit, "x_centered")
    a3 <- coef_value(mediator_fit, "x_centered:w_centered")
    b <- coef_value(outcome_fit, "m")
    points <- effect_points(moderator_sd)
    for (i in seq_along(effect_labels)) {
      label <- effect_labels[[i]]
      effects[[label]] <- c(effects[[label]], (a1 + a3 * points[[i]]) * b)
    }
    index_values <- c(index_values, a3 * b)
  } else {
    mediator_fit <- lm(m ~ x_centered + c1, data = sample)
    outcome_fit <- lm(y ~ x_centered + m + w_centered + `m:w_centered` + c1, data = sample)
    a <- coef_value(mediator_fit, "x_centered")
    b1 <- coef_value(outcome_fit, "m")
    b3 <- coef_value(outcome_fit, "m:w_centered")
    points <- effect_points(moderator_sd)
    for (i in seq_along(effect_labels)) {
      label <- effect_labels[[i]]
      effects[[label]] <- c(effects[[label]], a * (b1 + b3 * points[[i]]))
    }
    index_values <- c(index_values, a * b3)
  }
}

if (model == "mediation") {
  ci <- percentile_ci(indirect)
  cat_value("indirect_low", ci[[1]])
  cat_value("indirect_high", ci[[2]])
} else {
  for (label in effect_labels) {
    ci <- percentile_ci(effects[[label]])
    cat_value(paste0("effect_", label, "_low"), ci[[1]])
    cat_value(paste0("effect_", label, "_high"), ci[[2]])
  }
  ci <- percentile_ci(index_values)
  cat_value("index_low", ci[[1]])
  cat_value("index_high", ci[[2]])
}

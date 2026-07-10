#!/usr/bin/env Rscript

args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 2) {
  stop("usage: logistic_regression_reference.R <csv> <continuous|categorical>", call. = FALSE)
}

data_path <- args[[1]]
mode <- args[[2]]
frame <- read.csv(data_path, na.strings = c("", "NA"), check.names = FALSE)

if (mode == "continuous") {
  formula <- event ~ x1 + x2
} else if (mode == "categorical") {
  frame$group <- factor(frame$group, levels = c("control", "treat", "placebo"))
  formula <- event ~ x1 + group
} else {
  stop("unsupported mode", call. = FALSE)
}

control <- glm.control(epsilon = 1e-14, maxit = 200, trace = FALSE)
fit <- glm(formula, data = frame, family = binomial(link = "logit"), control = control)
null_fit <- glm(event ~ 1, data = model.frame(fit), family = binomial(link = "logit"), control = control)

if (!isTRUE(fit$converged) || !isTRUE(null_fit$converged)) {
  stop("R logistic reference did not converge", call. = FALSE)
}

coefficient_table <- summary(fit)$coefficients
model_matrix <- model.matrix(fit)
fitted_probabilities <- fitted(fit)
weighted_design <- model_matrix * sqrt(fitted_probabilities * (1 - fitted_probabilities))
fisher_covariance <- solve(crossprod(weighted_design))
fisher_standard_errors <- sqrt(diag(fisher_covariance))
log_likelihood <- as.numeric(logLik(fit))
null_log_likelihood <- as.numeric(logLik(null_fit))
lr <- 2 * (log_likelihood - null_log_likelihood)
df <- length(coef(fit)) - 1

emit_vector <- function(name, values) {
  formatted <- paste(formatC(as.numeric(values), digits = 17, format = "g"), collapse = ",")
  cat(name, "=", formatted, "\n", sep = "")
}

emit_scalar <- function(name, value) {
  cat(name, "=", formatC(as.numeric(value), digits = 17, format = "g"), "\n", sep = "")
}

emit_vector("coef", coef(fit))
emit_vector("se", fisher_standard_errors)
emit_vector("glm_summary_se", coefficient_table[, "Std. Error"])
emit_vector("fitted", fitted_probabilities)
emit_scalar("log_likelihood", log_likelihood)
emit_scalar("null_log_likelihood", null_log_likelihood)
emit_scalar("deviance", deviance(fit))
emit_scalar("aic", AIC(fit))
emit_scalar("lr", lr)
emit_scalar("df", df)
emit_scalar("lr_p", pchisq(lr, df = df, lower.tail = FALSE))
emit_scalar("nobs", nobs(fit))

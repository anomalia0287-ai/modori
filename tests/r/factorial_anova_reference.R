args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 3) {
  stop("Usage: factorial_anova_reference.R <csv> <factor_a_levels_csv> <factor_b_levels_csv>")
}

frame <- read.csv(args[[1]], stringsAsFactors = FALSE, check.names = FALSE)
required <- c("y", "factor_a", "factor_b")
if (!identical(names(frame), required)) {
  stop("Reference CSV must contain exactly y,factor_a,factor_b")
}

levels_a <- strsplit(args[[2]], ",", fixed = TRUE)[[1]]
levels_b <- strsplit(args[[3]], ",", fixed = TRUE)[[1]]
frame$factor_a <- factor(frame$factor_a, levels = levels_a)
frame$factor_b <- factor(frame$factor_b, levels = levels_b)
if (anyNA(frame) || any(!is.finite(frame$y))) {
  stop("Reference frame contains missing, unknown-level, or non-finite values")
}

options(contrasts = c("contr.sum", "contr.poly"))
fit <- lm(y ~ factor_a * factor_b, data = frame)
design <- model.matrix(fit)
assignment <- attr(design, "assign")
coefficients <- coef(fit)
covariance <- vcov(fit)
df_error <- df.residual(fit)
sse <- sum(residuals(fit)^2)
mse <- sse / df_error

wald <- function(term_index) {
  indices <- which(assignment == term_index)
  if (length(indices) == 0 || anyNA(coefficients[indices])) {
    stop(paste("Missing full-rank coefficient block for term", term_index))
  }
  beta <- coefficients[indices]
  block <- covariance[indices, indices, drop = FALSE]
  f_value <- as.numeric(t(beta) %*% solve(block, beta) / length(indices))
  list(
    ss = f_value * length(indices) * mse,
    df = length(indices),
    f = f_value,
    p = pf(f_value, length(indices), df_error, lower.tail = FALSE)
  )
}

effect_a <- wald(1)
effect_b <- wald(2)
interaction <- wald(3)

emit <- function(key, value) {
  cat(key, "=", format(value, digits = 17, scientific = TRUE), "\n", sep = "")
}

emit("effect_a_ss", effect_a$ss)
emit("effect_a_df", effect_a$df)
emit("effect_a_f", effect_a$f)
emit("effect_a_p", effect_a$p)
emit("effect_b_ss", effect_b$ss)
emit("effect_b_df", effect_b$df)
emit("effect_b_f", effect_b$f)
emit("effect_b_p", effect_b$p)
emit("interaction_ss", interaction$ss)
emit("interaction_df", interaction$df)
emit("interaction_f", interaction$f)
emit("interaction_p", interaction$p)
emit("df_error", df_error)
emit("sse", sse)
emit("mse", mse)

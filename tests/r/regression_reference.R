if (!requireNamespace("sandwich", quietly = TRUE)) {
  stop("R package 'sandwich' is required", call. = FALSE)
}

model <- lm(mpg ~ wt + hp + cyl, data = mtcars)
x <- model.matrix(model)
classic <- summary(model)
coef_table <- classic$coefficients
hc3_cov <- sandwich::vcovHC(model, type = "HC3")
hc3_se <- sqrt(diag(hc3_cov))
hc3_t <- coef(model) / hc3_se
hc3_p <- 2 * pt(abs(hc3_t), df = df.residual(model), lower.tail = FALSE)

vif_values <- sapply(c("wt", "hp", "cyl"), function(predictor) {
  other_predictors <- setdiff(c("wt", "hp", "cyl"), predictor)
  rhs <- paste(other_predictors, collapse = " + ")
  vif_model <- lm(as.formula(paste(predictor, "~", rhs)), data = mtcars)
  1 / (1 - summary(vif_model)$r.squared)
})

fmt_vec <- function(x) {
  paste(formatC(as.numeric(x), digits = 12, format = "fg", flag = "#"), collapse = ",")
}

cat("{")
cat("\"classical\":{")
cat("\"coef\":[", fmt_vec(coef(model)), "],", sep = "")
cat("\"se\":[", fmt_vec(coef_table[, "Std. Error"]), "],", sep = "")
cat("\"r_squared\":", formatC(classic$r.squared, digits = 12, format = "fg", flag = "#"), ",", sep = "")
cat("\"f\":", formatC(unname(classic$fstatistic[1]), digits = 12, format = "fg", flag = "#"), ",", sep = "")
cat("\"vif\":[", fmt_vec(vif_values), "]", sep = "")
cat("},")
cat("\"hc3\":{")
cat("\"se\":[", fmt_vec(hc3_se), "],", sep = "")
cat("\"t\":[", fmt_vec(hc3_t), "],", sep = "")
cat("\"p\":[", fmt_vec(hc3_p), "]", sep = "")
cat("}")
cat("}\n")

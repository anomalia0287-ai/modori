#!/usr/bin/env Rscript

cat_value <- function(name, value) {
  cat(sprintf("%s=%.17g\n", name, value))
}

mwu_x <- c(1, 1, 1, 1, 10, 10)
mwu_y <- c(5, 6, 7, 8, 9, 10)
mwu <- wilcox.test(mwu_x, mwu_y, exact = FALSE, correct = TRUE)
cat_value("mann_whitney_statistic", as.numeric(mwu$statistic))
cat_value("mann_whitney_p_value", mwu$p.value)

before <- c(10, 11, 12, 13, 14, 15, 16)
after <- c(10, 12, 13, 15, 14, 19, 21)
wilcoxon <- wilcox.test(after, before, paired = TRUE, exact = FALSE, correct = TRUE)
cat_value("wilcoxon_r_v_statistic", as.numeric(wilcoxon$statistic))
cat_value("wilcoxon_p_value", wilcoxon$p.value)

kruskal <- kruskal.test(list(
  c(1, 1, 2, 2),
  c(2, 3, 3, 3),
  c(4, 4, 5, 5)
))
cat_value("kruskal_statistic", as.numeric(kruskal$statistic))
cat_value("kruskal_df", as.numeric(kruskal$parameter))
cat_value("kruskal_p_value", kruskal$p.value)

friedman_frame <- data.frame(
  pre = c(1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 5),
  mid = c(1, 2, 2, 3, 3, 4, 4, 5, 5, 5, 5),
  post = c(2, 2, 3, 3, 4, 4, 5, 5, 5, 5, 5)
)
friedman <- friedman.test(as.matrix(friedman_frame))
cat_value("friedman_statistic", as.numeric(friedman$statistic))
cat_value("friedman_df", as.numeric(friedman$parameter))
cat_value("friedman_p_value", friedman$p.value)

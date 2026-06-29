# Kaggle Read-Only Learning Notes

Date: 2026-06-29

Scope and limits:

- Public Kaggle notebook pages were viewed in browser/read-only mode.
- No login, API use, file download, dataset download, notebook execution, package installation, upload, copy/edit, or local code import was performed.
- Observations below are conceptual comparison notes, not code to copy.

Public notebooks viewed:

- https://www.kaggle.com/code/pmarcelino/comprehensive-data-exploration-with-python
- https://www.kaggle.com/code/serigne/stacked-regressions-top-4-on-leaderboard
- https://www.kaggle.com/code/startupsci/titanic-data-science-solutions

Official documentation used to validate which patterns are production-suitable:

- scikit-learn pipelines and composite estimators: https://scikit-learn.org/stable/modules/compose.html
- scikit-learn cross-validation: https://scikit-learn.org/stable/modules/cross_validation.html
- pandas scaling guidance: https://pandas.pydata.org/docs/user_guide/scale.html

## Useful Patterns

### 1. Analysis flow should be staged and explainable

The strongest reusable pattern is not a specific code block. It is the order of reasoning:

1. define the problem and target variable,
2. inspect variable meaning and expected relevance,
3. run univariate summaries,
4. run multivariate relationships,
5. handle missing data, outliers, and categorical features,
6. test assumptions,
7. compare models or diagnostics,
8. explain the result in user-facing language.

TongTong already has an educational/reporting direction. The improvement opportunity is to make this sequence explicit in the app and report output, especially around why a variable was included, excluded, transformed, or warned about.

### 2. Correlation and scatter diagnostics are useful, but need guardrails

The EDA notebook pattern uses correlation heatmaps, pairwise scatter plots, and target-distribution checks to orient the user quickly.

For TongTong this should become a bounded diagnostic layer:

- cap the number of variables shown by default,
- prefer top-N relevant relationships instead of full dense plots,
- warn when sample size is too small,
- distinguish exploratory correlation from causal or model-backed claims,
- keep chart generation deterministic and reproducible.

### 3. Missing-data handling should be explicit and justified

The notebooks make missingness visible before transforming data. That is a useful UX and reporting pattern.

For TongTong, each automatic or user-selected missing-data action should carry:

- count and percent missing,
- affected variables,
- method used,
- reason/warning,
- downstream effect on sample size or model eligibility.

This aligns with the existing project principle that silent failure and silent mutation are unacceptable.

### 4. Modeling code should prefer pipelines for repeatable preprocessing

The modeling notebook uses scikit-learn pipeline-style composition, scaling, cross-validation, model comparison, and ensemble wrappers.

The production-suitable version for TongTong is not Kaggle-style global notebook state. It is a typed, testable pipeline object:

- preprocessing and model steps stay together,
- cross-validation uses explicit splitter settings,
- random seeds are fixed where randomness exists,
- preprocessing statistics are learned only from the training fold,
- feature names and warnings are preserved for reporting.

This is supported by scikit-learn's own guidance on pipelines and cross-validation.

### 5. Cross-validation and model comparison should report uncertainty

Kaggle notebooks commonly show mean score and variation across folds. That pattern is useful for user trust, provided the UI states the limitation clearly.

For TongTong:

- expose fold count, splitter type, seed, metric, mean, and spread,
- avoid claiming generalization when the sample is too small,
- warn when i.i.d. assumptions are questionable,
- keep model comparison optional and scoped to the app's educational promise.

## Patterns Not To Copy

### 1. Unbounded file reads

Kaggle notebooks usually read a known competition file directly into memory. That is acceptable in a controlled notebook environment but not acceptable for a desktop app that opens arbitrary user files.

TongTong should keep the earlier audit finding as high priority: preview/import must enforce file size, row, column, and cell limits.

### 2. Global notebook state

The notebooks rely on mutable top-level variables, sequential cell execution, and implicit state.

TongTong should keep deterministic, replayable step objects and avoid notebook-style hidden dependencies.

### 3. Warning suppression

Some notebooks suppress warnings globally to keep output clean.

TongTong should not suppress warnings globally. Warnings should become structured diagnostics or explicit user-facing notes.

### 4. Competition-score optimization

Leaderboard code often favors predictive score over interpretability, maintainability, dependency minimality, and explainability.

TongTong's priority is educational trustworthiness and reproducible statistical reporting, so ensemble-heavy or external-booster patterns should not be added unless a clear product requirement exists.

### 5. Copying user-generated code

Kaggle code is user-generated and license/quality varies. The viewed notebooks are useful as examples of analysis communication, but code should not be copied into this repository.

## Concrete Impact On TongTong Priorities

The Kaggle read-only pass strengthens these priorities from the security/code-health review:

1. bounded import/preview is still the first fix,
2. variable diagnostics should be staged and explainable,
3. missing-data and outlier handling need explicit report provenance,
4. any future model-comparison feature should use scikit-learn-style pipelines and explicit cross-validation settings,
5. notebook-style global state, warning suppression, and full-memory assumptions should be treated as anti-patterns for this app.


from __future__ import annotations

FORBIDDEN_STATISTICS_IMPORTS = {
    "factor_analyzer",
    "math",
    "numpy",
    "pandas",
    "pingouin",
    "scipy",
    "sklearn",
    "statistics",
    "statsmodels",
}

FORBIDDEN_REDUCTION_CALLS = {
    "agg",
    "corr",
    "cov",
    "describe",
    "groupby",
    "mean",
    "median",
    "quantile",
    "sem",
    "std",
    "sum",
    "var",
}

FORBIDDEN_NETWORK_IMPORTS = {
    "httpx",
    "requests",
    "socket",
    "urllib",
    "webbrowser",
}

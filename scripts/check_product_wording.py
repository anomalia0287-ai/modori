from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
import re


PRODUCT_ROOTS = (Path("src/modori"), Path("library"))
OPTIONAL_PRODUCT_ROOTS = (Path("README.md"), Path("docs/product"))
HISTORICAL_ALLOWLIST = {
    Path("src/modori/recommendation_baseline.py"),
    Path("src/modori/recommendation_benchmark.py"),
    Path("src/modori/recommendation_benchmark_io.py"),
}
TEXT_SUFFIXES = {".py", ".qml", ".json", ".yaml", ".yml", ".md"}
BANNED = (
    "강한 추천",
    "기본 추천",
    "추천 분석 실행",
    "strong recommendation",
    "expert-level recommendation",
    "전문가 수준 추천",
)
BANNED_PATTERNS = (
    (
        "recommendation-accuracy-percentage",
        re.compile(
            r"(?:추천|recommendation)[^\n]{0,40}\d+(?:\.\d+)?\s*%",
            re.IGNORECASE,
        ),
    ),
    (
        "expert-equivalence-claim",
        re.compile(
            r"(?:전문가[^\n]{0,20}(?:동등|같은 수준)|"
            r"(?:equal|equivalent|matches)[^\n]{0,20}expert|"
            r"expert[^\n]{0,20}(?:equal|equivalent|matches))",
            re.IGNORECASE,
        ),
    ),
)


def _text_files(path: Path) -> Iterable[Path]:
    if path.is_file():
        if path.suffix.lower() in TEXT_SUFFIXES:
            yield path
        return
    if not path.is_dir():
        return
    yield from sorted(
        candidate
        for candidate in path.rglob("*")
        if candidate.is_file() and candidate.suffix.lower() in TEXT_SUFFIXES
    )


def product_wording_violations(repository_root: Path) -> tuple[str, ...]:
    repository_root = repository_root.resolve()
    paths: list[Path] = []
    for relative_root in (*PRODUCT_ROOTS, *OPTIONAL_PRODUCT_ROOTS):
        paths.extend(_text_files(repository_root / relative_root))

    violations: list[str] = []
    for path in sorted(set(paths)):
        relative = path.relative_to(repository_root)
        if relative in HISTORICAL_ALLOWLIST:
            continue
        text = path.read_text(encoding="utf-8")
        folded = text.casefold()
        for phrase in BANNED:
            if phrase.casefold() in folded:
                violations.append(f"{relative.as_posix()}:{phrase}")
        for label, pattern in BANNED_PATTERNS:
            if pattern.search(text):
                violations.append(f"{relative.as_posix()}:{label}")
    return tuple(sorted(violations))

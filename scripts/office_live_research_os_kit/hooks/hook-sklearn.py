"""Collect only scikit-learn files required by the frozen runtime."""

from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files


SOURCE_ONLY_SUFFIXES = frozenset(
    {
        ".build",
        ".c",
        ".cpp",
        ".h",
        ".lib",
        ".pxd",
        ".pxi",
        ".pyi",
        ".pyx",
        ".tp",
    }
)
SOURCE_ONLY_DIRECTORIES = frozenset({"src", "tests"})


def _is_runtime_data(source: str, destination: str) -> bool:
    destination_parts = {part.casefold() for part in Path(destination).parts}
    if not destination_parts.isdisjoint(SOURCE_ONLY_DIRECTORIES):
        return False
    return Path(source).suffix.casefold() not in SOURCE_ONLY_SUFFIXES


datas = [
    item for item in collect_data_files("sklearn") if _is_runtime_data(item[0], item[1])
]

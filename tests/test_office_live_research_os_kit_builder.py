from __future__ import annotations

from dataclasses import replace
import hashlib
import importlib.util
import io
from pathlib import Path
import re
import runpy
import zipfile

import pytest

from scripts.build_office_live_research_os_kit import (
    BENCHMARK_EXECUTABLE_NAME,
    PACKAGE_LOCK_SOURCE,
    PYINSTALLER_BUILD_NAME,
    PYINSTALLER_HOOK_SOURCE,
    RUNTIME_IDENTITY_RESOURCE_NAME,
    TEMPLATE_SOURCE_FILES,
    KitBuildError,
    KitSource,
    OuterBuildRequest,
    RuntimeProduct,
    _clean_head,
    build_outer_kit,
    build_pyinstaller_command,
    validate_pyinstaller_diagnostics,
    validate_runtime_member_names,
)
from scripts.live_research_os_office_kit import (
    BUILDER_CONTRACT_VERSION,
    VERIFIER_CONTRACT_VERSION,
    KitIdentity,
    PackageLockEntry,
    identity_bytes,
    package_lock_bytes,
    parse_manifest,
    sha256_bytes,
)


SOURCE_COMMIT = "1" * 40


def _lock() -> bytes:
    return package_lock_bytes(
        (
            PackageLockEntry("numpy", "2.5.0"),
            PackageLockEntry("pandas", "3.0.3"),
            PackageLockEntry("pyinstaller", "6.21.0"),
            PackageLockEntry("pyside6", "6.11.1"),
        )
    )


def _identity() -> KitIdentity:
    return KitIdentity(
        source_commit=SOURCE_COMMIT,
        source_date_epoch=1_752_000_000,
        protocol_digest="2" * 64,
        fixture_digest="3" * 64,
        python_version="3.12.10",
        sqlite_version="3.49.1",
        pyside_version="6.11.1",
        numpy_version="2.5.0",
        pandas_version="3.0.3",
        pyinstaller_version="6.21.0",
        pyinstaller_bootloader_sha256="4" * 64,
        package_lock_sha256=sha256_bytes(_lock()),
        executable_path=f"runtime/{BENCHMARK_EXECUTABLE_NAME}.exe",
        runtime_layout="pyinstaller_onefolder_console",
        builder_contract_version=BUILDER_CONTRACT_VERSION,
        verifier_contract_version=VERIFIER_CONTRACT_VERSION,
        result_schema_id="modori.live_research_os_office_benchmark",
        result_schema_version=1,
    )


def _runtime(tmp_path: Path, *, identity: KitIdentity | None = None) -> RuntimeProduct:
    identity = identity or _identity()
    root = tmp_path / "runtime-product"
    internal = root / "_internal"
    plugins = internal / "PySide6" / "plugins" / "platforms"
    plugins.mkdir(parents=True)
    (root / f"{BENCHMARK_EXECUTABLE_NAME}.exe").write_bytes(b"MZ-runtime")
    (internal / "python312.dll").write_bytes(b"python")
    (internal / "numpy-core.pyd").write_bytes(b"numpy")
    (internal / "pandas-core.pyd").write_bytes(b"pandas")
    (internal / "PySide6" / "Qt6Core.dll").write_bytes(b"qt")
    (plugins / "qwindows.dll").write_bytes(b"platform")
    (internal / RUNTIME_IDENTITY_RESOURCE_NAME).write_bytes(identity_bytes(identity))
    return RuntimeProduct(root=root, identity=identity)


def _source() -> KitSource:
    return KitSource(
        command_template=(b"@echo off\nrem __POWERSHELL_SHA256__\n"),
        powershell_template=(
            b"$Manifest='__MANIFEST_SHA256__'\n$Identity='__IDENTITY_SHA256__'\n"
        ),
        readme="사용 안내\n".encode(),
        package_lock=_lock(),
    )


def _request(
    tmp_path: Path, *, runtime: RuntimeProduct | None = None
) -> OuterBuildRequest:
    return OuterBuildRequest(
        output_dir=(tmp_path / "dist" / "live-research-os-office").resolve(),
        runtime=runtime or _runtime(tmp_path),
        source=_source(),
    )


def _member(result, relative: str) -> bytes:
    with zipfile.ZipFile(result.archive) as archive:
        return archive.read(f"{result.kit_name}/{relative}")


def test_pyinstaller_command_is_dedicated_onedir_console_and_closed(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repo"
    repository.mkdir()
    identity_resource = tmp_path / RUNTIME_IDENTITY_RESOURCE_NAME
    identity_resource.write_bytes(b"{}")
    command = build_pyinstaller_command(
        repository_root=repository,
        identity_resource=identity_resource,
        work_root=tmp_path / "work",
    )
    assert command[:3] == [str(Path(__import__("sys").executable)), "-m", "PyInstaller"]
    assert "--onedir" in command
    assert "--console" in command
    assert "--onefile" not in command
    assert "--windowed" not in command
    assert command[command.index("--name") + 1] == PYINSTALLER_BUILD_NAME
    assert command[command.index("--distpath") + 1] == str(tmp_path / "work" / "d")
    assert command[command.index("--workpath") + 1] == str(tmp_path / "work" / "w")
    assert command[command.index("--specpath") + 1] == str(tmp_path / "work" / "s")
    assert command[command.index("--additional-hooks-dir") + 1] == str(
        repository / PYINSTALLER_HOOK_SOURCE
    )
    assert command[-1] == str(
        repository / "scripts" / "run_office_live_research_os_benchmark.py"
    )
    joined = "\n".join(command).casefold()
    for required in ("numpy", "pandas", "pyside6.qtcore"):
        assert required in joined
    assert "modori.exe" not in joined


def test_outer_builder_is_byte_identical_for_three_repacks(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path / "shared")
    results = tuple(
        build_outer_kit(_request(tmp_path / str(index), runtime=runtime))
        for index in range(3)
    )
    assert len({result.archive.read_bytes() for result in results}) == 1
    assert len({result.archive_sha256 for result in results}) == 1
    for result in results:
        assert result.digest_file.read_text(encoding="ascii") == (
            f"{result.archive_sha256}  {result.archive.name}\n"
        )


def test_outer_builder_creates_complete_manifest_identity_bootstrap_chain(
    tmp_path: Path,
) -> None:
    result = build_outer_kit(_request(tmp_path))
    identity = _member(result, "KIT-IDENTITY.json")
    manifest = _member(result, "MANIFEST.json")
    powershell = _member(result, "VERIFY-AND-RUN.ps1")
    command = _member(result, "RUN-MODORI-LIVE-RESEARCH-OS-BENCHMARK.cmd")
    assert hashlib.sha256(identity).hexdigest().encode() in powershell
    assert hashlib.sha256(manifest).hexdigest().encode() in powershell
    assert hashlib.sha256(powershell).hexdigest().encode() in command
    assert b"__IDENTITY_SHA256__" not in powershell
    assert b"__MANIFEST_SHA256__" not in powershell
    assert b"__POWERSHELL_SHA256__" not in command
    assert b"\r\n" in command
    assert b"\n" not in command.replace(b"\r\n", b"")

    paths = {entry.path for entry in parse_manifest(manifest)}
    assert {
        "KIT-IDENTITY.json",
        "PACKAGE-LOCK.json",
        "README-KO.txt",
        f"runtime/{BENCHMARK_EXECUTABLE_NAME}.exe",
        f"runtime/_internal/{RUNTIME_IDENTITY_RESOURCE_NAME}",
        "runtime/_internal/PySide6/Qt6Core.dll",
        "runtime/_internal/PySide6/plugins/platforms/qwindows.dll",
        "runtime/_internal/numpy-core.pyd",
        "runtime/_internal/pandas-core.pyd",
        "runtime/_internal/python312.dll",
    } == paths


def test_archive_has_one_root_sorted_entries_and_no_repository_material(
    tmp_path: Path,
) -> None:
    result = build_outer_kit(_request(tmp_path))
    with zipfile.ZipFile(result.archive) as archive:
        names = tuple(info.filename for info in archive.infolist())
    assert names == tuple(sorted(names))
    assert all(name.startswith(result.kit_name + "/") for name in names)
    assert any(name.endswith("/results/") for name in names)
    assert any(name.endswith("/work/") for name in names)
    forbidden = re.compile(r"(?:^|/)(?:\.git|\.venv|tests|fixtures|src)(?:/|$)")
    assert not any(forbidden.search(name) for name in names)


def test_builder_rejects_runtime_identity_mismatch_extra_link_and_case_collision(
    tmp_path: Path,
) -> None:
    mismatched = _runtime(tmp_path / "mismatch")
    mismatched_identity = replace(mismatched.identity, source_commit="2" * 40)
    with pytest.raises(KitBuildError, match="runtime identity"):
        build_outer_kit(
            _request(
                tmp_path / "one",
                runtime=RuntimeProduct(
                    root=mismatched.root,
                    identity=mismatched_identity,
                ),
            )
        )

    linked = _runtime(tmp_path / "linked")
    link = linked.root / "_internal" / "linked.dll"
    try:
        link.symlink_to(linked.root / "_internal" / "python312.dll")
    except OSError:
        pytest.skip("symlink creation is unavailable")
    with pytest.raises(KitBuildError, match="link|reparse"):
        build_outer_kit(_request(tmp_path / "two", runtime=linked))

    with pytest.raises(KitBuildError, match="case-colliding"):
        validate_runtime_member_names(
            ("_internal/python312.dll", "_internal/PYTHON312.DLL")
        )


def test_builder_rejects_overwrite_noncanonical_lock_and_output_escape(
    tmp_path: Path,
) -> None:
    request = _request(tmp_path)
    build_outer_kit(request)
    with pytest.raises(KitBuildError, match="exists"):
        build_outer_kit(request)
    with pytest.raises(KitBuildError, match="package lock"):
        build_outer_kit(
            replace(
                _request(tmp_path / "lock"),
                source=replace(_source(), package_lock=_lock() + b"\n"),
            )
        )
    with pytest.raises(KitBuildError, match="dedicated output"):
        build_outer_kit(
            replace(
                _request(tmp_path / "escape"), output_dir=(tmp_path / "dist").resolve()
            )
        )


@pytest.mark.parametrize(
    "diagnostics",
    (
        "WARNING: hidden import 'modori.fake' not found",
        "ERROR: build failed",
        "Traceback (most recent call last):",
    ),
)
def test_unexpected_pyinstaller_diagnostics_are_rejected(diagnostics: str) -> None:
    with pytest.raises(KitBuildError, match="diagnostic"):
        validate_pyinstaller_diagnostics(diagnostics)
    assert validate_pyinstaller_diagnostics("") == ()


def test_scipy_118_hook_removes_only_the_retired_cdflib_hidden_import() -> None:
    assert importlib.util.find_spec("scipy.special._cdflib") is None
    namespace = runpy.run_path(
        "scripts/office_live_research_os_kit/hooks/hook-scipy.special._ufuncs.py"
    )
    assert namespace["hiddenimports"] == [
        "scipy.special._ufuncs_cxx",
        "scipy.special._special_ufuncs",
    ]


def test_sklearn_hook_keeps_runtime_data_without_tests_or_build_sources() -> None:
    namespace = runpy.run_path(
        "scripts/office_live_research_os_kit/hooks/hook-sklearn.py"
    )
    datas = tuple(namespace["datas"])
    forbidden_suffixes = namespace["SOURCE_ONLY_SUFFIXES"]

    assert datas
    assert any(
        "datasets\\data" in destination.casefold()
        and Path(source).suffix.casefold() == ".gz"
        for source, destination in datas
    )
    assert any(Path(source).suffix.casefold() == ".dll" for source, _ in datas)
    for source, destination in datas:
        parts = {part.casefold() for part in Path(destination).parts}
        assert parts.isdisjoint({"tests", "src"})
        assert Path(source).suffix.casefold() not in forbidden_suffixes


def test_templates_are_powershell_51_literal_offline_and_non_elevating() -> None:
    root = Path("scripts/office_live_research_os_kit")
    command = (root / "RUN-MODORI-LIVE-RESEARCH-OS-BENCHMARK.cmd.in").read_text(
        encoding="utf-8"
    )
    powershell = (root / "VERIFY-AND-RUN.ps1.in").read_text(encoding="utf-8")
    assert command.count("__POWERSHELL_SHA256__") == 1
    assert powershell.count("__MANIFEST_SHA256__") == 1
    assert powershell.count("__IDENTITY_SHA256__") == 1
    assert "-LiteralPath" in powershell
    assert "--verify-kit-identity" in powershell
    assert "--release" in powershell
    assert "kit_path_too_long" in powershell
    assert "230" in powershell
    combined = (command + "\n" + powershell).casefold()
    for forbidden in (
        "invoke-webrequest",
        "start-bitstransfer",
        "http://",
        "https://",
        "runas",
        "-verb",
        "set-itemproperty",
        "new-service",
        "encodedcommand",
        "powercfg",
    ):
        assert forbidden not in combined


def test_package_lock_and_templates_use_a_closed_source_location() -> None:
    assert PACKAGE_LOCK_SOURCE == (
        "scripts/office_live_research_os_kit/PACKAGE-LOCK.json"
    )
    assert PYINSTALLER_HOOK_SOURCE == "scripts/office_live_research_os_kit/hooks"
    assert TEMPLATE_SOURCE_FILES == {
        "cmd": (
            "scripts/office_live_research_os_kit/"
            "RUN-MODORI-LIVE-RESEARCH-OS-BENCHMARK.cmd.in"
        ),
        "powershell": "scripts/office_live_research_os_kit/VERIFY-AND-RUN.ps1.in",
        "readme": "scripts/office_live_research_os_kit/README-KO.txt",
    }


def test_clean_head_gate_rejects_dirty_detached_and_mismatched_source(
    tmp_path: Path,
    monkeypatch,
) -> None:
    commit = "a" * 40

    def install(responses: dict[tuple[str, ...], bytes]) -> None:
        monkeypatch.setattr(
            "scripts.build_office_live_research_os_kit._git",
            lambda _root, *arguments: responses[tuple(arguments)],
        )

    install({("status", "--porcelain"): b" M changed.py\n"})
    with pytest.raises(KitBuildError, match="clean"):
        _clean_head(tmp_path, None)

    install(
        {
            ("status", "--porcelain"): b"",
            ("symbolic-ref", "-q", "HEAD"): b"",
        }
    )
    with pytest.raises(KitBuildError, match="detached"):
        _clean_head(tmp_path, None)

    install(
        {
            ("status", "--porcelain"): b"",
            ("symbolic-ref", "-q", "HEAD"): b"refs/heads/codex/test\n",
            ("rev-parse", "HEAD"): f"{commit}\n".encode(),
        }
    )
    with pytest.raises(KitBuildError, match="does not match"):
        _clean_head(tmp_path, "b" * 40)

    install(
        {
            ("status", "--porcelain"): b"",
            ("symbolic-ref", "-q", "HEAD"): b"refs/heads/codex/test\n",
            ("rev-parse", "HEAD"): f"{commit}\n".encode(),
            ("show", "-s", "--format=%ct", commit): b"1752000000\n",
        }
    )
    assert _clean_head(tmp_path, commit) == (commit, 1_752_000_000)


def test_zip_digest_changes_after_one_byte_mutation(tmp_path: Path) -> None:
    result = build_outer_kit(_request(tmp_path))
    mutated = io.BytesIO(result.archive.read_bytes() + b"x").getvalue()
    assert hashlib.sha256(mutated).hexdigest() != result.archive_sha256

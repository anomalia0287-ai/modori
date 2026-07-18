from __future__ import annotations

import ast
from copy import deepcopy
from dataclasses import dataclass
import hashlib
from pathlib import Path
import stat
import warnings
import zipfile

from scripts.verify_office_live_research_os_kit import (
    KitVerificationError,
    verify_kit,
    verify_returned_result_bytes,
)
from tests.test_office_live_research_os_kit_runner import (
    _rehash_forged_mapping,
    _returned_bytes,
    _sealed,
)
from tests.test_office_live_research_os_kit_verifier import (
    _archive_with_sidecar,
    _fake_kit,
    _identity,
    _write_zip,
)


@dataclass(frozen=True)
class _Mutation:
    family: str
    ordinal: int


def _mutation_corpus() -> tuple[_Mutation, ...]:
    cases = tuple(
        _Mutation(family, ordinal)
        for family, count in (
            ("outer_byte", 60),
            ("immutable_member", 60),
            ("path_inventory_crc", 60),
            ("result_byte", 60),
            ("result_contract", 40),
            ("summary_byte", 20),
        )
        for ordinal in range(count)
    )
    assert len(cases) == 300
    assert len({(case.family, case.ordinal) for case in cases}) == 300
    return cases


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def _copy_info(info: zipfile.ZipInfo, *, name: str | None = None) -> zipfile.ZipInfo:
    copied = zipfile.ZipInfo(info.filename if name is None else name, info.date_time)
    copied.create_system = info.create_system
    copied.external_attr = info.external_attr
    copied.compress_type = info.compress_type
    return copied


def _extra_info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, (2025, 7, 9, 0, 0, 0))
    info.create_system = 3
    info.external_attr = (stat.S_IFREG | 0o644) << 16
    info.compress_type = zipfile.ZIP_DEFLATED
    return info


def _repack_path_case(
    baseline: Path,
    target: Path,
    *,
    category: int,
    variant: int,
) -> None:
    with zipfile.ZipFile(baseline, "r") as source:
        items = [(_copy_info(info), source.read(info)) for info in source.infolist()]
    root = next(
        info.filename[:-1] for info, _ in items if info.filename.count("/") == 1
    )
    readme_name = f"{root}/README-KO.txt"
    if category == 0:
        items.append((_extra_info(f"{root}/../escape-{variant}.txt"), b"x"))
    elif category == 1:
        items.append((_extra_info(f"{root}/runtime/member-{variant}:ads"), b"x"))
    elif category == 2:
        items.append((_extra_info(f"C:/absolute-{variant}.txt"), b"x"))
    elif category == 3:
        items.append((_extra_info(f"{root}/runtime/CON/entry-{variant}"), b"x"))
    elif category == 4:
        items.append((_extra_info(f"{root}/runtime/nested-{variant}.zip"), b"x"))
    elif category == 5:
        items.append((_extra_info(f"{root}/work/forged-{variant}.json"), b"x"))
    elif category == 6:
        suffix = ".py" if variant % 2 == 0 else ".pyc"
        items.append((_extra_info(f"{root}/runtime/source-{variant}{suffix}"), b"x"))
    elif category == 7:
        items.append((_extra_info(f"{root}/runtime/undeclared-{variant}.dat"), b"x"))
    elif category == 8:
        items = [
            item
            for item in items
            if not item[0].filename.endswith("runtime/_internal/python312.dll")
        ]
    elif category == 9:
        items.append((_extra_info(f"{root}/readme-ko.TXT"), b"x"))
    elif category == 10:
        duplicate = next(item for item in items if item[0].filename == readme_name)
        items.append((_copy_info(duplicate[0]), duplicate[1]))
    elif category == 11:
        items.reverse()
    else:
        raise AssertionError(category)
    if category not in {10, 11}:
        items.sort(key=lambda item: item[0].filename)
    target.parent.mkdir(parents=True)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        with zipfile.ZipFile(target, "x") as archive:
            for info, raw in items:
                archive.writestr(info, raw)


def _corrupt_crc(baseline: Path, target: Path, ordinal: int) -> None:
    raw = bytearray(baseline.read_bytes())
    with zipfile.ZipFile(baseline, "r") as archive:
        candidates = [
            info
            for info in archive.infolist()
            if not info.is_dir() and info.compress_size > 8
        ]
        info = candidates[ordinal % len(candidates)]
    offset = info.header_offset
    name_length = int.from_bytes(raw[offset + 26 : offset + 28], "little")
    extra_length = int.from_bytes(raw[offset + 28 : offset + 30], "little")
    data_offset = offset + 30 + name_length + extra_length
    raw[data_offset + info.compress_size // 2] ^= 0x01
    target.parent.mkdir(parents=True)
    target.write_bytes(raw)


def _sidecar_for(path: Path) -> Path:
    sidecar = path.with_name(path.name + ".sha256")
    sidecar.write_bytes(
        f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}\n".encode(
            "ascii"
        )
    )
    return sidecar


def test_verifier_is_independent_of_builder_runner_network_and_product_ui() -> None:
    path = Path("scripts/verify_office_live_research_os_kit.py")
    modules = _imported_modules(path)
    assert "scripts.build_office_live_research_os_kit" not in modules
    assert "scripts.run_office_live_research_os_benchmark" not in modules
    forbidden_roots = {
        "aiohttp",
        "ftplib",
        "http",
        "requests",
        "smtplib",
        "socket",
        "tkinter",
        "urllib",
        "webbrowser",
        "winreg",
    }
    assert {module.split(".", 1)[0] for module in modules}.isdisjoint(forbidden_roots)
    source = path.read_text(encoding="utf-8")
    assert "modori.steps" not in source
    assert "modori.ui" not in source
    assert "modori.workflow" not in source


def test_bootstrap_holds_verified_streams_and_has_only_fixed_identity_release_modes() -> (
    None
):
    root = Path("scripts/office_live_research_os_kit")
    powershell = (root / "VERIFY-AND-RUN.ps1.in").read_text(encoding="utf-8")
    command = (root / "RUN-MODORI-LIVE-RESEARCH-OS-BENCHMARK.cmd.in").read_text(
        encoding="utf-8"
    )
    combined = (powershell + "\n" + command).casefold()
    assert "fileshare]::read" in combined
    assert "verifiedstreams" in combined
    assert "--verify-kit-identity" in combined
    assert "--release" in combined
    assert "$work" not in combined
    assert "obsolete_work_root_present" in combined
    assert "beforerunnerdiagnostics" in combined
    assert "newrunnerdiagnosticcount" in combined
    assert "$runnerexitcode = $lastexitcode" in combined
    assert r"bootstrap-error-\d{8}t\d{6}z\.txt" in combined
    assert 'stop-modorikit ("runner_exit_" + $runnerexitcode) $false' in combined
    for forbidden in (
        "invoke-webrequest",
        "invoke-restmethod",
        "start-bitstransfer",
        "http://",
        "https://",
        "runas",
        "encodedcommand",
        "powercfg",
        "new-service",
    ):
        assert forbidden not in combined


def test_runbook_closes_operator_paths_outputs_and_claim_limits() -> None:
    text = Path("docs/qa/live-research-os-office-benchmark-runbook.md").read_text(
        encoding="utf-8"
    )
    folded = text.casefold()
    for required in (
        "%localappdata%\\mbl-",
        "ac 전원",
        "usb에서 직접 실행하지",
        "onedrive",
        "google drive",
        "reparse point",
        ".json.sha256",
        ".summary-ko.txt",
        "bootstrap-error-",
        "valid_stop",
        "invalid_run",
        "origin authentication",
    ):
        assert required in folded
    assert "hp_tools" not in folded
    assert "파티션" in folded and "수정하지" in folded


def test_runbook_prevents_explorer_from_duplicating_the_archive_root() -> None:
    text = Path("docs/qa/live-research-os-office-benchmark-runbook.md").read_text(
        encoding="utf-8"
    )
    folded = " ".join(text.casefold().split())

    assert "0x80010135" in folded
    assert "zip 안에 같은 이름의 최상위 폴더" in folded
    assert "압축 풀기 창의 대상 폴더" in folded
    assert "zip 파일명까지 자동으로 붙인 기본값" in folded
    assert "%localappdata%\\mbl-<source_commit[0:12]>" in folded


def test_300_sealed_mutations_fail_before_runtime_or_valid_result(
    tmp_path: Path,
) -> None:
    root = _fake_kit(tmp_path / "source")
    baseline, baseline_sidecar = _archive_with_sidecar(root, tmp_path)
    baseline_raw = baseline.read_bytes()
    immutable_targets = (
        "runtime/ModoriLiveResearchOSBenchmark.exe",
        "runtime/_internal/python312.dll",
        "runtime/_internal/PySide6/Qt6Core.dll",
        "runtime/_internal/numpy-core.pyd",
        "runtime/_internal/pandas-core.pyd",
        "runtime/_internal/LIVE-RESEARCH-OS-RUNTIME-IDENTITY.json",
        "KIT-IDENTITY.json",
        "PACKAGE-LOCK.json",
        "MANIFEST.json",
        "VERIFY-AND-RUN.ps1",
        "RUN-MODORI-LIVE-RESEARCH-OS-BENCHMARK.cmd",
        "README-KO.txt",
    )
    result = _sealed()
    result_name, result_raw, result_sidecar, result_summary = _returned_bytes(result)
    runtime_calls = 0
    observed: dict[str, int] = {}

    def forbidden_probe(*_args) -> None:
        nonlocal runtime_calls
        runtime_calls += 1

    for case in _mutation_corpus():
        observed[case.family] = observed.get(case.family, 0) + 1
        if case.family == "outer_byte":
            raw = bytearray(baseline_raw)
            position = 64 + (case.ordinal * 104_729) % (len(raw) - 128)
            raw[position] ^= 0x01
            target = tmp_path / f"outer-{case.ordinal}" / baseline.name
            target.parent.mkdir()
            target.write_bytes(raw)
            try:
                verify_kit(
                    target,
                    sidecar=baseline_sidecar,
                    runtime_probe=forbidden_probe,
                )
            except KitVerificationError:
                pass
            else:
                raise AssertionError(case)
        elif case.family == "immutable_member":
            relative = immutable_targets[case.ordinal % len(immutable_targets)]
            path = root / relative
            original = path.read_bytes()
            path.write_bytes(original + bytes((case.ordinal + 1,)))
            target = tmp_path / f"member-{case.ordinal}" / baseline.name
            target.parent.mkdir()
            _write_zip(root, target)
            path.write_bytes(original)
            try:
                verify_kit(
                    target,
                    sidecar=baseline_sidecar,
                    runtime_probe=forbidden_probe,
                )
            except KitVerificationError:
                pass
            else:
                raise AssertionError(case)
        elif case.family == "path_inventory_crc":
            category, variant = divmod(case.ordinal, 5)
            target = tmp_path / f"path-{case.ordinal}" / baseline.name
            if category == 11 and variant % 2 == 1:
                _corrupt_crc(baseline, target, variant)
            else:
                _repack_path_case(
                    baseline,
                    target,
                    category=category,
                    variant=variant,
                )
            sidecar = _sidecar_for(target)
            try:
                verify_kit(target, sidecar=sidecar, runtime_probe=forbidden_probe)
            except KitVerificationError:
                pass
            else:
                raise AssertionError(case)
        elif case.family == "result_byte":
            raw = bytearray(result_raw)
            position = (case.ordinal * 65_537) % len(raw)
            raw[position] ^= 0x01
            verified = verify_returned_result_bytes(
                _identity(),
                json_name=result_name,
                result_bytes=bytes(raw),
                sidecar_bytes=result_sidecar,
                summary_bytes=result_summary,
            )
            assert verified.status == "invalid_run", case
        elif case.family == "result_contract":
            changed = deepcopy(result)
            category, variant = divmod(case.ordinal, 10)
            if category == 0:
                waits = changed["observations"]["decision_waits"]
                waits.pop(variant % len(waits))
            elif category == 1:
                waits = changed["observations"]["identity_waits"]
                index = variant % (len(waits) - 1)
                waits[index], waits[index + 1] = waits[index + 1], waits[index]
            elif category == 2:
                changed["observations"]["identity_waits"][variant]["duration_ns"] = (
                    30_000_000_001
                )
            elif category == 3:
                changed["protocol"]["cold_processes_per_stratum"] = 19
            else:
                raise AssertionError(category)
            forged_raw = _rehash_forged_mapping(changed)
            forged_sidecar = (
                f"{hashlib.sha256(forged_raw).hexdigest()}  {result_name}\n".encode(
                    "ascii"
                )
            )
            verified = verify_returned_result_bytes(
                _identity(),
                json_name=result_name,
                result_bytes=forged_raw,
                sidecar_bytes=forged_sidecar,
                summary_bytes=result_summary,
            )
            assert verified.status == "invalid_run", case
        elif case.family == "summary_byte":
            summary = bytearray(result_summary)
            position = (case.ordinal * 257) % len(summary)
            summary[position] ^= 0x01
            verified = verify_returned_result_bytes(
                _identity(),
                json_name=result_name,
                result_bytes=result_raw,
                sidecar_bytes=result_sidecar,
                summary_bytes=bytes(summary),
            )
            assert verified.status == "invalid_run", case
        else:
            raise AssertionError(case.family)

    assert runtime_calls == 0
    assert observed == {
        "immutable_member": 60,
        "outer_byte": 60,
        "path_inventory_crc": 60,
        "result_byte": 60,
        "result_contract": 40,
        "summary_byte": 20,
    }

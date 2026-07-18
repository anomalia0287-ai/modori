from __future__ import annotations

from dataclasses import replace
from io import BytesIO
from pathlib import Path
from threading import Event
from types import SimpleNamespace
import hashlib
import os

import pytest

from modori.research_flow import (
    DatasetIdentity,
    FINGERPRINT_CONTRACT_ID,
    ResearchFlowState,
)
from modori.research_os import P1TaskProfile, PrimaryAction
from modori.ui.research_flow_controller import (
    ResearchFlowPipelineSnapshot,
    ResearchFlowRuntime,
)
from scripts.live_research_os_office_benchmark import (
    ACCEPTANCE_DATASET_FINGERPRINT,
    ACCEPTANCE_SOURCE_SCHEMA_FINGERPRINT,
    PROFILE_LATER_ROUND_COUNTS,
    PUBLIC_P1_ACTIONS,
    OfficeBenchmarkProtocol,
    build_acceptance_fixture,
    build_stress_fixture,
    canonical_result_bytes,
    canonical_summary_bytes,
    result_filename,
    result_sidecar_bytes,
)
from scripts.live_research_os_office_kit import (
    BUILDER_CONTRACT_VERSION,
    VERIFIER_CONTRACT_VERSION,
    KitIdentity,
    PackageLockEntry,
    identity_bytes,
    package_lock_bytes,
    sha256_bytes,
)
from scripts.run_office_live_research_os_benchmark import (
    BenchmarkRunnerError,
    ChildObservation,
    build_child_environment,
    build_fixed_child_command,
    cleanup_synthetic_child_root,
    execute_child_process,
    execute_release_benchmark,
    initialize_working_root,
    load_runtime_identity,
    measure_public_acknowledgements,
    main as benchmark_child_main,
    parse_cli_arguments,
    parse_entry_mode,
    prepare_isolated_child_root,
    quarantine_existing_run_residues,
    quarantine_crash_residue,
    run_identity_sample,
    run_stress_fingerprint_check,
    run_complete_benchmark,
    run_child_mode,
    run_benchmark_and_write_outputs,
    run_profile_scenario,
    run_warm_iteration,
    verify_scenario_recovery,
    verify_packaged_kit_identity,
    write_benchmark_outputs,
)


SOURCE_COMMIT = "a" * 40
RUN_ID = "12345678-1234-4abc-8def-1234567890ab"
RUNTIME_IDENTITY_RESOURCE_NAME = "LIVE-RESEARCH-OS-RUNTIME-IDENTITY.json"


@pytest.fixture(scope="module")
def acceptance_fixture():
    return build_acceptance_fixture()


def _identity(fixture, *, pipeline_version: int = 1) -> DatasetIdentity:
    return DatasetIdentity(
        fingerprint_contract_id=FINGERPRINT_CONTRACT_ID,
        dataset_fingerprint=ACCEPTANCE_DATASET_FINGERPRINT,
        source_schema_fingerprint=ACCEPTANCE_SOURCE_SCHEMA_FINGERPRINT,
        variable_ids=tuple(fixture.dataset.df.columns),
        pipeline_version=pipeline_version,
    )


def _working_root(tmp_path: Path) -> Path:
    return initialize_working_root(tmp_path / "ModoriBenchmarkRuns", run_id=RUN_ID)


def _kit_lock() -> bytes:
    return package_lock_bytes(
        (
            PackageLockEntry("numpy", "2.5.0"),
            PackageLockEntry("pandas", "3.0.3"),
            PackageLockEntry("pyinstaller", "6.21.0"),
            PackageLockEntry("pyside6", "6.11.1"),
        )
    )


def _kit_identity() -> KitIdentity:
    import numpy
    import pandas
    import PySide6
    import sqlite3
    import sys

    return KitIdentity(
        source_commit=SOURCE_COMMIT,
        source_date_epoch=1_752_000_000,
        protocol_digest=(
            "b2f24c4c752daaa2f2f34c7095ecb10518e6175ed7475d59621ea5bcefe72193"
        ),
        fixture_digest=(
            "f0a70250178dbf4a2a59795b72356d6c1dcaa1046e0ce4dada04885d5814602b"
        ),
        python_version=sys.version.split()[0],
        sqlite_version=sqlite3.sqlite_version,
        pyside_version=PySide6.__version__,
        numpy_version=numpy.__version__,
        pandas_version=pandas.__version__,
        pyinstaller_version="6.21.0",
        pyinstaller_bootloader_sha256="4" * 64,
        package_lock_sha256=sha256_bytes(_kit_lock()),
        executable_path="runtime/ModoriLiveResearchOSBenchmark.exe",
        runtime_layout="pyinstaller_onefolder_console",
        builder_contract_version=BUILDER_CONTRACT_VERSION,
        verifier_contract_version=VERIFIER_CONTRACT_VERSION,
        result_schema_id="modori.live_research_os_office_benchmark",
        result_schema_version=1,
    )


def _packaged_runtime(tmp_path: Path) -> tuple[Path, Path, KitIdentity]:
    identity = _kit_identity()
    kit_root = tmp_path / "kit"
    internal = kit_root / "runtime" / "_internal"
    internal.mkdir(parents=True)
    (kit_root / "results").mkdir()
    (kit_root / "work").mkdir()
    executable = kit_root / "runtime" / "ModoriLiveResearchOSBenchmark.exe"
    executable.write_bytes(b"MZ")
    (internal / RUNTIME_IDENTITY_RESOURCE_NAME).write_bytes(identity_bytes(identity))
    (kit_root / "KIT-IDENTITY.json").write_bytes(identity_bytes(identity))
    (kit_root / "PACKAGE-LOCK.json").write_bytes(_kit_lock())
    return kit_root, executable, identity


EXPECTED_STEPS = {
    P1TaskProfile.NUMERIC_DISTRIBUTION: "stats.descriptives_table1",
    P1TaskProfile.CATEGORY_FREQUENCY: "stats.frequency_crosstab",
    P1TaskProfile.INDEPENDENT_TWO_GROUP_MEAN: "stats.compare_groups",
    P1TaskProfile.PAIRED_TWO_TIME_MEAN_CHANGE: "stats.paired_comparison",
    P1TaskProfile.LINEAR_CO_MOVEMENT: "stats.correlation",
    P1TaskProfile.RANK_CO_MOVEMENT: "stats.correlation",
}
EXPECTED_CAPABILITIES = {
    P1TaskProfile.NUMERIC_DISTRIBUTION: (
        "descriptive_summary:unweighted_summary:summary:independent_unweighted:roles-v1"
    ),
    P1TaskProfile.CATEGORY_FREQUENCY: (
        "frequency_distribution:unweighted_frequency:frequency_distribution:"
        "independent_unweighted:roles-v1"
    ),
    P1TaskProfile.INDEPENDENT_TWO_GROUP_MEAN: (
        "compare_two_groups:welch_mean_difference:group_contrast_mean:"
        "independent_unweighted:roles-v1"
    ),
    P1TaskProfile.PAIRED_TWO_TIME_MEAN_CHANGE: (
        "compare_two_groups:paired_t_mean_change:within_unit_mean_change:"
        "paired_unweighted:roles-v1"
    ),
    P1TaskProfile.LINEAR_CO_MOVEMENT: (
        "bivariate_association:pearson_product_moment:association_correlation:"
        "independent_unweighted:roles-v1"
    ),
    P1TaskProfile.RANK_CO_MOVEMENT: (
        "bivariate_association:spearman_rank_monotonic:association_correlation:"
        "independent_unweighted:roles-v1"
    ),
}


def _expected_scenario_components(profile: P1TaskProfile) -> tuple[str, ...]:
    names = {
        "initial.ledger_create_open",
        "initial.projection",
        "initial.publication_readback_audit",
        "initial.request_build",
        "initial.request_initialize_append",
        "initial.resolve_plan_passport_append",
        "initial.task_index_allocate",
        "initial.task_session",
    }
    final_round = PROFILE_LATER_ROUND_COUNTS[profile.value]
    for ordinal in range(1, final_round + 1):
        prefix = f"later.{ordinal}"
        names.update(
            {
                f"{prefix}.answer_append_transition",
                f"{prefix}.answer_build",
                f"{prefix}.projection",
                f"{prefix}.publication_readback_audit",
                f"{prefix}.resolve_plan_passport_append",
            }
        )
        if ordinal == final_round:
            names.update({f"{prefix}.handoff", f"{prefix}.preflight"})
    return tuple(sorted(names))


def test_identity_sample_times_only_full_uncached_fingerprint(
    acceptance_fixture,
) -> None:
    trace: list[str] = []
    observation = run_identity_sample(
        OfficeBenchmarkProtocol(cold_processes_per_stratum=1, warm_iterations=1),
        run_id=RUN_ID,
        child_id="cold-identity-00",
        cache_state="cold",
        fixture=acceptance_fixture,
        source_commit=SOURCE_COMMIT,
        pipeline_version=1,
        trace=trace.append,
    )

    assert observation.profile is None
    assert observation.identity_wait_ns is not None
    assert observation.initial_decision_ns is None
    assert observation.later_decision_ns == ()
    assert observation.dataset_fingerprint == ACCEPTANCE_DATASET_FINGERPRINT
    assert observation.source_schema_fingerprint == (
        ACCEPTANCE_SOURCE_SCHEMA_FINGERPRINT
    )
    assert trace == [
        "identity_wait:begin",
        "fingerprint:begin",
        "fingerprint:end",
        "identity_wait:end",
    ]
    assert observation.component_spans == (
        ("fingerprint", observation.identity_wait_ns),
    )


@pytest.mark.parametrize("cooperative", (False, True))
def test_identity_sample_enforces_the_internal_fingerprint_worker_deadline(
    acceptance_fixture,
    monkeypatch,
    cooperative: bool,
) -> None:
    from modori.research_flow import FingerprintCancelled

    protocol = OfficeBenchmarkProtocol(
        cold_processes_per_stratum=1,
        warm_iterations=1,
        fingerprint_worker_limit_ms=1,
    )
    ticks = iter((0, 1_000_001, 1_000_002))

    def slow_fingerprint(
        _dataset,
        _source_schema,
        *,
        pipeline_version: int,
        cancel_requested,
    ):
        if cooperative and cancel_requested():
            raise FingerprintCancelled("injected worker deadline")
        return _identity(acceptance_fixture, pipeline_version=pipeline_version)

    monkeypatch.setattr(
        "scripts.run_office_live_research_os_benchmark.fingerprint_dataset",
        slow_fingerprint,
    )
    with pytest.raises(BenchmarkRunnerError, match="fingerprint worker.*timed out"):
        run_identity_sample(
            protocol,
            run_id=RUN_ID,
            child_id="cold-identity-00",
            cache_state="cold",
            fixture=acceptance_fixture,
            source_commit=SOURCE_COMMIT,
            pipeline_version=1,
            timer=lambda: next(ticks),
        )


@pytest.mark.parametrize("profile", tuple(P1TaskProfile))
def test_each_profile_walks_real_authority_chain_to_exact_preparation(
    tmp_path: Path,
    acceptance_fixture,
    profile: P1TaskProfile,
) -> None:
    working_root = _working_root(tmp_path)
    child_id = f"cold-scenario-{profile.value}-00"
    local_app_data = prepare_isolated_child_root(
        working_root,
        run_id=RUN_ID,
        child_id=child_id,
    )
    trace: list[str] = []

    observation = run_profile_scenario(
        OfficeBenchmarkProtocol(cold_processes_per_stratum=1, warm_iterations=1),
        run_id=RUN_ID,
        child_id=child_id,
        cache_state="cold",
        profile=profile,
        fixture=acceptance_fixture,
        identity=_identity(acceptance_fixture),
        source_commit=SOURCE_COMMIT,
        isolated_local_app_data=local_app_data,
        working_root=working_root,
        trace=trace.append,
    )

    assert observation.profile is profile
    assert observation.identity_wait_ns is None
    assert observation.initial_decision_ns > 0
    assert (
        len(observation.later_decision_ns)
        == (PROFILE_LATER_ROUND_COUNTS[profile.value])
    )
    assert tuple(ordinal for ordinal, _ns in observation.later_decision_ns) == (
        tuple(range(1, PROFILE_LATER_ROUND_COUNTS[profile.value] + 1))
    )
    assert observation.final_action == PrimaryAction.RECOMMEND_LOCAL.value
    assert observation.final_step_type == EXPECTED_STEPS[profile]
    assert observation.preflight_disposition == "prepare_ready"
    assert len(observation.passport_digest) == 64
    assert len(observation.preparation_digest) == 64
    assert len(observation.ledger_head_hash) == 64
    assert observation.ledger_event_count > 0
    assert trace[0] == "initial_decision:begin"
    assert trace[-1] == "later_decision:end"
    assert "task_session:begin" in trace
    assert "request_build:begin" in trace
    assert "decision_commit:begin" in trace
    assert "projection:begin" in trace
    assert "handoff:begin" in trace
    assert "preflight:begin" in trace
    assert (
        trace.count("answer_commit:begin")
        == (PROFILE_LATER_ROUND_COUNTS[profile.value])
    )
    assert tuple(name for name, _duration in observation.component_spans) == (
        _expected_scenario_components(profile)
    )
    parent_durations = {
        "initial": observation.initial_decision_ns,
        **{
            f"later.{ordinal}": duration
            for ordinal, duration in observation.later_decision_ns
        },
    }
    assert all(
        duration <= parent_durations[".".join(name.split(".")[:2])]
        if name.startswith("later.")
        else duration <= parent_durations["initial"]
        for name, duration in observation.component_spans
    )


def test_scenario_reuses_only_exact_cached_identity_without_rehashing(
    tmp_path: Path,
    acceptance_fixture,
    monkeypatch,
) -> None:
    working_root = _working_root(tmp_path)
    child_id = "cold-scenario-numeric_distribution-00"
    local_app_data = prepare_isolated_child_root(
        working_root,
        run_id=RUN_ID,
        child_id=child_id,
    )

    def forbidden_fingerprint(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("decision round rehashed the fixture")

    monkeypatch.setattr(
        "scripts.run_office_live_research_os_benchmark.fingerprint_dataset",
        forbidden_fingerprint,
    )
    observation = run_profile_scenario(
        OfficeBenchmarkProtocol(cold_processes_per_stratum=1, warm_iterations=1),
        run_id=RUN_ID,
        child_id=child_id,
        cache_state="cold",
        profile=P1TaskProfile.NUMERIC_DISTRIBUTION,
        fixture=acceptance_fixture,
        identity=_identity(acceptance_fixture),
        source_commit=SOURCE_COMMIT,
        isolated_local_app_data=local_app_data,
        working_root=working_root,
    )
    assert observation.final_step_type == "stats.descriptives_table1"


def test_product_runtime_reuses_cached_identity_until_pipeline_version_changes(
    tmp_path: Path,
    acceptance_fixture,
    monkeypatch,
) -> None:
    monkeypatch.setenv("LOCALAPPDATA", str((tmp_path / "local").resolve()))
    snapshot = ResearchFlowPipelineSnapshot(
        dataset=acceptance_fixture.dataset,
        source_schema=acceptance_fixture.source_schema,
        variable_labels={
            name: variable.label or name
            for name, variable in acceptance_fixture.dataset.variables.items()
        },
    )

    class Access:
        def capture(self):
            return snapshot

    class NoExistingSession:
        def locate_existing(self, identity):
            return None

    class UnusedCoordinator:
        pass

    calls: list[int] = []

    def fingerprinter(*_args: object, pipeline_version: int, **_kwargs: object):
        calls.append(pipeline_version)
        return _identity(acceptance_fixture, pipeline_version=pipeline_version)

    version = [1]
    runtime = ResearchFlowRuntime(
        pipeline_access=Access(),
        pipeline_version_provider=lambda: version[0],
        session_store=NoExistingSession(),
        coordinator=UnusedCoordinator(),
        initial_event_id_factory=lambda: "event:initial:1",
        answer_event_id_factory=lambda: "event:answer:1",
        language=__import__("modori.research_os", fromlist=["Language"]).Language.KO,
        fingerprint=fingerprinter,
    )
    assert runtime.start(pipeline_version=1, cancel_event=Event()).standard.state is (
        ResearchFlowState.INTAKE_CAUSAL
    )
    # A second capture at the same version must use the exact sealed identity.
    runtime._fresh_context(pipeline_version=1, cancel_event=Event())
    assert calls == [1]
    version[0] = 2
    runtime.note_pipeline_version(2)
    runtime.start(pipeline_version=2, cancel_event=Event())
    assert calls == [1, 2]


@pytest.mark.parametrize(
    "poison_name",
    (
        "legacy_recommendation",
        "handoff",
        "preflight",
        "projection",
    ),
)
def test_runner_never_shortcuts_required_authority_components(
    tmp_path: Path,
    acceptance_fixture,
    monkeypatch,
    poison_name: str,
) -> None:
    working_root = _working_root(tmp_path)
    child_id = "cold-scenario-linear_co_movement-00"
    local_app_data = prepare_isolated_child_root(
        working_root,
        run_id=RUN_ID,
        child_id=child_id,
    )

    if poison_name == "legacy_recommendation":
        monkeypatch.setattr(
            "modori.recommendations.RecommendationService.recommend",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(
                AssertionError("legacy recommendation was called")
            ),
            raising=False,
        )
        run_profile_scenario(
            OfficeBenchmarkProtocol(cold_processes_per_stratum=1, warm_iterations=1),
            run_id=RUN_ID,
            child_id=child_id,
            cache_state="cold",
            profile=P1TaskProfile.LINEAR_CO_MOVEMENT,
            fixture=acceptance_fixture,
            identity=_identity(acceptance_fixture),
            source_commit=SOURCE_COMMIT,
            isolated_local_app_data=local_app_data,
            working_root=working_root,
        )
        return

    target = {
        "handoff": "map_passport_to_step",
        "preflight": "preflight_mapped_step",
        "projection": "present_durable_record",
    }[poison_name]
    monkeypatch.setattr(
        f"scripts.run_office_live_research_os_benchmark.{target}",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            RuntimeError(f"poisoned_{poison_name}")
        ),
    )
    with pytest.raises(RuntimeError, match=f"poisoned_{poison_name}"):
        run_profile_scenario(
            OfficeBenchmarkProtocol(cold_processes_per_stratum=1, warm_iterations=1),
            run_id=RUN_ID,
            child_id=child_id,
            cache_state="cold",
            profile=P1TaskProfile.LINEAR_CO_MOVEMENT,
            fixture=acceptance_fixture,
            identity=_identity(acceptance_fixture),
            source_commit=SOURCE_COMMIT,
            isolated_local_app_data=local_app_data,
            working_root=working_root,
        )


def test_schema_only_forged_identity_and_preseeded_storage_are_rejected(
    tmp_path: Path,
    acceptance_fixture,
) -> None:
    working_root = _working_root(tmp_path)
    child_id = "cold-scenario-rank_co_movement-00"
    local_app_data = prepare_isolated_child_root(
        working_root,
        run_id=RUN_ID,
        child_id=child_id,
    )
    forged = replace(
        _identity(acceptance_fixture),
        dataset_fingerprint="f" * 64,
    )
    with pytest.raises(BenchmarkRunnerError, match="identity"):
        run_profile_scenario(
            OfficeBenchmarkProtocol(cold_processes_per_stratum=1, warm_iterations=1),
            run_id=RUN_ID,
            child_id=child_id,
            cache_state="cold",
            profile=P1TaskProfile.RANK_CO_MOVEMENT,
            fixture=acceptance_fixture,
            identity=forged,
            source_commit=SOURCE_COMMIT,
            isolated_local_app_data=local_app_data,
            working_root=working_root,
        )

    contaminated_id = "cold-scenario-rank_co_movement-01"
    contaminated = prepare_isolated_child_root(
        working_root,
        run_id=RUN_ID,
        child_id=contaminated_id,
    )
    (contaminated / "Modori").mkdir()
    with pytest.raises(BenchmarkRunnerError, match="fresh|preseed"):
        run_profile_scenario(
            OfficeBenchmarkProtocol(cold_processes_per_stratum=1, warm_iterations=1),
            run_id=RUN_ID,
            child_id=contaminated_id,
            cache_state="cold",
            profile=P1TaskProfile.RANK_CO_MOVEMENT,
            fixture=acceptance_fixture,
            identity=_identity(acceptance_fixture),
            source_commit=SOURCE_COMMIT,
            isolated_local_app_data=contaminated,
            working_root=working_root,
        )


def test_fresh_tasks_never_reuse_passport_or_preparation_authority(
    tmp_path: Path,
    acceptance_fixture,
) -> None:
    working_root = _working_root(tmp_path)
    observations = []
    for index in range(2):
        child_id = f"cold-scenario-numeric_distribution-{index:02d}"
        local_app_data = prepare_isolated_child_root(
            working_root,
            run_id=RUN_ID,
            child_id=child_id,
        )
        observations.append(
            run_profile_scenario(
                OfficeBenchmarkProtocol(
                    cold_processes_per_stratum=2,
                    warm_iterations=1,
                ),
                run_id=RUN_ID,
                child_id=child_id,
                cache_state="cold",
                profile=P1TaskProfile.NUMERIC_DISTRIBUTION,
                fixture=acceptance_fixture,
                identity=_identity(acceptance_fixture),
                source_commit=SOURCE_COMMIT,
                isolated_local_app_data=local_app_data,
                working_root=working_root,
            )
        )
    assert observations[0].passport_digest != observations[1].passport_digest
    assert observations[0].preparation_digest != observations[1].preparation_digest
    assert observations[0].ledger_head_hash != observations[1].ledger_head_hash


def test_warm_iteration_runs_one_uncached_identity_and_all_six_fresh_tasks(
    tmp_path: Path,
    acceptance_fixture,
) -> None:
    working_root = _working_root(tmp_path)
    observations = run_warm_iteration(
        OfficeBenchmarkProtocol(cold_processes_per_stratum=1, warm_iterations=1),
        run_id=RUN_ID,
        iteration=0,
        fixture=acceptance_fixture,
        source_commit=SOURCE_COMMIT,
        working_root=working_root,
    )
    assert len(observations) == 7
    identity, *scenarios = observations
    assert identity.identity_wait_ns is not None
    assert tuple(item.profile for item in scenarios) == tuple(P1TaskProfile)
    assert len({item.passport_digest for item in scenarios}) == 6


def test_public_acknowledgement_suite_covers_every_closed_action() -> None:
    samples = measure_public_acknowledgements(cache_state="warm")
    assert tuple(action for action, _duration in samples) == PUBLIC_P1_ACTIONS
    assert all(type(duration) is int and duration > 0 for _action, duration in samples)


def test_working_root_and_child_root_are_closed_fresh_and_application_owned(
    tmp_path: Path,
) -> None:
    working_root = _working_root(tmp_path)
    child = prepare_isolated_child_root(
        working_root,
        run_id=RUN_ID,
        child_id="cold-identity-00",
    )
    assert (
        child
        == (
            working_root / RUN_ID / "children" / "cold-identity-00" / "LocalAppData"
        ).resolve()
    )
    assert child.is_dir()
    assert tuple(child.iterdir()) == ()
    with pytest.raises(BenchmarkRunnerError, match="working root|outside"):
        prepare_isolated_child_root(
            tmp_path / "not-initialized",
            run_id=RUN_ID,
            child_id="cold-identity-01",
        )
    with pytest.raises(BenchmarkRunnerError, match="child_id"):
        prepare_isolated_child_root(
            working_root,
            run_id=RUN_ID,
            child_id="../../escape",
        )


def test_next_run_reuses_only_the_application_root_and_quarantines_old_residue(
    tmp_path: Path,
) -> None:
    first_run = RUN_ID
    second_run = "87654321-4321-4cba-8fed-ba0987654321"
    root = initialize_working_root(tmp_path / "ModoriBenchmarkRuns", run_id=first_run)
    residue = prepare_isolated_child_root(
        root,
        run_id=first_run,
        child_id="cold-identity-00",
    )
    (residue / "partial.bin").write_bytes(b"partial")

    assert initialize_working_root(root, run_id=second_run) == root
    rename_attempts: list[int] = []

    def transient_lock(source: str | Path, target: str | Path) -> None:
        rename_attempts.append(1)
        if len(rename_attempts) == 1:
            raise PermissionError("injected Windows sharing violation")
        os.replace(source, target)

    quarantined = quarantine_existing_run_residues(
        root,
        current_run_id=second_run,
        rename_operation=transient_lock,
        sleeper=lambda _delay: None,
    )

    # The first sharing violation is injected.  Windows may independently keep
    # the just-written directory locked for another bounded attempt.
    assert 2 <= len(rename_attempts) <= 7
    assert len(quarantined) == 1
    assert quarantined[0].parent.name == "quarantine"
    assert not (root / first_run).exists()
    assert (quarantined[0] / "children").is_dir()


def test_residue_quarantine_retries_only_bounded_permission_errors(
    tmp_path: Path,
) -> None:
    next_run = "87654321-4321-4cba-8fed-ba0987654321"
    root = initialize_working_root(tmp_path / "ModoriBenchmarkRuns", run_id=RUN_ID)
    prepare_isolated_child_root(
        root,
        run_id=RUN_ID,
        child_id="cold-identity-00",
    )
    attempts: list[int] = []
    delays: list[float] = []

    def permanently_locked(_source: str | Path, _target: str | Path) -> None:
        attempts.append(1)
        raise PermissionError("injected persistent sharing violation")

    with pytest.raises(BenchmarkRunnerError, match="remained locked"):
        quarantine_existing_run_residues(
            root,
            current_run_id=next_run,
            rename_operation=permanently_locked,
            sleeper=delays.append,
        )

    assert len(attempts) == 7
    assert delays == [0.025, 0.05, 0.1, 0.2, 0.4, 0.8]
    assert (root / RUN_ID).is_dir()


def test_residue_quarantine_does_not_retry_other_os_errors(tmp_path: Path) -> None:
    next_run = "87654321-4321-4cba-8fed-ba0987654321"
    root = initialize_working_root(tmp_path / "ModoriBenchmarkRuns", run_id=RUN_ID)
    prepare_isolated_child_root(
        root,
        run_id=RUN_ID,
        child_id="cold-identity-00",
    )
    attempts: list[int] = []

    def invalid_rename(_source: str | Path, _target: str | Path) -> None:
        attempts.append(1)
        raise OSError("injected non-lock filesystem failure")

    with pytest.raises(OSError, match="non-lock"):
        quarantine_existing_run_residues(
            root,
            current_run_id=next_run,
            rename_operation=invalid_rename,
            sleeper=lambda _delay: pytest.fail("non-lock error was retried"),
        )

    assert attempts == [1]


@pytest.mark.parametrize("cloud_name", ("OneDrive", "Google Drive", "Dropbox"))
def test_cloud_or_synced_working_roots_are_rejected(
    tmp_path: Path, cloud_name: str
) -> None:
    with pytest.raises(BenchmarkRunnerError, match="cloud|synced"):
        initialize_working_root(tmp_path / cloud_name / "runs", run_id=RUN_ID)


def test_fixed_child_command_and_environment_have_no_arbitrary_surface(
    tmp_path: Path,
    monkeypatch,
) -> None:
    executable = tmp_path / "ModoriLiveResearchOSBenchmark.exe"
    executable.write_bytes(b"verified executable")
    working_root = _working_root(tmp_path)
    local_app_data = prepare_isolated_child_root(
        working_root,
        run_id=RUN_ID,
        child_id="cold-identity-00",
    )
    command = build_fixed_child_command(
        executable,
        mode="identity",
        run_id=RUN_ID,
        child_id="cold-identity-00",
        source_commit=SOURCE_COMMIT,
        working_root=working_root,
        profile=None,
    )
    assert command == (
        str(executable.resolve()),
        "--child-mode",
        "identity",
        "--run-id",
        RUN_ID,
        "--child-id",
        "cold-identity-00",
        "--source-commit",
        SOURCE_COMMIT,
        "--working-root",
        str(working_root),
    )
    monkeypatch.setenv("PYTHONPATH", "poison")
    monkeypatch.setenv("MODORI_ARBITRARY", "poison")
    environment = build_child_environment(
        local_app_data,
        nonce="c" * 32,
    )
    assert "PYTHONPATH" not in environment
    assert "MODORI_ARBITRARY" not in environment
    assert environment["LOCALAPPDATA"] == str(local_app_data)
    assert environment["MODORI_BENCHMARK_CHILD_NONCE"] == "c" * 32


def test_child_process_uses_shell_false_fixed_timeout_and_verified_output(
    tmp_path: Path,
    acceptance_fixture,
) -> None:
    executable = tmp_path / "ModoriLiveResearchOSBenchmark.exe"
    executable.write_bytes(b"verified executable")
    working_root = _working_root(tmp_path)
    local_app_data = prepare_isolated_child_root(
        working_root,
        run_id=RUN_ID,
        child_id="cold-identity-00",
    )
    observation = run_identity_sample(
        OfficeBenchmarkProtocol(cold_processes_per_stratum=1, warm_iterations=1),
        run_id=RUN_ID,
        child_id="cold-identity-00",
        cache_state="cold",
        fixture=acceptance_fixture,
        source_commit=SOURCE_COMMIT,
        pipeline_version=1,
    )
    calls: list[tuple[object, object]] = []

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        return SimpleNamespace(
            returncode=0,
            stdout=observation.to_bytes() + b"\n",
            stderr=b"",
        )

    received = execute_child_process(
        executable,
        mode="identity",
        run_id=RUN_ID,
        child_id="cold-identity-00",
        source_commit=SOURCE_COMMIT,
        working_root=working_root,
        local_app_data=local_app_data,
        profile=None,
        nonce="d" * 32,
        subprocess_run=fake_run,
    )
    assert received == observation
    command, kwargs = calls[0]
    assert tuple(command) == build_fixed_child_command(
        executable,
        mode="identity",
        run_id=RUN_ID,
        child_id="cold-identity-00",
        source_commit=SOURCE_COMMIT,
        working_root=working_root,
        profile=None,
    )
    assert kwargs["shell"] is False
    assert kwargs["timeout"] > 0
    assert kwargs["check"] is False
    assert kwargs["capture_output"] is True
    assert kwargs["env"]["MODORI_BENCHMARK_PARENT_START_NS"].isdigit()


@pytest.mark.parametrize(
    "failure",
    ("timeout", "nonzero", "stderr", "partial", "wrong_child", "duplicate"),
)
def test_child_process_failures_never_become_duration_samples(
    tmp_path: Path,
    acceptance_fixture,
    failure: str,
) -> None:
    executable = tmp_path / "ModoriLiveResearchOSBenchmark.exe"
    executable.write_bytes(b"verified executable")
    working_root = _working_root(tmp_path)
    local_app_data = prepare_isolated_child_root(
        working_root,
        run_id=RUN_ID,
        child_id="cold-identity-00",
    )
    observation = run_identity_sample(
        OfficeBenchmarkProtocol(cold_processes_per_stratum=1, warm_iterations=1),
        run_id=RUN_ID,
        child_id="cold-identity-00",
        cache_state="cold",
        fixture=acceptance_fixture,
        source_commit=SOURCE_COMMIT,
        pipeline_version=1,
    )
    if failure == "wrong_child":
        observation = replace(observation, child_id="cold-identity-99")
    if failure == "duplicate":
        seen = {"cold-identity-00"}
    else:
        seen = set()

    def fake_run(_command, **_kwargs):
        if failure == "timeout":
            raise __import__("subprocess").TimeoutExpired("child", 1)
        return SimpleNamespace(
            returncode=7 if failure == "nonzero" else 0,
            stdout=(b"{" if failure == "partial" else observation.to_bytes()),
            stderr=b"closed-error" if failure == "stderr" else b"",
        )

    with pytest.raises(BenchmarkRunnerError):
        execute_child_process(
            executable,
            mode="identity",
            run_id=RUN_ID,
            child_id="cold-identity-00",
            source_commit=SOURCE_COMMIT,
            working_root=working_root,
            local_app_data=local_app_data,
            profile=None,
            nonce="e" * 32,
            subprocess_run=fake_run,
            seen_child_ids=seen,
        )


def test_child_process_preserves_a_closed_fingerprint_timeout_reason(
    tmp_path: Path,
) -> None:
    executable = tmp_path / "ModoriLiveResearchOSBenchmark.exe"
    executable.write_bytes(b"verified executable")
    working_root = _working_root(tmp_path)
    local_app_data = prepare_isolated_child_root(
        working_root,
        run_id=RUN_ID,
        child_id="cold-identity-00",
    )

    def timed_out(_command, **_kwargs):
        return SimpleNamespace(
            returncode=20,
            stdout=b"",
            stderr=b"modori-child-error:fingerprint_timeout\n",
        )

    with pytest.raises(BenchmarkRunnerError, match="fingerprint_timeout"):
        execute_child_process(
            executable,
            mode="identity",
            run_id=RUN_ID,
            child_id="cold-identity-00",
            source_commit=SOURCE_COMMIT,
            working_root=working_root,
            local_app_data=local_app_data,
            profile=None,
            nonce="e" * 32,
            subprocess_run=timed_out,
        )


def test_child_main_emits_only_one_closed_failure_line(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.setenv("MODORI_BENCHMARK_CHILD_NONCE", "e" * 32)
    monkeypatch.setenv("MODORI_BENCHMARK_PARENT_START_NS", "1")

    def fingerprint_timeout(**_kwargs):
        raise BenchmarkRunnerError("fingerprint worker timed out")

    monkeypatch.setattr(
        "scripts.run_office_live_research_os_benchmark.run_child_mode",
        fingerprint_timeout,
    )
    stdout = BytesIO()
    stderr = BytesIO()
    result = benchmark_child_main(
        [
            "--child-mode",
            "identity",
            "--run-id",
            RUN_ID,
            "--child-id",
            "cold-identity-00",
            "--source-commit",
            SOURCE_COMMIT,
            "--working-root",
            str(tmp_path),
        ],
        stdout=stdout,
        stderr=stderr,
    )

    assert result == 20
    assert stdout.getvalue() == b""
    assert stderr.getvalue() == b"modori-child-error:fingerprint_timeout\n"


def test_crash_residue_is_verified_then_quarantined_not_merged(
    tmp_path: Path,
    acceptance_fixture,
) -> None:
    working_root = _working_root(tmp_path)
    child_id = "cold-scenario-numeric_distribution-00"
    local_app_data = prepare_isolated_child_root(
        working_root,
        run_id=RUN_ID,
        child_id=child_id,
    )
    with pytest.raises(RuntimeError, match="after_request_initialize"):
        run_profile_scenario(
            OfficeBenchmarkProtocol(cold_processes_per_stratum=1, warm_iterations=1),
            run_id=RUN_ID,
            child_id=child_id,
            cache_state="cold",
            profile=P1TaskProfile.NUMERIC_DISTRIBUTION,
            fixture=acceptance_fixture,
            identity=_identity(acceptance_fixture),
            source_commit=SOURCE_COMMIT,
            isolated_local_app_data=local_app_data,
            working_root=working_root,
            poison_stage="after_request_initialize",
        )
    recovery = verify_scenario_recovery(
        local_app_data,
        working_root=working_root,
        run_id=RUN_ID,
        child_id=child_id,
        identity=_identity(acceptance_fixture),
    )
    assert recovery == "pending_decision"
    quarantined = quarantine_crash_residue(
        local_app_data,
        working_root=working_root,
        run_id=RUN_ID,
        child_id=child_id,
        nonce="f" * 32,
    )
    assert quarantined.is_dir()
    assert not local_app_data.parent.exists()


def test_cleanup_removes_only_exact_marked_synthetic_child_root(tmp_path: Path) -> None:
    working_root = _working_root(tmp_path)
    child_id = "cold-identity-00"
    local_app_data = prepare_isolated_child_root(
        working_root,
        run_id=RUN_ID,
        child_id=child_id,
    )
    sibling = working_root / "unrelated.txt"
    sibling.write_text("preserve", encoding="utf-8")
    (local_app_data / "synthetic.txt").write_text("delete", encoding="utf-8")

    cleanup_synthetic_child_root(
        local_app_data,
        working_root=working_root,
        run_id=RUN_ID,
        child_id=child_id,
    )

    assert not local_app_data.parent.exists()
    assert sibling.read_text(encoding="utf-8") == "preserve"
    with pytest.raises(BenchmarkRunnerError, match="exact|marker|outside|missing"):
        cleanup_synthetic_child_root(
            working_root,
            working_root=working_root,
            run_id=RUN_ID,
            child_id=child_id,
        )


def test_child_observation_canonical_roundtrip_rejects_mutation(
    acceptance_fixture,
) -> None:
    observation = run_identity_sample(
        OfficeBenchmarkProtocol(cold_processes_per_stratum=1, warm_iterations=1),
        run_id=RUN_ID,
        child_id="cold-identity-00",
        cache_state="cold",
        fixture=acceptance_fixture,
        source_commit=SOURCE_COMMIT,
        pipeline_version=1,
    )
    raw = observation.to_bytes()
    assert ChildObservation.from_bytes(raw) == observation
    assert hashlib.sha256(raw).hexdigest() == observation.observation_digest
    with pytest.raises(BenchmarkRunnerError):
        ChildObservation.from_bytes(raw + b" ")

    integer_prefix = b'"identity_wait_ns":'
    integer_start = raw.index(integer_prefix) + len(integer_prefix)
    integer_end = raw.index(b",", integer_start)
    oversized_integer = raw[:integer_start] + (b"9" * 5_000) + raw[integer_end:]
    with pytest.raises(BenchmarkRunnerError, match="strict JSON"):
        ChildObservation.from_bytes(oversized_integer)


def _fake_observation(
    *,
    cache_state: str,
    child_id: str,
    profile: P1TaskProfile | None,
    include_acknowledgements: bool = False,
) -> ChildObservation:
    acknowledgements = (
        tuple((action, 1_000_000) for action in PUBLIC_P1_ACTIONS)
        if include_acknowledgements
        else ()
    )
    if profile is None:
        return ChildObservation(
            run_id=RUN_ID,
            child_id=child_id,
            source_commit=SOURCE_COMMIT,
            cache_state=cache_state,
            profile=None,
            dataset_fingerprint=ACCEPTANCE_DATASET_FINGERPRINT,
            source_schema_fingerprint=ACCEPTANCE_SOURCE_SCHEMA_FINGERPRINT,
            identity_wait_ns=10_000_000,
            initial_decision_ns=None,
            later_decision_ns=(),
            acknowledgement_ns=acknowledgements,
            component_spans=(("fingerprint", 10_000_000),),
            peak_working_set_bytes=128 * 1024 * 1024,
            process_cpu_time_ns=10_000_000,
            read_bytes=1_024,
            write_bytes=2_048,
            final_action=None,
            final_capability_key=None,
            final_step_type=None,
            preflight_disposition=None,
            passport_digest=None,
            preparation_digest=None,
            ledger_head_hash=None,
            ledger_event_count=0,
            fixture_build_ns=1_000_000 if cache_state == "cold" else None,
            process_startup_import_ns=1_000_000 if cache_state == "cold" else None,
        )
    rounds = PROFILE_LATER_ROUND_COUNTS[profile.value]
    token = hashlib.sha256(child_id.encode("ascii")).hexdigest()
    return ChildObservation(
        run_id=RUN_ID,
        child_id=child_id,
        source_commit=SOURCE_COMMIT,
        cache_state=cache_state,
        profile=profile,
        dataset_fingerprint=ACCEPTANCE_DATASET_FINGERPRINT,
        source_schema_fingerprint=ACCEPTANCE_SOURCE_SCHEMA_FINGERPRINT,
        identity_wait_ns=None,
        initial_decision_ns=10_000_000,
        later_decision_ns=tuple(
            (ordinal, 10_000_000) for ordinal in range(1, rounds + 1)
        ),
        acknowledgement_ns=(),
        component_spans=tuple(
            (name, 1_000_000) for name in _expected_scenario_components(profile)
        ),
        peak_working_set_bytes=128 * 1024 * 1024,
        process_cpu_time_ns=10_000_000,
        read_bytes=1_024,
        write_bytes=2_048,
        final_action=PrimaryAction.RECOMMEND_LOCAL.value,
        final_capability_key=EXPECTED_CAPABILITIES[profile],
        final_step_type=EXPECTED_STEPS[profile],
        preflight_disposition="prepare_ready",
        passport_digest=token,
        preparation_digest=hashlib.sha256(
            f"preparation:{child_id}".encode()
        ).hexdigest(),
        ledger_head_hash=hashlib.sha256(f"ledger:{child_id}".encode()).hexdigest(),
        ledger_event_count=2 + (2 * rounds),
        fixture_build_ns=1_000_000 if cache_state == "cold" else None,
        process_startup_import_ns=1_000_000 if cache_state == "cold" else None,
    )


def _execution_conditions() -> dict[str, object]:
    return {
        "ac_power": True,
        "drive_type": "fixed",
        "is_internal": True,
        "is_regular_directory": True,
        "is_reparse_point": False,
        "is_synced_root": False,
        "release_protocol": False,
        "runtime_verified": True,
        "working_root_class": "local_application_owned",
    }


def _hardware() -> dict[str, object]:
    return {
        "logical_cpu_count": 4,
        "machine": "amd64",
        "physical_core_count": 2,
        "physical_memory_bytes": 8 * 1024**3,
        "storage": {
            "bus_type": "sata",
            "filesystem": "ntfs",
            "media_type": "ssd",
        },
        "windows_version_family": "windows_11",
    }


def test_complete_runner_collects_exact_cold_warm_inventory_and_discards_warmup(
    tmp_path: Path,
    acceptance_fixture,
) -> None:
    protocol = OfficeBenchmarkProtocol(cold_processes_per_stratum=1, warm_iterations=1)
    executable = tmp_path / "ModoriLiveResearchOSBenchmark.exe"
    executable.write_bytes(b"verified")
    working_root = initialize_working_root(
        tmp_path / "ModoriBenchmarkRuns",
        run_id=RUN_ID,
    )
    cold_calls: list[str] = []
    warm_calls: list[int] = []
    nonces = iter(f"{index:032x}" for index in range(1, 8))

    def child_executor(_executable: Path, **kwargs: object) -> ChildObservation:
        child_id = kwargs["child_id"]
        cold_calls.append(child_id)
        return _fake_observation(
            cache_state="cold",
            child_id=child_id,
            profile=kwargs["profile"],
            include_acknowledgements=kwargs["mode"] == "identity",
        )

    def warm_runner(_protocol: OfficeBenchmarkProtocol, **kwargs: object):
        iteration = kwargs["iteration"]
        warm_calls.append(iteration)
        return (
            _fake_observation(
                cache_state="warm",
                child_id=f"warm-identity-{iteration:02d}",
                profile=None,
                include_acknowledgements=True,
            ),
            *(
                _fake_observation(
                    cache_state="warm",
                    child_id=f"warm-{profile.value}-{iteration:02d}",
                    profile=profile,
                )
                for profile in P1TaskProfile
            ),
        )

    result = run_complete_benchmark(
        protocol,
        verified_self_executable=executable,
        working_root=working_root,
        source_commit=SOURCE_COMMIT,
        kit_identity_digest="b" * 64,
        execution_conditions=_execution_conditions(),
        hardware=_hardware(),
        recorded_at_utc="2026-07-18T01:02:03Z",
        run_id=RUN_ID,
        fixture_builder=lambda: acceptance_fixture,
        child_process_executor=child_executor,
        warm_iteration_runner=warm_runner,
        stress_check_runner=lambda _protocol: {
            "column_count": 40,
            "duration_ns": None,
            "error_code": None,
            "fixture_digest": (
                "3dad9993f2e0114ec310436e3df6d02381ff696404a5947022c0cdbca14fdc82"
            ),
            "fixture_id": "modori.live_research_os.office_stress_fixture.v1",
            "outcome": "not_run",
            "row_count": 125_000,
        },
        nonce_factory=lambda: next(nonces),
    )

    assert len(cold_calls) == 7
    assert warm_calls == [1, 0]  # one discarded warm-up, then one measured iteration
    observations = result["observations"]
    assert len(observations["identity_waits"]) == 2
    assert len(observations["decision_waits"]) == 44
    assert len(observations["acknowledgements"]) == 2 * len(PUBLIC_P1_ACTIONS)
    assert len(observations["resources"]) == 14
    assert result["evaluation"]["disposition"] == "stop"
    assert result["evaluation"]["reason_codes"] == ["execution_conditions_invalid"]
    assert canonical_result_bytes(result)


def test_outputs_publish_json_last_and_remove_every_partial_on_failure(
    tmp_path: Path,
) -> None:
    from tests.test_live_research_os_office_benchmark_contract import _base_result

    from scripts.live_research_os_office_benchmark import seal_result

    result = seal_result(_base_result())
    output = tmp_path / "success"
    output.mkdir()
    paths = write_benchmark_outputs(result, output_directory=output)
    json_path, sidecar_path, summary_path = paths
    assert json_path.name == result_filename(result)
    assert json_path.read_bytes() == canonical_result_bytes(result)
    assert sidecar_path.read_bytes() == result_sidecar_bytes(result)
    assert summary_path.read_bytes() == canonical_summary_bytes(result)

    failed = tmp_path / "failed"
    failed.mkdir()

    def fail_final_json(source: str | Path, target: str | Path) -> None:
        if Path(target).suffix == ".json":
            raise OSError("injected final publish failure")
        os.replace(source, target)

    with pytest.raises(BenchmarkRunnerError, match="publish"):
        write_benchmark_outputs(
            result,
            output_directory=failed,
            replace_operation=fail_final_json,
        )
    assert tuple(failed.iterdir()) == ()


def test_child_cli_is_closed_and_has_no_release_count_override(
    tmp_path: Path,
    acceptance_fixture,
) -> None:
    working_root = _working_root(tmp_path)
    child_id = "cold-identity-00"
    local = prepare_isolated_child_root(
        working_root,
        run_id=RUN_ID,
        child_id=child_id,
    )
    observation = run_child_mode(
        mode="identity",
        run_id=RUN_ID,
        child_id=child_id,
        source_commit=SOURCE_COMMIT,
        working_root=working_root,
        local_app_data=local,
        profile=None,
        child_nonce="d" * 32,
        fixture_builder=lambda: acceptance_fixture,
    )
    assert observation.acknowledgement_ns
    assert observation.profile is None

    parsed = parse_cli_arguments(
        [
            "--child-mode",
            "identity",
            "--run-id",
            RUN_ID,
            "--child-id",
            child_id,
            "--source-commit",
            SOURCE_COMMIT,
            "--working-root",
            str(working_root),
        ]
    )
    assert parsed.child_mode == "identity"
    with pytest.raises(SystemExit):
        parse_cli_arguments(
            [
                "--child-mode",
                "identity",
                "--run-id",
                RUN_ID,
                "--child-id",
                child_id,
                "--source-commit",
                SOURCE_COMMIT,
                "--working-root",
                str(working_root),
                "--warm-iterations",
                "1",
            ]
        )


def test_cold_scenario_child_computes_full_identity_before_decision_timer(
    tmp_path: Path,
    acceptance_fixture,
    monkeypatch,
) -> None:
    from modori.research_flow import fingerprint_dataset as real_fingerprint_dataset

    working_root = _working_root(tmp_path)
    child_id = "cold-numeric_distribution-00"
    local = prepare_isolated_child_root(
        working_root,
        run_id=RUN_ID,
        child_id=child_id,
    )
    calls: list[tuple[object, object, int, bool]] = []

    def observed_fingerprint(
        dataset,
        source_schema,
        *,
        pipeline_version: int,
        cancel_requested,
    ):
        calls.append(
            (
                dataset,
                source_schema,
                pipeline_version,
                cancel_requested(),
            )
        )
        return real_fingerprint_dataset(
            dataset,
            source_schema,
            pipeline_version=pipeline_version,
            cancel_requested=cancel_requested,
        )

    monkeypatch.setattr(
        "scripts.run_office_live_research_os_benchmark.fingerprint_dataset",
        observed_fingerprint,
    )
    observation = run_child_mode(
        mode="scenario",
        run_id=RUN_ID,
        child_id=child_id,
        source_commit=SOURCE_COMMIT,
        working_root=working_root,
        local_app_data=local,
        profile=P1TaskProfile.NUMERIC_DISTRIBUTION,
        child_nonce="e" * 32,
        fixture_builder=lambda: acceptance_fixture,
    )

    assert calls == [
        (
            acceptance_fixture.dataset,
            acceptance_fixture.source_schema,
            1,
            False,
        )
    ]
    assert observation.identity_wait_ns is None
    assert observation.final_step_type == "stats.descriptives_table1"


def test_failed_complete_run_writes_only_closed_bootstrap_error(
    tmp_path: Path,
    acceptance_fixture,
) -> None:
    executable = tmp_path / "ModoriLiveResearchOSBenchmark.exe"
    executable.write_bytes(b"verified")
    working_root = initialize_working_root(
        tmp_path / "ModoriBenchmarkRuns",
        run_id=RUN_ID,
    )
    output = tmp_path / "output"
    output.mkdir()

    def timeout(*_args: object, **_kwargs: object) -> ChildObservation:
        raise BenchmarkRunnerError("child process timed out")

    with pytest.raises(BenchmarkRunnerError, match="timed out"):
        run_benchmark_and_write_outputs(
            OfficeBenchmarkProtocol(cold_processes_per_stratum=1, warm_iterations=1),
            output_directory=output,
            error_timestamp="20260718T010203Z",
            verified_self_executable=executable,
            working_root=working_root,
            source_commit=SOURCE_COMMIT,
            kit_identity_digest="b" * 64,
            execution_conditions=_execution_conditions(),
            hardware=_hardware(),
            recorded_at_utc="2026-07-18T01:02:03Z",
            run_id=RUN_ID,
            fixture_builder=lambda: acceptance_fixture,
            child_process_executor=timeout,
            nonce_factory=lambda: "e" * 32,
        )
    files = tuple(output.iterdir())
    assert [path.name for path in files] == ["bootstrap-error-20260718T010203Z.txt"]
    assert files[0].read_text(encoding="utf-8") == (
        "Modori 라이브 Research OS 벤치마크 오류\n"
        "reason_code: child_timeout\n"
        "result_json_created: false\n"
    )


def test_stress_check_records_completion_and_cooperative_limit_without_gating() -> None:
    stress = build_stress_fixture()

    def immediate_identity(dataset, source_schema, **kwargs: object):
        _ = source_schema, kwargs
        return DatasetIdentity(
            fingerprint_contract_id=FINGERPRINT_CONTRACT_ID,
            dataset_fingerprint="c" * 64,
            source_schema_fingerprint="d" * 64,
            variable_ids=tuple(dataset.df.columns),
            pipeline_version=1,
        )

    completed = run_stress_fingerprint_check(
        OfficeBenchmarkProtocol(cold_processes_per_stratum=1, warm_iterations=1),
        fixture_builder=lambda: stress,
        fingerprint=immediate_identity,
    )
    assert completed["outcome"] == "completed"
    assert completed["error_code"] is None

    from modori.research_flow import FingerprintCancelled

    def cooperative_cancel(_dataset, _source_schema, **kwargs: object):
        cancel_requested = kwargs["cancel_requested"]
        while not cancel_requested():
            pass
        raise FingerprintCancelled("test limit reached")

    cancelled = run_stress_fingerprint_check(
        OfficeBenchmarkProtocol(
            cold_processes_per_stratum=1,
            warm_iterations=1,
            fingerprint_worker_limit_ms=1,
        ),
        fixture_builder=lambda: stress,
        fingerprint=cooperative_cancel,
    )
    assert cancelled["outcome"] == "cancelled"
    assert cancelled["error_code"] == "fingerprint_cancelled"


def test_runtime_self_identity_is_canonical_and_checks_imported_runtime_versions(
    tmp_path: Path,
) -> None:
    kit_root, _executable, identity = _packaged_runtime(tmp_path)
    resource_root = kit_root / "runtime" / "_internal"
    assert load_runtime_identity(resource_root=resource_root) == identity
    raw = (resource_root / RUNTIME_IDENTITY_RESOURCE_NAME).read_bytes()
    (resource_root / RUNTIME_IDENTITY_RESOURCE_NAME).write_bytes(raw + b"\n")
    with pytest.raises(BenchmarkRunnerError, match="runtime identity"):
        load_runtime_identity(resource_root=resource_root)


def test_packaged_identity_binds_external_identity_lock_protocol_and_executable(
    tmp_path: Path,
) -> None:
    kit_root, executable, identity = _packaged_runtime(tmp_path)
    assert (
        verify_packaged_kit_identity(
            kit_root=kit_root,
            self_executable=executable,
            runtime_identity=identity,
        )
        == identity
    )
    (kit_root / "PACKAGE-LOCK.json").write_bytes(_kit_lock() + b"\n")
    with pytest.raises(BenchmarkRunnerError, match="package lock"):
        verify_packaged_kit_identity(
            kit_root=kit_root,
            self_executable=executable,
            runtime_identity=identity,
        )


def test_entry_mode_is_closed_and_release_has_no_arbitrary_arguments() -> None:
    assert parse_entry_mode(["--self-identity"]) == "self_identity"
    assert parse_entry_mode(["--verify-kit-identity"]) == "verify_kit_identity"
    assert parse_entry_mode(["--release"]) == "release"
    assert (
        parse_entry_mode(
            [
                "--child-mode",
                "identity",
                "--run-id",
                RUN_ID,
                "--child-id",
                "cold-identity-00",
                "--source-commit",
                SOURCE_COMMIT,
                "--working-root",
                "C:/fixed",
            ]
        )
        == "child"
    )
    with pytest.raises(BenchmarkRunnerError, match="entry arguments"):
        parse_entry_mode(["--release", "--output", "C:/arbitrary"])


def test_self_identity_and_verify_modes_emit_no_freeform_output(tmp_path: Path) -> None:
    kit_root, executable, identity = _packaged_runtime(tmp_path)
    resource_root = kit_root / "runtime" / "_internal"
    stdout = BytesIO()
    stderr = BytesIO()
    assert (
        benchmark_child_main(
            ["--self-identity"],
            stdout=stdout,
            stderr=stderr,
            resource_root=resource_root,
            self_executable=executable,
        )
        == 0
    )
    assert stdout.getvalue() == identity_bytes(identity) + b"\n"
    assert stderr.getvalue() == b""

    stdout = BytesIO()
    stderr = BytesIO()
    assert (
        benchmark_child_main(
            ["--verify-kit-identity"],
            stdout=stdout,
            stderr=stderr,
            resource_root=resource_root,
            self_executable=executable,
        )
        == 0
    )
    assert stdout.getvalue() == b""
    assert stderr.getvalue() == b""

    (kit_root / "KIT-IDENTITY.json").write_bytes(
        identity_bytes(replace(identity, source_commit="b" * 40))
    )
    stderr = BytesIO()
    assert (
        benchmark_child_main(
            ["--verify-kit-identity"],
            stdout=BytesIO(),
            stderr=stderr,
            resource_root=resource_root,
            self_executable=executable,
        )
        != 0
    )
    assert stderr.getvalue() == b"modori-runtime-error:runtime_identity_mismatch\n"


def test_release_executor_uses_fixed_protocol_paths_and_identity(
    tmp_path: Path,
) -> None:
    kit_root, executable, identity = _packaged_runtime(tmp_path)
    captured: dict[str, object] = {}
    expected_outputs = (
        kit_root / "results" / "result.json",
        kit_root / "results" / "result.json.sha256",
        kit_root / "results" / "result.summary-ko.txt",
    )

    def publisher(protocol, **kwargs):
        captured["protocol"] = protocol
        captured.update(kwargs)
        return expected_outputs

    result = execute_release_benchmark(
        self_executable=executable,
        kit_root=kit_root,
        identity=identity,
        execution_conditions_provider=lambda _root: _execution_conditions(),
        hardware_provider=lambda _root: _hardware(),
        utc_now=lambda: "2026-07-18T12:34:56Z",
        benchmark_publisher=publisher,
    )
    assert result == expected_outputs
    assert captured["protocol"] == OfficeBenchmarkProtocol()
    assert captured["output_directory"] == kit_root / "results"
    assert captured["working_root"] == kit_root / "work"
    assert captured["verified_self_executable"] == executable
    assert captured["source_commit"] == SOURCE_COMMIT
    assert captured["kit_identity_digest"] == sha256_bytes(identity_bytes(identity))
    assert captured["recorded_at_utc"] == "2026-07-18T12:34:56Z"
    assert captured["error_timestamp"] == "20260718T123456Z"

from dataclasses import dataclass
import importlib
from pathlib import Path

import pytest

import modori.steps  # noqa: F401  # Registers built-in Step types for specs.
from modori.analysis_catalog import AnalysisStatus, RecommendationPolicy, module_specs
from modori.core import PipelineContext, Step, StepResult
from modori.core import model as core_model
from modori.knowledge import load_library, resolve_help_key


@dataclass
class ContractHarnessProbeStep(Step):
    step_type = "contract.probe"
    CURRENT_SCHEMA_VERSION = 1

    @classmethod
    def migrate_params(cls, params: dict[str, object]) -> dict[str, object]:
        return params

    @classmethod
    def validate_params(cls, params: dict[str, object]) -> dict[str, object]:
        return params

    def compute(self, ctx: PipelineContext) -> StepResult:
        return StepResult()

    def reads(self) -> set[str]:
        return set()

    def writes(self) -> set[str]:
        return set()


def test_step_registry_read_helpers_are_public_contract(monkeypatch):
    registered_step_types = getattr(core_model, "registered_step_types", None)
    step_class_for_type = getattr(core_model, "step_class_for_type", None)

    assert callable(registered_step_types)
    assert callable(step_class_for_type)

    monkeypatch.setattr(Step, "_registry", dict(Step._registry))
    Step.register_type(ContractHarnessProbeStep.step_type, ContractHarnessProbeStep)

    assert ContractHarnessProbeStep.step_type in registered_step_types()
    assert step_class_for_type(ContractHarnessProbeStep.step_type) is ContractHarnessProbeStep


@pytest.mark.parametrize("spec", module_specs(), ids=lambda spec: spec.key)
def test_executable_module_specs_have_required_contract_fields(spec):
    if spec.status is not AnalysisStatus.EXECUTABLE:
        pytest.skip(f"{spec.key} is not executable")

    assert spec.step_type
    assert spec.result_type
    assert spec.variable_roles
    assert spec.supported_measures
    assert spec.unsupported_cases
    assert spec.reference_sources
    assert spec.contract_tests
    assert all(Path(path).is_file() for path in spec.contract_tests)
    assert spec.help_keys
    assert spec.step_type in core_model.registered_step_types()


@pytest.mark.parametrize("spec", module_specs(), ids=lambda spec: spec.key)
def test_module_spec_help_keys_resolve_against_seed_library(spec):
    if spec.status is not AnalysisStatus.EXECUTABLE:
        pytest.skip(f"{spec.key} is not executable")

    library = load_library()
    missing = []
    for help_key in spec.help_keys:
        slug = resolve_help_key(help_key)
        if slug is None or slug not in library.all_slugs():
            missing.append(help_key)

    assert missing == []


@pytest.mark.parametrize("spec", module_specs(), ids=lambda spec: spec.key)
def test_result_type_module_is_importable(spec):
    if spec.status is not AnalysisStatus.EXECUTABLE:
        pytest.skip(f"{spec.key} is not executable")

    assert spec.result_type is not None
    module_name, class_name = spec.result_type.rsplit(".", 1)
    module = importlib.import_module(module_name)
    assert getattr(module, class_name)


@pytest.mark.parametrize("spec", module_specs(), ids=lambda spec: spec.key)
def test_recommended_modules_have_eligibility_provider(spec):
    if spec.recommendation_policy in {
        RecommendationPolicy.NEVER,
        RecommendationPolicy.MANUAL_ONLY,
    }:
        pytest.skip(f"{spec.key} does not require recommendation eligibility")

    provider_module = importlib.import_module(f"modori.{spec.key}_recommendation")
    provider = getattr(provider_module, "eligibility_provider")()
    assert provider.module_key == spec.key
    assert callable(provider.candidates)


@pytest.mark.parametrize("spec", module_specs(), ids=lambda spec: spec.key)
def test_executable_steps_expose_schema_migration_contract(spec):
    if spec.status is not AnalysisStatus.EXECUTABLE:
        pytest.skip(f"{spec.key} is not executable")

    assert spec.step_type is not None
    step_cls = core_model.step_class_for_type(spec.step_type)
    assert isinstance(step_cls.CURRENT_SCHEMA_VERSION, int)
    assert step_cls.CURRENT_SCHEMA_VERSION >= 1
    assert callable(step_cls.migrate_params)
    assert callable(step_cls.validate_params)


@pytest.mark.parametrize("spec", module_specs(), ids=lambda spec: spec.key)
def test_executable_step_schema_examples_are_gated_by_contract(spec):
    if spec.status is not AnalysisStatus.EXECUTABLE:
        pytest.skip(f"{spec.key} is not executable")

    assert spec.step_type is not None
    step_cls = core_model.step_class_for_type(spec.step_type)
    examples = getattr(step_cls, "CONTRACT_PARAM_EXAMPLES", None)

    assert isinstance(examples, dict)
    assert {"current", "newer", "unknown_current"} <= set(examples)

    current = step_cls.validate_params(step_cls.migrate_params(dict(examples["current"])))
    assert current["schema_version"] == step_cls.CURRENT_SCHEMA_VERSION

    if examples.get("legacy") is not None:
        legacy = step_cls.validate_params(step_cls.migrate_params(dict(examples["legacy"])))
        assert legacy["schema_version"] == step_cls.CURRENT_SCHEMA_VERSION

    with pytest.raises(ValueError, match="newer schema_version|newer schema"):
        step_cls.migrate_params(dict(examples["newer"]))

    with pytest.raises(ValueError, match="unknown|Unsupported"):
        step_cls.validate_params(
            step_cls.migrate_params(dict(examples["unknown_current"]))
        )

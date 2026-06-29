# TongTong — Reference Vertical Slice Spec #01
## Import Likert → Reverse-code → Compose → Reliability → Two-group comparison → APA report → One-click re-run

> **Purpose of this document.** Define the *first complete vertical slice* for Codex to implement. This single slice exercises the product's anchor ("rework-free pipeline") and every core mechanism (pipeline, assumption checks, automatic rerouting, automatic APA prose, automatic visualization, A/B modes). **All later analyses are built by cloning this skeleton.**
>
> Language: English for engineering record (see `docs/POLICY.md` §1). Product-facing output (UI strings, generated APA text) is Korean-first — that is product content, not engineering record, and is intentional.
> Visual design (color, layout, typography) is **out of scope** for this document (packaging comes later).

---

## PART 0 — Non-negotiable principles (project-wide; stated up front)

These apply to **all of TongTong**, not only this slice.

### P1. Replayable pipeline — highest priority
Every data operation and analysis is a **recorded, replayable Step**, never an in-place mutation.
- Source data is never destroyed. Each step reads its inputs and produces **new outputs**.
- Every step is serializable (JSON) for save/restore. A project file = data + pipeline.
- When an input changes (data, or an upstream step's parameters), **only the dependent downstream steps** recompute, in topological order.
- → This is the implementation basis of the anchor, "re-run everything with one click." **Retrofitting this later means a rewrite. Build it from line 1.**

### P2. Numerical trustworthiness — non-negotiable
All statistics are computed with validated libraries (`scipy` / `statsmodels` / `pingouin` / `factor_analyzer`) and checked against **golden datasets** to at least 3 decimals against published/reference values (§7).

### P3. A/B modes are exposure levels of one engine
A (Guided) mode and B (Standard) mode are *not separate code paths*. Both produce the **same Steps**. The only difference is **how a Step's parameters get filled** (guided dialog vs. direct dialog). C (Expert) mode is out of scope for this slice, but the data model is designed to accept it (§6).

### P4. Deterministic intelligence — no AI
Test selection, assumption checks, rerouting, and prose generation are entirely rule-based. No external calls, no LLM, no randomness (beyond fixed seeds).

### P5. Educational layer — no black boxes
Every result carries (a) "why this test", (b) a plain-language interpretation, and (c) a notice when a reroute occurred (§5.4).

---

## PART 1 — Core data model & pipeline (project-wide foundation)

> Define only what this slice needs, but keep interfaces able to survive project-wide extension.

### 1.1 Variable (column metadata)

```python
class Measure(Enum):
    NOMINAL = "nominal"      # categorical (sex, group)
    ORDINAL = "ordinal"      # ordered (single Likert item)
    SCALE   = "scale"        # continuous / score (composite)

@dataclass
class Variable:
    name: str
    label: str | None                  # human-readable name
    measure: Measure
    value_labels: dict[float, str]      # {1: "strongly disagree", ..., 5: "strongly agree"}
    missing_values: list[float]         # user-defined missing codes (e.g. [99, -9])
    dtype: str                          # "float" | "int" | "string"
    origin_step_id: str | None          # the Step that created this variable (None if raw import)
```

### 1.2 Dataset

```python
@dataclass
class Dataset:
    df: pandas.DataFrame                # actual values (missing normalized to NaN at compute time)
    variables: dict[str, Variable]      # column name → metadata
    # invariant: the column set of df and variables always matches
```

Codes listed in `missing_values` are treated as NaN **at compute time** (the raw df keeps the codes; masking happens during calculation — non-destructive, per P1).

### 1.3 Step (pipeline unit) — abstract

```python
@dataclass
class Step(ABC):
    id: str                             # stable unique id (UUID)
    title: str                          # human-readable step name
    params: dict                        # all parameters, fully serializable
    input_step_ids: list[str]           # ids of upstream steps depended on

    @abstractmethod
    def compute(self, ctx: "PipelineContext") -> "StepResult": ...

    @abstractmethod
    def reads(self) -> set[str]:  ...    # column/object keys read (for the recompute graph)

    @abstractmethod
    def writes(self) -> set[str]: ...    # column/object keys produced

    def provenance(self) -> str:  ...    # one line, e.g. "reverse-coded q3, q7 on a 5-point scale"
```

```python
@dataclass
class StepResult:
    new_columns: dict[str, pandas.Series]   # added/updated columns
    new_variables: dict[str, Variable]      # added/updated variable metadata
    analysis: "AnalysisResult | None"       # analysis output, if any
    notes: list[str]                        # educational-layer messages (P5)
```

### 1.4 Pipeline & recomputation

```python
class Pipeline:
    steps: list[Step]                   # insertion order = default topological order

    def add(self, step: Step) -> None
    def remove(self, step_id: str) -> None
    def edit_params(self, step_id: str, params: dict) -> None   # → triggers recompute
    def recompute(self, dirty_from: str | None) -> None
    def to_json(self) -> str
    @classmethod
    def from_json(cls, s: str) -> "Pipeline"
```

**Recompute rules (core of P1):**
1. If a Step `S`'s params change, or the data (Import) changes, mark `S` dirty.
2. **Transitively** mark dirty every downstream Step whose `reads()` references a key produced by `writes(S)`.
3. Recompute dirty Steps via `compute` in topological order; reuse cached results for non-dirty Steps.
4. → Adding one respondent = only Import dirty → steps 2–6 all refresh automatically. **One click for the user.**

> **Codex note:** correct `reads()/writes()` declarations are the entirety of recompute correctness. Omissions cause stale results. Enforced by tests (§7.3).

---

## PART 2 — Slice workflow (step-by-step spec)

Scenario: a "job satisfaction" scale measured by 8 five-point Likert items (`q1`–`q8`), of which `q3` and `q7` are negatively worded (need reverse-coding), plus a `group` variable (1 = control, 2 = treatment) splitting two groups.

### STEP 1 — Import

**Step type:** `ImportStep(params={path, file_type})`

- Supported formats: `.sav` (SPSS, via `pyreadstat`, preserving value/variable labels and missing codes) / `.csv` / `.xlsx` (`pandas` / `openpyxl`).
  - **`.sav` / `.xlsx` support is a deliberate differentiator** (jamovi cannot read .xls — see competitive notes in `tongtong-project-direction`).
- Output: a `Dataset`. Map `pyreadstat` metadata into `Variable` (value_labels, missing_ranges → missing_values).
- `.csv` has no metadata, so heuristically infer `measure` (≤10 unique & integer → ordinal/nominal, else scale) and let **the user correct it in the variable view**.
- `notes`: summary of row/column counts and missing-cell count.

### STEP 2 — Reverse-code

**Step type:** `RecodeReverseStep(params={columns:[...], scale_min:1, scale_max:5})`

- Formula: `new = (scale_min + scale_max) - old`. (For a 5-point scale: `6 - old`.)
- Output column name: original + `_R` (e.g. `q3_R`). Original is preserved (P1).
- The new `Variable` copies the original's value_labels with **reversed mapping**.
- A-mode prompt: "Is this a *negatively worded* item? (a higher score means *lower* satisfaction) → if so, it needs reverse-coding."
- B-mode: multi-select columns + scale-range input dialog.
- `reads = {q3, q7}`, `writes = {q3_R, q7_R}`.

### STEP 3 — Compose scale

**Step type:** `ComposeScaleStep(params={items:[...], method:"mean"|"sum", name:"job_sat", missing_policy})`

- `method="mean"` (default, robust to missingness) or `"sum"`.
- **Missing handling — user choice (presets + custom)**, `missing_policy`:
  | Preset | Rule | Character |
  |--------|------|-----------|
  | `"survey"` (default) | compute from available items if valid-response ratio ≥ **0.8** | survey-realistic (lenient) |
  | `"conservative"` | NaN if any item is missing (complete cases only) | conservative (listwise) |
  | `"custom"` | user specifies `min_valid` (0–1) directly | custom |
- The default comes from global settings (§5.5). But a created Step owns its `missing_policy` → changeable per case, and a change triggers P1 recompute.
- `notes`: applied policy, number of items used, number of cases dropped for missingness.
- `reads = {8 items}`, `writes = {job_sat}`. Output `job_sat` has `measure=SCALE`.

### STEP 4 — Reliability

**Step type:** `ReliabilityStep(params={items:[...same 8 items...]})`

- Computes:
  - Cronbach's α — `pingouin.cronbach_alpha` (point estimate + 95% CI).
  - McDonald's ω — ω_total derived from a single-factor model's loadings (estimate one-factor loadings via `factor_analyzer`, then apply the formula). *Library choice is Codex's discretion as long as golden values match (§7).*
  - Corrected item-total correlations and an **"alpha if item deleted"** table.
- Returns an `AnalysisResult` of type `ReliabilityResult` (§3).
- Automatic visualization (§5.3): a horizontal bar of corrected item-total correlations per item (low items highlighted). **One chart only by default.**
- Educational note: automatic α grading (table in §5.2 / §4.1).
- `reads = {8 items}`, `writes = {reliability:job_sat}` (analysis object key).

### STEP 5 — Compare two groups ★ heart of deterministic intelligence

**Step type:** `CompareGroupsStep(params={dv:"job_sat", group:"group", routing_policy})`

With dependent `dv` (SCALE) and `group` (two-level NOMINAL), **test selection, assumptions, and rerouting are fully automatic** (P4).

#### 5.1 Decision rule (exact thresholds — Codex implements verbatim)

```
input: dv values for the two groups g1, g2 (missing listwise-dropped)
n1, n2 = group sizes

1) Normality:  Shapiro–Wilk per group (scipy.stats.shapiro)
     normality_violated = (p_g1 < .05) OR (p_g2 < .05)

2) Equal variance:  Levene (pingouin.homoscedasticity, center="median")
     variance_unequal = (p_levene < .05)

3) Test routing:
     IF normality_violated AND min(n1, n2) < 30:
         → Mann–Whitney U  (pingouin.mwu)         # nonparametric reroute
         effect = rank-biserial correlation
         route_reason = "normality violated + small sample"
     ELIF variance_unequal:
         → Welch's t-test  (pingouin.ttest, correction=True)
         effect = Cohen's d
         route_reason = "unequal variance → Welch correction"
     ELSE:
         → Student's t-test (pingouin.ttest, correction=False)
         effect = Cohen's d
         route_reason = "assumptions met"
```

> **Rationale (also surfaced in the educational note):** with n≥30 the Central Limit Theorem makes t robust to non-normality, so we reroute to nonparametric only for small samples. Unequal variance is *always* handled safely by Welch.

**User customization (settings — §5.5):** the rule above is isolated as a swappable policy object `RoutingPolicy`. Selectable presets in global settings:
| Preset | Behavior |
|--------|----------|
| `"modern"` (default) | the rule above, verbatim |
| `"always_welch"` | ignore normality/variance checks; two groups always use Welch t (for methodologists who prefer simple & robust) |
| `"classic"` | check variance then Student/Welch; nonparametric auto-reroute OFF (user selects manually) |
| `"custom"` | user sets normality p threshold, nonparametric n cutoff, and whether Levene is used |

The policy is **snapshotted into `CompareGroupsStep.params` at Step-creation time** (changing global settings later does not alter existing analyses — reproducibility). To change an existing analysis, edit that Step's policy params → P1 recompute. A mode always exposes `modern` (beginner protection); the policy-change UI lives in B / settings.

#### 5.2 Output
`ComparisonResult` (§3): test name, per-group M/SD/n (or median/rank), test statistic, df, p, effect size + interpretation, 95% CI of the mean difference, and the chosen route with its reason.

#### 5.3 Automatic visualization (per §5.3 rules)
- t-family: **per-group mean bars + 95% CI error bars + jittered raw points.**
- MWU: **box plot (or violin)** — median-based (honest for a nonparametric test).
- The chart changes *automatically* with the analysis route (means vs. medians).

### STEP 6 — Report (APA)

**Step type:** `ReportStep(params={include:[reliability, comparison]})`

- Gathers upstream analysis results into one document object: **APA tables + automatic prose + figures.**
- Output: on-screen preview + **Word (.docx) export** (`python-docx`). Tables in APA 7th-edition format; figures as 300 dpi PNG + vector (SVG/EPS) simultaneously.
- Prose is generated from the §4 templates. **Numbers are injected directly from result objects → zero transcription error (the anchor's loss-elimination point).**

### STEP 7 — Re-run (proves the anchor)

Not a separate Step — a demonstration of the P1 mechanism:
- The user adds N respondents to Import (or inserts an outlier-exclusion Step, or changes the `group` definition).
- → Import dirty → steps 2·3·4·5·6 transitively dirty → topological recompute → **every table, sentence, and figure in the report refreshes at once.**
- Acceptance (§7.2): after a data change, **one** user action yields a consistently updated final .docx.

---

## PART 3 — Analysis result data structures

```python
@dataclass
class ReliabilityResult:
    scale_name: str
    n_items: int
    n_cases: int
    cronbach_alpha: float
    alpha_ci: tuple[float, float]
    mcdonald_omega: float
    item_total_corr: dict[str, float]      # corrected
    alpha_if_deleted: dict[str, float]
    apa_template_id: str = "reliability.v1"
    chart_spec: "ChartSpec"

@dataclass
class ComparisonResult:
    dv: str
    group_var: str
    test_name: str                         # "student_t" | "welch_t" | "mann_whitney"
    route_reason: str
    groups: dict[str, "GroupDesc"]         # label → (n, mean, sd, median)
    statistic: float                       # t or U
    df: float | None
    p_value: float
    effect_name: str                       # "cohen_d" | "rank_biserial"
    effect_value: float
    mean_diff_ci: tuple[float, float] | None
    assumptions: dict                      # {shapiro_g1_p, shapiro_g2_p, levene_p}
    apa_template_id: str                   # "ttest.v1" | "mwu.v1"
    chart_spec: "ChartSpec"
```

`AnalysisResult = ReliabilityResult | ComparisonResult`. **Every result carries its own `chart_spec` (how to draw it) and `apa_template_id` (how to write it)** — a contract all future analyses follow.

`ChartSpec` is a library-independent description (chart type + data + axes/labels) interpreted by a matplotlib renderer (renderer is swappable later).

---

## PART 4 — Automatic APA prose templates

> **Mechanism:** a template = numeric slots + conditional branches. Not an LLM (P4). Hallucination is impossible. **Korean primary / English secondary** (English-language tools cannot auto-write Korean → a differentiator). Number formatting follows APA: p to three decimals (`p = .009`, `p < .001`), statistics to two.

### 4.1 Reliability (`reliability.v1`)

α grade (qualifier) branch uses five tiers, matching the reporting engine and
standard reliability-reporting convention:
`≥.90 excellent / 매우 높은`, `≥.80 good / 높은`,
`≥.70 acceptable / 수용 가능한`, `≥.60 questionable / 다소 낮은`,
`<.60 low / 낮은`.

- **KO:** `"{scale_name} 척도는 {qualifier_ko} 내적 일관성을 보였다(Cronbach's α = {α}, McDonald's ω = {ω})."`
- **EN:** `"The {scale_name} scale showed {qualifier_en} internal consistency (Cronbach's α = {α}, McDonald's ω = {ω})."`
- If α < .70, also surface the "alpha if item deleted" table in the educational note and point to the item with the largest improvement. The `.60 ≤ α < .70` band must be reported as `questionable` / `다소 낮은`, not silently collapsed into `low`.

### 4.2 Independent / Welch t (`ttest.v1`)

Significant / non-significant branch. Group descriptives are included in the
manuscript sentence so a data or coding change that shifts group means cannot
produce a visually identical report sentence.

- **Significant (p<.05) KO:** `"독립표본 t검정 결과, {g1_label}(M = {m1}, SD = {sd1}, n = {n1})와 {g2_label}(M = {m2}, SD = {sd2}, n = {n2})의 {dv_label} 점수 차이(Mdiff = {mean_diff})는 통계적으로 유의하였다, t({df}) = {t}, {p}, 95% CI [{ci_low}, {ci_high}], Cohen's d = {d}."`
- **Non-significant KO:** `"독립표본 t검정 결과, {g1_label}(M = {m1}, SD = {sd1}, n = {n1})와 {g2_label}(M = {m2}, SD = {sd2}, n = {n2})의 {dv_label} 점수 차이(Mdiff = {mean_diff})는 통계적으로 유의하지 않았다, t({df}) = {t}, {p}, 95% CI [{ci_low}, {ci_high}], Cohen's d = {d}."`
- **Significant (p<.05) EN:** `"An independent-samples t test showed a statistically significant {dv_label} score difference between {g1_label}(M = {m1}, SD = {sd1}, n = {n1}) and {g2_label}(M = {m2}, SD = {sd2}, n = {n2}), t({df}) = {t}, {p}, 95% CI [{ci_low}, {ci_high}], Cohen's d = {d}."`
- **Non-significant EN:** `"An independent-samples t test showed no statistically significant {dv_label} score difference between {g1_label}(M = {m1}, SD = {sd1}, n = {n1}) and {g2_label}(M = {m2}, SD = {sd2}, n = {n2}), t({df}) = {t}, {p}, 95% CI [{ci_low}, {ci_high}], Cohen's d = {d}."`
- On the Welch route, say the correction once by using the test label `독립표본 t검정(Welch 보정)` / `Welch independent-samples t test`; do not append a second "Welch 보정" phrase.
- For Welch, `df` is shown with decimals.

### 4.3 Mann–Whitney U (`mwu.v1`)

- **KO:** `"정규성 가정이 충족되지 않고 표본이 작아 Mann–Whitney U 검정을 실시하였다. {g1_label}(Mdn = {md1})과 {g2_label}(Mdn = {md2}) 간 차이는 {유의/유의하지 않}았다, U = {U}, p = {p}, r = {r}."`

---

## PART 5 — A/B modes & educational layer

### 5.1 A mode (Guided) — STEP 5 entry flow example
Plain-language questions (no statistical jargon); never ask what the variable view can infer:
1. "Do you want to see whether two groups' scores **differ**?" → yes → CompareGroups
2. "Which score is the outcome?" → `job_sat` (offer only SCALE variables)
3. "Which variable splits the groups?" → `group` (offer only two-level NOMINAL variables)
4. (The rest — normality, equal variance, test selection, rerouting — is **automatic**, not asked.)

### 5.2 B mode (Standard)
Menu `Analyze ▸ Compare Means ▸ Independent Samples` → dialog (specify dependent / group). Assumptions, rerouting, APA, and charts are **automatic, identical to A**. The only difference is skipping the guided dialog (P3).

### 5.3 Automatic visualization rules (project-wide)
- **One canonical chart per analysis by default** (no chart spam). The rest under "show more".
- The analysis route determines the chart (mean ± CI vs. box).
- Publication defaults: grayscale-print-safe palette, automatic axes/labels, vector export.

### 5.4 Educational layer (P5) — accompanies every result
- (a) **Why:** "The sample is small and normality was doubtful, so we switched to a nonparametric test."
- (b) **Interpretation:** "p = .009 → less than a 1% chance the group difference is due to chance."
- (c) **Reroute notice:** prominently shown whenever the route departs from the default.

---

## PART 5.5 — Settings & reproducibility principle

Allow user customization **without breaking reproducibility (P1/P2)**, via one rule:

> **Settings = default provider; the Step = owner of truth.**
> Global settings (e.g. routing policy, missing-data policy, default compose method) are **snapshotted into a Step's `params` *when the Step is created*.** After creation the Step owns its params; changing global settings later **never alters existing Steps or existing results.**

Why: if a global setting silently changed an already-computed result, reopening a project six months later could yield different numbers — a disaster. To change a result, you always **explicitly edit that Step's params** → P1 recompute (a visible change).

```python
@dataclass
class AnalysisPreferences:           # global defaults (persisted in app settings)
    routing_policy: str = "modern"           # §5.1
    missing_policy: str = "survey"           # STEP 3
    default_compose_method: str = "mean"
    report_language: str = "ko"              # ko primary / en
    # for the "custom" presets:
    custom_routing: dict | None = None
    custom_min_valid: float | None = None
```

- On Step creation: `step.params = snapshot(prefs)` (relevant keys only).
- Per-case override: edit that Step's params (B mode / properties panel).
- A mode: safe defaults are fixed; policy changes only in settings (beginner protection).

---

## PART 6 — Design notes for C-mode acceptance (not implemented here)

This slice implements only A/B, but to **avoid a rewrite** it observes:
- `Step` / `AnalysisResult` are polymorphic — C's future SEM / multilevel models follow the same `compute` / `chart_spec` / `apa_template_id` contract.
- `CompareGroupsStep`'s auto-routing is a **swappable policy object** (`RoutingPolicy`) — the injection point for C's user overrides.
- `ChartSpec` renderer is decoupled (accepts C's advanced graphics).

---

## PART 7 — Validation & Definition of Done

### 7.1 Numerical golden tests (P2)
Against a public dataset (e.g. a well-known Likert scale dataset):
- α, ω, t/Welch/U, and Cohen's d must **match R (`psych`, `effsize`) or SPSS reference output to 3 decimals** in unit tests.
- Test the routing rule (§5.1) at boundary values (p near .05, n = 29/30).

### 7.2 Anchor (re-run) acceptance test
- Add cases to the data → **one** user action → every number, sentence, and figure in the final .docx matches the new data (no staleness).
- Change a reverse-code Step param → compose, reliability, comparison, and report all update automatically.

### 7.3 Pipeline integrity tests
- Correctness of every Step's `reads()/writes()`: dirty propagation touches exactly the necessary Steps (both over- and under-recompute count as failures).
- Pipeline serialization round-trip (to_json → from_json → identical results).

### 7.4 Slice Definition of Done
7.1–7.3 pass + the scenario runs end-to-end (to .docx output) in **both** A and B modes.

---

## PART 8 — Explicitly out of scope for this slice (scope discipline)
The following are **not implemented here** (to prevent sprawl). The §6 contract keeps them acceptable later.
- 3+ groups / covariates / repeated measures; regression, factor analysis, mediation (later slices)
- Missing-data imputation — this slice goes only as far as available-case computation + missingness reporting
- C (Expert) mode, network visualization (v1.5)
- Design / theming / packaging

---

## PART 9 — Codex build order & handoff checklist

**Recommended implementation order** (each is a prerequisite for the next — do not go backward):
1. **Data model + pipeline core** (PART 1) — `Variable`/`Dataset`/`Step`/`Pipeline`/recompute graph. Validate headless with unit tests first (§7.3), no UI.
2. **ImportStep** (.sav/.csv/.xlsx) + variable-view data structures.
3. **Data-prep Steps**: RecodeReverse → ComposeScale (including missing policy).
4. **ReliabilityStep** (+ golden tests §7.1).
5. **CompareGroupsStep** + `RoutingPolicy` (+ boundary-value tests).
6. **APA template engine** (PART 4) + **ChartSpec / matplotlib renderer**.
7. **ReportStep** → .docx.
8. **Re-run acceptance test** (§7.2) — proves the anchor.
9. **PySide6 UI** + A/B mode exposure. (UI last — after the engine is correct headless.)

**Agreed before handoff (fixed in this document):** P1–P5 principles · default routing/missing/language policies · the settings-snapshot reproducibility rule · Definition of Done (§7.4) · out-of-scope (PART 8).

**Reviewer (planning) gate:** review first whenever Codex finishes items 1 and 8 — if the pipeline core and re-run are correct, the rest is pattern cloning.

---

### Appendix A — Library mapping (Codex starting point, changeable)
| Function | Primary library |
|----------|-----------------|
| .sav I/O | `pyreadstat` |
| dataframes | `pandas` |
| α / t / Welch / MWU / Levene | `pingouin` |
| normality (Shapiro) | `scipy.stats` |
| McDonald's ω / one-factor loadings | `factor_analyzer` (or equivalent, subject to golden-value match) |
| visualization | `matplotlib` (+ `seaborn` helper) |
| .docx export | `python-docx` |
| UI | `PySide6` |

# TongTong — Vertical Slice Spec #03
## Knowledge Library — the deterministic methods-knowledge base behind click-help & method advice

> **Purpose.** Build the curated, citable knowledge base of research-methods knowledge
> that powers two *deterministic* assist features (no AI): contextual click-help and
> the method advisor. The user confirmed: **SLM deferred — deterministic only.** This
> slice is the foundation those features (and any *future, optional* SLM) sit on.
>
> **Reuse, do not re-specify.** Inherits everything from
> `specs/01-reference-slice-likert-to-report.md` and `docs/POLICY.md`
> (P1–P5, the data/Step/Pipeline model, validation honesty, KO-first product output).
>
> Language: spec/code in English (POLICY §1). **Library content is product-facing →
> Korean-first, English secondary** (the documented product-content exception).

---

## PART 0 — Principles for this slice

Inherits P1–P5. Three library-specific rules, elevated from the slice #01/#02 reviews:

- **L1. Citations must be real (no fabrication).** Same discipline that caught the
  slice #01 ω defect, applied to *content*. Every reference is a real, canonical
  source. Any locator (page/section) or claim the author is not certain of is marked
  `verification_status: needs_review` and surfaced for human approval. Never present an
  uncertain citation as verified.
- **L2. Deterministic & offline.** The library is static curated data shipped with the
  app. Lookup is a pure function of (slug, language). No network, no model, no
  generation at runtime. Works fully on low-spec PCs.
- **L3. Link integrity is load-bearing (like reads/writes in P1).** Every cross-link
  and every help-key must resolve to an existing entry; every term the engine emits
  must be covered. Enforced by tests (PART 5).

---

## PART 1 — LibraryEntry schema

```python
class EntryKind(Enum):
    METHOD      = "method"       # e.g. independent t-test, OLS regression
    CONCEPT     = "concept"      # e.g. p-value, confidence interval
    ASSUMPTION  = "assumption"   # e.g. normality, homoscedasticity
    STATISTIC   = "statistic"    # e.g. VIF, R², Cronbach's α
    DIAGNOSTIC  = "diagnostic"   # e.g. Breusch–Pagan, Cook's distance
    EFFECT_SIZE = "effect_size"  # e.g. Cohen's d, rank-biserial

class VerificationStatus(Enum):
    VERIFIED      = "verified"       # author confident; >=1 verified reference
    NEEDS_REVIEW  = "needs_review"   # awaiting human confirmation (L1)

@dataclass(frozen=True)
class Reference:
    citation: str            # full human-readable ref, e.g.
                             # "Cohen, J. (1988). Statistical Power Analysis for the
                             #  Behavioral Sciences (2nd ed.). Erlbaum."
    locator: str | None      # page/section/table, or None if not certain
    verified: bool           # False => author not certain it exists/locates; user must confirm

@dataclass(frozen=True)
class LibraryEntry:
    slug: str                # stable id, kebab-case: "independent-t-test", "p-value"
    kind: EntryKind
    title_ko: str
    title_en: str
    summary_ko: str          # 1–2 sentences, plain language for the stats-anxious user
    summary_en: str
    interpretation_ko: str | None  # "how to read it" — e.g. p-value: "우연일 확률…"
    interpretation_en: str | None
    when_to_use_ko: str | None     # for METHOD/DIAGNOSTIC
    when_to_use_en: str | None
    how_to_report_ko: str | None   # APA reporting guidance
    how_to_report_en: str | None
    pitfalls_ko: str | None        # common mistakes
    pitfalls_en: str | None
    assumptions: list[str] = []    # slugs (for METHOD) → ASSUMPTION entries
    alternatives: list[str] = []   # slugs (e.g. independent-t-test → mann-whitney-u)
    related: list[str] = []        # see-also slugs
    references: list[Reference] = []
    verification_status: VerificationStatus = VerificationStatus.NEEDS_REVIEW
```

Not every field applies to every kind (a CONCEPT has no `assumptions`); unused fields
are `None`/empty. Required-by-kind rules are enforced in PART 5.

---

## PART 2 — Storage & loading

- One file per entry, in `library/entries/<slug>.yaml` (or `.json`) — diff-able,
  reviewable, version-controlled. Human-curated content; not generated.
- A loader parses files into `LibraryEntry` objects at startup into an in-memory
  `Library`. Parsing is strict: unknown fields or missing required fields → load error
  (fail fast, never silently drop content).
- Bilingual fields live in the same entry file (KO + EN side by side).

---

## PART 3 — Integration contracts (how ② and ③ consume the library)

This slice ships the library + its consumption API. The *UI* of click-help and the
*conversational* advisor are later UI slices; here we define and test the contracts so
those become wire-up, not redesign.

### 3.1 Click-help (②) — entity → slug resolution
Every explainable thing the app shows must resolve to a library slug:
- result/table fields (e.g. `"p_value"`, `"r_squared"`, `"vif"`, `"cohen_d"`),
- test names (`"student_t"`, `"welch_t"`, `"mann_whitney"`, `"regression_ols"`),
- assumption/diagnostic keys (`"shapiro_resid_p"`, `"breusch_pagan"`, `"durbin_watson"`),
- menu/analysis identifiers.

A deterministic **help-key registry** maps these engine/UI vocabulary keys → slugs:
```python
HELP_KEYS: dict[str, str] = {
    "p_value": "p-value",
    "welch_t": "welch-t-test",
    "vif": "vif",
    ...
}
```
The right-click UI (later) calls `library.explain(slug, language)`; this slice provides
`resolve_help_key(entity_key) -> slug | None` and `explain(...)`.

### 3.2 Method advisor (③) — decision-tree leaves → slug
The slice #01 A-mode decision tree's recommendations carry a `library_slug`, so a
recommendation can show the entry's `when_to_use` / `assumptions` / `why`. This slice
does not build the tree UI; it requires that **every method the tree can recommend has
an entry** (coverage test, PART 5).

### 3.3 Retrieval API (headless, deterministic)
```python
class Library:
    def get(self, slug: str) -> LibraryEntry            # KeyError if missing
    def explain(self, slug: str, language: str) -> dict # fields click-help renders
    def resolve_help_key(self, entity_key: str) -> str | None
    def all_slugs(self) -> set[str]
    def needs_review(self) -> list[LibraryEntry]         # L1 surfacing for the user
```
`explain` returns only the relevant localized fields (title, summary, interpretation,
when_to_use, how_to_report, pitfalls, resolved links, references) for the requested
language, falling back to the other language only with an explicit flag.

---

## PART 4 — Educational layer wiring (P5 made pervasive)
The existing per-result educational notes (P5) should, where natural, reference library
slugs so the UI can deep-link ("왜 이 검정인가" → the method entry; a flagged assumption
→ that assumption entry). This slice only adds the *links/keys*; rendering is UI work.

---

## PART 5 — Validation & Definition of Done

### 5.1 Schema & required-by-kind tests
- Every entry loads; required fields present in BOTH languages
  (title/summary always; `when_to_use` required for METHOD/DIAGNOSTIC;
  `interpretation` required for CONCEPT/STATISTIC/EFFECT_SIZE; etc.).

### 5.2 Link-integrity tests (L3 — load-bearing)
- Every slug in `assumptions`/`alternatives`/`related` resolves to an existing entry
  (no dangling links).
- Every value in `HELP_KEYS` resolves to an existing entry.
- Slugs are unique and kebab-case.

### 5.3 Coverage tests (the engine's vocabulary is fully explainable)
- Every `test_name`, `effect_name`, diagnostic key, and `apa_template_id` the engine
  can produce (slices #01/#02) has a `HELP_KEYS` entry → a library entry. A test
  enumerates the engine's emitted vocabulary and asserts full coverage. (Prevents the
  UI from ever showing an unexplainable term.)

### 5.4 Citation honesty (L1)
- Every `VERIFIED` entry has ≥1 reference with `verified: true`.
- `library.needs_review()` lists all `NEEDS_REVIEW` entries; a report (not a failure)
  is emitted for the user to action. Unverified locators must not be marked verified.

### 5.5 Definition of Done
- 5.1–5.4 pass; the seed set (PART 6) is loaded and link-complete; existing slice
  #01/#02 tests remain green; no runtime network/model use.

---

## PART 6 — Seed content (authored by Claude, reviewed by the user)

Author entries covering the vocabulary already produced by slices #01/#02 so click-help
and the advisor work for everything currently shippable:

- **Methods:** cronbach-alpha, mcdonald-omega, independent-t-test, welch-t-test,
  mann-whitney-u, multiple-regression-ols.
- **Concepts:** p-value, confidence-interval, statistical-significance,
  listwise-deletion, standardized-beta.
- **Assumptions:** normality, homogeneity-of-variance, linearity,
  independence-of-errors, multicollinearity, homoscedasticity.
- **Statistics/diagnostics/effect sizes:** r-squared, adjusted-r-squared, f-test,
  vif, breusch-pagan, durbin-watson, cooks-distance, corrected-item-total-correlation,
  shapiro-wilk, cohens-d, rank-biserial.

### Authoring discipline (Claude → user review)
- Draft from canonical sources only (e.g. Field, *Discovering Statistics*; Tabachnick &
  Fidell, *Using Multivariate Statistics*; Cohen, 1988; APA *Publication Manual*, 7th;
  Nunnally & Bernstein, *Psychometric Theory*; Hair et al., *Multivariate Data
  Analysis*). Cite only sources I am confident exist.
- Do NOT invent page numbers or exact quotations. Uncertain locators →
  `verified: false`; uncertain entries → `verification_status: needs_review`.
- The user reviews/approves; `needs_review` items get the user's verification.

### Plain-language standard (content rule for every entry)
The target reader is the stats-anxious user who "didn't follow the stats class."
Two rules, applied to all entries:
- **Plain-first:** `summary_ko`/`summary_en` must be understandable with ZERO
  statistics background — no undefined jargon in the opening. If a technical term is
  unavoidable, gloss it in the same breath. The formal term name (e.g.
  "내적 일관성 신뢰도" / "internal-consistency reliability") goes in `interpretation`
  or the title, NOT in the summary's first clause. (Example: Cronbach's α summary
  leads with "여러 문항이 정말 '같은 것'을 재고 있는지 알려 주는 0~1 점수", and names the
  formal term only in `interpretation`.)
- **Every term is a door:** any statistics term used in any field should itself be (or
  become) a library slug, so the click-help UI can explain it recursively — the
  library explains its own vocabulary. New jargon surfaced while authoring becomes a
  new entry (or a `needs_review` stub). Reviewer/coverage checks (§5.3) guard the
  engine's vocabulary; authors keep summaries jargon-free by hand (no reliable
  automated reading-level gate — it stays a human review item).

### Example seed entry (illustrative shape)
```yaml
slug: welch-t-test
kind: method
title_ko: "Welch 독립표본 t검정"
title_en: "Welch's independent-samples t-test"
summary_ko: "두 집단의 평균이 다른지 보되, 두 집단의 분산이 다를 때 안전한 t검정."
summary_en: "Compares two group means while correcting for unequal group variances."
when_to_use_ko: "두 독립 집단의 평균 비교에서 등분산 가정이 의심될 때(기본 권장)."
when_to_use_en: "Comparing two independent group means when equal variances are doubtful."
how_to_report_ko: "t(df) = …, p = …, Cohen's d = … 형식으로 보고. df는 소수로 표기."
how_to_report_en: "Report t(df) = …, p = …, Cohen's d = …; df is fractional."
pitfalls_ko: "정규성이 심하게 깨지고 표본이 작으면 Mann–Whitney U를 고려."
pitfalls_en: "With small, strongly non-normal samples, consider Mann–Whitney U."
assumptions: [independence-of-errors, normality]
alternatives: [student-t-test, mann-whitney-u]
related: [cohens-d, p-value]
references:
  - citation: "Field, A. (2018). Discovering Statistics Using IBM SPSS Statistics (5th ed.). Sage."
    locator: null            # [검증요망] exact page
    verified: false
verification_status: needs_review
```

---

## PART 7 — Explicitly out of scope
- **SLM / any runtime model** (deferred; the Library API is the grounding source a
  future optional SLM would retrieve from — no rework needed to add it later).
- The **right-click UI** rendering and the **conversational advisor UI** (later UI
  slices; this slice ships the data + headless API + contracts).
- Content beyond the seed set; the decision-tree implementation itself (#01 A-mode).
- Design/theming.

---

## PART 8 — Build order & reviewer gate
1. `LibraryEntry`/`Reference`/enums + strict loader (`library/entries/*.yaml`).
2. `Library` retrieval API + `HELP_KEYS` registry + `resolve_help_key`/`explain`.
3. Validation tests: schema/required-by-kind (5.1), link-integrity (5.2),
   coverage of engine vocabulary (5.3), citation honesty report (5.4).
4. Seed content authored (Claude) → user review of `needs_review` items → committed.
5. Wire result educational notes / advisor leaves to slugs (light links).

**Reviewer (planning) gate:** review after (3) — schema + integrity/coverage tests are
the foundation's correctness. Then review the seed content for methodological accuracy
and citation honesty (the reviewer/author will flag every `needs_review` item rather
than assert unverified citations).

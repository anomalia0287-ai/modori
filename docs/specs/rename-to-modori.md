# Directive — Rename code package: tongtong → modori (mechanical, behavior-unchanged)

The product is renamed to **Modori** (모도리). Rename the Python package and all
internal references now, while the project is small. This is a pure mechanical refactor:
**no logic changes, behavior identical, all tests still green.** Per docs/POLICY.md.

## Scope — DO
1. **Package directory:** `src/tongtong/` → `src/modori/` (including subpackages
   `core/`, `steps/`, `knowledge/` and all modules).
2. **Imports:** every `import tongtong...` / `from tongtong...` → `modori` across
   `src/` and `tests/`.
3. **pyproject.toml:** `name = "tongtong"` → `"modori"`; console script
   `tongtong = "tongtong.app:main"` → `modori = "modori.app:main"`. Keep
   `where = ["src"]` and `pythonpath = ["src"]`.
4. **Env vars / cache dirs / internal name strings:** `TONGTONG_*` → `MODORI_*`
   (e.g. `TONGTONG_MPLCONFIGDIR`, and `TONGTONG_RSCRIPT` used in tests), the
   `.tongtong_cache` directory name → `.modori_cache`, and any other literal
   "tongtong" identifiers in code. Update tests that reference these consistently.
5. **Product-facing strings in code:** app/window title and report headings
   (e.g. the docx heading "TongTong analysis report" → "Modori analysis report").
   UI/product strings remain Korean-first where applicable.
6. **Reinstall editable** so the entry point + metadata refresh:
   `pip install -e .` (the egg-info regenerates under the new name).

## Scope — DO NOT
- **Do NOT rename the repo OS folder** `C:\Users\V\Desktop\TongTong` (would disrupt the
  active working directory / session paths). Folder rename is deferred, separate.
- **Do NOT touch the historical spec docs' wordmarks** (`docs/specs/01..03*`,
  `docs/POLICY.md`) in this pass — they are engineering records; a doc wordmark sweep is
  a separate, optional task. (New docs use Modori.)
- No behavior/logic changes; no new features.

## Verify (Definition of Done)
- `library/entries/*` still loads (the loader's entries-dir path is depth-based, not
  name-based; renaming `src/tongtong`→`src/modori` keeps the same depth — confirm
  `load_library()` works).
- Full suite green: 178 passed / 2 skipped (R-gated) / 0 fail, same as before.
- `python -c "import modori"` works; `import tongtong` no longer resolves.
- No residual references: `grep -ri "tongtong" src tests pyproject.toml` returns nothing
  (case-insensitive — also catches TONGTONG_*). The only remaining "TongTong" allowed is
  in the historical `docs/specs/*` and the OS folder name.
- compileall passes.

## Note for the reviewer
After this lands, the reviewer re-runs the suite and the residual-reference grep to
confirm a clean rename, then resumes the UI work (which will use the Modori name).

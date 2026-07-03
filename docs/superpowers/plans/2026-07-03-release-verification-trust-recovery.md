# Release Verification Trust Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore trust in the clean-Windows release verification path before making any stronger accuracy or release-readiness claim.

**Architecture:** Treat verification scripts as product-adjacent code with explicit contracts and regression tests. Separate import-preview samples from engine-smoke samples, and make the VM payload self-describing so a failed run can be classified as product failure, verification-tool failure, or operator/environment failure.

**Tech Stack:** PowerShell 5.1 scripts, Windows batch files, PyInstaller packaged `Modori.exe`, pytest static contract tests, clean Hyper-V Windows VM.

---

### Task 1: Lock the Clean VM Payload Contract

**Files:**
- Create: `tests/test_clean_vm_payload_script.py`
- Modify: `scripts/attach_modori_payload_disk.ps1`

- [ ] **Step 1: Write the failing test**

Add a test that reads `scripts/attach_modori_payload_disk.ps1` and asserts:

```python
def test_payload_script_writes_a_human_readable_contract_file() -> None:
    text = Path("scripts/attach_modori_payload_disk.ps1").read_text(encoding="utf-8")

    assert "QA_CONTRACT.txt" in text
    assert "engine-smoke-reference.xlsx" in text
    assert "visible-import-reference.xlsx" in text
    assert "Engine smoke sample" in text
    assert "Import visibility samples" in text
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_clean_vm_payload_script.py::test_payload_script_writes_a_human_readable_contract_file -q
```

Expected: FAIL because `QA_CONTRACT.txt` is not yet written.

- [ ] **Step 3: Write minimal implementation**

Update `scripts/attach_modori_payload_disk.ps1` to write `QA_CONTRACT.txt` at the payload drive root with:

```text
Engine smoke sample: Samples\engine-smoke-reference.xlsx
Import visibility samples:
- Samples\visible-import-reference.csv
- Samples\visible-import-reference.xlsx
- Samples\visible-import-reference.sav
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_clean_vm_payload_script.py::test_payload_script_writes_a_human_readable_contract_file -q
```

Expected: PASS.

### Task 2: Lock Engine Smoke Batch Semantics

**Files:**
- Modify: `tests/test_clean_vm_payload_script.py`
- Verify: `scripts/attach_modori_payload_disk.ps1`

- [ ] **Step 1: Write the failing-or-guard test**

Add a test that asserts the generated batch command uses `start /wait`, passes `engine-smoke-reference.xlsx`, does not pass `visible-import-reference.xlsx` to `--engine-smoke`, prints the JSON, and returns the executable exit code.

- [ ] **Step 2: Run the test**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_clean_vm_payload_script.py -q
```

Expected: PASS after Task 1 and the prior engine-smoke correction.

### Task 3: Verify Host Reference Before VM Re-run

**Files:**
- No code changes.

- [ ] **Step 1: Run host packaged engine smoke against `engine-smoke-reference.xlsx`**

Run:

```powershell
.\.venv\Scripts\python.exe -c "from pathlib import Path; import subprocess, json; root=Path.cwd(); out=root/'.visual-qa/clean-win-vm-payload/host-engine-smoke-reference.json'; out.unlink(missing_ok=True); completed=subprocess.run([str(root/'dist/Modori/Modori.exe'),'--engine-smoke',str(root/'.visual-qa/clean-win-vm-payload/engine-smoke-reference.xlsx'),str(out)], timeout=60); print(completed.returncode); print(out.read_text(encoding='utf-8'))"
```

Expected: return code `0`, JSON contains `"ok": true`.

### Task 4: Rebuild and Attach VM Payload V2

**Files:**
- Use: `RUN_ATTACH_PAYLOAD_AS_ADMIN.cmd`

- [ ] **Step 1: Run attach script from host as Administrator**

Run:

```text
C:\Users\V\Desktop\TongTong\RUN_ATTACH_PAYLOAD_AS_ADMIN.cmd
```

Expected: `ModoriPayloadV2.vhdx` exists and `MODORIQA2` appears in the VM.

### Task 5: Clean VM Verification

**Files:**
- Use VM payload only.

- [ ] **Step 1: In the VM, run `MODORIQA2\Run-Engine-Smoke-XLSX.bat`**

Expected: `Exit code: 0`, JSON contains `"ok": true`.

- [ ] **Step 2: In the VM, run `MODORIQA2\Run-Modori.bat`**

Expected: app opens, entry screen is visible.

- [ ] **Step 3: Use visible import samples**

Use:

```text
MODORIQA2\Samples\visible-import-reference.csv
MODORIQA2\Samples\visible-import-reference.xlsx
MODORIQA2\Samples\visible-import-reference.sav
```

Expected: import preview opens and identifies rows/columns without crashing.

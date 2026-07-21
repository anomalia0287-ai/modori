# Compact Control Correction Implementation Plan

> **Goal:** Replace the oversized mode selector and native-looking form controls with compact, coherent cream-and-nacre controls, then verify and relaunch the real Modori application.

## 1. Lock the visual contract with tests

- Add a focused UI contract test for compact sizing, the true two-state mode switch, and the moderately rounded checkbox.
- Assert that user-facing forms no longer instantiate raw `CheckBox`, `TextField`, `ComboBox`, or `SpinBox` controls.
- Run the test once and confirm that it fails against the current implementation.

## 2. Implement the shared control system

- Add `AppCheckBox`, `AppTextField`, `AppComboBox`, and `AppSpinBox` based on Qt Quick Controls Basic.
- Use official Lucide icons for check and chevron marks.
- Keep checkbox corners at 4 px: softened square, never a capsule.
- Replace the wide mode buttons with one compact switch flanked by concise mode labels.

## 3. Tighten hierarchy and surfaces

- Reduce command-bar and control heights and lower the visual weight of button labels.
- Tune the cream/teal palette to a quieter nacre appearance.
- Reduce large panel radii and nested raised surfaces so the workspace reads as one grounded plane.

## 4. Verify and relaunch

- Run the focused contract test, the complete UI test suite, and the relevant application tests.
- Render the actual QML at the same desktop viewport, compare it with the reported screenshots, and fix visible regressions.
- Stop only the previously launched Modori process and launch the corrected application from the project environment.

from pathlib import Path


SCRIPT = Path("installer/modori.iss")


def _text() -> str:
    return SCRIPT.read_text(encoding="utf-8")


def test_inno_script_has_permanent_safe_install_contract() -> None:
    text = _text()
    for expected in [
        "AppId={{{#AppIdValue}}",
        r"DefaultDirName={localappdata}\Programs\Modori",
        "PrivilegesRequired=lowest",
        "ArchitecturesAllowed=x64compatible",
        "CloseApplications=yes",
        "RestartApplications=no",
        r'Type: filesandordirs; Name: "{app}\Modori"',
        r'DestDir: "{app}\Modori"',
        r'Filename: "{app}\Modori\Modori.exe"',
    ]:
        assert expected in text


def test_inno_script_requires_boolean_custom_dir_compile_definition() -> None:
    text = _text()

    assert "#ifndef AllowCustomDirValue" in text
    assert "#error AllowCustomDirValue is required" in text
    assert "Int(AllowCustomDirValue) != 0" in text
    assert "Int(AllowCustomDirValue) != 1" in text


def test_inno_script_locks_final_production_directory() -> None:
    text = _text()

    assert "DisableDirPage=yes" in text
    assert "UsePreviousAppDir=no" in text

    code = text.split("[Code]", 1)[1]
    signature = "function PrepareToInstall(var NeedsRestart: Boolean): String;"
    assert signature in code
    prepare_to_install = code.split(signature, 1)[1].split(
        "function InitializeSetup", 1
    )[0]

    for expected in [
        "Result := '';",
        "#if Int(AllowCustomDirValue) == 0",
        "CompareText(WizardDirValue(), ExpandConstant(",
        r"{localappdata}\Programs\Modori",
        "<> 0",
        "Result := 'Modori must be installed in '",
    ]:
        assert expected in prepare_to_install


def test_inno_delete_boundary_never_targets_user_state() -> None:
    text = _text()
    install_delete = text.split("[InstallDelete]", 1)[1].split("[", 1)[0]

    assert r"{app}\Modori" in install_delete
    assert r"{localappdata}\Modori" not in install_delete
    assert "{userdocs}" not in install_delete
    assert "{app}\\*" not in install_delete


def test_inno_script_fails_closed_on_downgrade() -> None:
    text = _text()
    for expected in [
        "function InitializeSetup: Boolean;",
        "RegQueryStringValue(HKCU",
        "DisplayVersion",
        "InstalledDisplayVersion + '.0'",
        "StrToVersion",
        "ComparePackedVersion",
        "ComparePackedVersion(CandidatePacked, InstalledPacked) < 0",
        "Result := False",
    ]:
        assert expected in text


def test_inno_script_is_offline_and_has_no_system_integration() -> None:
    text = _text().casefold()

    for forbidden in [
        "http://",
        "https://",
        "downloadtemporaryfile",
        "[registry]",
        "changesenvironment=yes",
    ]:
        assert forbidden not in text

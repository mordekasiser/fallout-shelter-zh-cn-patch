from pathlib import Path
import json
import shutil
import subprocess
import sys
import textwrap

import pytest


def ps_quote(path: Path | str) -> str:
    return "'" + str(path).replace("'", "''") + "'"


def test_patch_build_script_returns_only_output_bundle_path(tmp_path: Path) -> None:
    powershell = shutil.which("powershell.exe") or shutil.which("pwsh")
    if powershell is None:
        pytest.skip("PowerShell is required to test the Windows patch script")

    project_dir = tmp_path / "project"
    game_dir = tmp_path / "game"
    tools_dir = project_dir / "tools"
    translations_dir = project_dir / "translations"
    bundle_dir = game_dir / "FalloutShelter_Data"
    tools_dir.mkdir(parents=True)
    translations_dir.mkdir(parents=True)
    bundle_dir.mkdir(parents=True)

    (tools_dir / "__init__.py").write_text("", encoding="utf-8")
    (translations_dir / "zh_cn_full.csv").write_text(
        "term,zh_cn\nButton_Accept,接受\n",
        encoding="utf-8",
    )
    (bundle_dir / "data.unity3d").write_bytes(b"bundle")
    (tools_dir / "build_patch.py").write_text(
        textwrap.dedent(
            """
            from pathlib import Path
            import argparse
            import json

            parser = argparse.ArgumentParser()
            parser.add_argument("--bundle")
            parser.add_argument("--game-dir")
            parser.add_argument("--translations")
            parser.add_argument("--output-dir")
            parser.add_argument("--allow-unmatched-translations", action="store_true")
            parser.add_argument("--font-file")
            parser.add_argument("--font-name")
            args = parser.parse_args()

            output = Path(args.output_dir) / "FalloutShelter_Data" / "data.unity3d"
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(b"patched")
            (Path(args.output_dir) / "args.json").write_text(
                json.dumps(vars(args), ensure_ascii=False),
                encoding="utf-8",
            )
            print("fake build output")
            """
        ).strip(),
        encoding="utf-8",
    )

    repo_root = Path(__file__).resolve().parents[1]
    common_ps1 = repo_root / "scripts" / "common.ps1"
    script = f"""
    $ErrorActionPreference = 'Stop'
    . {ps_quote(common_ps1)}
    $script:PatchProjectRoot = {ps_quote(project_dir)}
    function Get-ChineseFontInfo {{
        [pscustomobject]@{{ Path = (Join-Path $env:WINDIR 'Fonts\\simhei.ttf'); Name = 'SimHei' }}
    }}
    $result = Invoke-FalloutShelterPatchBuild -PythonExe {ps_quote(sys.executable)} -GameDir {ps_quote(game_dir)}
    $resultItems = @($result)
    if ($resultItems.Count -ne 1) {{
        throw "expected one return item, got $($resultItems.Count)"
    }}
    $argsJson = Get-Content -LiteralPath (Join-Path {ps_quote(project_dir)} 'dist\\FalloutShelter_汉化补丁\\args.json') -Raw | ConvertFrom-Json
    [pscustomobject]@{{
        returnedPath = [string]$resultItems[0]
        allowUnmatched = $argsJson.allow_unmatched_translations
        bundleExists = Test-Path -LiteralPath $argsJson.bundle
    }} | ConvertTo-Json -Compress
    """

    completed = subprocess.run(
        [
            powershell,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            script,
        ],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    payload = json.loads(completed.stdout.strip().splitlines()[-1])
    assert payload["allowUnmatched"]
    assert payload["bundleExists"]
    assert payload["returnedPath"].endswith(
        "dist\\FalloutShelter_汉化补丁\\FalloutShelter_Data\\data.unity3d"
    )

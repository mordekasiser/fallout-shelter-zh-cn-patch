Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$script:PatchProjectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path

function Write-Step {
    param([Parameter(Mandatory = $true)][string]$Message)

    Write-Host ""
    Write-Host "== $Message" -ForegroundColor Cyan
}

function Test-PathQuiet {
    param([Parameter(Mandatory = $true)][string]$Path)

    return [bool](Test-Path -LiteralPath $Path -ErrorAction SilentlyContinue)
}

function Invoke-NativeCommand {
    param(
        [Parameter(Mandatory = $true)][string]$FilePath,
        [Parameter(Mandatory = $true)][string[]]$Arguments
    )

    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed: $FilePath $($Arguments -join ' ')"
    }
}

function Get-PythonLauncher {
    $candidates = @(
        @{ Command = "py"; Args = @("-3.11"); Display = "py -3.11" },
        @{ Command = "py"; Args = @("-3"); Display = "py -3" },
        @{ Command = "python"; Args = @(); Display = "python" }
    )

    foreach ($candidate in $candidates) {
        if (-not (Get-Command $candidate.Command -CommandType Application -ErrorAction SilentlyContinue)) {
            continue
        }

        $args = @()
        $args += $candidate.Args
        $args += @("-c", "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)")
        try {
            & $candidate.Command @args 2>$null
            if ($LASTEXITCODE -eq 0) {
                return [pscustomobject]$candidate
            }
        }
        catch {
            continue
        }
    }

    throw "没有找到 Python 3.11 或更新版本。请先安装 Python：https://www.python.org/downloads/，安装时勾选 Add python.exe to PATH。"
}

function Ensure-ProjectVenv {
    $venvDir = Join-Path $script:PatchProjectRoot ".venv"
    $venvPython = Join-Path $venvDir "Scripts\python.exe"

    if (-not (Test-Path -LiteralPath $venvPython)) {
        $launcher = Get-PythonLauncher
        Write-Host "正在使用 $($launcher.Display) 创建 Python 环境..."
        $args = @()
        $args += $launcher.Args
        $args += @("-m", "venv", $venvDir)
        Invoke-NativeCommand -FilePath $launcher.Command -Arguments $args
    }

    return $venvPython
}

function Install-ProjectDependencies {
    param([Parameter(Mandatory = $true)][string]$PythonExe)

    $requirements = Join-Path $script:PatchProjectRoot "requirements.txt"
    Invoke-NativeCommand -FilePath $PythonExe -Arguments @("-m", "pip", "install", "-r", $requirements)
}

function Get-NormalizedGameDir {
    param([Parameter(Mandatory = $true)][string]$Path)

    $cleanPath = $Path.Trim().Trim('"')
    if (-not (Test-PathQuiet -Path $cleanPath)) {
        return $cleanPath
    }

    $resolved = (Resolve-Path -LiteralPath $cleanPath).Path
    $directBundle = Join-Path $resolved "data.unity3d"
    if ((Split-Path -Leaf $resolved) -ieq "FalloutShelter_Data" -and (Test-Path -LiteralPath $directBundle)) {
        return (Split-Path -Parent $resolved)
    }

    return $resolved
}

function Get-GameBundlePath {
    param([Parameter(Mandatory = $true)][string]$GameDir)

    return [System.IO.Path]::Combine($GameDir, "FalloutShelter_Data", "data.unity3d")
}

function Test-FalloutShelterGameDir {
    param([Parameter(Mandatory = $true)][string]$Path)

    $normalized = Get-NormalizedGameDir -Path $Path
    $bundle = Get-GameBundlePath -GameDir $normalized
    return (Test-PathQuiet -Path $bundle)
}

function Get-UniquePathList {
    param([Parameter(Mandatory = $true)][string[]]$Paths)

    $seen = @{}
    foreach ($path in $Paths) {
        if ([string]::IsNullOrWhiteSpace($path)) {
            continue
        }
        $key = $path.ToLowerInvariant()
        if (-not $seen.ContainsKey($key)) {
            $seen[$key] = $true
            $path
        }
    }
}

function Get-SteamLibraryRoots {
    $roots = New-Object System.Collections.Generic.List[string]
    $steamRoots = @(
        "${env:ProgramFiles(x86)}\Steam",
        "$env:ProgramFiles\Steam"
    )

    foreach ($steamRoot in $steamRoots) {
        if ([string]::IsNullOrWhiteSpace($steamRoot) -or -not (Test-Path -LiteralPath $steamRoot)) {
            continue
        }

        $resolvedSteamRoot = (Resolve-Path -LiteralPath $steamRoot).Path
        $roots.Add($resolvedSteamRoot)

        $libraryFile = Join-Path $resolvedSteamRoot "steamapps\libraryfolders.vdf"
        if (Test-Path -LiteralPath $libraryFile) {
            foreach ($line in Get-Content -LiteralPath $libraryFile) {
                if ($line -match '"path"\s+"([^"]+)"') {
                    $libraryPath = $matches[1] -replace "\\\\", "\"
                    if (Test-Path -LiteralPath $libraryPath) {
                        $roots.Add((Resolve-Path -LiteralPath $libraryPath).Path)
                    }
                }
            }
        }
    }

    foreach ($drive in [System.IO.DriveInfo]::GetDrives()) {
        if (-not $drive.IsReady) {
            continue
        }
        $roots.Add((Join-Path $drive.RootDirectory.FullName "SteamLibrary"))
        $roots.Add((Join-Path $drive.RootDirectory.FullName "Steam"))
    }

    return Get-UniquePathList -Paths $roots.ToArray()
}

function Resolve-FalloutShelterGameDir {
    param([string]$GameDir)

    if (-not [string]::IsNullOrWhiteSpace($GameDir)) {
        $normalized = Get-NormalizedGameDir -Path $GameDir
        if (Test-FalloutShelterGameDir -Path $normalized) {
            return $normalized
        }
        throw "游戏目录不正确：$GameDir"
    }

    if (-not [string]::IsNullOrWhiteSpace($env:FALLOUT_SHELTER_DIR)) {
        $normalized = Get-NormalizedGameDir -Path $env:FALLOUT_SHELTER_DIR
        if (Test-FalloutShelterGameDir -Path $normalized) {
            return $normalized
        }
    }

    foreach ($libraryRoot in Get-SteamLibraryRoots) {
        $candidate = Join-Path $libraryRoot "steamapps\common\Fallout Shelter"
        if (Test-FalloutShelterGameDir -Path $candidate) {
            return (Get-NormalizedGameDir -Path $candidate)
        }
    }

    while ($true) {
        Write-Host ""
        Write-Host "没有自动找到 Fallout Shelter。"
        Write-Host "请打开 Steam -> Fallout Shelter -> 属性 -> 已安装文件 -> 浏览。"
        $manualPath = Read-Host "把打开的游戏文件夹路径粘贴到这里"
        if ([string]::IsNullOrWhiteSpace($manualPath)) {
            continue
        }

        $normalized = Get-NormalizedGameDir -Path $manualPath
        if (Test-FalloutShelterGameDir -Path $normalized) {
            return $normalized
        }

        Write-Warning "这个文件夹里没有 FalloutShelter_Data\data.unity3d，请重新粘贴游戏目录。"
    }
}

function Get-ChineseFontInfo {
    $fontCandidates = @(
        @{ Path = Join-Path $env:WINDIR "Fonts\simhei.ttf"; Name = "SimHei" },
        @{ Path = Join-Path $env:WINDIR "Fonts\msyh.ttc"; Name = "Microsoft YaHei" },
        @{ Path = Join-Path $env:WINDIR "Fonts\simsun.ttc"; Name = "SimSun" }
    )

    foreach ($candidate in $fontCandidates) {
        if (Test-Path -LiteralPath $candidate.Path) {
            return [pscustomobject]$candidate
        }
    }

    return $null
}

function Invoke-FalloutShelterPatchBuild {
    param(
        [Parameter(Mandatory = $true)][string]$PythonExe,
        [Parameter(Mandatory = $true)][string]$GameDir
    )

    $bundlePath = Get-GameBundlePath -GameDir $GameDir
    $translations = Join-Path $script:PatchProjectRoot "translations\zh_cn_full.csv"
    $outputDir = Join-Path $script:PatchProjectRoot "dist\FalloutShelter_汉化补丁"
    $font = Get-ChineseFontInfo

    if ($null -eq $font) {
        throw "没有在 Windows 字体目录找到中文字体。请先安装 Windows 简体中文语言支持，然后重新运行脚本。"
    }

    Write-Host "提示：如果当前游戏版本和翻译表不完全一致，脚本会跳过已经不存在的旧文本并继续生成。" -ForegroundColor Yellow
    Write-Host "提示：新版新增文本暂时会保持原文；生成后请先测试，不正常时可在 Steam 验证游戏文件恢复。" -ForegroundColor Yellow

    $args = @(
        "-m", "tools.build_patch",
        "--bundle", $bundlePath,
        "--game-dir", $GameDir,
        "--translations", $translations,
        "--output-dir", $outputDir,
        "--allow-unmatched-translations",
        "--font-file", $font.Path,
        "--font-name", $font.Name
    )

    Push-Location $script:PatchProjectRoot
    try {
        Invoke-NativeCommand -FilePath $PythonExe -Arguments $args | ForEach-Object {
            Write-Host $_
        }
    }
    finally {
        Pop-Location
    }

    $outputBundle = Join-Path $outputDir "FalloutShelter_Data\data.unity3d"
    if (-not (Test-Path -LiteralPath $outputBundle)) {
        throw "补丁生成命令已结束，但没有找到输出文件：$outputBundle"
    }

    return $outputBundle
}

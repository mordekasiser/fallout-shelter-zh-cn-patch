param([string]$GameDir)

try {
    [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
    $OutputEncoding = [Console]::OutputEncoding
}
catch {
}

. "$PSScriptRoot\common.ps1"

try {
    Write-Step "准备 Python 环境"
    $pythonExe = Ensure-ProjectVenv

    Write-Step "安装依赖"
    Install-ProjectDependencies -PythonExe $pythonExe

    Write-Step "查找 Fallout Shelter 游戏目录"
    $resolvedGameDir = Resolve-FalloutShelterGameDir -GameDir $GameDir
    Write-Host "游戏目录：$resolvedGameDir"

    Write-Step "生成汉化补丁"
    $patchBundle = Invoke-FalloutShelterPatchBuild -PythonExe $pythonExe -GameDir $resolvedGameDir
    $patchRoot = Split-Path -Parent (Split-Path -Parent $patchBundle)

    Write-Host ""
    Write-Host "生成完成。" -ForegroundColor Green
    Write-Host "补丁文件夹：$patchRoot"
    Write-Host "游戏目录：$resolvedGameDir"
    Write-Host ""
    Write-Host "下一步："
    Write-Host "1. 关闭游戏。"
    Write-Host "2. 把补丁文件夹里的 FalloutShelter_Data 拖到游戏目录。"
    Write-Host "3. Windows 提示是否覆盖时，选择覆盖。"
    Write-Host "4. 从 Steam 启动游戏。"

    if (Test-Path -LiteralPath $patchRoot) {
        Start-Process explorer.exe -ArgumentList "`"$patchRoot`""
    }
    if (Test-Path -LiteralPath $resolvedGameDir) {
        Start-Process explorer.exe -ArgumentList "`"$resolvedGameDir`""
    }
}
catch {
    Write-Host ""
    Write-Host "错误：$($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

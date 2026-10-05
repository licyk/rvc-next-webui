python -V *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Host "未找到 Python, 终止运行"
    Read-Host | Out-Null
    exit 1
}

python -c "import venv" *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Host "未找到 Python venv 模块, 终止运行"
    Read-Host | Out-Null
    exit 1
}

Set-Location $PSScriptRoot

if (!(Test-Path .\venv\Scripts\Activate.ps1)) {
    Write-Host "创建虚拟环境中..."
    python -m venv venv
    if ($LASTEXITCODE -ne 0) {
        Write-Host "创建虚拟环境失败, 终止运行"
        Read-Host | Out-Null
        exit 1
    }
}

. .\venv\Scripts\Activate.ps1

python launch.py @args
$ExitCode = $LASTEXITCODE

Write-Host "按 Enter 键继续..."
Read-Host | Out-Null
exit $ExitCode

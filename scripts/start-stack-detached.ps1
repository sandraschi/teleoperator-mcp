$ErrorActionPreference = "Stop"

$ports = @(10892, 10901, 10900)
foreach ($p in $ports) {
    Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue | ForEach-Object {
        Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue
    }
}

$uv = "C:\Users\sandr\.local\bin\uv.exe"

# yahboom-mcp backend :10892
Start-Process -FilePath $uv `
    -ArgumentList @("run", "python", "-m", "yahboom_mcp.server", "--mode", "dual", "--port", "10892") `
    -WorkingDirectory "D:\Dev\repos\yahboom-mcp" `
    -WindowStyle Hidden `
    -RedirectStandardOutput "D:\Dev\repos\yahboom-mcp\yahboom-serve.out.log" `
    -RedirectStandardError "D:\Dev\repos\yahboom-mcp\yahboom-serve.err.log"

# teleoperator backend :10901
Start-Process -FilePath $uv `
    -ArgumentList @("run", "python", "-m", "teleoperator_mcp.server", "--mode", "dual", "--port", "10901") `
    -WorkingDirectory "D:\Dev\repos\teleoperator-mcp" `
    -WindowStyle Hidden `
    -RedirectStandardOutput "D:\Dev\repos\teleoperator-mcp\teleop-serve.out.log" `
    -RedirectStandardError "D:\Dev\repos\teleoperator-mcp\teleop-serve.err.log"

Write-Host "launched (handles are in files, processes fully detached)"

# Teleoperator MCP MCPB pack script.
# Stages a fresh copy of src/ -> mcpb/src/ immediately before pack, then
# runs `mcpb pack . dist/<name>-v<version>.mcpb` from the mcpb/ package root
# and verifies the 3-4-100 prompt gate + self-import + non-trivial output size.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Version = "0.1.0"
$Pkg = "teleoperator_mcp"

function Word-Count([string]$Path) {
    (@(Get-Content -Raw $Path) -split '\s+' | Where-Object { $_ }).Count
}

Write-Host "=== teleoperator-mcp MCPB pack ===" -ForegroundColor Cyan

# Gate 0: 3-4-100 prompt verification (before pack)
$sys = Word-Count "$Root\mcpb\assets\prompts\system.md"
$user = Word-Count "$Root\mcpb\assets\prompts\user.md"
$ex = (Get-Content "$Root\mcpb\assets\prompts\examples.json" -Raw | ConvertFrom-Json).Count
Write-Host "  prompts: system=$sys words, user=$user words, examples=$ex"
if ($sys -lt 3000 -or $user -lt 4000 -or $ex -lt 100) {
    throw "3-4-100 FAIL: system=$sys user=$user examples=$ex (need 3000 / 4000 / 100)"
}
Write-Host "  3-4-100 gate PASS" -ForegroundColor Green

# Fresh stage: wipe + recopy src/<pkg> -> mcpb/src/<pkg> (no __pycache__)
$mcpbSrc = "$Root\mcpb\src"
if (Test-Path $mcpbSrc) { Remove-Item $mcpbSrc -Recurse -Force }
New-Item -ItemType Directory -Force -Path $mcpbSrc | Out-Null
Copy-Item "$Root\src\$Pkg" "$mcpbSrc\$Pkg" -Recurse -Force
Get-ChildItem $mcpbSrc -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force
Get-ChildItem $mcpbSrc -Recurse -Filter "*.pyc" | Remove-Item -Force
Write-Host "  staged fresh src/$Pkg -> mcpb/src/$Pkg" -ForegroundColor Green

# Assert no pycache/pyc/bak under mcpb/
$junk = Get-ChildItem "$Root\mcpb" -Recurse -Include "*.pyc", "__pycache__", "*.bak" -ErrorAction SilentlyContinue
if ($junk) { throw "Junk found under mcpb/: $($junk.Count) items" }

# Verify the bundle can import itself (flat layout = broken bundle)
uv run python -c "import sys,importlib.util as u; sys.path.insert(0,r'mcpb\src'); s=u.find_spec('$Pkg'); print(s.origin if s else 'NOT FOUND'); assert s and r'mcpb\src' in s.origin"

# Pack from the mcpb/ package root (manifest.json + src/ + assets/ live there)
Push-Location "$Root\mcpb"
try {
    npx --yes @anthropic-ai/mcpb pack . "$Root\dist\teleoperator-mcp-v${Version}.mcpb"
    if ($LASTEXITCODE -ne 0) { throw "mcpb pack failed with exit code $LASTEXITCODE" }
}
finally {
    Pop-Location
}

# Gate: output exists and is non-trivial
$out = "$Root\dist\teleoperator-mcp-v${Version}.mcpb"
if (-not (Test-Path $out)) { throw "Pack output missing: $out" }
$sizeMB = (Get-Item $out).Length / 1MB
if ($sizeMB -lt 0.01) { throw "Pack output is runt size: $([math]::Round($sizeMB,3)) MB" }
Write-Host "  Packed: $out ($([math]::Round($sizeMB,2)) MB)" -ForegroundColor Green
Write-Host "=== MCPB pack complete ===" -ForegroundColor Green

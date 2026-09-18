param([string]$Python='python', [int]$Jobs=4)
$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
$source=Join-Path $root 'third_party/sts_lightspeed'
$patch=Join-Path $root 'patches/lightspeed-relic-state.patch'
$installed=$false
if (Test-Path -LiteralPath (Join-Path $source 'bindings/integrated-card-env.cpp')) {
    git -C $source apply --reverse --check $patch 2>$null
    $installed=$LASTEXITCODE -eq 0
}
if (-not $installed) {
    & (Join-Path $PSScriptRoot 'build-enemy-potion.ps1') -Python $Python -Jobs $Jobs
    if ($LASTEXITCODE -ne 0) { throw 'Base build failed' }
    git -C $source apply --check $patch
    if ($LASTEXITCODE -ne 0) { throw 'Relic patch conflicts; existing work was preserved' }
    git -C $source apply $patch
    if ($LASTEXITCODE -ne 0) { throw 'Relic patch application failed' }
}
$savedPath=$env:PATH
try {
    $env:PATH='C:/msys64/mingw64/bin;'+$savedPath
    C:/msys64/mingw64/bin/cmake.exe --build (Join-Path $source 'build') --target slaythespire --parallel $Jobs
    if ($LASTEXITCODE -ne 0) { throw 'Relic backend build failed' }
    & $Python -c 'import hashlib,pathlib,sys; sys.path.insert(0,sys.argv[1]); import slaythespire as s; assert hasattr(s,"RelicStateBattleEnv"); assert s.RELIC_STATE_REGISTRY_SHA256==hashlib.sha256(pathlib.Path(sys.argv[2]).read_bytes()).hexdigest(); print("Relic backend fingerprint verified")' (Join-Path $source 'build') (Join-Path $root 'sts/env/relic-state-registry.json')
    if ($LASTEXITCODE -ne 0) { throw 'Relic backend fingerprint check failed' }
} finally { $env:PATH=$savedPath }

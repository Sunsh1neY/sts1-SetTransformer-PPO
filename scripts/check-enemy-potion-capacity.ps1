# 使用正式构建对象测试Release关闭断言后的队列写入边界。
$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
$source=Join-Path $root 'third_party/sts_lightspeed'
$epObjects=Get-ChildItem (Join-Path $source 'build/CMakeFiles/slaythespire.dir/src') -Recurse -Filter '*.obj' | ForEach-Object { $_.FullName }
if (-not $epObjects) { throw '请先运行build-enemy-potion.ps1。' }
$oldPath=$env:PATH
try {
    $env:PATH='C:/msys64/mingw64/bin;'+$oldPath
    $output=Join-Path $root 'reference/enemy-potion-capacity-probe.exe'
    & C:/msys64/mingw64/bin/g++.exe -std=c++17 -DNDEBUG "-I$(Join-Path $source 'include')" (Join-Path $PSScriptRoot 'enemy-potion-capacity-probe.cpp') @epObjects -o $output
    if ($LASTEXITCODE -ne 0) { throw '队列探针编译失败。' }
    & $output
    if ($LASTEXITCODE -ne 0) { throw '队列探针失败。' }
} finally { $env:PATH=$oldPath }

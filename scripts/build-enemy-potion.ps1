# 独立扩展构建；不向其他工作区写文件，不替换冻结基础补丁。
param([string]$Python='python',[int]$Jobs=1)
$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
$source=Join-Path $root 'third_party/sts_lightspeed'
$patch=Join-Path $root 'patches/lightspeed-enemy-potion.patch'
$installed=$false
if (Test-Path (Join-Path $source 'bindings/enemy-potion-env.cpp')) {
    git -C $source apply --reverse --check $patch
    if ($LASTEXITCODE -ne 0) { throw '独立增量补丁与当前源码冲突；保留现场，请核查。' }
    $installed=$true
}
if (-not $installed) {
    & (Join-Path $PSScriptRoot 'build-lightspeed.ps1') -Python $Python -Jobs $Jobs
    if ($LASTEXITCODE -ne 0) { throw '基础构建失败。' }
    git -C $source apply --check $patch
    if ($LASTEXITCODE -ne 0) { throw '增量补丁不适用；不覆盖已有改动。' }
    git -C $source apply $patch
    if ($LASTEXITCODE -ne 0) { throw '应用增量补丁失败。' }
}
& $Python (Join-Path $PSScriptRoot 'generate-enemy-potion-contract.py')
if ($LASTEXITCODE -ne 0) { throw '扩展契约生成失败。' }
$oldPath=$env:PATH
try {
    $env:PATH='C:/msys64/mingw64/bin;'+$oldPath
    $buildDir=Join-Path $source 'build'
    $cachePath=Join-Path $buildDir 'CMakeCache.txt'
    if (Test-Path -LiteralPath $cachePath) {
        $homeEntry=Get-Content -LiteralPath $cachePath | Select-String '^CMAKE_HOME_DIRECTORY:INTERNAL=(.+)$'
        if ($homeEntry -and [IO.Path]::GetFullPath($homeEntry.Matches[0].Groups[1].Value) -ne [IO.Path]::GetFullPath($source)) {
            $resolvedBuild=[IO.Path]::GetFullPath($buildDir)
            $backup=Join-Path $source 'build-before-desktop-move'
            if ($resolvedBuild -ne [IO.Path]::GetFullPath((Join-Path $root 'third_party/sts_lightspeed/build'))) { throw '构建目录越界' }
            if (Test-Path -LiteralPath $backup) { throw '旧构建备份已存在，请核查' }
            Move-Item -LiteralPath $resolvedBuild -Destination $backup
        }
    }
    if (-not (Test-Path -LiteralPath $cachePath)) {
        $pythonPath=(& $Python -c 'import sys; print(sys.executable)').Trim()
        if ($LASTEXITCODE -ne 0) { throw 'Python路径读取失败' }
        $launcher='cmd;/c;' + ((Join-Path $PSScriptRoot 'lightspeed-gxx-wrap.bat') -replace '\\','/')
        & C:/msys64/mingw64/bin/cmake.exe -S $source -B $buildDir -G Ninja '-DCMAKE_BUILD_TYPE=Release' '-DCMAKE_POLICY_VERSION_MINIMUM=3.5' '-DCMAKE_MAKE_PROGRAM=C:/msys64/mingw64/bin/ninja.exe' '-DCMAKE_CXX_COMPILER=C:/msys64/mingw64/bin/g++.exe' "-DCMAKE_CXX_COMPILER_LAUNCHER=$launcher" "-DPYTHON_EXECUTABLE=$pythonPath"
        if ($LASTEXITCODE -ne 0) { throw '新路径CMake配置失败' }
    }
    & C:/msys64/mingw64/bin/cmake.exe --build $buildDir --target slaythespire --parallel $Jobs
    if ($LASTEXITCODE -ne 0) { throw '扩展构建失败。' }
    foreach ($dll in @('libstdc++-6.dll','libgcc_s_seh-1.dll','libwinpthread-1.dll')) {
        Copy-Item -LiteralPath (Join-Path 'C:/msys64/mingw64/bin' $dll) -Destination $buildDir -Force
    }
    & $Python -c 'import sys; sys.path.insert(0,sys.argv[1]); import slaythespire as s; assert hasattr(s,"EnemyPotionBattleEnv"); print("enemy/potion import OK")' (Join-Path $source 'build')
    if ($LASTEXITCODE -ne 0) { throw '独立入口导入失败。' }
} finally { $env:PATH=$oldPath }

# 从锁定上游与本项目补丁构建战斗扩展；保留已有本地改动，不执行 reset/clean。
param(
    [string]$Python = 'python',
    [string]$Toolchain = 'C:\msys64\mingw64\bin',
    [int]$Jobs = 4,
    [string]$ExtraPatch = ""
)
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$sourceDir = Join-Path $repoRoot 'third_party/sts_lightspeed'
$buildDir = Join-Path $sourceDir 'build'
$lock = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'lightspeed-lock.json') -Raw | ConvertFrom-Json
$patchPath = Join-Path $repoRoot $lock.patch
$cmake = Join-Path $Toolchain 'cmake.exe'
$ninja = Join-Path $Toolchain 'ninja.exe'
$compiler = Join-Path $Toolchain 'g++.exe'
$configuredCompiler = $compiler
# c++.exe 与 g++.exe 在此工具链中是同一编译器的入口；保留已有缓存入口，避免 CMake 清空其他配置。
$cachePath = Join-Path $buildDir 'CMakeCache.txt'
if (Test-Path -LiteralPath $cachePath) {
    $compilerEntry = Get-Content -LiteralPath $cachePath | Select-String '^CMAKE_CXX_COMPILER:FILEPATH=(.+)$'
    if ($compilerEntry) {
        $cachedCompiler = $compilerEntry.Matches[0].Groups[1].Value
        $alternateCompiler = Join-Path $Toolchain 'c++.exe'
        if ([IO.Path]::GetFullPath($cachedCompiler) -eq [IO.Path]::GetFullPath($alternateCompiler)) {
            $configuredCompiler = $cachedCompiler
        }
    }
}

function Invoke-Checked {
    param([string]$Program, [string[]]$ProgramArguments)
    & $Program @ProgramArguments
    if ($LASTEXITCODE -ne 0) {
        throw "命令失败（退出码 $LASTEXITCODE）：$Program $($ProgramArguments -join ' ')"
    }
}

foreach ($required in @($cmake, $ninja, $compiler, $patchPath)) {
    if (-not (Test-Path -LiteralPath $required -PathType Leaf)) {
        throw "缺少构建文件：$required。请参照 README 准备 MSYS2 mingw64 工具链。"
    }
}
if ($Jobs -lt 1) { throw 'Jobs 必须为正整数。' }
$pythonPath = (& $Python -c 'import sys; print(sys.executable)').Trim()
if ($LASTEXITCODE -ne 0) { throw '无法运行指定的 Python。' }

if (-not (Test-Path -LiteralPath $sourceDir)) {
    Invoke-Checked 'git' @('clone', $lock.repository, $sourceDir)
    Invoke-Checked 'git' @('-C', $sourceDir, 'checkout', '--detach', $lock.commit)
}
$actualCommit = (& git -C $sourceDir rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0 -or $actualCommit -ne $lock.commit) {
    throw "上游提交与锁文件不同：$actualCommit。请核对本地工作，脚本不会覆盖已有检出。"
}

# 已初始化的子模块不反复回退，避免每次重建都撤销 pybind11 的锁定升级。
foreach ($module in @('json', 'pybind11')) {
    if (-not (Test-Path -LiteralPath (Join-Path $sourceDir "$module/.git"))) {
        Invoke-Checked 'git' @('-C', $sourceDir, 'submodule', 'update', '--init', '--recursive', '--', $module)
    }
}
$jsonCommit = (& git -C (Join-Path $sourceDir 'json') rev-parse HEAD).Trim()
if ($jsonCommit -ne $lock.json_commit) { throw 'json 子模块提交与锁文件不同，请核对本地检出。' }
$bindingDir = Join-Path $sourceDir 'pybind11'
$bindingCommit = (& git -C $bindingDir rev-parse HEAD).Trim()
if ($bindingCommit -ne $lock.pybind11_commit) {
    $bindingChanges = & git -C $bindingDir status --porcelain --untracked-files=no
    if ($bindingChanges) { throw 'pybind11 含本地改动，请先核对；脚本不会覆盖。' }
    Invoke-Checked 'git' @('-C', $bindingDir, 'fetch', '--tags', 'origin', $lock.pybind11_tag)
    Invoke-Checked 'git' @('-C', $bindingDir, 'checkout', '--detach', $lock.pybind11_commit)
}

# 增量补丁已经应用时，基础补丁的整文件反向检查会受新增内容影响。
$extraAlreadyApplied = $false
if ($ExtraPatch) {
    $ExtraPatch = (Resolve-Path -LiteralPath $ExtraPatch).Path
    & git -C $sourceDir apply --reverse --check $ExtraPatch 2>$null
    $extraAlreadyApplied = $LASTEXITCODE -eq 0
}
# 允许重复执行；若补丁未完整应用且与本地改动冲突，直接报告，不强行覆盖。
$previousErrorPreference = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
& git -C $sourceDir apply --reverse --check $patchPath 2>&1 | Out-Null
$patchAlreadyApplied = $LASTEXITCODE -eq 0
$ErrorActionPreference = $previousErrorPreference
if (-not $patchAlreadyApplied -and -not $extraAlreadyApplied) {
    Invoke-Checked 'git' @('-C', $sourceDir, 'apply', '--check', $patchPath)
    Invoke-Checked 'git' @('-C', $sourceDir, 'apply', $patchPath)
}

if ($ExtraPatch -and -not $extraAlreadyApplied) {
    Invoke-Checked 'git' @('-C', $sourceDir, 'apply', '--check', $ExtraPatch)
    Invoke-Checked 'git' @('-C', $sourceDir, 'apply', $ExtraPatch)
}

if ($ExtraPatch) {
    Invoke-Checked $pythonPath @((Join-Path $PSScriptRoot 'generate-ironclad-contract.py'))
}
# 新公开环境的动作/容量与Python共用单一JSON契约。
Invoke-Checked $pythonPath @((Join-Path $PSScriptRoot 'generate-public-contract.py'))

$previousPath = $env:PATH
try {
    $env:PATH = "$Toolchain;$previousPath"
    $launcher = 'cmd;/c;' + ((Join-Path $PSScriptRoot 'lightspeed-gxx-wrap.bat') -replace '\\', '/')
    Invoke-Checked $cmake @('-S', $sourceDir, '-B', $buildDir, '-G', 'Ninja',
        '-DCMAKE_BUILD_TYPE=Release', '-DCMAKE_POLICY_VERSION_MINIMUM=3.5',
        "-DCMAKE_MAKE_PROGRAM=$ninja", "-DCMAKE_CXX_COMPILER=$configuredCompiler",
        "-DCMAKE_CXX_COMPILER_LAUNCHER=$launcher", "-DPYTHON_EXECUTABLE=$pythonPath")
    Invoke-Checked $cmake @('--build', $buildDir, '--target', 'slaythespire', 'test', '--parallel', "$Jobs")
    foreach ($dll in @('libstdc++-6.dll', 'libgcc_s_seh-1.dll', 'libwinpthread-1.dll')) {
        Copy-Item -LiteralPath (Join-Path $Toolchain $dll) -Destination $buildDir -Force
    }
    Invoke-Checked $pythonPath @('-c', 'import sys; sys.path.insert(0, sys.argv[1]); import slaythespire as s; assert hasattr(s, ''IroncladBattleEnv'') and hasattr(s, ''PublicBattleEnv''); print(''minimal/public battle imports OK'')', $buildDir)
    Write-Host "战斗扩展已构建：$buildDir"
} finally {
    $env:PATH = $previousPath
}

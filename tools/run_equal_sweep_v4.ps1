# Phase 4 sweep: placement_kill_sharpness + revive_knock_mean (8 conditions).
# - placement_kill_sharpness: PLACEMENT_KILL_FACTOR was hard-coded; we exposed
#   it via a log-space sharpness knob to test "intervention on placement
#   structure" as a distinct axis from raw kill supply.
# - revive_knock_mean: structurally fed only into telemetry (MatchResult.revived_knocks),
#   never into allocate_kills/scored_kills. Sweep is a sanity check that
#   reading the code matches reality.
# Level 3 (base) of both sweeps is sweep_equal_base.json (already on disk).

$ErrorActionPreference = "Stop"

$Repo = Split-Path -Parent $PSScriptRoot
Set-Location $Repo

$OutDir = Join-Path $Repo "out"
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

$BaseArgs = @(
    "-m", "cli",
    "--region-profile", "custom",
    "--strength-sigma", "0.05",
    "--sims", "10000",
    "--seed", "42",
    "--workers", "0",
    "--no-plot",
    "--quiet"
)

$Conditions = @(
    @{ Flag = "--placement-kill-sharpness"; Value = "0.0"; Suffix = "placement_kill_sharpness_lvl1" }
    @{ Flag = "--placement-kill-sharpness"; Value = "0.5"; Suffix = "placement_kill_sharpness_lvl2" }
    @{ Flag = "--placement-kill-sharpness"; Value = "1.5"; Suffix = "placement_kill_sharpness_lvl4" }
    @{ Flag = "--placement-kill-sharpness"; Value = "2.0"; Suffix = "placement_kill_sharpness_lvl5" }

    @{ Flag = "--revive-knock-mean";        Value = "4.0";  Suffix = "revive_knock_mean_lvl1" }
    @{ Flag = "--revive-knock-mean";        Value = "7.0";  Suffix = "revive_knock_mean_lvl2" }
    @{ Flag = "--revive-knock-mean";        Value = "13.0"; Suffix = "revive_knock_mean_lvl4" }
    @{ Flag = "--revive-knock-mean";        Value = "16.0"; Suffix = "revive_knock_mean_lvl5" }
)

$Total = $Conditions.Count
$Idx = 0
$Start = Get-Date

foreach ($cond in $Conditions) {
    $Idx++
    $Suffix = $cond.Suffix
    $JsonOut = Join-Path $OutDir ("sweep_eq_{0}.json" -f $Suffix)

    if (Test-Path $JsonOut) {
        Write-Host "[$Idx/$Total] SKIP (exists): $Suffix"
        continue
    }

    $Args = $BaseArgs + @($cond.Flag, $cond.Value) + @(
        "--output-json", $JsonOut
    )

    Write-Host "[$Idx/$Total] running: $Suffix ..."
    $RunStart = Get-Date
    & python @Args
    if ($LASTEXITCODE -ne 0) {
        throw "cli exited with code $LASTEXITCODE for $Suffix"
    }
    $Elapsed = (Get-Date) - $RunStart
    Write-Host ("[$Idx/$Total] done in {0:N1}s -> {1}" -f $Elapsed.TotalSeconds, $JsonOut)
}

$Total = (Get-Date) - $Start
Write-Host ("`nAll {0} conditions complete in {1:N1}s." -f $Conditions.Count, $Total.TotalSeconds)

# Tilted-lobby sweep for the "did-not-move at strength_sigma=0.05" set.
#
# The article's section 5 lists 7 parameters whose equal-baseline sweeps
# (strength_sigma=0.05) moved the mean ending match by at most ±0.12. The
# stated mechanism is "in a flat-strength world, the internals of strength
# do not matter because every team is interchangeable" — i.e. the 7 should
# come alive once teams actually differ in strength.
#
# This script repeats those 7 sweeps at strength_sigma=0.35 (the median of
# the 4-region cycle-9 fit). Each sweep keeps the same 5-level value set as
# the equal-baseline run; the tilted base (lvl3) is a single new run that
# all 7 sweeps share. Output suffix `sweep_tilt_*` so the new files sit
# beside the existing `sweep_eq_*` without clobbering them.

$ErrorActionPreference = "Stop"

$Repo = Split-Path -Parent $PSScriptRoot
Set-Location $Repo

$OutDir = Join-Path $Repo "out"
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

$BaseArgs = @(
    "-m", "cli",
    "--region-profile", "custom",
    "--strength-sigma", "0.35",
    "--sims", "10000",
    "--seed", "42",
    "--workers", "0",
    "--no-plot",
    "--quiet"
)

# Tilted base (lvl3 for all 7 sweeps): strength_sigma=0.35, everything else
# at SimulationConfig defaults.
$TiltedBaseJson = Join-Path $OutDir "sweep_tilt_base.json"

# 7 sweeps. Each entry: parameter CLI flag + 4 off-center values (lvl1, 2,
# 4, 5). Values mirror tools/build_sweep_table.py:SWEEP_DEFINITIONS so the
# tilt-vs-flat comparison is apples-to-apples.
$Conditions = @(
    @{ Flag = "--rank-beta";                   Value = "0.4";  Suffix = "rank_beta_lvl1" }
    @{ Flag = "--rank-beta";                   Value = "0.7";  Suffix = "rank_beta_lvl2" }
    @{ Flag = "--rank-beta";                   Value = "1.3";  Suffix = "rank_beta_lvl4" }
    @{ Flag = "--rank-beta";                   Value = "1.6";  Suffix = "rank_beta_lvl5" }

    @{ Flag = "--kill-beta";                   Value = "0.4";  Suffix = "kill_beta_lvl1" }
    @{ Flag = "--kill-beta";                   Value = "0.6";  Suffix = "kill_beta_lvl2" }
    @{ Flag = "--kill-beta";                   Value = "1.0";  Suffix = "kill_beta_lvl4" }
    @{ Flag = "--kill-beta";                   Value = "1.2";  Suffix = "kill_beta_lvl5" }

    @{ Flag = "--win-beta";                    Value = "0.30"; Suffix = "win_beta_lvl1" }
    @{ Flag = "--win-beta";                    Value = "0.55"; Suffix = "win_beta_lvl2" }
    @{ Flag = "--win-beta";                    Value = "1.05"; Suffix = "win_beta_lvl4" }
    @{ Flag = "--win-beta";                    Value = "1.30"; Suffix = "win_beta_lvl5" }

    @{ Flag = "--placement-win-correlation";   Value = "0.10"; Suffix = "place_win_corr_lvl1" }
    @{ Flag = "--placement-win-correlation";   Value = "0.30"; Suffix = "place_win_corr_lvl2" }
    @{ Flag = "--placement-win-correlation";   Value = "0.70"; Suffix = "place_win_corr_lvl4" }
    @{ Flag = "--placement-win-correlation";   Value = "0.90"; Suffix = "place_win_corr_lvl5" }

    @{ Flag = "--base-match-noise";            Value = "0.40"; Suffix = "base_noise_lvl1" }
    @{ Flag = "--base-match-noise";            Value = "0.60"; Suffix = "base_noise_lvl2" }
    @{ Flag = "--base-match-noise";            Value = "1.00"; Suffix = "base_noise_lvl4" }
    @{ Flag = "--base-match-noise";            Value = "1.20"; Suffix = "base_noise_lvl5" }

    @{ Flag = "--volatility-mean";             Value = "0.6";  Suffix = "volatility_mean_lvl1" }
    @{ Flag = "--volatility-mean";             Value = "0.8";  Suffix = "volatility_mean_lvl2" }
    @{ Flag = "--volatility-mean";             Value = "1.2";  Suffix = "volatility_mean_lvl4" }
    @{ Flag = "--volatility-mean";             Value = "1.4";  Suffix = "volatility_mean_lvl5" }

    @{ Flag = "--respawn-dispersion";          Value = "2.0";  Suffix = "respawn_disp_lvl1" }
    @{ Flag = "--respawn-dispersion";          Value = "3.0";  Suffix = "respawn_disp_lvl2" }
    @{ Flag = "--respawn-dispersion";          Value = "5.0";  Suffix = "respawn_disp_lvl4" }
    @{ Flag = "--respawn-dispersion";          Value = "6.0";  Suffix = "respawn_disp_lvl5" }
)

$Total = $Conditions.Count + 1  # +1 for the tilted base
$Idx = 0
$Start = Get-Date

# Run the tilted base first so every per-parameter sweep has its lvl3 sibling.
$Idx++
if (Test-Path $TiltedBaseJson) {
    Write-Host "[$Idx/$Total] SKIP (exists): tilt_base"
} else {
    $Args = $BaseArgs + @("--output-json", $TiltedBaseJson)
    Write-Host "[$Idx/$Total] running: tilt_base (strength_sigma=0.35, defaults) ..."
    $RunStart = Get-Date
    & python @Args
    if ($LASTEXITCODE -ne 0) {
        throw "cli exited with code $LASTEXITCODE for tilt_base"
    }
    $Elapsed = (Get-Date) - $RunStart
    Write-Host ("[$Idx/$Total] done in {0:N1}s -> {1}" -f $Elapsed.TotalSeconds, $TiltedBaseJson)
}

foreach ($cond in $Conditions) {
    $Idx++
    $Suffix = $cond.Suffix
    $JsonOut = Join-Path $OutDir ("sweep_tilt_{0}.json" -f $Suffix)

    if (Test-Path $JsonOut) {
        Write-Host "[$Idx/$Total] SKIP (exists): $Suffix"
        continue
    }

    $Args = $BaseArgs + @($cond.Flag, $cond.Value) + @("--output-json", $JsonOut)

    Write-Host "[$Idx/$Total] running: $Suffix ..."
    $RunStart = Get-Date
    & python @Args
    if ($LASTEXITCODE -ne 0) {
        throw "cli exited with code $LASTEXITCODE for $Suffix"
    }
    $Elapsed = (Get-Date) - $RunStart
    Write-Host ("[$Idx/$Total] done in {0:N1}s -> {1}" -f $Elapsed.TotalSeconds, $JsonOut)
}

$TotalElapsed = (Get-Date) - $Start
Write-Host ("`nAll {0} conditions complete in {1:N1}s." -f $Total, $TotalElapsed.TotalSeconds)

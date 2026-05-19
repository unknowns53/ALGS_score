# Tilted-lobby sweep at strength_sigma=0.30 (cycle-13 pinned baseline).
#
# Re-evaluates the article's 12 active parameters under tilted strength so the
# section 2-6 rewrite has tilt-mode numerics to quote. 12 = main 5 (strength_
# sigma / lost_kill_rate / respawn_mean / mp_win_penalty / placement_kill_
# sharpness) + the "no-effect at equal-baseline" 7 (rank_beta / kill_beta /
# win_beta / placement_win_correlation / base_match_noise / volatility_mean /
# respawn_dispersion). Each parameter is swept 4 off-center levels (lvl1, 2,
# 4, 5) sharing a single tilted base run at lvl3 = (ss=0.30, defaults).
#
# strength_sigma itself becomes a 5-level symmetric sweep around 0.30; the
# per-condition --strength-sigma overrides the BaseArgs value (argparse
# last-wins).
#
# Output suffix `sweep_tilt30_*` so the new files sit beside the existing
# `sweep_tilt_*` (ss=0.35 reference set) without clobbering.

$ErrorActionPreference = "Stop"

$Repo = Split-Path -Parent $PSScriptRoot
Set-Location $Repo

$OutDir = Join-Path $Repo "out"
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

$BaseArgs = @(
    "-m", "cli",
    "--region-profile", "custom",
    "--strength-sigma", "0.30",
    "--sims", "10000",
    "--seed", "42",
    "--workers", "0",
    "--no-plot",
    "--quiet"
)

# Shared lvl3 base (ss=0.30, everything else at SimulationConfig defaults).
$TiltedBaseJson = Join-Path $OutDir "sweep_tilt30_base.json"

# 12 params, 4 off-center levels each. Values mirror build_sweep_table.py's
# SWEEP_DEFINITIONS for apples-to-apples comparison with the equal-baseline
# tables — except strength_sigma itself, whose tilt30 sweep is symmetric
# around 0.30 instead of one-sided from 0.05.
$Conditions = @(
    # --- main 5: strength_sigma (symmetric around 0.30) ---
    @{ Flag = "--strength-sigma";              Value = "0.10"; Suffix = "strength_sigma_lvl1" }
    @{ Flag = "--strength-sigma";              Value = "0.20"; Suffix = "strength_sigma_lvl2" }
    @{ Flag = "--strength-sigma";              Value = "0.40"; Suffix = "strength_sigma_lvl4" }
    @{ Flag = "--strength-sigma";              Value = "0.50"; Suffix = "strength_sigma_lvl5" }

    # --- main 5: lost_kill_rate ---
    @{ Flag = "--lost-kill-rate";              Value = "0.00"; Suffix = "lost_kill_rate_lvl1" }
    @{ Flag = "--lost-kill-rate";              Value = "0.03"; Suffix = "lost_kill_rate_lvl2" }
    @{ Flag = "--lost-kill-rate";              Value = "0.09"; Suffix = "lost_kill_rate_lvl4" }
    @{ Flag = "--lost-kill-rate";              Value = "0.12"; Suffix = "lost_kill_rate_lvl5" }

    # --- main 5: respawn_mean ---
    @{ Flag = "--respawn-mean";                Value = "2.0";  Suffix = "respawn_mean_lvl1" }
    @{ Flag = "--respawn-mean";                Value = "4.0";  Suffix = "respawn_mean_lvl2" }
    @{ Flag = "--respawn-mean";                Value = "8.0";  Suffix = "respawn_mean_lvl4" }
    @{ Flag = "--respawn-mean";                Value = "10.0"; Suffix = "respawn_mean_lvl5" }

    # --- main 5: mp_win_penalty ---
    @{ Flag = "--mp-win-penalty";              Value = "0.00"; Suffix = "mp_win_penalty_lvl1" }
    @{ Flag = "--mp-win-penalty";              Value = "0.05"; Suffix = "mp_win_penalty_lvl2" }
    @{ Flag = "--mp-win-penalty";              Value = "0.15"; Suffix = "mp_win_penalty_lvl4" }
    @{ Flag = "--mp-win-penalty";              Value = "0.20"; Suffix = "mp_win_penalty_lvl5" }

    # --- main 5: placement_kill_sharpness ---
    @{ Flag = "--placement-kill-sharpness";    Value = "0.00"; Suffix = "placement_kill_sharpness_lvl1" }
    @{ Flag = "--placement-kill-sharpness";    Value = "0.50"; Suffix = "placement_kill_sharpness_lvl2" }
    @{ Flag = "--placement-kill-sharpness";    Value = "1.50"; Suffix = "placement_kill_sharpness_lvl4" }
    @{ Flag = "--placement-kill-sharpness";    Value = "2.00"; Suffix = "placement_kill_sharpness_lvl5" }

    # --- "no-effect at equal" 7: rank_beta ---
    @{ Flag = "--rank-beta";                   Value = "0.4";  Suffix = "rank_beta_lvl1" }
    @{ Flag = "--rank-beta";                   Value = "0.7";  Suffix = "rank_beta_lvl2" }
    @{ Flag = "--rank-beta";                   Value = "1.3";  Suffix = "rank_beta_lvl4" }
    @{ Flag = "--rank-beta";                   Value = "1.6";  Suffix = "rank_beta_lvl5" }

    # --- "no-effect at equal" 7: kill_beta ---
    @{ Flag = "--kill-beta";                   Value = "0.4";  Suffix = "kill_beta_lvl1" }
    @{ Flag = "--kill-beta";                   Value = "0.6";  Suffix = "kill_beta_lvl2" }
    @{ Flag = "--kill-beta";                   Value = "1.0";  Suffix = "kill_beta_lvl4" }
    @{ Flag = "--kill-beta";                   Value = "1.2";  Suffix = "kill_beta_lvl5" }

    # --- "no-effect at equal" 7: win_beta ---
    @{ Flag = "--win-beta";                    Value = "0.30"; Suffix = "win_beta_lvl1" }
    @{ Flag = "--win-beta";                    Value = "0.55"; Suffix = "win_beta_lvl2" }
    @{ Flag = "--win-beta";                    Value = "1.05"; Suffix = "win_beta_lvl4" }
    @{ Flag = "--win-beta";                    Value = "1.30"; Suffix = "win_beta_lvl5" }

    # --- "no-effect at equal" 7: placement_win_correlation ---
    @{ Flag = "--placement-win-correlation";   Value = "0.10"; Suffix = "place_win_corr_lvl1" }
    @{ Flag = "--placement-win-correlation";   Value = "0.30"; Suffix = "place_win_corr_lvl2" }
    @{ Flag = "--placement-win-correlation";   Value = "0.70"; Suffix = "place_win_corr_lvl4" }
    @{ Flag = "--placement-win-correlation";   Value = "0.90"; Suffix = "place_win_corr_lvl5" }

    # --- "no-effect at equal" 7: base_match_noise ---
    @{ Flag = "--base-match-noise";            Value = "0.40"; Suffix = "base_noise_lvl1" }
    @{ Flag = "--base-match-noise";            Value = "0.60"; Suffix = "base_noise_lvl2" }
    @{ Flag = "--base-match-noise";            Value = "1.00"; Suffix = "base_noise_lvl4" }
    @{ Flag = "--base-match-noise";            Value = "1.20"; Suffix = "base_noise_lvl5" }

    # --- "no-effect at equal" 7: volatility_mean ---
    @{ Flag = "--volatility-mean";             Value = "0.6";  Suffix = "volatility_mean_lvl1" }
    @{ Flag = "--volatility-mean";             Value = "0.8";  Suffix = "volatility_mean_lvl2" }
    @{ Flag = "--volatility-mean";             Value = "1.2";  Suffix = "volatility_mean_lvl4" }
    @{ Flag = "--volatility-mean";             Value = "1.4";  Suffix = "volatility_mean_lvl5" }

    # --- "no-effect at equal" 7: respawn_dispersion ---
    @{ Flag = "--respawn-dispersion";          Value = "2.0";  Suffix = "respawn_disp_lvl1" }
    @{ Flag = "--respawn-dispersion";          Value = "3.0";  Suffix = "respawn_disp_lvl2" }
    @{ Flag = "--respawn-dispersion";          Value = "5.0";  Suffix = "respawn_disp_lvl4" }
    @{ Flag = "--respawn-dispersion";          Value = "6.0";  Suffix = "respawn_disp_lvl5" }
)

$Total = $Conditions.Count + 1  # +1 for the tilted base
$Idx = 0
$Start = Get-Date

$Idx++
if (Test-Path $TiltedBaseJson) {
    Write-Host "[$Idx/$Total] SKIP (exists): tilt30_base"
} else {
    $Args = $BaseArgs + @("--output-json", $TiltedBaseJson)
    Write-Host "[$Idx/$Total] running: tilt30_base (strength_sigma=0.30, defaults) ..."
    $RunStart = Get-Date
    & python @Args
    if ($LASTEXITCODE -ne 0) {
        throw "cli exited with code $LASTEXITCODE for tilt30_base"
    }
    $Elapsed = (Get-Date) - $RunStart
    Write-Host ("[$Idx/$Total] done in {0:N1}s -> {1}" -f $Elapsed.TotalSeconds, $TiltedBaseJson)
}

foreach ($cond in $Conditions) {
    $Idx++
    $Suffix = $cond.Suffix
    $JsonOut = Join-Path $OutDir ("sweep_tilt30_{0}.json" -f $Suffix)

    if (Test-Path $JsonOut) {
        Write-Host "[$Idx/$Total] SKIP (exists): $Suffix"
        continue
    }

    # Per-condition flag appended *after* BaseArgs. For strength_sigma sweep
    # this overrides BaseArgs's --strength-sigma 0.30 via argparse last-wins.
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

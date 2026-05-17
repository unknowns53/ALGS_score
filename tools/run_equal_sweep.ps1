# Run the equal-baseline sweep: 1 base + 7 parameters x 4 off-base values = 29 conditions.
# Each condition: 10000 sims, seed=42, workers=0 (all cores), output JSON only.

$ErrorActionPreference = "Stop"

$Repo = Split-Path -Parent $PSScriptRoot
Set-Location $Repo

$OutDir = Join-Path $Repo "out"
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

# Shared base flags. strength_sigma is forced to 0.05 here so that any condition
# that does NOT override strength_sigma inherits the equal-baseline value.
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

# (flag, value, suffix). flag=$null and value=$null means "use base only".
$Conditions = @(
    @{ Flag = $null;                          Value = $null;  Suffix = "base" }

    # strength_sigma (base = 0.05 = level1; 4 off-base)
    @{ Flag = "--strength-sigma";             Value = "0.15"; Suffix = "strength_sigma_015" }
    @{ Flag = "--strength-sigma";             Value = "0.30"; Suffix = "strength_sigma_030" }
    @{ Flag = "--strength-sigma";             Value = "0.43"; Suffix = "strength_sigma_043" }
    @{ Flag = "--strength-sigma";             Value = "0.55"; Suffix = "strength_sigma_055" }

    # lost_kill_rate (base = 0.06 at level2; off-base: 0.02, 0.10, 0.16, 0.22)
    @{ Flag = "--lost-kill-rate";             Value = "0.02"; Suffix = "lost_kill_rate_002" }
    @{ Flag = "--lost-kill-rate";             Value = "0.10"; Suffix = "lost_kill_rate_010" }
    @{ Flag = "--lost-kill-rate";             Value = "0.16"; Suffix = "lost_kill_rate_016" }
    @{ Flag = "--lost-kill-rate";             Value = "0.22"; Suffix = "lost_kill_rate_022" }

    # respawn_mean (base = 6.0 at level3; off-base: 2.0, 4.0, 8.0, 10.0; suffix is value*10)
    @{ Flag = "--respawn-mean";               Value = "2.0";  Suffix = "respawn_mean_020" }
    @{ Flag = "--respawn-mean";               Value = "4.0";  Suffix = "respawn_mean_040" }
    @{ Flag = "--respawn-mean";               Value = "8.0";  Suffix = "respawn_mean_080" }
    @{ Flag = "--respawn-mean";               Value = "10.0"; Suffix = "respawn_mean_100" }

    # mp_win_penalty (base = 0.10 at level3; off-base: 0.00, 0.05, 0.20, 0.30)
    @{ Flag = "--mp-win-penalty";             Value = "0.00"; Suffix = "mp_win_penalty_000" }
    @{ Flag = "--mp-win-penalty";             Value = "0.05"; Suffix = "mp_win_penalty_005" }
    @{ Flag = "--mp-win-penalty";             Value = "0.20"; Suffix = "mp_win_penalty_020" }
    @{ Flag = "--mp-win-penalty";             Value = "0.30"; Suffix = "mp_win_penalty_030" }

    # win_beta (base = 0.80 at level3; off-base: 0.30, 0.55, 1.05, 1.30)
    @{ Flag = "--win-beta";                   Value = "0.30"; Suffix = "win_beta_030" }
    @{ Flag = "--win-beta";                   Value = "0.55"; Suffix = "win_beta_055" }
    @{ Flag = "--win-beta";                   Value = "1.05"; Suffix = "win_beta_105" }
    @{ Flag = "--win-beta";                   Value = "1.30"; Suffix = "win_beta_130" }

    # placement_win_correlation (base = 0.50 at level4; off-base: 0.05, 0.20, 0.35, 0.65)
    @{ Flag = "--placement-win-correlation";  Value = "0.05"; Suffix = "place_win_corr_005" }
    @{ Flag = "--placement-win-correlation";  Value = "0.20"; Suffix = "place_win_corr_020" }
    @{ Flag = "--placement-win-correlation";  Value = "0.35"; Suffix = "place_win_corr_035" }
    @{ Flag = "--placement-win-correlation";  Value = "0.65"; Suffix = "place_win_corr_065" }

    # base_match_noise (base = 0.80 at level3; off-base: 0.40, 0.60, 1.00, 1.30)
    @{ Flag = "--base-match-noise";           Value = "0.40"; Suffix = "base_noise_040" }
    @{ Flag = "--base-match-noise";           Value = "0.60"; Suffix = "base_noise_060" }
    @{ Flag = "--base-match-noise";           Value = "1.00"; Suffix = "base_noise_100" }
    @{ Flag = "--base-match-noise";           Value = "1.30"; Suffix = "base_noise_130" }
)

$Total = $Conditions.Count
$Idx = 0
$StartAll = Get-Date

foreach ($c in $Conditions) {
    $Idx++
    $Suffix = $c.Suffix
    $JsonPath = Join-Path $OutDir "sweep_equal_$Suffix.json"
    $CsvPath  = Join-Path $OutDir "sweep_equal_$Suffix.csv"

    if (Test-Path $JsonPath) {
        Write-Host "[$Idx/$Total] skip (exists): $JsonPath"
        continue
    }

    $Args = $BaseArgs + @("--output-json", $JsonPath, "--output-csv", $CsvPath)
    if ($null -ne $c.Flag) {
        $Args += @($c.Flag, $c.Value)
    }

    $Start = Get-Date
    Write-Host "[$Idx/$Total] running: suffix=$Suffix" -ForegroundColor Cyan
    & python @Args
    if ($LASTEXITCODE -ne 0) {
        throw "cli exited with $LASTEXITCODE for condition $Suffix"
    }
    $Elapsed = (Get-Date) - $Start
    Write-Host "[$Idx/$Total] done in $([math]::Round($Elapsed.TotalSeconds, 1))s" -ForegroundColor Green
}

$TotalElapsed = (Get-Date) - $StartAll
Write-Host "All conditions complete in $([math]::Round($TotalElapsed.TotalMinutes, 2)) min." -ForegroundColor Green

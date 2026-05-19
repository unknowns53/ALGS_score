# Supplementary tilt30 sweep for sections 4 (MP-brother sweeps) and 6
# (categorical conditions) of the article rewrite.
#
# Adds 11 conditions to the existing tilt30 base, at strength_sigma=0.30:
#   - mp_kill_penalty x 4 levels (for section 4)
#   - mp_pressure_lost_kill_multiplier x 4 levels (for section 4)
#   - mp_pressure_enabled=false (categorical, section 6)
#   - starting_points_mode=seeded (categorical, section 6)
#   - respawn_model=poisson (categorical, section 6)

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

$Conditions = @(
    @{ Extra = @("--mp-kill-penalty", "0.000");                 Suffix = "mp_kill_penalty_lvl1" }
    @{ Extra = @("--mp-kill-penalty", "0.025");                 Suffix = "mp_kill_penalty_lvl2" }
    @{ Extra = @("--mp-kill-penalty", "0.075");                 Suffix = "mp_kill_penalty_lvl4" }
    @{ Extra = @("--mp-kill-penalty", "0.100");                 Suffix = "mp_kill_penalty_lvl5" }

    @{ Extra = @("--mp-pressure-lost-kill-multiplier", "0.75"); Suffix = "mp_pressure_lost_kill_mult_lvl1" }
    @{ Extra = @("--mp-pressure-lost-kill-multiplier", "1.00"); Suffix = "mp_pressure_lost_kill_mult_lvl2" }
    @{ Extra = @("--mp-pressure-lost-kill-multiplier", "1.50"); Suffix = "mp_pressure_lost_kill_mult_lvl4" }
    @{ Extra = @("--mp-pressure-lost-kill-multiplier", "1.75"); Suffix = "mp_pressure_lost_kill_mult_lvl5" }

    @{ Extra = @("--no-mp-pressure");                           Suffix = "no_mp_pressure" }
    @{ Extra = @("--starting-points", "seeded");                Suffix = "seeded" }
    @{ Extra = @("--respawn-model", "poisson");                 Suffix = "respawn_poisson" }
)

$Total = $Conditions.Count
$Idx = 0
$Start = Get-Date

foreach ($cond in $Conditions) {
    $Idx++
    $Suffix = $cond.Suffix
    $JsonOut = Join-Path $OutDir ("sweep_tilt30_{0}.json" -f $Suffix)

    if (Test-Path $JsonOut) {
        Write-Host "[$Idx/$Total] SKIP (exists): $Suffix"
        continue
    }

    $Args = $BaseArgs + $cond.Extra + @("--output-json", $JsonOut)

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
Write-Host ("`nAll {0} supplementary conditions complete in {1:N1}s." -f $Total, $TotalElapsed.TotalSeconds)

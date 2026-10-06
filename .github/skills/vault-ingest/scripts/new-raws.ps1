<#
.SYNOPSIS
  Find and dump every UN-INGESTED raw source in the vault, in one shot.

.DESCRIPTION
  Token-saver for the vault-ingest skill. Replaces a dozen file reads / git calls:
    1. (optional) syncs git: fetch + pull --rebase origin main
    2. classifies every raw .md under 00-Raw (Voice/Clippings/Inbox/OCR) as covered or not.
       A raw is COVERED if EITHER:
         (a) its basename is linked in 10-Refined
             (e.g. [[00-Raw/Voice/Voice 260104_180416]]), OR
         (b) a distinctive slice of its body already appears in 10-Refined
             (catches older source pages that embed the verbatim transcript without a backlink).
       Matching is whitespace/quote-normalised, so line-wrapped quotes still match.
    3. prints each UNCOVERED raw's path + clean body (frontmatter stripped, full, no truncation),
       tagged NEW (arrived since the last `ingest:` commit) or OLDER/MISSED.

.PARAMETER NoSync
  Skip the git fetch/pull step (just report uncovered raws against the current tree).

.EXAMPLE
  pwsh -File .github/skills/vault-ingest/scripts/new-raws.ps1
  pwsh -File .github/skills/vault-ingest/scripts/new-raws.ps1 -NoSync
#>
param([switch]$NoSync)

$ErrorActionPreference = 'Stop'
$repo = (git rev-parse --show-toplevel 2>$null)
if (-not $repo) { Write-Error 'Not inside the vault git repo.'; exit 1 }
Set-Location $repo

if (-not $NoSync) {
  Write-Output '=== GIT SYNC ==='
  git fetch origin 2>&1 | Select-Object -Last 2
  $before = git rev-parse HEAD
  git pull --rebase origin main 2>&1 | Select-Object -Last 4
  $after = git rev-parse HEAD
  Write-Output "HEAD: $before -> $after"
  Write-Output ''
}

# Build one text blob of the processed (Refined) content to test coverage against.
$coverageFiles = @(Get-ChildItem -Recurse -File -Path '10-Refined' -Filter '*.md')
$coverageBlob = ($coverageFiles | Get-Content -Raw) -join "`n"

function Normalize([string]$s) {
  if (-not $s) { return '' }
  # drop frontmatter, quote markers and all whitespace; lowercase -> defeats line-wrapping.
  return ($s -replace '(?s)^\s*---.*?---', '' -replace '[>\s]', '').ToLowerInvariant()
}
$coverageNorm = Normalize $coverageBlob

# Raws that arrived since the last ingest commit = the "newly arrived" set (for tagging).
$lastIngest = git log -1 --format='%H' --grep='^ingest' 2>$null
$newSet = @{}
if ($lastIngest) {
  git diff --name-only --diff-filter=AM "$lastIngest..HEAD" -- 00-Raw/ 2>$null |
  ForEach-Object { $newSet[[IO.Path]::GetFileNameWithoutExtension($_)] = $true }
}

# Raw source folders that hold ingestable notes (exclude Archive/assets and structured exports).
$rawDirs = 'Voice', 'Clippings', 'Inbox', 'OCR'
$raws = foreach ($d in $rawDirs) {
  $p = Join-Path '00-Raw' $d
  if (Test-Path $p) { Get-ChildItem -Recurse -File -Path $p -Filter '*.md' }
}

$uncovered = foreach ($f in ($raws | Sort-Object FullName)) {
  $base = [IO.Path]::GetFileNameWithoutExtension($f.Name)
  if ($coverageBlob.Contains($base)) { continue }                # (a) basename linked
  $bn = Normalize ((Get-Content $f.FullName -Raw) ?? '')
  $probe = if ($bn.Length -ge 40) { $bn.Substring(0, 40) } else { $bn }
  if ($probe -and $coverageNorm.Contains($probe)) { continue }    # (b) body embedded
  [pscustomobject]@{ File = $f; New = [bool]$newSet[$base] }
}

$count = @($uncovered).Count
$nNew = @($uncovered | Where-Object New).Count
$nOld = $count - $nNew
Write-Output "=== UNCOVERED RAWS: $count  (new since last ingest: $nNew, older/missed: $nOld) ==="
if ($count -eq 0) { Write-Output '(nothing to ingest -- vault is fully covered)'; exit 0 }

foreach ($u in $uncovered) {
  $f = $u.File
  $rel = [IO.Path]::GetRelativePath($repo, $f.FullName) -replace '\\', '/'
  $raw = (Get-Content $f.FullName -Raw) ?? ''
  # Strip leading YAML frontmatter (--- ... ---) if present; keep the body verbatim.
  $body = if ($raw -match '(?s)^\s*---.*?---\s*(.*)$') { $Matches[1].Trim() } else { $raw.Trim() }
  # Pull a couple of useful frontmatter fields for context.
  $recorded = if ($raw -match '(?m)^recorded:\s*(.+)$') { $Matches[1].Trim() } else { '' }
  $dur = if ($raw -match '(?m)^duration_s:\s*(.+)$') { $Matches[1].Trim() } else { '' }
  $tag = if ($u.New) { 'NEW' } else { 'OLDER/MISSED' }
  Write-Output ''
  Write-Output ('#' * 70)
  Write-Output "[$tag] FILE: $rel"
  if ($recorded) { Write-Output "recorded: $recorded  duration_s: $dur" }
  Write-Output ('#' * 70)
  if ([string]::IsNullOrWhiteSpace($body)) { Write-Output '(EMPTY FILE)' } else { Write-Output $body }
}

<#
.SYNOPSIS
  Gather every passage matching a narrative theme across 00-Raw and 10-Refined, in one shot.

.DESCRIPTION
  Token-saver for the story-agent skill. Instead of many grep / file-read calls, this finds every
  raw source and Refined page that matches the theme (and any extra keywords) and prints the
  matching lines with context + a date, sorted oldest-first so the arc / change-over-time is easy
  to see.

  It does NOT interpret anything — it assembles the evidence the agent reads. Interpretation
  (spine / want-vs-need / arc / theme / stakes) and drafting threads is the agent's job (SKILL.md).

.PARAMETER Theme
  The narrative theme/keyword to gather (e.g. "shipping", "purpose", "craft"). Matched
  case-insensitively on a word boundary. Optional if you give a date window (-Since/-Until) to
  gather a whole era instead of a theme.

.PARAMETER Keywords
  Optional extra synonyms/related terms to also match (e.g. vocation,calling for "purpose").

.PARAMETER Since
  Optional. Only include notes dated on/after this YYYY-MM-DD (by filename / frontmatter date).

.PARAMETER Until
  Optional. Only include notes dated on/before this YYYY-MM-DD.

.PARAMETER Era
  Optional label for the run header (e.g. "first-builds") — does not affect matching; it just titles an
  era gather when you're assembling a chapter's evidence.

.PARAMETER Context
  Lines of context to show around each match. Default 1.

.EXAMPLE
  # Theme gather (for a Bible thread):
  pwsh -File .github/skills/story-agent/scripts/gather-narrative.ps1 -Theme shipping
  pwsh -File .github/skills/story-agent/scripts/gather-narrative.ps1 -Theme purpose -Keywords vocation,calling,teach
  # Era / time-window gather (for a Book chapter), oldest-first:
  pwsh -File .github/skills/story-agent/scripts/gather-narrative.ps1 -Era first-builds -Since 2026-01-01 -Until 2026-03-31
#>
param(
  [string]$Theme,
  [string[]]$Keywords = @(),
  [string]$Since,
  [string]$Until,
  [string]$Era,
  [int]$Context = 1
)

if (-not $Theme -and -not $Since -and -not $Until) {
  Write-Error 'Give a -Theme (and/or -Keywords), or a date window (-Since/-Until) for an era gather.'
  exit 1
}

$ErrorActionPreference = 'Stop'
$repo = (git rev-parse --show-toplevel 2>$null)
if (-not $repo) { Write-Error 'Not inside the vault git repo.'; exit 1 }
Set-Location $repo

# Build a case-insensitive, word-boundary regex for the theme + any extra keywords (if given).
$terms = @($Theme) + $Keywords | Where-Object { $_ } | ForEach-Object { [regex]::Escape($_) }
$pattern = if ($terms) { '(?i)\b(' + ($terms -join '|') + ')\b' } else { $null }

# Pull a usable date for sorting: prefer a leading YYYY-MM-DD in the filename, else the
# frontmatter `created:` field, else a Voice-style stamp, else the file's last-write time.
function Get-NoteDate([string]$path, [string]$body) {
  $name = [IO.Path]::GetFileNameWithoutExtension($path)
  if ($name -match '(\d{4}-\d{2}-\d{2})') { return $matches[1] }
  if ($body -match '(?m)^created:\s*(\d{4}-\d{2}-\d{2})') { return $matches[1] }
  # Voice raws look like "Voice 260613_105841" -> 2026-06-13
  if ($name -match 'Voice\s+(\d{2})(\d{2})(\d{2})_') { return "20$($matches[1])-$($matches[2])-$($matches[3])" }
  return (Get-Item $path).LastWriteTime.ToString('yyyy-MM-dd')
}

$folders = @('00-Raw', '10-Refined')
$hits = @()

foreach ($folder in $folders) {
  if (-not (Test-Path $folder)) { continue }
  $files = Get-ChildItem -Recurse -File -Path $folder -Filter '*.md' |
  Where-Object { $_.FullName -notmatch '[\\/]Archive[\\/]' }
  foreach ($f in $files) {
    $lines = Get-Content -LiteralPath $f.FullName
    $body = ($lines -join "`n")
    if ($pattern -and $body -notmatch $pattern) { continue }
    $date = Get-NoteDate $f.FullName $body
    if ($Since -and $date -lt $Since) { continue }
    if ($Until -and $date -gt $Until) { continue }
    $rel = (Resolve-Path -LiteralPath $f.FullName -Relative) -replace '^\.[\\/]', '' -replace '\\', '/'
    if ($pattern) {
      # collect matching line numbers + a small context window
      $matchLines = for ($i = 0; $i -lt $lines.Count; $i++) {
        if ($lines[$i] -match $pattern) {
          $lo = [Math]::Max(0, $i - $Context)
          $hi = [Math]::Min($lines.Count - 1, $i + $Context)
          ($lo..$hi | ForEach-Object { '    ' + $lines[$_].Trim() }) -join "`n"
        }
      }
      $snippet = ($matchLines -join "`n    ---`n")
    }
    else {
      # era gather (no theme): show a short head preview of the note body
      $preview = $lines |
      Where-Object { $_ -notmatch '^---\s*$' -and $_ -notmatch '^\w[\w -]*:\s' -and $_.Trim() } |
      Select-Object -First 3 |
      ForEach-Object { '    ' + $_.Trim() }
      $snippet = ($preview -join "`n")
    }
    $hits += [pscustomobject]@{
      Date    = $date
      Layer   = $folder
      Path    = $rel
      Snippet = $snippet
    }
  }
}

if (-not $hits) {
  Write-Output "No matching passages found in 00-Raw or 10-Refined for this gather."
  exit 0
}

$label = if ($Era) { "ERA $Era" } elseif ($Theme) { $Theme } else { "time window" }
$sinceTxt = if ($Since) { $Since } else { '…' }
$untilTxt = if ($Until) { $Until } else { '…' }
$window = if ($Since -or $Until) { "  |  Window: $sinceTxt -> $untilTxt" } else { '' }
$termsTxt = if ($terms) { $terms -join ', ' } else { '(era gather — no theme)' }
Write-Output "=== STORY NARRATIVE GATHER: $label ==="
Write-Output "Terms: $termsTxt  |  Matches: $($hits.Count) file(s)$window"
Write-Output "Sorted oldest-first. Read for SPINE, WANT vs NEED, ARC over time, THEME, and honest STAKES."
Write-Output ''

foreach ($h in ($hits | Sort-Object Date)) {
  Write-Output "[$($h.Date)] ($($h.Layer)) [[$($h.Path -replace '\.md$','')]]"
  Write-Output $h.Snippet
  Write-Output ''
}

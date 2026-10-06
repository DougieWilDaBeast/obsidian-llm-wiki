#!/usr/bin/env pwsh
<#
.SYNOPSIS
  Assemble the 30-Story/ Book + Bible into exportable manuscripts under 90-Export/.

.DESCRIPTION
  The GENERATED-OUTPUT builder behind the Story layer's "exportable" promise (CLAUDE.md §12 / §13).
  Reads chapter + thread frontmatter from 30-Story/ ONLY — nothing else in the vault — filters by status,
  orders the Book by book_order (story-time), strips each chapter's "## Sources & fidelity" and
  "## Revisions" footers, and writes:

    90-Export/Book.md            one ordered manuscript (the whole Book)
    90-Export/Seed.md            the Bible threads concatenated as seed-context
    90-Export/Book — <arc>.md    per-arc manuscripts (only with -ByArc)

  Outputs are regenerable and marked "do not hand-edit". Promotion is what changes them: a chapter
  only lands in the default export once it is `living` or `canonical`.

.PARAMETER CanonicalOnly
  Only include status: canonical (the human-signed, exportable version).

.PARAMETER IncludeDrafts
  Also include status: draft and stub (default is living + canonical).

.PARAMETER ByArc
  Additionally emit one manuscript per arc (every arc named in a chapter's `arcs:` list).

.NOTES
  Scope wall (CLAUDE.md §13): this script globs 30-Story/ only and asserts that it never reads
  or writes outside 30-Story/ and 90-Export/. Keep anything private out of the vault's Story layer
  and this guard keeps it out of the export too. Do not weaken it.

.EXAMPLE
  pwsh -File .github/skills/story-agent/scripts/assemble-book.ps1
  pwsh -File .github/skills/story-agent/scripts/assemble-book.ps1 -IncludeDrafts -ByArc
  pwsh -File .github/skills/story-agent/scripts/assemble-book.ps1 -CanonicalOnly
#>
[CmdletBinding()]
param(
    [switch]$CanonicalOnly,
    [switch]$IncludeDrafts,
    [switch]$ByArc
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# --- locate vault root (four levels up from this skill's scripts/ dir) ---
$root = (Resolve-Path (Join-Path $PSScriptRoot '../../../..')).Path
$storyDir = Join-Path $root '30-Story'
$exportDir = Join-Path $root '90-Export'

if (-not (Test-Path -LiteralPath $storyDir)) { throw "Story dir not found: $storyDir" }

# --- SCOPE WALL: this tool only ever reads 30-Story/ and writes 90-Export/ ---
function Assert-InScope {
    param([string]$Path)
    $full = [IO.Path]::GetFullPath($Path)
    $ok = foreach ($dir in @($storyDir, $exportDir)) {
        $d = [IO.Path]::GetFullPath($dir)
        if ($full -eq $d -or $full.StartsWith($d + [IO.Path]::DirectorySeparatorChar)) { $true }
    }
    if (-not $ok) {
        throw "Scope violation: assemble-book only reads 30-Story/ and writes 90-Export/ ($Path)"
    }
}

# --- status filter ---
$statuses = if ($CanonicalOnly) { @('canonical') }
elseif ($IncludeDrafts) { @('canonical', 'living', 'draft', 'stub') }
else { @('canonical', 'living') }

# --- provenance for the generated header ---
$commit = try { (git -C $root rev-parse --short HEAD 2>$null).Trim() } catch { 'unknown' }
if (-not $commit) { $commit = 'unknown' }
$today = Get-Date -Format 'yyyy-MM-dd'

function Get-Frontmatter {
    param([string]$Path)
    $lines = Get-Content -LiteralPath $Path
    if ($lines.Count -eq 0 -or $lines[0].Trim() -ne '---') { return $null }
    $fm = [ordered]@{}
    $currentListKey = $null
    $end = -1
    for ($i = 1; $i -lt $lines.Count; $i++) {
        if ($lines[$i].Trim() -eq '---') { $end = $i; break }
        if ($lines[$i] -match '^([A-Za-z0-9_]+):\s*(.*)$') {
            $key = $Matches[1]
            $value = $Matches[2].Trim()
            if ($value) {
                $fm[$key] = $value
                $currentListKey = $null
            }
            else {
                $fm[$key] = [string[]]@()
                $currentListKey = $key
            }
            continue
        }
        if ($currentListKey -and $lines[$i] -match '^\s*-\s*(.+?)\s*$') {
            $fm[$currentListKey] = [string[]](@($fm[$currentListKey]) + $Matches[1].Trim())
            continue
        }
        $currentListKey = $null
    }
    if ($end -lt 0) { return $null }
    $body = if ($end + 1 -lt $lines.Count) { $lines[($end + 1)..($lines.Count - 1)] } else { @() }
    [pscustomobject]@{ Front = $fm; Body = $body }
}

function Get-ArcList {
    param($Front)
    if (-not $Front.Contains('arcs')) { return @() }
    $value = $Front['arcs']
    if ($value -isnot [string]) {
        return @($value) | ForEach-Object { ([string]$_).Trim().Trim("'`"") } | Where-Object { $_ }
    }
    $raw = ([string]$value).Trim().TrimStart('[').TrimEnd(']').Trim()
    if (-not $raw) { return @() }
    return ($raw -split ',') | ForEach-Object { $_.Trim().Trim("'`"") } | Where-Object { $_ }
}

function Get-Field {
    param($Front, [string]$Key)
    if ($Front.Contains($Key)) { return [string]$Front[$Key] } else { return '' }
}

function Remove-FromHeading {
    # return the body up to (but excluding) the first line matching $Pattern
    param([string[]]$Body, [string]$Pattern)
    $cut = $Body.Count
    for ($i = 0; $i -lt $Body.Count; $i++) {
        if ($Body[$i] -match $Pattern) { $cut = $i; break }
    }
    $kept = if ($cut -gt 0) { @($Body[0..($cut - 1)]) } else { @() }
    while ($kept.Count -gt 0 -and ($kept[-1].Trim() -eq '' -or $kept[-1].Trim() -eq '---')) {
        $kept = if ($kept.Count -gt 1) { @($kept[0..($kept.Count - 2)]) } else { @() }
    }
    return $kept
}

function Format-Chapter {
    param($Ch)
    $meta = if ($Ch.StoryDate) { "_$($Ch.Era) — $($Ch.StoryDate)_" } else { "_$($Ch.Era)_" }
    # drop the chapter's own leading H1 (we re-emit the title as H2) and leading blanks
    $b = $Ch.Body
    $j = 0
    while ($j -lt $b.Count -and $b[$j].Trim() -eq '') { $j++ }
    if ($j -lt $b.Count -and $b[$j] -match '^#\s+') { $j++ }
    while ($j -lt $b.Count -and $b[$j].Trim() -eq '') { $j++ }
    $prose = if ($j -lt $b.Count) { @($b[$j..($b.Count - 1)]) } else { @() }
    return @("## $($Ch.Title)", '', $meta, '') + $prose
}

function Write-Manuscript {
    param([string]$Path, [string]$Title, $Chapters, [string]$Scope)
    Assert-InScope $Path
    $header = @(
        "# $Title",
        '',
        "<!-- GENERATED by .github/skills/story-agent/scripts/assemble-book.ps1 on $today (commit $commit). DO NOT HAND-EDIT. -->",
        "<!-- Scope: $Scope · status filter: $($statuses -join ', ') · chapters: $($Chapters.Count) · source: 30-Story/ only (nothing else read). -->",
        '',
        '> [!warning] Generated file — do not hand-edit.',
        '> Regenerate with `.github/skills/story-agent/scripts/assemble-book.ps1`. Promote chapters to',
        '> `living` / `canonical` to change what lands here.',
        ''
    )
    $parts = foreach ($ch in $Chapters) { (Format-Chapter $ch); '' }
    Set-Content -LiteralPath $Path -Value ($header + $parts) -Encoding utf8
    Write-Host ("  wrote {0} — {1} chapter(s)" -f ([IO.Path]::GetFileName($Path)), $Chapters.Count)
}

# --- gather chapters (30-Story/ + _Drafts/) ---
$chapterFiles = Get-ChildItem -LiteralPath $storyDir -Recurse -Filter 'Chapter*.md'
$chapters = foreach ($f in $chapterFiles) {
    Assert-InScope $f.FullName
    $p = Get-Frontmatter -Path $f.FullName
    if (-not $p) { continue }
    $st = Get-Field $p.Front 'status'
    if ($statuses -notcontains $st) { continue }
    [pscustomobject]@{
        Title     = Get-Field $p.Front 'title'
        Order     = [int](Get-Field $p.Front 'book_order')
        Era       = Get-Field $p.Front 'era'
        StoryDate = (Get-Field $p.Front 'story_date').Trim('"')
        Status    = $st
        Arcs      = Get-ArcList $p.Front
        Body      = Remove-FromHeading $p.Body '^##\s+Sources\s*&\s*fidelity'
    }
}
$chapters = @($chapters | Sort-Object Order)

# --- gather Bible threads (top-level Story — *.md, type: story) ---
$seedOrder = @{ 'Spine' = 1; 'Want vs Need' = 2; 'Arc' = 3; 'Theme' = 4; 'Character' = 5; 'Velocity' = 6 }
$threadFiles = Get-ChildItem -LiteralPath $storyDir -Filter 'Story*.md'
$threads = foreach ($f in $threadFiles) {
    Assert-InScope $f.FullName
    $p = Get-Frontmatter -Path $f.FullName
    if (-not $p) { continue }
    if ((Get-Field $p.Front 'type') -ne 'story') { continue }   # excludes story-index (Arcs + index)
    $st = Get-Field $p.Front 'status'
    if ($statuses -notcontains $st) { continue }
    [pscustomobject]@{
        Title = Get-Field $p.Front 'title'
        Body  = Remove-FromHeading $p.Body '^##\s+Connections'
    }
}
$threads = @($threads | Sort-Object { $o = $seedOrder[$_.Title]; if ($o) { $o } else { 99 } })

# --- write outputs ---
if (-not (Test-Path -LiteralPath $exportDir)) { New-Item -ItemType Directory -Path $exportDir | Out-Null }
Assert-InScope $exportDir

Write-Host "Assembling Book + Seed (status: $($statuses -join ', '))..."
Write-Manuscript -Path (Join-Path $exportDir 'Book.md') -Title 'The Book' -Chapters $chapters -Scope 'full Book (all arcs)'

if ($ByArc) {
    $arcNames = @($chapters | ForEach-Object { $_.Arcs } | Where-Object { $_ } | Sort-Object -Unique)
    foreach ($arc in $arcNames) {
        $sel = @($chapters | Where-Object { $_.Arcs -contains $arc })
        Write-Manuscript -Path (Join-Path $exportDir "Book — $arc.md") -Title "The Book — $arc" -Chapters $sel -Scope "arc: $arc"
    }
}

# --- Seed.md ---
$seedHeader = @(
    '# Story Seed — self-narrative context',
    '',
    "<!-- GENERATED by .github/skills/story-agent/scripts/assemble-book.ps1 on $today (commit $commit). DO NOT HAND-EDIT. -->",
    "<!-- The Bible threads (analytical backing) — status filter: $($statuses -join ', ') · source: 30-Story/ only (nothing else read). -->",
    '',
    '> [!warning] Generated file — do not hand-edit. Regenerate with the assemble-book script.',
    '> This is the compact, exportable read of who the author is — to seed another system or the author themselves.',
    ''
)
$seedParts = foreach ($t in $threads) {
    $b = $t.Body
    $j = 0
    while ($j -lt $b.Count -and $b[$j].Trim() -eq '') { $j++ }
    $rest = if ($j -lt $b.Count -and $b[$j] -match '^#\s+(.+)$') {
        @("## $($Matches[1])") + @($b[($j + 1)..($b.Count - 1)])
    }
    else { $b }
    $rest; ''
}
Set-Content -LiteralPath (Join-Path $exportDir 'Seed.md') -Value ($seedHeader + $seedParts) -Encoding utf8
Write-Host ("  wrote Seed.md — {0} thread(s)" -f $threads.Count)

Write-Host "Done. Outputs in 90-Export/ (generated; regenerate any time)."

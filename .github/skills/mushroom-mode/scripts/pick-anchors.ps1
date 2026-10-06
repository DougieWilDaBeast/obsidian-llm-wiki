<#
.SYNOPSIS
  Mushroom Mode anchor picker: pull FAR-APART Refined notes into contact and strip the structure
  that already connects them, so a fresh, non-obvious bridge can be forced between them.

.DESCRIPTION
  Mushroom mode exists to find links the existing organisation would never surface, so this picker
  does the OPPOSITE of normal browsing:
    * it selects anchor notes that are FAR APART - not linked, not sharing tags, not co-listed in a
      MOC, not mentioning each other (the -Dose knob controls how far apart they must be);
    * it prints each anchor's PROSE only - frontmatter, tags, the ## Connections / ## Sources /
      transcript trailers and every [[link]] bracket stripped out - so the content is read fresh,
      not the structure around it;
    * it lists the suppressed structure separately, under a "do NOT reuse" header, so you can
      consciously avoid re-deriving connections that already exist.

  It assembles raw material only. Forcing the bridge, judging quality honestly, discarding the
  strained pairings, and writing the rare keeper to state/connections.md is the agent's job
  (see SKILL.md). It never edits the wiki.

.PARAMETER Draws
  How many independent anchor SETS to pull this run. Default 3. (Most yield nothing - that's fine.)

.PARAMETER Count
  Notes per set. Default 2.

.PARAMETER Dose
  Low | Medium | High - how far apart the anchors must be. Default High.
    Low    = still somewhat related (share a tag/MOC/mention) but NOT directly linked - grounded.
    Medium = at most a faint overlap.
    High   = share nothing at all (no link, tag, MOC, or mention) - wildest, lowest hit rate.

.PARAMETER Seed
  Optional note (title or path). It becomes one anchor in every draw; the rest are pulled far from it.

.PARAMETER IncludeDigests
  Include the roll-up digests (Captures / Tasks / wearable digests / AI-Chats catalog) and MOCs in the pool.
  Off by default - they are roll-ups, not idea notes.

.PARAMETER Wrap
  Column width for word-wrapping any long single-line bodies. Default 100.

.PARAMETER RngSeed
  Fixed RNG seed for reproducible draws. Default: random (randomness is the feature).

.EXAMPLE
  pwsh -File .github/skills/mushroom-mode/scripts/pick-anchors.ps1
  pwsh -File .github/skills/mushroom-mode/scripts/pick-anchors.ps1 -Dose Low -Draws 5
  pwsh -File .github/skills/mushroom-mode/scripts/pick-anchors.ps1 -Seed "BME280" -Dose High
#>
param(
    [int]$Draws = 3,
    [int]$Count = 2,
    [ValidateSet('Low', 'Medium', 'High')][string]$Dose = 'High',
    [string]$Seed = '',
    [switch]$IncludeDigests,
    [int]$Wrap = 100,
    [int]$RngSeed = 0
)

$ErrorActionPreference = 'Stop'
$repo = (git rev-parse --show-toplevel 2>$null)
if (-not $repo) { Write-Error 'Not inside the vault git repo.'; exit 1 }
Set-Location $repo

$rng = if ($RngSeed -ne 0) { [Random]::new($RngSeed) } else { [Random]::new() }

function To-Rel([string]$full) {
    ((Resolve-Path -LiteralPath $full -Relative) -replace '^\.[\\/]', '' -replace '\\', '/')
}
function Wrap-Body([string]$text, [int]$width) {
    [regex]::Replace($text, "(.{1,$width})(\s+|$)", "`$1`n")
}

# strip everything that tells you how a note is "supposed" to connect: frontmatter, the
# Connections/Sources/transcript trailers, and the [[link]] brackets themselves.
function Strip-Content([string]$raw) {
    $body = $raw -replace '(?s)^\s*---.*?---\s*', ''
    $m = [regex]::Match($body, '(?m)^##\s+(Connections|Sources|Original transcript|Original scan)')
    if ($m.Success) { $body = $body.Substring(0, $m.Index) }
    $body = [regex]::Replace($body, '\[\[([^\]\|]+)\|([^\]]+)\]\]', '$2')  # [[Link|Alias]] -> Alias
    $body = [regex]::Replace($body, '\[\[([^\]]+)\]\]', '$1')             # [[Link]]       -> Link
    return $body.Trim()
}

# --- build the pool of candidate idea-notes --------------------------------------------------
$digestRe = '(?i)(Captures|Tasks|digest|AI-Chats catalog)\.md$'
$files = Get-ChildItem -Recurse -File -Path '10-Refined' -Filter '*.md' |
Where-Object { $_.FullName -notmatch '[\\/]MOCs[\\/]' -and $_.FullName -notmatch '[\\/]_' }
if (-not $IncludeDigests) { $files = $files | Where-Object { $_.Name -notmatch $digestRe } }
if (-not $files -or @($files).Count -lt $Count) { Write-Output 'Not enough candidate pages in 10-Refined.'; exit 0 }

# parse each page: title, tags, outbound link basenames, raw body
$pages = @{}
foreach ($f in $files) {
    $raw = Get-Content -LiteralPath $f.FullName -Raw
    $title = [IO.Path]::GetFileNameWithoutExtension($f.Name)
    $tags = @()
    if ($raw -match '(?ms)^tags:\s*\[(.*?)\]') {
        $tags = ($matches[1] -split ',') | ForEach-Object { $_.Trim().Trim('"').Trim("'") } | Where-Object { $_ }
    }
    $links = [regex]::Matches($raw, '\[\[([^\]]+)\]\]') |
    ForEach-Object { (($_.Groups[1].Value -split '\|')[0].Trim() -replace '\.md$', '') } |
    ForEach-Object { Split-Path $_ -Leaf } | Sort-Object -Unique
    $pages[$title] = [pscustomobject]@{
        Title = $title; Rel = (To-Rel $f.FullName); Tags = @($tags); Links = @($links); Raw = $raw
    }
}

# MOC membership: page-title -> set of MOC names that link it (structure to avoid)
$mocMembership = @{}
$mocFiles = Get-ChildItem -Recurse -File -Path '10-Refined/MOCs' -Filter '*.md' -ErrorAction SilentlyContinue
foreach ($mf in $mocFiles) {
    $mraw = Get-Content -LiteralPath $mf.FullName -Raw
    $mname = [IO.Path]::GetFileNameWithoutExtension($mf.Name)
    $mlinks = [regex]::Matches($mraw, '\[\[([^\]]+)\]\]') |
    ForEach-Object { (($_.Groups[1].Value -split '\|')[0].Trim() -replace '\.md$', '') } |
    ForEach-Object { Split-Path $_ -Leaf }
    foreach ($lk in ($mlinks | Sort-Object -Unique)) {
        if (-not $mocMembership.ContainsKey($lk)) { $mocMembership[$lk] = New-Object System.Collections.Generic.List[string] }
        if ($mocMembership[$lk] -notcontains $mname) { $mocMembership[$lk].Add($mname) }
    }
}

# relatedness score: higher = MORE already-connected (i.e. LESS interesting to mushroom mode)
function Get-Relatedness($a, $b) {
    $score = 0
    if ($a.Links -contains $b.Title -or $b.Links -contains $a.Title) { $score += 5 }   # directly linked
    $amoc = if ($mocMembership.ContainsKey($a.Title)) { $mocMembership[$a.Title] } else { @() }
    $bmoc = if ($mocMembership.ContainsKey($b.Title)) { $mocMembership[$b.Title] } else { @() }
    if (@($amoc | Where-Object { $bmoc -contains $_ }).Count -gt 0) { $score += 2 }      # shared MOC
    if (@($a.Tags | Where-Object { $b.Tags -contains $_ }).Count -gt 0) { $score += 1 }  # shared tag
    if ($a.Raw -match [regex]::Escape($b.Title) -or $b.Raw -match [regex]::Escape($a.Title)) { $score += 1 } # mention
    return $score
}

switch ($Dose) {
    'High' { $minR = 0; $maxR = 0 }
    'Medium' { $minR = 0; $maxR = 1 }
    'Low' { $minR = 1; $maxR = 4 }   # grounded but never directly linked (link = 5)
}

$seedPage = $null
if ($Seed) {
    $key = (Split-Path ($Seed -replace '\.md$', '') -Leaf)
    if ($pages.ContainsKey($key)) { $seedPage = $pages[$key] }
    else { Write-Output "(-Seed '$Seed' not found as a Refined page - running unseeded.)`n" }
}

function Build-Set($seedPage, $minR, $maxR) {
    $set = New-Object System.Collections.Generic.List[object]
    $chosen = New-Object System.Collections.Generic.HashSet[string]
    if ($seedPage) { [void]$set.Add($seedPage); [void]$chosen.Add($seedPage.Title) }
    $titles = @($pages.Keys)
    $attempts = 0
    while ($set.Count -lt $Count -and $attempts -lt 600) {
        $attempts++
        $cand = $pages[$titles[$rng.Next($titles.Count)]]
        if ($chosen.Contains($cand.Title)) { continue }
        $ok = $true
        foreach ($mem in $set) {
            $r = Get-Relatedness $mem $cand
            if ($r -lt $minR -or $r -gt $maxR) { $ok = $false; break }
        }
        if ($ok) { [void]$set.Add($cand); [void]$chosen.Add($cand.Title) }
    }
    return $set
}

Write-Output ''
Write-Output "=== MUSHROOM MODE: $Draws draw(s), $Count anchor(s) each, dose=$Dose (pool: $($pages.Count) notes) ==="
Write-Output 'Ignore how these notes are already organised. Read the stripped CONTENT of each anchor,'
Write-Output 'then force a genuine, NON-OBVIOUS bridge. Most draws yield nothing - discard those honestly.'
Write-Output 'Write only real keepers to state/connections.md; never edit the wiki. (SKILL.md)'
Write-Output ''

for ($d = 1; $d -le $Draws; $d++) {
    $set = Build-Set $seedPage $minR $maxR
    $relaxed = $false
    if ($set.Count -lt $Count) { $relaxed = $true; $set = Build-Set $seedPage 0 6 }  # fallback so a draw never comes up empty
    if ($set.Count -lt $Count) { continue }

    Write-Output '################################################################################'
    $names = ($set | ForEach-Object { "[[$($_.Title)]]" }) -join '  ×  '
    Write-Output "# DRAW $d  ·  dose=$Dose$(if($relaxed){' (relaxed - nothing far enough at this dose)'})"
    Write-Output "#   $names"
    Write-Output '################################################################################'
    # transparency: how far apart they actually are
    for ($i = 0; $i -lt $set.Count; $i++) {
        for ($j = $i + 1; $j -lt $set.Count; $j++) {
            Write-Output ("#   distance {0} × {1}  ->  relatedness r={2}  (0 = nothing in common)" -f $set[$i].Title, $set[$j].Title, (Get-Relatedness $set[$i] $set[$j]))
        }
    }
    Write-Output ''

    foreach ($a in $set) {
        Write-Output "----- ANCHOR: [[$($a.Title)]]   (read this CONTENT only) -----"
        Write-Output (Strip-Content $a.Raw)
        Write-Output ''
    }

    Write-Output '----- SUPPRESSED STRUCTURE (do NOT reuse - these are the links that already exist) -----'
    foreach ($a in $set) {
        $amocs = if ($mocMembership.ContainsKey($a.Title)) { $mocMembership[$a.Title] } else { @() }
        Write-Output "  [[$($a.Title)]]"
        Write-Output ("      tags:  " + (($a.Tags) -join ', '))
        Write-Output ("      MOCs:  " + (($amocs) -join ', '))
        Write-Output ("      links: " + (($a.Links | Select-Object -First 15) -join ', '))
    }
    Write-Output ''
    Write-Output ''
}

Write-Output '=== Integration: write ONLY genuine keepers to .github/skills/mushroom-mode/state/connections.md ==='
Write-Output '=== (see reference/templates.md), surface them in chat, and stop. The user is the filter. (SKILL.md) ==='

<#
.SYNOPSIS
  One-shot, READ-ONLY health report across every layer of the vault. The diagnose half of
  the full-diagnostic skill: it tells you what state the repo is in and which skill to run next.

.DESCRIPTION
  Chains the read-only discovery steps of the other vault skills into a single consolidated
  report. It NEVER edits a page, never commits, never pulls/pushes — it only inspects and prints.
  Five sections, each ending in a verdict line:  OK  or  ATTENTION -> <skill to run>.

    1. SYNC            - git ahead/behind + uncommitted-file count (status only, no network).
    2. INGEST BACKLOG  - uncovered raws (delegates to vault-ingest/new-raws.ps1 -NoSync).
    3. STRUCTURAL      - headless mirror of Dashboard.md: coverage / orphans / stubs +
                         frontmatter sanity (sources-count vs ## Sources list, bad `updated:`).
    4. AUDIT COVERAGE  - parses vault-audit/state/audit-ledger.md: % of Refined ever audited.
    5. STORY FRESHNESS - 30-Story pages + _Drafts; is Refined moving ahead of the narrative?

  Footer prints a RECOMMENDED RUN ORDER built from whichever sections raised ATTENTION.

  This is Phase A of the skill. Phase B (actually running ingest/audit/story) is driven by
  the agent per SKILL.md, honoring each sub-skill's own human gates.

.PARAMETER Quiet
  Print only each section's verdict line + the recommended run order (skip the detail bodies).

.PARAMETER AuditSample
  How many pages vault-audit would sample in Phase B (echoed into the run-order hint). Default 3.

.EXAMPLE
  pwsh -File .github/skills/full-diagnostic/scripts/run-diagnostic.ps1
  pwsh -File .github/skills/full-diagnostic/scripts/run-diagnostic.ps1 -Quiet
#>
param(
    [switch]$Quiet,
    [int]$AuditSample = 3
)

$ErrorActionPreference = 'Stop'
$repo = (git rev-parse --show-toplevel 2>$null)
if (-not $repo) { Write-Error 'Not inside the vault git repo.'; exit 1 }
Set-Location $repo

# --- helpers ---------------------------------------------------------------------------------
$recommend = [System.Collections.Generic.List[string]]::new()
function Flag([string]$skill) { if (-not $recommend.Contains($skill)) { $recommend.Add($skill) } }
function Section([string]$title) { if (-not $Quiet) { Write-Output ''; Write-Output "===== $title =====" } }
function Detail([string]$line) { if (-not $Quiet) { Write-Output $line } }
function Verdict([string]$title, [string]$line) {
    if ($Quiet) { Write-Output ("{0,-18} {1}" -f "[$title]", $line) } else { Write-Output $line }
}
function To-Rel([string]$full) { ([IO.Path]::GetRelativePath($repo, $full) -replace '\\', '/') }

# basenames of every Refined page (for wikilink resolution / inlink tests). Case-insensitive,
# because Obsidian wikilinks are case-insensitive ([[esp32]] resolves to ESP32.md).
$refinedFiles = Get-ChildItem -Recurse -File -Path '10-Refined' -Filter '*.md'
$refinedNames = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
foreach ($f in $refinedFiles) { [void]$refinedNames.Add([IO.Path]::GetFileNameWithoutExtension($f.Name)) }
$refinedBlob = ($refinedFiles | Get-Content -Raw) -join "`n"

# Wikilink-resolution set: Refined + Story basenames. Refined pages MAY link into 30-Story
# (CLAUDE.md §12a), so those backlinks must NOT be counted as dead. Story files are added ONLY to
# this name set, never to $refinedFiles (which drives the frontmatter / coverage / stub walks).
$linkTargets = [System.Collections.Generic.HashSet[string]]::new($refinedNames, [System.StringComparer]::OrdinalIgnoreCase)
if (Test-Path '30-Story') {
    Get-ChildItem -Recurse -File -Path '30-Story' -Filter '*.md' |
    ForEach-Object { [void]$linkTargets.Add([IO.Path]::GetFileNameWithoutExtension($_.Name)) }
}

Write-Output '################################################################################'
Write-Output "#  VAULT FULL-DIAGNOSTIC  -  $(Get-Date -Format 'yyyy-MM-dd HH:mm')  (read-only)"
Write-Output '################################################################################'

# === 1. SYNC =================================================================================
Section '1. SYNC (git, status-only)'
$branchLine = (git status -sb 2>$null | Select-Object -First 1)
$dirty = @(git status --porcelain 2>$null).Where({ $_ -ne '' })
$ahead = if ($branchLine -match '\[ahead (\d+)') { [int]$Matches[1] } else { 0 }
$behind = if ($branchLine -match 'behind (\d+)') { [int]$Matches[1] } else { 0 }
Detail $branchLine
Detail "Uncommitted files: $($dirty.Count)  |  ahead: $ahead  behind: $behind"
if ($dirty.Count -gt 0 -or $ahead -gt 0 -or $behind -gt 0) {
    Verdict 'SYNC' "ATTENTION -> commit/sync before a full update ($($dirty.Count) uncommitted, ahead $ahead, behind $behind)."
}
else { Verdict 'SYNC' 'OK - clean working tree, in sync with origin.' }

# === 2. INGEST BACKLOG =======================================================================
Section '2. INGEST BACKLOG (uncovered raws)'
$newRaws = Join-Path $repo '.github/skills/vault-ingest/scripts/new-raws.ps1'
$uncovered = -1; $nNew = 0; $nOld = 0
if (Test-Path $newRaws) {
    $out = & pwsh -NoProfile -File $newRaws -NoSync 2>$null
    $hdr = ($out | Select-String -Pattern 'UNCOVERED RAWS:\s*(\d+)\s*\(new since last ingest:\s*(\d+),\s*older/missed:\s*(\d+)\)' | Select-Object -First 1)
    if ($hdr) {
        $uncovered = [int]$hdr.Matches[0].Groups[1].Value
        $nNew = [int]$hdr.Matches[0].Groups[2].Value
        $nOld = [int]$hdr.Matches[0].Groups[3].Value
    }
    # list just the uncovered filenames (not the full bodies)
    $names = $out | Select-String -Pattern '^\[(NEW|OLDER/MISSED)\] FILE:\s*(.+)$' | ForEach-Object {
        "  - [$($_.Matches[0].Groups[1].Value)] $($_.Matches[0].Groups[2].Value)"
    }
    if (-not $Quiet -and $names) { $names | ForEach-Object { Detail $_ } }
}
else { Detail "(new-raws.ps1 not found at $newRaws)" }
if ($uncovered -lt 0) { Verdict 'INGEST' 'UNKNOWN - could not read new-raws.ps1 output.' }
elseif ($uncovered -eq 0) { Verdict 'INGEST' 'OK - vault fully covered, nothing to ingest.' }
else { Flag 'vault-ingest'; Verdict 'INGEST' "ATTENTION -> vault-ingest ($uncovered uncovered: $nNew new, $nOld older/missed)." }

# === 3. STRUCTURAL HEALTH ====================================================================
Section '3. STRUCTURAL HEALTH (Dashboard mirror + frontmatter sanity)'
# 3a. coverage: Voice/Clippings raws with no basename appearing in Refined
$rawCheck = foreach ($d in 'Voice', 'Clippings') {
    $p = Join-Path '00-Raw' $d
    if (Test-Path $p) { Get-ChildItem -Recurse -File -Path $p -Filter '*.md' }
}
$uncov = @($rawCheck | Where-Object { -not $refinedBlob.Contains([IO.Path]::GetFileNameWithoutExtension($_.Name)) })

# 3b/3c/3d: walk Refined frontmatter once
$stubs = 0; $badUpdated = 0; $countMismatch = 0; $deadLinks = 0; $orphans = 0
$metaIssues = [System.Collections.Generic.List[string]]::new()
foreach ($f in $refinedFiles) {
    $raw = Get-Content -LiteralPath $f.FullName -Raw
    $rel = To-Rel $f.FullName
    $type = if ($raw -match '(?m)^type:\s*(\S+)') { $Matches[1] } else { '' }
    if ($type -in @('dashboard', 'moc', 'story-index')) { continue }
    $status = if ($raw -match '(?m)^status:\s*(\S+)') { $Matches[1] } else { '' }
    if ($status -eq 'stub') { $stubs++ }
    # updated: must be ISO yyyy-mm-dd
    if ($raw -match '(?m)^updated:\s*(.+)$') {
        if ($Matches[1].Trim() -notmatch '^\d{4}-\d{2}-\d{2}$') { $badUpdated++; $metaIssues.Add("  - bad updated: -> [[$($rel -replace '\.md$','')]]") }
    }
    else { $badUpdated++; $metaIssues.Add("  - missing updated: -> [[$($rel -replace '\.md$','')]]") }
    # sources: N  vs  count of [[wikilinks]] under ## Sources. Count LINKS not bullets (so a single
    # "Raw: [[a]] · [[b]] · [[c]]" bullet and a non-link "URL: <...>" line are handled), but drop
    # trailing "> [!note]" callout lines whose cross-refs aren't sources.
    if ($raw -match '(?m)^sources:\s*(\d+)') {
        $declared = [int]$Matches[1]
        if ($raw -match '(?s)##\s*Sources\s*(.*?)(\n##\s|\z)') {
            $srcBody = (($Matches[1] -split "`n") | Where-Object { $_ -notmatch '^\s*>' }) -join "`n"
            $listed = ([regex]::Matches($srcBody, '\[\[[^\]]+\]\]')).Count
            if ($listed -gt 0 -and $listed -ne $declared) {
                $countMismatch++
                $metaIssues.Add("  - sources count $declared but ## Sources lists $listed -> [[$($rel -replace '\.md$','')]]")
            }
        }
    }
    # unresolved wikilinks (skip 00-Raw/ links, non-page anchors, and links inside code spans).
    # Resolve against $linkTargets so Refined -> 30-Story backlinks (allowed, §12a) aren't "dead".
    $noCode = [regex]::Replace($raw, '(?s)\x60{3}.*?\x60{3}', '')   # fenced code blocks
    $noCode = [regex]::Replace($noCode, '\x60[^\x60]*\x60', '')      # inline `code`
    foreach ($m in [regex]::Matches($noCode, '\[\[([^\]]+)\]\]')) {
        $tgt = ($m.Groups[1].Value -split '\|')[0].Trim() -replace '\.md$', ''
        $tgt = ($tgt -split '#')[0].Trim()   # drop any #section anchor
        if (-not $tgt) { continue }
        if ($tgt -match '^00-Raw/' -or $tgt -match '^(index|log|Dashboard)$' -or $tgt -match '/') { continue }
        if (-not $linkTargets.Contains($tgt)) { $deadLinks++ }
    }
}
Detail "Coverage (Voice/Clippings raws not yet in Refined): $($uncov.Count)"
if (-not $Quiet) { $uncov | Select-Object -First 8 | ForEach-Object { Detail "  - $(To-Rel $_.FullName)" } }
Detail "Stubs (status: stub): $stubs"
Detail "Frontmatter issues: $badUpdated bad/missing updated, $countMismatch sources-count mismatch, $deadLinks unresolved wikilink(s)"
if (-not $Quiet) { $metaIssues | Select-Object -First 10 | ForEach-Object { Detail $_ } }
$structBad = ($uncov.Count -gt 0) -or ($badUpdated -gt 0) -or ($countMismatch -gt 0) -or ($deadLinks -gt 0)
if ($structBad) {
    if ($uncov.Count -gt 0) { Flag 'vault-ingest' }
    Flag 'vault-audit'
    Verdict 'STRUCTURAL' "ATTENTION -> vault-audit (and fix): coverage $($uncov.Count), updated $badUpdated, sourcecount $countMismatch, deadlinks $deadLinks."
}
else { Verdict 'STRUCTURAL' "OK - $stubs stub(s), no coverage gaps or frontmatter problems." }

# === 4. AUDIT COVERAGE =======================================================================
Section '4. AUDIT COVERAGE (spot-check ledger)'
$ledger = Join-Path $repo '.github/skills/vault-audit/state/audit-ledger.md'
$claimPages = @($refinedFiles | Where-Object {
        $r = Get-Content -LiteralPath $_.FullName -Raw
        ($r -match '(?m)^type:\s*(entity|concept|project|source|person)') -and ($r -notmatch '(?m)^type:\s*(dashboard|moc|story-index)')
    })
$total = $claimPages.Count
$auditedSet = @{}; $lastRun = ''
if (Test-Path $ledger) {
    foreach ($line in (Get-Content -LiteralPath $ledger)) {
        if ($line -match '^\s*-\s*\[(\d{4}-\d{2}-\d{2})\]\s*audited\s*::\s*(.+?)\s*$') { $auditedSet[$Matches[2]] = $Matches[1] }
        if ($line -match '^##\s*\[(\d{4}-\d{2}-\d{2})\]\s*audit run') { if ($Matches[1] -gt $lastRun) { $lastRun = $Matches[1] } }
    }
}
$auditedCount = $auditedSet.Count
$pct = if ($total -gt 0) { [math]::Round(100.0 * $auditedCount / $total) } else { 0 }
$never = $total - $auditedCount
Detail "Refined claim-bearing pages: $total  |  ever audited: $auditedCount ($pct%)  |  never audited: $never"
Detail ("Last audit run: " + $(if ($lastRun) { $lastRun } else { 'never' }))
if ($total -eq 0 -or $pct -lt 80 -or -not $lastRun) {
    Flag 'vault-audit'
    Verdict 'AUDIT' "ATTENTION -> vault-audit (only $pct% ever cross-checked; sample $AuditSample next run)."
}
else { Verdict 'AUDIT' "OK - $pct% of pages have been cross-checked (last run $lastRun)." }

# === 5. STORY FRESHNESS ======================================================================
Section '5. STORY FRESHNESS (30-Story)'
$storyDir = Join-Path $repo '30-Story'
$storyNewest = ''; $storyPages = 0; $storyDrafts = 0
if (Test-Path $storyDir) {
    $sp = Get-ChildItem -Recurse -File -Path $storyDir -Filter '*.md' | Where-Object { $_.Name -notin @('README.md', 'story-index.md') }
    foreach ($s in $sp) {
        if ($s.FullName -match '[\\/]_Drafts[\\/]') { $storyDrafts++; continue }
        $storyPages++
        $r = Get-Content -LiteralPath $s.FullName -Raw
        if ($r -match '(?m)^updated:\s*(\d{4}-\d{2}-\d{2})') { if ($Matches[1] -gt $storyNewest) { $storyNewest = $Matches[1] } }
    }
}
# newest dated Refined SOURCE page (proxy for "how far the plot has moved")
$refNewest = ''
foreach ($f in $refinedFiles) {
    if ($f.Name -match '^(\d{4}-\d{2}-\d{2})') { if ($Matches[1] -gt $refNewest) { $refNewest = $Matches[1] } }
}
Detail "Story pages: $storyPages  |  drafts pending: $storyDrafts  |  newest Story updated: $(if($storyNewest){$storyNewest}else{'n/a'})"
Detail "Newest Refined source date: $(if($refNewest){$refNewest}else{'n/a'})"
if ($storyDrafts -gt 0 -or ($refNewest -and $storyNewest -and $refNewest -gt $storyNewest)) {
    Flag 'story-agent'
    $why = if ($storyDrafts -gt 0) { "$storyDrafts draft(s) pending" } else { "Refined ($refNewest) has moved past Story ($storyNewest)" }
    Verdict 'STORY' "ATTENTION -> story-agent ($why)."
}
else { Verdict 'STORY' 'OK - narrative is level with the refined record.' }

# === FOOTER: recommended run order ===========================================================
$order = @('vault-ingest', 'vault-audit', 'story-agent') | Where-Object { $recommend.Contains($_) }
Write-Output ''
Write-Output '================================================================================'
if ($order.Count -eq 0) {
    Write-Output 'RECOMMENDED RUN ORDER:  (none) - vault is healthy across every layer.'
}
else {
    Write-Output "RECOMMENDED RUN ORDER:  $($order -join '  ->  ')"
    Write-Output 'Phase B: hand each flagged skill to its own SKILL workflow, in this order.'
    Write-Output 'Reminder: ingest auto-commits; audit/story only DRAFT + ask - the human confirms.'
}
Write-Output '================================================================================'

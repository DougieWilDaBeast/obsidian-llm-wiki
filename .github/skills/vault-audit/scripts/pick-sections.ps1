<#
.SYNOPSIS
  Roll an unpredictable spot-audit: randomly pick a few Refined pages and dump everything
  needed to cross-check them against their sources, in one shot.

.DESCRIPTION
  Token-saver for the vault-audit skill. The audit is deliberately RANDOM in two ways:
    * random sections  - it picks pages at random (not the oldest, not a fixed sweep), so the
      whole vault has to stay honest because you can't predict what gets scrutinised;
    * random frequency - with -Roll it first flips a weighted coin to decide whether to audit
      at all, so the cadence is unpredictable when wired into a scheduler / post-ingest hook.

  For each picked page it prints:
    * the page's frontmatter (sources count, updated date) + full body;
    * the verbatim body of every 00-Raw source the page cites (word-wrapped so long single-line
      Whisper transcripts are not truncated) - this is the GROUND TRUTH to cross-check against;
    * the names of other Refined pages that mention this page's title (where contradictions hide).

  It ONLY assembles evidence. It interprets nothing, edits nothing, and resolves nothing -
  cross-checking, drilling into anything that surfaces, and (crucially) preparing QUESTIONS or
  OPTIONS rather than assuming an answer is the agent's job (see SKILL.md).

.PARAMETER Count
  How many pages to pick. Default 3.

.PARAMETER Roll
  Random-frequency gate. If set, the script first decides (probability -Chance) whether to run
  at all; if the coin says "skip", it prints SKIP and exits 0 without picking anything.

.PARAMETER Chance
  Probability (0..1) used by -Roll that this invocation actually audits. Default 0.5.

.PARAMETER BiasUnaudited
  If set, pages never recorded in the ledger are weighted more heavily so coverage compounds.
  Off by default - default behaviour is genuinely uniform-random.

.PARAMETER IncludeDigests
  By default the roll-up digests (YYYY-MM Captures / Tasks, weekly wearable digests, AI-Chats catalog) and MOCs
  are excluded (they are summaries, not claim-bearing pages). Set this to include them.

.PARAMETER Wrap
  Column width for word-wrapping raw bodies. Default 110.

.PARAMETER Seed
  Optional fixed RNG seed for reproducible picks (e.g. to re-dump the same set). Default: random.

.EXAMPLE
  pwsh -File .github/skills/vault-audit/scripts/pick-sections.ps1
  pwsh -File .github/skills/vault-audit/scripts/pick-sections.ps1 -Count 2 -BiasUnaudited
  pwsh -File .github/skills/vault-audit/scripts/pick-sections.ps1 -Roll -Chance 0.3
#>
param(
    [int]$Count = 3,
    [switch]$Roll,
    [double]$Chance = 0.5,
    [switch]$BiasUnaudited,
    [switch]$IncludeDigests,
    [int]$Wrap = 110,
    [int]$Seed = 0
)

$ErrorActionPreference = 'Stop'
$repo = (git rev-parse --show-toplevel 2>$null)
if (-not $repo) { Write-Error 'Not inside the vault git repo.'; exit 1 }
Set-Location $repo

$rng = if ($Seed -ne 0) { [Random]::new($Seed) } else { [Random]::new() }

# --- random-frequency gate -------------------------------------------------------------------
if ($Roll) {
    $r = $rng.NextDouble()
    if ($r -ge $Chance) {
        Write-Output "=== SPOT-AUDIT ROLL: SKIP ==="
        Write-Output "Rolled $([math]::Round($r,3)) >= chance $Chance - no audit this time."
        exit 0
    }
    Write-Output "=== SPOT-AUDIT ROLL: GO (rolled $([math]::Round($r,3)) < $Chance) ==="
}

# --- ledger (what was audited before) --------------------------------------------------------
$ledgerPath = Join-Path $repo '.github/skills/vault-audit/state/audit-ledger.md'
$audited = @{}   # page-relpath -> last audited date string
if (Test-Path $ledgerPath) {
    foreach ($line in (Get-Content -LiteralPath $ledgerPath)) {
        # matches: - [2026-06-20] audited :: 10-Refined/Some Page.md
        if ($line -match '^\s*-\s*\[(\d{4}-\d{2}-\d{2})\]\s*audited\s*::\s*(.+?)\s*$') {
            $audited[$matches[2]] = $matches[1]
        }
    }
}

function To-Rel([string]$full) {
    ((Resolve-Path -LiteralPath $full -Relative) -replace '^\.[\\/]', '' -replace '\\', '/')
}

function Wrap-Body([string]$text, [int]$width) {
    # word-wrap so single-line Whisper transcripts are readable (not truncated at 2000 chars)
    [regex]::Replace($text, "(.{1,$width})(\s+|$)", "`$1`n")
}

# resolve a [[wikilink]] (basename or path) to an actual file under 00-Raw / 10-Refined
function Resolve-Link([string]$link) {
    $link = ($link -split '\|')[0].Trim() -replace '\.md$', ''
    $leaf = Split-Path $link -Leaf
    foreach ($root in @('00-Raw', '10-Refined')) {
        if (-not (Test-Path $root)) { continue }
        $hit = Get-ChildItem -Recurse -File -Path $root -Filter "$leaf.md" -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($hit) { return $hit.FullName }
    }
    return $null
}

# --- candidate pool ---------------------------------------------------------------------------
$digestRe = '(?i)(Captures|Tasks|digest|AI-Chats catalog)\.md$'
$pool = Get-ChildItem -Recurse -File -Path '10-Refined' -Filter '*.md' |
Where-Object { $_.FullName -notmatch '[\\/]MOCs[\\/]' -and $_.FullName -notmatch '[\\/]_' }
if (-not $IncludeDigests) { $pool = $pool | Where-Object { $_.Name -notmatch $digestRe } }

if (-not $pool) { Write-Output 'No candidate pages found in 10-Refined.'; exit 0 }

# weight: each page gets a random key; unaudited pages get a boost when -BiasUnaudited
$ranked = foreach ($f in $pool) {
    $rel = To-Rel $f.FullName
    $key = $rng.NextDouble()
    if ($BiasUnaudited -and -not $audited.ContainsKey($rel)) { $key += 1.0 }  # push to the top
    [pscustomobject]@{ File = $f; Rel = $rel; Key = $key; Last = $audited[$rel] }
}
$picks = $ranked | Sort-Object -Property Key -Descending | Select-Object -First $Count

Write-Output ''
Write-Output "=== SPOT-AUDIT: $($picks.Count) page(s) picked at random from $($pool.Count) candidates ==="
Write-Output 'Cross-check each page against the RAW bodies below. Anything that does not line up,'
Write-Output 'chase it with focus. Do NOT assume a fix - prepare a QUESTION or OPTIONS (see SKILL.md).'
Write-Output ''

foreach ($p in $picks) {
    $body = Get-Content -LiteralPath $p.File.FullName -Raw
    $lastTxt = if ($p.Last) { "last audited $($p.Last)" } else { 'never audited' }
    Write-Output '################################################################################'
    Write-Output "# PAGE: [[$($p.Rel -replace '\.md$','')]]   ($lastTxt)"
    Write-Output '################################################################################'
    Write-Output $body.TrimEnd()
    Write-Output ''

    # cited 00-Raw sources -> dump verbatim (ground truth)
    $links = [regex]::Matches($body, '\[\[([^\]]+)\]\]') | ForEach-Object { $_.Groups[1].Value }
    $rawDumped = $false
    foreach ($lk in ($links | Sort-Object -Unique)) {
        $target = Resolve-Link $lk
        if ($target -and $target -match '[\\/]00-Raw[\\/]') {
            if (-not $rawDumped) { Write-Output '----- GROUND TRUTH (cited 00-Raw sources, verbatim) -----'; $rawDumped = $true }
            Write-Output ">>> RAW: $(To-Rel $target)"
            Write-Output (Wrap-Body ((Get-Content -LiteralPath $target -Raw).Trim()) $Wrap)
            Write-Output ''
        }
    }
    # source pages the agent may want to trace further
    $srcPages = foreach ($lk in ($links | Sort-Object -Unique)) {
        $target = Resolve-Link $lk
        if ($target -and $target -match '[\\/]10-Refined[\\/]' -and (To-Rel $target) -ne $p.Rel) { To-Rel $target }
    }
    if ($srcPages) {
        Write-Output '----- LINKED REFINED PAGES (trace if a claim needs corroboration) -----'
        $srcPages | Sort-Object -Unique | ForEach-Object { Write-Output "  - [[$($_ -replace '\.md$','')]]" }
        Write-Output ''
    }

    # where contradictions hide: other Refined pages that name this page's title
    $title = [IO.Path]::GetFileNameWithoutExtension($p.File.Name)
    $titleRe = '(?i)' + [regex]::Escape($title)
    $mentioners = Get-ChildItem -Recurse -File -Path '10-Refined' -Filter '*.md' |
    Where-Object { $_.FullName -ne $p.File.FullName } |
    Where-Object { (Get-Content -LiteralPath $_.FullName -Raw) -match $titleRe } |
    ForEach-Object { To-Rel $_.FullName }
    if ($mentioners) {
        Write-Output '----- PEER PAGES THAT MENTION THIS TITLE (cross-check for contradictions) -----'
        $mentioners | Sort-Object -Unique | Select-Object -First 12 | ForEach-Object { Write-Output "  - [[$($_ -replace '\.md$','')]]" }
        Write-Output ''
    }
    Write-Output ''
}

Write-Output '=== After auditing: append an `audited` line per page to state/audit-ledger.md, ==='
Write-Output '=== record any OPEN findings + the human INDICATOR responses there, and log one  ==='
Write-Output '=== `audit` entry in log.md. Never auto-fix without the human saying so. (SKILL.md) ==='

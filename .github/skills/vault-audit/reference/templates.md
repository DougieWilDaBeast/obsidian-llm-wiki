# vault-audit — templates

Operational templates for the random cross-check skill. Authoritative schema:
[`CLAUDE.md`](../../../../CLAUDE.md) §8 (Lint), §9 (conservative synthesis), §10 (never).

---

## 1. Finding — QUESTION form (use when you don't have a clean set of resolutions)

Use this when something doesn't line up and the honest move is to ask, not to guess.

```markdown
- **[YYYY-MM-DD] OPEN · <page>** — <what doesn't line up, stated plainly>.
  - Evidence: page says "<claim>" ([[10-Refined/…]]) but raw says "<verbatim>" ([[00-Raw/…]]).
  - Question for human: <one specific question — no leading assumption baked in>.
  - Status: open · awaiting indicator.
```

## 2. Finding — OPTIONS form (use when there are a few plausible resolutions)

Offer options so the human can react fast — but the options are _candidates to react to_, not a
forced choice. Always include an escape hatch ("none of these / it's more nuanced").

```markdown
- **[YYYY-MM-DD] OPEN · <page>** — <the discrepancy>.
  - Evidence: <claim + cited source> vs <conflicting source/raw>.
  - Options:
    - (a) <resolution A>
    - (b) <resolution B>
    - (c) <resolution C>
    - (d) none of these — you'd frame it differently (please say how).
  - Status: open · awaiting indicator.
```

## 3. Recording the human's reply — as an INDICATOR, not a verdict

When the human answers, **do not** treat it as settled truth and rewrite the page. Record their
reply as a dated _indicator_ on the finding. It informs the next pass; the matter stays open
unless they explicitly tell you to settle/fix it.

```markdown
- **Indicator [YYYY-MM-DD]:** <what the human said, verbatim-ish>.
  Read as: <perspective added | partial answer | likely answer — your honest classification>.
- Status: still-open (perspective added) ← default

# only when the human explicitly says "settle it / fix it":

- Status: settled [YYYY-MM-DD] — human directed the fix; page edited accordingly.
```

> Why: the human "may just have added a perspective, not an answer." One reply is one signal.
> Convergence across replies/sources is what closes a finding — never a single response.

## 4. Ledger entries (`state/audit-ledger.md`)

One `audited` line per page each run (the picker reads these to bias coverage), plus any open
findings carried forward. Keep it terse.

```markdown
## [YYYY-MM-DD] audit run

- [YYYY-MM-DD] audited :: 10-Refined/<Page A>.md
- [YYYY-MM-DD] audited :: 10-Refined/<Page B>.md

### Open findings

<paste the QUESTION/OPTIONS findings here; move to "Resolved" only when settled>

### Resolved

- **[YYYY-MM-DD] settled · <page>** — <what changed and that the human directed it>.
```

## 5. `log.md` entry (public timeline — terse, no raw findings dumped)

```markdown
## [YYYY-MM-DD] audit | spot-check (<N> pages)

- Cross-checked [[Page A]], [[Page B]], [[Page C]] against sources. Raised <k> question(s) for
  the human (see vault-audit ledger). No pages edited (awaiting indicators).
```

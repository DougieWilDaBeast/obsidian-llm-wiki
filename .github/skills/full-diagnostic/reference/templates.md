# full-diagnostic — templates

Operational templates for the meta-skill. Authoritative schema:
[`CLAUDE.md`](../../../../CLAUDE.md) §7 (index/log), §8 (Lint), §9 (headless), §10 (never).

---

## 1. Consolidated report (what to paste back to the human after Phase A)

Summarise the script's five verdicts + the run order. Keep it tight — the human is deciding
whether to proceed.

```markdown
**Vault full-diagnostic — <date>** (read-only)

| Section                   | Verdict                                       |
| ------------------------- | --------------------------------------------- |
| Sync                      | <OK / ATTENTION …>                            |
| Ingest backlog            | <OK / N uncovered>                            |
| Structural health         | <OK / coverage·updated·sourcecount·deadlinks> |
| Audit coverage            | <OK / N% ever cross-checked>                  |
| Story freshness           | <OK / N drafts · Refined ahead>               |

**Recommended run order:** <ingest → audit → story, only the flagged ones>

Proceed with Phase B? (or name a subset.)
```

## 2. `log.md` — umbrella diagnostic entry (append-only timeline)

One entry per full-diagnostic pass — alongside the existing `ingest` / `lint` / `audit` prefixes.
The sub-skills still write their own entries; this is the umbrella record.

```markdown
## [YYYY-MM-DD] diagnostic | <one-line summary>

- Ran full-diagnostic (Phase A). Flagged: <skills>.
- Phase B: <vault-ingest filed N raws / vault-audit raised K questions / story drafts / …>.
- Left for human: <open audit findings awaiting indicators / drafts awaiting canonisation / none>.
```

## 3. Verdict legend (how the script grades each section)

| Section           | OK when                                | ATTENTION → skill                  |
| ----------------- | -------------------------------------- | ---------------------------------- |
| Sync              | clean tree, in sync                    | commit/sync first                  |
| Ingest backlog    | 0 uncovered raws                       | vault-ingest                       |
| Structural health | no coverage gap / frontmatter issue    | vault-audit (+ ingest if coverage) |
| Audit coverage    | ≥80% ever audited & a prior run exists | vault-audit                        |
| Story freshness   | no drafts & Story level with Refined   | story-agent                        |

Thresholds are heuristics, not gates — the human decides what actually runs in Phase B.

# TROUBLESHOOTING.md — the gotchas you'll actually hit

These are the real problems encountered building and running this system, with the fixes. They
roughly follow the setup order.

---

## Data & git

### Your git _history_ can leak private data — start fresh, never fork

The single most important rule. If you build your real vault by cloning/forking a repo that
ever contained private notes, those notes live forever in the git history even after you delete
the files. **For your real vault, `git init` a fresh repo with zero history and use a private
remote.** Verify before pushing:

```bash
git log --oneline            # should be a clean history you control
git grep -i "secret-term"    # search the whole tree for anything sensitive
```

### CRLF ↔ LF mangles shell scripts

Editing scripts on Windows can introduce `\r\n` line endings, which break shebangs and `flock`
on Linux (`bad interpreter: /usr/bin/env bash^M`). The committed `.gitattributes` forces `LF`,
so keep it. The `warning: CRLF will be replaced by LF` messages are **expected and harmless** —
git is doing the right thing.

### Two devices both running git → merge chaos

If your phone and server both commit, you get constant conflicts. **Make the server the only
git brain.** Editing devices only write Markdown (synced via SyncThing etc.); the server runs
`vault_autocommit.sh` to commit/rebase/push. Exclude `.git` from device sync (`.stignore`).

### Auto-commit committing half-written agent output

The agent rewrites several pages per ingest; if the 2-minute auto-commit timer fires
mid-write you'd commit a partial page. The pipeline prevents this with a **presence lock**:
`ingest_one.sh`/`transcribe_new.sh` `touch` `/tmp/vault-ingest.lock`, and
`vault_autocommit.sh` bails while it exists.

### Two ingests (or a double-fired trigger) overlapping

A file-watcher can fire twice, or a long ingest can still be running when the next triggers.
Each script takes an **`flock` single-runner guard** (e.g. `/tmp/vault-ingest-run.lock`) and
simply skips if another instance holds it.

---

## The agent / ingest

### Dormant by default — "nothing happens"

If you run `ingest_one.sh` and it logs `NO-OP (INGEST_CMD unset; scaffold is dormant)`, that's
intended. The model backend is unset out of the box so an accidental trigger can't write
partial pages. Set `INGEST_CMD` (Stage 2 of `SETUP.md`) to activate it.

### Ingest costs credits; transcription doesn't — keep them separate

Voice transcription runs locally (free). The _ingest_ step may call a paid API. They're
deliberately decoupled so you can transcribe eagerly and ingest deliberately. Don't wire ingest
to fire on every capture until you're comfortable with the cost; a scheduled/batched ingest is
cheaper than per-file.

### Reasoning effort vs. cost

Bigger models / higher "thinking" settings produce better synthesis but cost more per ingest.
Start with a smaller/cheaper configuration and only raise it for sources that warrant deeper
synthesis.

### Agent silently overwrote a settled conclusion

In headless mode the agent integrates freely, which can flatten nuance. `CLAUDE.md` requires it
to record contradictions explicitly and flag big reinterpretations with a `> [!review]`
callout rather than overwriting. If you see settled pages changing silently, reinforce §9 of
`CLAUDE.md`.

---

## Voice pipeline

### Whisper transcripts are noisy / mis-transcribe names

Cheap microphones and background noise produce errors, especially on proper nouns. The pipeline
runs an **ffmpeg denoise pass** (`afftdn` + high/low-pass) before transcription, which helps.
Per `CLAUDE.md`, the agent keeps the **verbatim transcript** at the bottom of each voice source
page, so exact wording is recoverable even when the summary cleaned it up.

### Re-running re-transcribes everything

`backfill_transcribe.py` keeps a **sha256 ledger** so already-transcribed audio is skipped.
Don't delete the ledger unless you want to redo everything. Use `--dry-run` first to inventory
without writing.

### Duplicate clips from sync (`name (1).m4a`)

Sync transports create duplicate-named files. The transcriber normalises names (stripping a
trailing `(N)`) and prefers original formats, so the same note isn't transcribed twice.

---

## Sync & network

### Phone captures go stale when the private network is off

If the server reaches the phone over Tailscale (or similar) and that's down, captures sit on the
phone untranscribed. Nothing is lost — they sync when the link is back — but the wiki won't
update until then. Check the tunnel is up if new notes aren't appearing.

---

## n8n (optional automation)

### Can't log in — login just bounces back

n8n defaults to **secure cookies**, which browsers refuse over plain HTTP. On a private
HTTP-only network the login silently fails. Fix: set `N8N_SECURE_COOKIE=false` (already in the
shipped compose file) and recreate the container. If you put n8n behind HTTPS, remove that line
instead.

```bash
docker compose -f pipeline/n8n/docker-compose.yml up -d --force-recreate
docker exec llm-wiki-n8n printenv N8N_SECURE_COOKIE   # -> false
curl -s -o /dev/null -w '%{http_code}\n' localhost:${N8N_PORT}   # -> 200
```

### Importing the workflow says nodes "need to be installed"

Recent n8n builds flag the `localFileTrigger` and `executeCommand` nodes (they touch the
filesystem / run commands and are gated). The shipped workflow is a **template with those nodes
disabled and the workflow inactive** — it's safe in version control. At activation, enable the
nodes deliberately. If your build blocks them entirely, use the systemd/inotify trigger path
instead.

### The watcher runs inside the container and can't see git/the model

The n8n container has the vault mounted **read-only** at `/vault` but has no git or model. So
the workflow's Execute Command **SSHes back to the host** to run `ingest_one.sh` there. That
needs a container→host SSH key at `/home/node/.ssh/wiki_ingest`, and the command maps the
`/vault/...` path back to the host path. Don't expect the container to ingest by itself.

### Docker permission denied

`docker: permission denied while trying to connect to the Docker daemon socket`. Add yourself
to the docker group once: `sudo usermod -aG docker "$USER"`, then log out/in (or `newgrp
docker`).

### Host Node.js too old to run n8n natively

Distro Node (e.g. v18) can be too old for current n8n, with cryptic startup errors. Running n8n
in **Docker** (as this repo does) sidesteps the host Node version entirely.

---

## SSH to the server

### Password auth is flaky / drops mid-login

Password SSH can reset mid-authentication (`Connection closed by <ip> port 22`). Just retry. For
anything automated, **use key-based auth** — it's more reliable and required for the
container→host ingest hop.

### `sudo` over SSH fails without a TTY

Running `sudo` through a non-interactive SSH command fails (`sudo: no tty present`). Allocate a
TTY: `ssh -t user@host 'sudo ...'`.

### PowerShell → ssh quoting traps

When invoking `ssh` from PowerShell, `$(...)`, `$VAR`, and escaped `\"` in the _remote_ command
string get interpreted by **local** PowerShell first and mangle the command. Put any non-trivial
remote logic in a `.sh` file on the server and call that, rather than building a complex remote
command string inline.

---

## Quick reference — locks & state

| Path                                  | Purpose                                                    |
| ------------------------------------- | ---------------------------------------------------------- |
| `/tmp/vault-ingest.lock`              | presence lock; pauses auto-commit during ingest/transcribe |
| `/tmp/vault-ingest-run.lock`          | flock; one ingest at a time                                |
| `/tmp/vault-lint-run.lock`            | flock; one lint at a time                                  |
| `/tmp/voice-transcribe.lock`          | flock; one transcribe run at a time                        |
| `~/.local/state/llm-wiki/*.log`       | ingest / lint / transcribe logs                            |
| `~/.local/state/llm-wiki/ledger.json` | sha256 transcription ledger (idempotency)                  |

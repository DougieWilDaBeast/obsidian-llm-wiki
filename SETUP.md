# SETUP.md — building the wiki from scratch

This guide takes you from an empty machine to a working agent-maintained wiki. Work through it
in order; each stage is useful on its own, so you can stop after the parts you want.

- **Stage 1 — Vault & git** (everyone): the Obsidian vault and version control.
- **Stage 2 — A model backend** (everyone): wiring an LLM into `INGEST_CMD`.
- **Stage 3 — Voice transcription** (optional): faster-whisper + ffmpeg.
- **Stage 4 — Sync transport** (optional): get captures from your phone to a server.
- **Stage 5 — Automation** (optional): systemd timers and/or the n8n file-watcher.

A companion list of the things that _will_ bite you is in
[`TROUBLESHOOTING.md`](TROUBLESHOOTING.md). Skim it before Stage 5.

---

## Prerequisites

| You need            | Why                             | Check               |
| ------------------- | ------------------------------- | ------------------- |
| git ≥ 2.30          | version control + sync backbone | `git --version`     |
| bash                | the pipeline scripts            | `bash --version`    |
| Obsidian            | editing/reading the vault       | —                   |
| Python ≥ 3.9        | voice transcription (Stage 3)   | `python3 --version` |
| ffmpeg              | audio denoise (Stage 3)         | `ffmpeg -version`   |
| Docker _(optional)_ | the n8n watcher (Stage 5)       | `docker --version`  |

> **Linux/macOS** are the primary targets (the scripts are bash and the timers are systemd).
> On **Windows**, run the server-side pieces under WSL2.

---

## Stage 1 — Vault & git

1. **Get the repo and copy the env template.**

   ```bash
   git clone https://github.com/<you>/obsidian-llm-wiki.git
   cd obsidian-llm-wiki
   cp .env.example .env
   ```

2. **Open it as an Obsidian vault.** In Obsidian: _Open folder as vault_ → pick this folder.
   Read [`CLAUDE.md`](CLAUDE.md) — it's the schema the agent follows and the file you'll edit
   to evolve the system.

3. **Decide what's real.** This repo ships with a **synthetic example vault** under `00-Raw/`
   and `10-Refined/`. When you're ready to use it for real, delete the example pages (keep the
   folder structure and the `.gitkeep` files) and start with your own `index.md` / `log.md`.

4. **Point git at your own remote.** Use a **private** remote for your real vault — your
   refined notes are personal.

   ```bash
   git remote set-url origin git@github.com:<you>/my-private-vault.git
   git push -u origin main
   ```

5. **Line endings.** The repo's `.gitattributes` forces `LF` so the shell scripts stay
   executable across machines. Leave it in place; the `CRLF will be replaced by LF` warnings
   on Windows are expected and harmless.

---

## Stage 2 — A model backend (`INGEST_CMD`)

The pipeline is **dormant** until you tell it how to call a model. `ingest_one.sh` runs:

```bash
"$INGEST_CMD" "<absolute path to the new raw file>"
```

…and `lint_pass.sh` runs `"$INGEST_CMD" LINT`. The backend is responsible for reading the file,
following the `CLAUDE.md` Ingest (or Lint) workflow, and **editing files in `10-Refined/`,
`index.md`, and `log.md`**. The script handles locking and the git commit; the model only edits.

You can use any agent that can read files and write changes in the working directory. Write a
tiny wrapper and point `INGEST_CMD` at it. For example a Claude Code wrapper:

```bash
# pipeline/ingest_backend.sh
#!/usr/bin/env bash
set -euo pipefail
TARGET="$1"   # either an absolute raw-file path, or the literal token LINT
if [ "$TARGET" = "LINT" ]; then
  PROMPT="Run the Lint workflow from CLAUDE.md across the whole vault."
else
  PROMPT="Ingest this new source per CLAUDE.md: $TARGET"
fi
# Run the agent headlessly in the repo root so it can edit files in place.
exec claude -p "$PROMPT" --permission-mode acceptEdits
```

```bash
chmod +x pipeline/ingest_backend.sh
# in .env:
#   INGEST_CMD=/absolute/path/to/obsidian-llm-wiki/pipeline/ingest_backend.sh
```

The same pattern works for an OpenAI/local-model script, the GitHub Copilot CLI, or any other
agent — just have the wrapper take one argument and edit files in the current repo.

**Prove it's safe before going further:**

```bash
bash pipeline/selftest_ingest.sh    # writes nothing, makes no commit
```

To do a first **manual** ingest of one file:

```bash
export $(grep -v '^#' .env | xargs)          # load .env into the shell
bash pipeline/ingest_one.sh 00-Raw/Inbox/<some-note>.md
```

> **Cost note:** transcription (Stage 3) is local and free; _ingest_ may cost API credits.
> They're deliberately separate steps so you control when the model runs.

---

## Stage 3 — Voice transcription (optional)

Local, free voice-to-text with [faster-whisper](https://github.com/SYSTRAN/faster-whisper).

1. **Create a venv and install deps.**

   ```bash
   python3 -m venv ~/voice-pipeline/venv
   source ~/voice-pipeline/venv/bin/activate
   pip install faster-whisper
   sudo apt-get install -y ffmpeg      # or your platform's package manager
   ```

2. **Backfill an existing archive** (inventory first — `--dry-run` writes nothing):

   ```bash
   python pipeline/backfill_transcribe.py --dry-run --sources "/path/to/recordings"
   python pipeline/backfill_transcribe.py --sources "/path/to/recordings"   # transcribe
   ```

   Transcripts land in `00-Raw/Voice/`; a sha256 ledger (under
   `~/.local/state/llm-wiki/ledger.json` by default) makes re-runs idempotent. Pick a model
   size with `--model` (`tiny`/`base`/`small`/…); `small` + `int8` on CPU is a good default.

3. **Transcribe new clips as they arrive** with `transcribe_new.sh` (scheduled in Stage 5). It
   reads these env vars (set them in `.env` / the systemd unit):
   - `AUDIO_STAGING` — folder new phone clips land in
   - `WHISPER_VENV` — path to the venv's `activate` script
   - `VAULT_ROOT` — the repo path

---

## Stage 4 — Sync transport (optional)

To capture on a phone and have a server do the work, you need two private channels:

- **Audio/files phone → server:** e.g. [SyncThing](https://syncthing.net). Sync your voice
  recordings folder and (optionally) the vault. **Exclude `.git`** from device sync — the
  server is the only machine that runs git (see `.stignore`).
- **A private network:** e.g. [Tailscale](https://tailscale.com) gives every device a stable
  private IP so the server and phone reach each other without exposing anything publicly. Put
  that server IP in `.env` as `SERVER_IP`.

> The **server is the single git authority.** Editing devices write Markdown; only the server
> commits/pushes (`vault_autocommit.sh`). This avoids merge chaos from multiple git clients.

---

## Stage 5 — Automation (optional)

### 5a. systemd user timers

Three optional timers live in `pipeline/systemd/`. They're written for the user manager
(`%h` = home) and assume the repo at `~/obsidian-llm-wiki` (edit the `Environment=VAULT_ROOT`
line if not).

```bash
mkdir -p ~/.config/systemd/user
cp pipeline/systemd/wiki-*.service pipeline/systemd/wiki-*.timer ~/.config/systemd/user/
systemctl --user daemon-reload

systemctl --user enable --now wiki-autocommit.timer   # commit+sync every 2 min
systemctl --user enable --now wiki-transcribe.timer   # transcribe new clips every 10 min
systemctl --user enable --now wiki-lint.timer         # weekly lint (Mon 04:00)

systemctl --user list-timers | grep wiki
# So timers fire while you're logged out:
loginctl enable-linger "$USER"
```

`wiki-lint` (and the ingest path) stay **dormant until `INGEST_CMD` is set** — enabling the
timer can't trigger a real model run before you're ready.

### 5b. n8n file-watcher (optional, instead of/alongside an inotify trigger)

`pipeline/n8n/` contains a Docker compose file and a workflow **template that ships disabled**.
It watches the mounted `00-Raw/` folders and, on a new file, SSHes back to the host to run
`ingest_one.sh`.

1. Fill in `SERVER_IP`, `N8N_PORT`, `VAULT_PATH`, `TZ` (via `.env` next to the compose file).
2. One-time, privileged: add yourself to the docker group —
   `sudo usermod -aG docker "$USER"`, then re-login.
3. Bring it up:

   ```bash
   docker compose -f pipeline/n8n/docker-compose.yml up -d
   docker compose -f pipeline/n8n/docker-compose.yml ps
   ```

4. Open `http://${SERVER_IP}:${N8N_PORT}`, create the owner account, and import
   `pipeline/n8n/vault-ingest.workflow.json`.
5. **Activation:** the container has no git/model, so the workflow SSHes to the host. Set up a
   container→host SSH key at `/home/node/.ssh/wiki_ingest`, replace the `SERVER_USER` /
   `SERVER_IP` / `VAULT_PATH` placeholders in the Execute Command node, enable the (disabled)
   trigger nodes, and activate the workflow.

> See [`TROUBLESHOOTING.md`](TROUBLESHOOTING.md) for the n8n secure-cookie gotcha and the
> `localFileTrigger`/`executeCommand` node-sandboxing caveat.

---

## Verification checklist

- [ ] `bash pipeline/selftest_ingest.sh` prints all PASS and leaves the tree clean.
- [ ] A manual `ingest_one.sh` on a test note produces a sensible Refined page + a single
      commit.
- [ ] `git log` on your real vault is in a **private** repo.
- [ ] `systemctl --user list-timers | grep wiki` shows your enabled timers.
- [ ] (n8n) dropping a file in a watched folder triggers an execution in the n8n UI.

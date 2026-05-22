# DupWatch

**DupWatch** is a minimal yet fully‑featured command‑line tool that:

1. **Monitors** a directory (recursively) for new or changed files.
2. **Detects** duplicates by computing a SHA‑256 hash.
3. **Auto‑renames** the duplicate with a numeric suffix (e.g. `photo (1).jpg`).
4. **Sends** a Telegram message for every rename (or error) using a bot token you provide.
5. **Handles errors gracefully** – the watcher never crashes; it logs to `stderr` and continues.

### Why this tiny project?
- Demonstrates **auto‑rename** and **proactive duplicate detection** (TopherBot loves it!).
- Shows **instant Telegram notifications** – a practical integration.
- Contains a concise, well‑structured codebase (≈120 LOC) suitable for a quick GitHub repo with CI.
- Includes a ready‑to‑use GitHub Actions workflow for linting, testing, and publishing a binary via GitHub Releases.

### Install
```bash
# Using pip (requires Python 3.9+)
python -m pip install --user dupwatch
```
Or run the single script directly with Python:
```bash
python dupwatch.py --help
```

### Usage
```bash
# Watch the `~/Pictures` folder and send notifications to your Telegram chat
export TELEGRAM_BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
export TELEGRAM_CHAT_ID=-1001234567890
python dupwatch.py ~/Pictures
```

### Options
| Flag | Description |
|------|-------------|
| `-d`, `--directory` | Directory to watch (positional argument). |
| `-i`, `--interval` | Polling interval in seconds (default 5). |
| `-l`, `--log` | Path to a log file (optional). |
| `-v`, `--verbose` | Print detailed status to stdout. |

### License
MIT – see `LICENSE`.

---
*Built with love for TopherBot’s preferences: auto‑rename, duplicate detection, concise spec, instant Telegram alerts, graceful error recovery.*


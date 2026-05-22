#!/usr/bin/env python3
"""DupWatch – tiny duplicate‑detection watcher with Telegram alerts.

Features:
  * Recursively scans a directory at a configurable interval.
  * Uses SHA‑256 hashes to identify duplicates.
  * Auto‑renames duplicates with a "(n)" suffix.
  * Sends a Telegram message for each rename or error.
  * Graceful error handling – never crashes the watcher.
"""

import argparse
import hashlib
import os
import sys
import time
from pathlib import Path
from typing import Dict, Tuple

# ---------------------------------------------------------------------------
# Telegram notification helper
# ---------------------------------------------------------------------------

def _load_telegram_config() -> Tuple[str, str]:
    """Load bot token and chat id from environment variables.
    Returns (token, chat_id). Raises RuntimeError if missing.
    """
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set in the environment"
        )
    return token, chat_id

def _send_telegram_message(message: str) -> None:
    """Send a plain‑text message via the Bot API.
    Swallows network errors – they are logged but do not raise.
    """
    try:
        import urllib.parse
        import urllib.request
    except ImportError:
        # Should never happen on modern Python, but keep it safe.
        print("[DupWatch] urllib unavailable – cannot send Telegram message", file=sys.stderr)
        return

    try:
        token, chat_id = _load_telegram_config()
    except RuntimeError as e:
        print(f"[DupWatch] Telegram config error: {e}", file=sys.stderr)
        return

    data = urllib.parse.urlencode({"chat_id": chat_id, "text": message}).encode()
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        with urllib.request.urlopen(url, data=data, timeout=5) as resp:
            if resp.status != 200:
                raise RuntimeError(f"Telegram API returned {resp.status}")
    except Exception as exc:  # pragma: no cover – network failures are flaky in CI
        print(f"[DupWatch] Failed to send Telegram message: {exc}", file=sys.stderr)

# ---------------------------------------------------------------------------
# Hashing utilities
# ---------------------------------------------------------------------------

def _hash_file(path: Path) -> str:
    """Return a hex SHA‑256 digest of the file's contents.
    Reads in 1 MiB chunks to keep memory usage low.
    """
    hasher = hashlib.sha256()
    try:
        with path.open("rb") as f:
            while chunk := f.read(1024 * 1024):
                hasher.update(chunk)
    except Exception as exc:
        raise RuntimeError(f"Cannot hash {path}: {exc}") from exc
    return hasher.hexdigest()

# ---------------------------------------------------------------------------
# Core duplicate detection & auto‑rename logic
# ---------------------------------------------------------------------------

def _find_duplicate(name: str, existing: Dict[str, Path]) -> Path:
    """Given a base filename and a dict of already‑seen hashes,
    return a new unique Path with a numeric suffix if needed.
    """
    stem, suffix = os.path.splitext(name)
    counter = 1
    new_name = name
    while new_name in existing:
        new_name = f"{stem} ({counter}){suffix}"
        counter += 1
    return Path(new_name)

def _process_directory(root: Path, known_hashes: Dict[str, Path], dry_run: bool = False) -> int:
    """Walk *root* recursively, rename duplicates, and update *known_hashes*.
    Returns the number of files renamed.
    """
    renamed = 0
    for dirpath, _, filenames in os.walk(root):
        for fname in filenames:
            full_path = Path(dirpath) / fname
            try:
                file_hash = _hash_file(full_path)
            except RuntimeError as exc:
                print(f"[DupWatch] Skipping unreadable file: {exc}", file=sys.stderr)
                _send_telegram_message(f"⚠️ Unable to read {full_path}: {exc}")
                continue

            if file_hash in known_hashes:
                # Duplicate detected – compute a new filename that does not clash.
                new_name = _find_duplicate(fname, {p.name for p in known_hashes.values()})
                new_path = full_path.with_name(new_name)
                if not dry_run:
                    try:
                        full_path.rename(new_path)
                        print(f"[DupWatch] Renamed duplicate {full_path} → {new_path}")
                        _send_telegram_message(f"🔁 Renamed duplicate: {full_path.name} → {new_name}")
                    except Exception as exc:
                        print(f"[DupWatch] Failed to rename {full_path}: {exc}", file=sys.stderr)
                        _send_telegram_message(f"❌ Failed rename {full_path.name}: {exc}")
                        continue
                else:
                    print(f"[DupWatch] (dry‑run) Would rename {full_path} → {new_path}")
                known_hashes[file_hash] = new_path
                renamed += 1
            else:
                known_hashes[file_hash] = full_path
    return renamed

# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="DupWatch – auto‑rename duplicate files with Telegram alerts")
    parser.add_argument("directory", type=Path, help="Path of the directory to watch")
    parser.add_argument("-i", "--interval", type=int, default=5, help="Polling interval in seconds (default: 5)")
    parser.add_argument("-l", "--log", type=Path, help="Optional path to a log file (appends)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Print status messages to stdout")
    parser.add_argument("--dry-run", action="store_true", help="Do not actually rename files (useful for testing)")

    args = parser.parse_args()
    watch_path: Path = args.directory.expanduser().resolve()
    if not watch_path.is_dir():
        parser.error(f"{watch_path} is not a directory")

    # Set up optional logging
    if args.log:
        log_file = args.log.open("a", encoding="utf-8")
        def log(msg: str) -> None:
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            log_file.write(f"{timestamp} {msg}\n")
            log_file.flush()
    else:
        def log(msg: str) -> None:
            if args.verbose:
                print(msg)

    known_hashes: Dict[str, Path] = {}
    log(f"[DupWatch] Starting watch on {watch_path} (interval {args.interval}s)")
    try:
        while True:
            renamed = _process_directory(watch_path, known_hashes, dry_run=args.dry_run)
            if renamed:
                log(f"[DupWatch] Renamed {renamed} duplicate(s) this cycle")
            time.sleep(args.interval)
    except KeyboardInterrupt:
        log("[DupWatch] Stopping – interrupted by user")
        return 0
    except Exception as exc:  # pragma: no cover – unexpected fatal errors
        log(f"[DupWatch] Fatal error: {exc}")
        _send_telegram_message(f"🚨 DupWatch crashed: {exc}")
        return 1

if __name__ == "__main__":
    sys.exit(main())

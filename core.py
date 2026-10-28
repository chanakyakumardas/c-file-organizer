"""Chanakya's File Organizer: Core"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

EXT_MAP = {
    ".jpg": "JPG", ".jpeg": "JPG", ".png": "PNG",
    ".pdf": "PDF",
    ".doc": "DOCX", ".docx": "DOCX",
    ".xls": "EXCEL", ".xlsx": "EXCEL",
}

MONTHS = {
    1: "JANUARY", 2: "FEBRUARY", 3: "MARCH", 4: "APRIL",
    5: "MAY", 6: "JUNE", 7: "JULY", 8: "AUGUST",
    9: "SEPTEMBER", 10: "OCTOBER", 11: "NOVEMBER", 12: "DECEMBER",
}

LogFn = Callable[[str, str], None]


@dataclass
class Stats:
    total: int = 0
    moved: int = 0
    skipped: int = 0
    errors: int = 0


def unique_path(dest_dir: Path, base: str, ext: str) -> Path:
    candidate = dest_dir / f"{base}{ext}"
    i = 1
    while candidate.exists():
        candidate = dest_dir / f"{base}-{i}{ext}"
        i += 1
    return candidate


def organize(src_folder: str, target_root: str, log: Optional[LogFn] = None) -> Stats:
    log = log or (lambda kind, text: None)
    src, root = Path(src_folder), Path(target_root)

    if not src.is_dir():
        raise NotADirectoryError(f"Source folder not found: {src}")

    stats = Stats()
    for entry in sorted(src.iterdir()):
        stats.total += 1

        if not entry.is_file():
            log("skip", entry.name)
            stats.skipped += 1
            continue

        ext = entry.suffix.lower()
        if ext not in EXT_MAP:
            log("skip", f"{entry.name}  (Unsupported)")
            stats.skipped += 1
            continue

        kind = EXT_MAP[ext]
        try:
            dt = datetime.fromtimestamp(entry.stat().st_mtime)
            new_base = dt.strftime("%Y-%m-%d_%H-%M-%S")
            log("rename", f"{entry.name}  →  {new_base}{ext}")

            dest_dir = root / str(dt.year) / MONTHS[dt.month] / kind
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest = unique_path(dest_dir, new_base, ext)
            shutil.move(str(entry), str(dest))

            log("moved", str(dest.relative_to(root)))
            stats.moved += 1
        except Exception as e:
            log("error", f"{entry.name}  {e}")
            stats.errors += 1

    return stats

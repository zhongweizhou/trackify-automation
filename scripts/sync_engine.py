"""Sync Excel test cases ↔ .feature files. PoC for Task 14 (Day 5+).

Usage:
    python scripts/sync_engine.py              # one-shot diff + apply
    python scripts/sync_engine.py --dry-run    # print diff without writing
    python scripts/sync_engine.py --watch      # auto-trigger on xlsx mtime change

Contract: see TECHNICAL_SPEC.md §11 and docs/SCALING.md Q6.
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
import time
from datetime import date
from pathlib import Path

import openpyxl

ROOT = Path(__file__).parent.parent
EXCEL = ROOT / "data" / "test_cases.xlsx"
FEATURE_DIR = ROOT / "tests" / "features"
BACKUP_DIR = ROOT / "data" / ".backup"
SID_RE = re.compile(r"#\s*scenario_id:\s*(\S+)")
BLOCK_RE = re.compile(r"(#\s*scenario_id:\s*(\S+)\b[\s\S]*?)(?=\n#\s*scenario_id:|\Z)")


def parse_excel(path: Path) -> list[dict]:
    """Read xlsx; return rows with Automation Status == 'automated'."""
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb.active
    headers = [c.value for c in ws[1]]
    out = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if not row[0]:
            continue
        d = dict(zip(headers, row))
        if d.get("Automation Status") != "automated":
            continue
        steps = (d.get("Test Steps") or "").replace("\n", "\n    ")
        then = (d.get("Expected Result") or "").replace("\n", "\n    ")
        gherkin = f"  Given {d.get('Pre-conditions', '')}\n    When {steps}\n    Then {then}"
        out.append({
            "id": d["Test Case ID"],
            "module": d.get("Module", ""),
            "title": d["Scenario Title"],
            "tags": d.get("Tags") or "",
            "gherkin": gherkin,
        })
    return out


def parse_feature(path: Path) -> tuple[dict[str, tuple[int, int]], str]:
    """Return {scenario_id: (start, end)} and the raw text."""
    text = path.read_text()
    spans = {m.group(2): m.span() for m in BLOCK_RE.finditer(text)}
    return spans, text


def diff(excel_rows: list[dict], feat_spans: dict, feat_text: str) -> tuple[list, list, list, list]:
    """Return (added, modified, deleted, untouched) — all keyed by scenario_id.

    `modified` requires the rendered .feature block to differ from what Excel would produce.
    """
    excel_by_id = {r["id"]: r for r in excel_rows}
    excel_ids = {r["id"] for r in excel_rows}
    added = [r for r in excel_rows if r["id"] not in feat_spans]
    deleted = [sid for sid in feat_spans if sid not in excel_ids]
    modified, untouched = [], []
    for r in excel_rows:
        if r["id"] not in feat_spans:
            continue
        existing = feat_text[feat_spans[r["id"]][0]: feat_spans[r["id"]][1]].strip()
        new_block = f"# scenario_id: {r['id']}\n@{r['tags']}\nScenario: {r['title']}\n{r['gherkin']}".strip()
        if existing != new_block:
            modified.append(r)
        else:
            untouched.append(r["id"])
    return added, modified, deleted, sorted(untouched)


def apply(path: Path, text: str, spans: dict, rows: list[dict]) -> str:
    """Rewrite .feature with given rows replacing existing blocks. Untouched = byte-identical.

    `rows` includes both modified and added. Added rows (not in spans) get appended.
    """
    BACKUP_DIR.mkdir(exist_ok=True)
    backup = BACKUP_DIR / f"{path.name}.{date.today()}.bak"
    if not backup.exists():
        shutil.copy(path, backup)
    row_by_id = {r["id"]: r for r in rows}
    # Replace modified blocks in reverse offset order so byte positions stay valid
    for sid in sorted(spans, key=lambda s: spans[s][0], reverse=True):
        if sid in row_by_id:
            r = row_by_id[sid]
            new_block = f"# scenario_id: {sid}\n@{r['tags']}\nScenario: {r['title']}\n{r['gherkin']}\n"
            text = text[: spans[sid][0]] + new_block + text[spans[sid][1]:]
    # Append added blocks (anything in rows whose id is not in spans)
    added_blocks = [
        f"# scenario_id: {r['id']}\n@{r['tags']}\nScenario: {r['title']}\n{r['gherkin']}\n"
        for r in rows if r["id"] not in spans
    ]
    if added_blocks:
        text = text.rstrip() + "\n\n" + "\n\n".join(added_blocks) + "\n"
    return text


def run(dry_run: bool = False) -> int:
    if not EXCEL.exists():
        print(f"ERR: Excel not found: {EXCEL}", file=sys.stderr)
        return 1
    excel_rows = parse_excel(EXCEL)
    print(f"Excel: {len(excel_rows)} automated rows")
    if not FEATURE_DIR.exists():
        print(f"ERR: feature dir missing: {FEATURE_DIR}", file=sys.stderr)
        return 1
    total = {"added": 0, "modified": 0, "deleted": 0, "untouched": 0}
    for feat in sorted(FEATURE_DIR.glob("*.feature")):
        spans, text = parse_feature(feat)
        added, modified, deleted, untouched = diff(excel_rows, spans, text)
        flag = "[DRY]" if dry_run else "[APPLY]"
        print(f"  {flag} {feat.name}: +{len(added)} ~{len(modified)} -{len(deleted)} ={len(untouched)}")
        total["added"] += len(added); total["modified"] += len(modified)
        total["deleted"] += len(deleted); total["untouched"] += len(untouched)
        if not dry_run and (added or modified):
            new_text = apply(feat, text, spans, modified + added)
            (feat).write_text(new_text)
    print(f"TOTAL: +{total['added']} ~{total['modified']} -{total['deleted']} ={total['untouched']}")
    return 0


def watch() -> int:
    """Poll-based watcher. PoC: 5s loop, re-runs on mtime change."""
    print(f"Watching {EXCEL} (Ctrl-C to stop)...")
    last = EXCEL.stat().st_mtime if EXCEL.exists() else 0
    while True:
        time.sleep(5)
        if EXCEL.exists() and EXCEL.stat().st_mtime != last:
            last = EXCEL.stat().st_mtime
            print(f"\n--- Detected change @ {time.strftime('%H:%M:%S')} ---")
            run()


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--watch", action="store_true")
    args = p.parse_args()
    sys.exit(watch() if args.watch else run(dry_run=args.dry_run))
#!/usr/bin/env python3
"""
Stop Hook: セッション終了時にサマリを書き出す
output/generated/ 配下の最新パックの状態をログに記録する。
"""
import json
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output" / "generated"
LOG_FILE = PROJECT_ROOT / "output" / "session_log.jsonl"


def main():
    # 最新のパックを探す
    packs = []
    if OUTPUT_DIR.exists():
        for d in OUTPUT_DIR.iterdir():
            if d.is_dir():
                manifest = d / "_manifest.json"
                if manifest.exists():
                    try:
                        data = json.loads(manifest.read_text(encoding="utf-8"))
                        packs.append({
                            "dir": d.name,
                            "clinic": data.get("clinic_name", "?"),
                            "files": data.get("files", []),
                            "generated_at": data.get("generated_at", "?"),
                        })
                    except json.JSONDecodeError:
                        pass

    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "event": "session_stop",
        "packs_found": len(packs),
        "packs": packs,
    }

    # JSONL追記
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

    print(f"Session log updated: {LOG_FILE}")


if __name__ == "__main__":
    main()

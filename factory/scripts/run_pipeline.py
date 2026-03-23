#!/usr/bin/env python3
"""
Product Factory Pipeline Runner v0.1
=====================================
4本のスクリプトを順番実行するラッパー。
n8n から Execute Command 1本で呼べる。

使い方:
    python factory/scripts/run_pipeline.py --input factory/forms/sheets_row_example.json
    python factory/scripts/run_pipeline.py --input row.json --slug tanaka_dental
    python factory/scripts/run_pipeline.py --input row.json --slug tanaka_dental --llm
"""

import argparse
import io
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Windows cp932 対策
if sys.stdout.encoding and sys.stdout.encoding.lower().startswith("cp"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "factory" / "scripts"


def run_step(step_num: int, label: str, cmd: list[str]) -> dict:
    """1ステップを実行し、結果を返す。"""
    print(f"[{step_num}/4] {label}...")
    print(f"       cmd: {' '.join(cmd)}")

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
        encoding="utf-8",
        errors="replace",
        env={**__import__("os").environ, "PYTHONIOENCODING": "utf-8"},
    )

    if result.stdout.strip():
        for line in result.stdout.strip().split("\n")[-5:]:
            print(f"       {line}")

    status = "OK" if result.returncode == 0 else "FAIL"
    print(f"       → {status} (exit={result.returncode})")

    return {
        "step": step_num,
        "label": label,
        "exitCode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "status": status,
    }


def main():
    parser = argparse.ArgumentParser(description="Product Factory Pipeline Runner")
    parser.add_argument("--input", type=Path, required=True, help="入力row JSON")
    parser.add_argument("--slug", type=str, default=None, help="出力ディレクトリ名")
    parser.add_argument("--llm", action="store_true", help="LLMモードを有効にする")
    args = parser.parse_args()

    python = sys.executable
    input_path = args.input.resolve()

    if not input_path.exists():
        print(f"ERROR: 入力ファイルが見つかりません: {input_path}")
        sys.exit(1)

    # slug を決める（未指定なら入力ファイル名から）
    slug = args.slug or input_path.stem.replace(" ", "_")[:30]

    # 中間・出力パス
    normalized_json = PROJECT_ROOT / "factory" / "forms" / f"response_{slug}.json"
    profile_yaml = f"factory/input/{slug}.yaml"
    output_dir = f"output/generated/{slug}"

    print()
    print("=" * 55)
    print("  Product Factory Pipeline Runner v0.1")
    print("=" * 55)
    print(f"  入力:   {input_path}")
    print(f"  slug:   {slug}")
    print(f"  LLM:    {'ON' if args.llm else 'OFF (template)'}")
    print(f"  出力先: {output_dir}")
    print("=" * 55)
    print()

    results = []

    # --- [1] Normalize ---
    r = run_step(1, "Normalize Sheet Row", [
        python, str(SCRIPTS_DIR / "normalize_sheet_row.py"),
        "--input", str(input_path),
        "--output", str(normalized_json),
    ])
    results.append(r)
    if r["exitCode"] != 0:
        print("\n❌ Normalize で失敗。パイプライン中断。")
        write_summary(slug, output_dir, results, "FAIL")
        sys.exit(1)
    print()

    # --- [2] Create Profile ---
    r = run_step(2, "Create Profile", [
        python, str(SCRIPTS_DIR / "create_clinic_profile.py"),
        "--from-form", str(normalized_json),
        "--output", str(PROJECT_ROOT / profile_yaml),
    ])
    results.append(r)
    if r["exitCode"] != 0:
        print("\n❌ Create Profile で失敗。パイプライン中断。")
        write_summary(slug, output_dir, results, "FAIL")
        sys.exit(1)
    print()

    # --- [3] Generate Pack ---
    gen_cmd = [
        python, str(SCRIPTS_DIR / "generate_pack.py"),
        "--profile", profile_yaml,
        "--output", output_dir,
    ]
    if args.llm:
        gen_cmd.extend(["--llm", "faq", "review", "recruiting"])

    r = run_step(3, "Generate Pack", gen_cmd)
    results.append(r)
    if r["exitCode"] != 0:
        print("\n❌ Generate Pack で失敗。パイプライン中断。")
        write_summary(slug, output_dir, results, "FAIL")
        sys.exit(1)
    print()

    # --- [4] Validate Pack ---
    r = run_step(4, "Validate Pack", [
        python, str(SCRIPTS_DIR / "validate_pack.py"),
        "--pack", output_dir,
    ])
    results.append(r)
    print()

    # --- 最終判定 ---
    final_status = "PASS" if r["exitCode"] == 0 else "FAIL"
    write_summary(slug, output_dir, results, final_status)

    print("=" * 55)
    if final_status == "PASS":
        print(f"  ✅ PASS — {slug}")
    else:
        print(f"  ❌ FAIL — {slug}")
    print(f"  出力先: {output_dir}")
    print("=" * 55)

    sys.exit(0 if final_status == "PASS" else 1)


def write_summary(slug: str, output_dir: str, results: list[dict], status: str):
    """パイプライン実行サマリをJSONで書き出す。"""
    summary = {
        "timestamp": datetime.now().isoformat(),
        "slug": slug,
        "status": status,
        "steps": [
            {"step": r["step"], "label": r["label"], "status": r["status"], "exitCode": r["exitCode"]}
            for r in results
        ],
    }
    out_path = PROJECT_ROOT / output_dir
    out_path.mkdir(parents=True, exist_ok=True)
    summary_path = out_path / "_pipeline_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  サマリ: {summary_path}")


if __name__ == "__main__":
    main()

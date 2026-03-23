#!/usr/bin/env python3
"""
Product Factory v0.1 - Pack Validator
======================================
生成されたパック（4つのmd + manifest）を検証する。

使い方:
    python factory/scripts/validate_pack.py
    python factory/scripts/validate_pack.py --pack output/generated/sample_clinic
"""

import argparse
import io
import json
import sys
from pathlib import Path

# Windows cp932 でのUnicodeEncodeError を回避
if sys.stdout.encoding and sys.stdout.encoding.lower().startswith("cp"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_PACK = PROJECT_ROOT / "output" / "generated" / "sample_clinic"

EXPECTED_FILES = ["faq.md", "review_reply.md", "recruiting.md", "sales_onepager.md"]

# 各ファイルの最低限の品質基準
QUALITY_RULES = {
    "faq.md": {
        "min_lines": 30,
        "must_contain": ["Q1.", "回答"],
        "label": "FAQ",
    },
    "review_reply.md": {
        "min_lines": 20,
        "must_contain": ["返信例", "想定口コミ"],
        "label": "口コミ返信",
    },
    "recruiting.md": {
        "min_lines": 15,
        "must_contain": ["募集", "メリット"],
        "label": "求人文",
    },
    "sales_onepager.md": {
        "min_lines": 15,
        "must_contain": ["テンプレート", "導入ステップ"],
        "label": "Sales Onepager",
    },
}


def validate_pack(pack_dir: Path) -> list[dict]:
    """パックを検証し、結果リストを返す"""
    results = []

    # 1. ディレクトリ存在チェック
    if not pack_dir.exists():
        results.append({
            "check": "directory_exists",
            "status": "FAIL",
            "message": f"出力ディレクトリが存在しません: {pack_dir}",
        })
        return results

    results.append({
        "check": "directory_exists",
        "status": "PASS",
        "message": f"出力ディレクトリ: {pack_dir}",
    })

    # 2. 必須ファイル存在チェック
    for filename in EXPECTED_FILES:
        filepath = pack_dir / filename
        if filepath.exists():
            results.append({
                "check": f"file_exists:{filename}",
                "status": "PASS",
                "message": f"{filename} が存在",
            })
        else:
            results.append({
                "check": f"file_exists:{filename}",
                "status": "FAIL",
                "message": f"{filename} が見つかりません",
            })

    # 3. マニフェストチェック
    manifest_path = pack_dir / "_manifest.json"
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            results.append({
                "check": "manifest_valid",
                "status": "PASS",
                "message": f"マニフェスト: {manifest.get('clinic_name', '?')} / {manifest.get('generated_at', '?')}",
            })
        except json.JSONDecodeError:
            results.append({
                "check": "manifest_valid",
                "status": "FAIL",
                "message": "マニフェストのJSON解析に失敗",
            })
    else:
        results.append({
            "check": "manifest_valid",
            "status": "WARN",
            "message": "_manifest.json が見つかりません（旧バージョンで生成？）",
        })

    # 4. 品質チェック
    for filename, rules in QUALITY_RULES.items():
        filepath = pack_dir / filename
        if not filepath.exists():
            continue

        content = filepath.read_text(encoding="utf-8")
        lines = content.strip().split("\n")
        label = rules["label"]

        # 行数チェック
        if len(lines) < rules["min_lines"]:
            results.append({
                "check": f"quality:{filename}:lines",
                "status": "WARN",
                "message": f"{label}: {len(lines)}行（最低 {rules['min_lines']}行 推奨）",
            })
        else:
            results.append({
                "check": f"quality:{filename}:lines",
                "status": "PASS",
                "message": f"{label}: {len(lines)}行",
            })

        # 必須キーワードチェック
        for keyword in rules["must_contain"]:
            if keyword in content:
                results.append({
                    "check": f"quality:{filename}:keyword:{keyword}",
                    "status": "PASS",
                    "message": f"{label}: 「{keyword}」を含む",
                })
            else:
                results.append({
                    "check": f"quality:{filename}:keyword:{keyword}",
                    "status": "WARN",
                    "message": f"{label}: 「{keyword}」が見つかりません",
                })

        # 空の置換変数チェック（{xxx} が残っていないか）
        import re
        unresolved = re.findall(r"\{[a-z_]+\}", content)
        if unresolved:
            results.append({
                "check": f"quality:{filename}:unresolved",
                "status": "FAIL",
                "message": f"{label}: 未解決の変数: {', '.join(set(unresolved))}",
            })
        else:
            results.append({
                "check": f"quality:{filename}:unresolved",
                "status": "PASS",
                "message": f"{label}: 未解決変数なし",
            })

    # 5. 追加品質チェック
    # 5a. FAQ: 重複文チェック
    faq_path = pack_dir / "faq.md"
    if faq_path.exists():
        faq_text = faq_path.read_text(encoding="utf-8")
        # 同じフレーズが2回以上連続する破綻パターン
        import re
        dup_pattern = re.findall(r"(\S{4,})\1", faq_text)
        if dup_pattern:
            results.append({
                "check": "quality:faq.md:duplicate_phrases",
                "status": "WARN",
                "message": f"FAQ: 重複フレーズの可能性: {dup_pattern[:3]}",
            })
        else:
            results.append({
                "check": "quality:faq.md:duplicate_phrases",
                "status": "PASS",
                "message": "FAQ: 重複フレーズなし",
            })

    # 5b. recruiting.md: 3職種チェック
    rec_path = pack_dir / "recruiting.md"
    if rec_path.exists():
        rec_text = rec_path.read_text(encoding="utf-8")
        template_count = len(re.findall(r"## テンプレ \d+", rec_text))
        if template_count >= 3:
            results.append({
                "check": "quality:recruiting.md:3positions",
                "status": "PASS",
                "message": f"求人文: {template_count}職種構成",
            })
        else:
            results.append({
                "check": "quality:recruiting.md:3positions",
                "status": "WARN",
                "message": f"求人文: {template_count}職種のみ（3職種推奨）",
            })

        # 空の箇条書きチェック（"- " だけの行）
        empty_bullets = len(re.findall(r"^- \s*$", rec_text, re.MULTILINE))
        if empty_bullets > 0:
            results.append({
                "check": "quality:recruiting.md:empty_bullets",
                "status": "WARN",
                "message": f"求人文: 空の箇条書きが{empty_bullets}件あります",
            })
        else:
            results.append({
                "check": "quality:recruiting.md:empty_bullets",
                "status": "PASS",
                "message": "求人文: 空の箇条書きなし",
            })

        # 「求める人物像」セクションの有無
        if "求める人物像" in rec_text:
            results.append({
                "check": "quality:recruiting.md:personas",
                "status": "PASS",
                "message": "求人文: 「求める人物像」セクションあり",
            })
        else:
            results.append({
                "check": "quality:recruiting.md:personas",
                "status": "WARN",
                "message": "求人文: 「求める人物像」セクションが見つかりません",
            })

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Product Factory v0.1 - パック検証ツール"
    )
    parser.add_argument(
        "--pack",
        type=Path,
        default=DEFAULT_PACK,
        help="検証する出力ディレクトリ",
    )
    args = parser.parse_args()

    print(f"Pack Validator v0.1")
    print(f"対象: {args.pack}")
    print("=" * 50)

    results = validate_pack(args.pack)

    # 表示
    pass_count = 0
    warn_count = 0
    fail_count = 0

    for r in results:
        icon = {"PASS": "✅", "WARN": "⚠️", "FAIL": "❌"}.get(r["status"], "?")
        print(f"  {icon} [{r['status']}] {r['message']}")
        if r["status"] == "PASS":
            pass_count += 1
        elif r["status"] == "WARN":
            warn_count += 1
        else:
            fail_count += 1

    print()
    print("=" * 50)
    print(f"結果: ✅ {pass_count} PASS / ⚠️ {warn_count} WARN / ❌ {fail_count} FAIL")

    if fail_count > 0:
        print("→ FAILあり。再生成を推奨します。")
        return 1
    elif warn_count > 0:
        print("→ 軽微な警告あり。確認を推奨します。")
        return 0
    else:
        print("→ すべてPASS。パックは正常です。")
        return 0


if __name__ == "__main__":
    sys.exit(main())

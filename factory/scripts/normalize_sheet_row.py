#!/usr/bin/env python3
"""
Sheets Row Adapter v0.1
========================
Google Sheets の1行相当JSONを、既存の --from-form 用JSON形式に正規化する。

使い方:
    python factory/scripts/normalize_sheet_row.py --input factory/forms/sheets_row_example.json
    python factory/scripts/normalize_sheet_row.py --input row.json --output normalized.json
"""

import argparse
import io
import json
import sys
from pathlib import Path

# Windows cp932 対策
if sys.stdout.encoding and sys.stdout.encoding.lower().startswith("cp"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_OUTPUT = PROJECT_ROOT / "factory" / "forms" / "form_response_from_sheet.json"

# ---------------------------------------------------------------------------
# 列名ゆれ吸収マッピング
# ---------------------------------------------------------------------------
# 出力キー → 認識する列名パターンのリスト（先頭一致 or 完全一致）
COLUMN_ALIASES: dict[str, list[str]] = {
    "clinic_name": [
        "clinic_name", "医院名", "Q1_医院名", "Q1", "クリニック名",
        "院名", "歯科医院名",
    ],
    "target_type": [
        "target_type", "医院のタイプ", "Q2_医院のタイプ", "Q2",
        "医院タイプ", "種別", "医院の種別",
    ],
    "services": [
        "services", "診療内容", "Q3_診療内容", "Q3",
        "診療科目", "提供サービス",
    ],
    "features": [
        "features", "特徴", "Q4_特徴", "Q4",
        "医院の特徴", "強み", "アピールポイント",
    ],
    "booking_system": [
        "booking_system", "予約方法", "Q5_予約方法", "Q5",
        "予約システム", "予約手段",
    ],
    "cancel_policy": [
        "cancel_policy", "キャンセルポリシー", "Q6_キャンセルポリシー", "Q6",
        "キャンセル規定",
    ],
    "insurance": [
        "insurance", "保険診療", "Q7_保険診療", "Q7",
        "保険対応",
    ],
    "self_pay_options": [
        "self_pay_options", "自費支払い方法", "Q8_自費支払い方法", "Q8",
        "自費お支払い方法", "支払い方法", "自費決済",
    ],
    "hiring_positions": [
        "hiring_positions", "募集職種", "Q9_募集職種", "Q9",
        "採用職種", "求人職種",
    ],
    "hiring_details": [
        "hiring_details", "採用詳細", "Q10_採用詳細", "Q10",
        "採用条件", "求人詳細",
    ],
    "tone": [
        "tone", "トーン", "Q11_トーン", "Q11",
        "文体", "文章のトーン",
    ],
    "notes": [
        "notes", "その他メモ", "Q12_その他メモ", "Q12",
        "備考", "メモ", "その他",
    ],
}

# 無視する列（マッピング不要）
IGNORED_COLUMNS = {"タイムスタンプ", "timestamp", "Timestamp", "メールアドレス", "email"}


def resolve_column(col_name: str) -> str | None:
    """列名を出力キーに解決する。一致しなければ None。"""
    col_clean = col_name.strip()

    # 完全一致を先に試す（優先度高）
    for target_key, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if col_clean == alias:
                return target_key

    # 前方一致（aliasの後ろが区切り文字 or 末尾であることを確認）
    # "Q1" が "Q10" にマッチしないよう、alias直後が _ / 空白 / 末尾であることをチェック
    for target_key, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if col_clean.startswith(alias) and len(col_clean) > len(alias):
                next_char = col_clean[len(alias)]
                if next_char in ("_", " ", ".", ":", "：", "（", "("):
                    return target_key

    return None


def parse_csv_value(value) -> list[str]:
    """カンマ区切り文字列 or 配列 → リストに正規化。"""
    if isinstance(value, list):
        return [v.strip() for v in value if str(v).strip()]
    if isinstance(value, str):
        return [v.strip() for v in value.split(",") if v.strip()]
    return []


def normalize_sheet_row(data: dict) -> tuple[dict, list[str]]:
    """
    Sheets行JSONを form_response JSON に正規化する。
    Returns: (normalized_dict, warnings)
    """
    warnings = []
    result = {}
    used_columns = set()

    for col_name, value in data.items():
        # 無視する列
        if col_name.strip() in IGNORED_COLUMNS:
            used_columns.add(col_name)
            continue

        target_key = resolve_column(col_name)
        if target_key is None:
            warnings.append(f"不明な列をスキップ: 「{col_name}」")
            continue

        used_columns.add(col_name)

        # リスト型の項目
        if target_key in ("services", "features", "self_pay_options", "hiring_positions"):
            result[target_key] = parse_csv_value(value)
        else:
            # スカラー値
            result[target_key] = str(value).strip() if value is not None else ""

    # 必須チェック
    for required in ("clinic_name", "services", "features"):
        val = result.get(required)
        if not val or (isinstance(val, list) and len(val) == 0):
            warnings.append(f"必須項目が空: {required}")

    return result, warnings


def main():
    parser = argparse.ArgumentParser(
        description="Sheets Row Adapter v0.1 - Sheets行JSONをform_response形式に正規化"
    )
    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        metavar="JSON_PATH",
        help="Google Sheets 1行相当のJSONファイル",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="正規化後の出力先JSONパス",
    )
    args = parser.parse_args()

    # 読み込み
    print(f"[1/3] Sheets行JSON読み込み: {args.input}")
    if not args.input.exists():
        print(f"ERROR: ファイルが見つかりません: {args.input}")
        return 1

    try:
        with open(args.input, "r", encoding="utf-8-sig") as f:
            raw_data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"ERROR: JSONの解析に失敗: {e}")
        return 1

    print(f"       列数: {len(raw_data)}")

    # 正規化
    print("[2/3] 正規化中...")
    result, warnings = normalize_sheet_row(raw_data)

    if warnings:
        print()
        print("⚠️ 警告:")
        for w in warnings:
            print(f"  - {w}")
        print()

    # 出力
    print(f"[3/3] 出力: {args.output}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print()
    mapped_keys = [k for k in result if result[k]]
    print(f"✅ 正規化完了: {len(mapped_keys)} フィールドをマッピング")
    print()
    print("次のステップ:")
    print(f"  python factory/scripts/create_clinic_profile.py --from-form {args.output}")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())

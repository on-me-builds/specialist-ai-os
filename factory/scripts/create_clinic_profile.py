#!/usr/bin/env python3
"""
Clinic Profile Builder v0.2
============================
対話形式 or フォームJSON入力でクリニックプロフィールYAMLを生成する。
generate_pack.py に渡せる形式で保存する。

使い方:
    # 対話モード
    python factory/scripts/create_clinic_profile.py

    # フォームJSONから変換
    python factory/scripts/create_clinic_profile.py --from-form factory/forms/form_response_example.json

    # 出力先指定
    python factory/scripts/create_clinic_profile.py --from-form response.json --output factory/input/my_clinic.yaml
"""

import argparse
import io
import json
import re
import sys
from datetime import datetime
from pathlib import Path

# Windows cp932 対策
if sys.stdout.encoding and sys.stdout.encoding.lower().startswith("cp"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding="utf-8", errors="replace")

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML が必要です。 pip install pyyaml を実行してください。")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_OUTPUT = PROJECT_ROOT / "factory" / "input" / "clinic_profile.generated.yaml"


# ---------------------------------------------------------------------------
# Input helpers
# ---------------------------------------------------------------------------
def ask(prompt: str, required: bool = False, default: str = "") -> str:
    """単一行の入力を取得する。"""
    suffix = " *" if required else ""
    default_hint = f" [{default}]" if default else ""
    while True:
        answer = input(f"  {prompt}{suffix}{default_hint}: ").strip()
        if not answer and default:
            return default
        if not answer and required:
            print("    → 必須項目です。入力してください。")
            continue
        return answer


def ask_list(prompt: str, example: str = "", min_items: int = 0) -> list[str]:
    """複数項目をリスト入力する。空行で終了。"""
    print(f"  {prompt}")
    if example:
        print(f"    例: {example}")
    print("    （1行に1つ入力。空行で終了）")
    items = []
    while True:
        line = input("    - ").strip()
        if not line:
            if len(items) < min_items:
                print(f"    → 最低 {min_items} 件入力してください（現在 {len(items)} 件）。")
                continue
            break
        items.append(line)
    return items


def ask_yes_no(prompt: str, default: bool = True) -> bool:
    """Yes/Noの質問。"""
    hint = "[Y/n]" if default else "[y/N]"
    answer = input(f"  {prompt} {hint}: ").strip().lower()
    if not answer:
        return default
    return answer in ("y", "yes", "はい")


def ask_hiring_target() -> dict:
    """採用ターゲット1件を対話入力する。"""
    print("    --- 採用ターゲット ---")
    position = ask("職種名", required=True)
    experience = ask("応募条件（例: 経験者・ブランクOK / 未経験OK）", default="問わず")
    highlight = ask("この職種のアピールポイント（空白でスキップ）")
    target = {"position": position, "experience": experience}
    if highlight:
        target["highlight"] = highlight
    return target


# ---------------------------------------------------------------------------
# Main flow
# ---------------------------------------------------------------------------
def collect_profile() -> dict:
    """対話形式でプロフィールを収集する。"""
    print()
    print("=" * 55)
    print("  Clinic Profile Builder v0.1")
    print("  医院プロフィールを対話形式で作成します")
    print("=" * 55)
    print()
    print("  * = 必須項目  /  Enter = スキップ")
    print()

    # --- 基本情報 ---
    print("── 基本情報 ──")
    clinic_name = ask("医院名", required=True)
    target_type = ask(
        "医院の種別",
        default="一般歯科〜自費を少し扱う歯科医院",
    )

    # --- 診療内容 ---
    print()
    print("── 診療内容 ──")
    services = ask_list(
        "診療内容を入力してください",
        example="一般歯科（虫歯・歯周病） / 予防歯科 / 小児歯科 / ホワイトニング",
        min_items=1,
    )

    # --- 特徴 ---
    print()
    print("── 医院の特徴 ──")
    features = ask_list(
        "医院の特徴・強みを入力してください",
        example="担当衛生士制 / キッズスペースあり / 土曜診療 / CT完備",
        min_items=1,
    )

    # --- 予約ルール ---
    print()
    print("── 予約ルール ──")
    booking_system = ask("予約方法", default="電話 + Web予約")
    cancel_policy = ask("キャンセルポリシー", default="前日までに連絡")
    first_visit = ask("初診時の目安時間", default="初回は30分〜1時間程度")

    # --- 支払い ---
    print()
    print("── 支払い方法 ──")
    has_insurance = ask_yes_no("保険診療に対応していますか？", default=True)
    self_pay = ask_list(
        "自費の支払い方法を入力してください",
        example="クレジットカード / デンタルローン / 電子マネー",
    )
    price_note = ask("費用に関する補足（空白でスキップ）", default="自費治療は事前にお見積もりをお出しします")

    # --- 採用ターゲット ---
    print()
    print("── 採用ターゲット ──")
    print("  採用したい職種を1つずつ入力します。")
    hiring_targets = []
    while True:
        target = ask_hiring_target()
        hiring_targets.append(target)
        if not ask_yes_no("さらに職種を追加しますか？", default=False):
            break

    # --- トーン・備考 ---
    print()
    print("── トーン・備考 ──")
    tone = ask("文体の方向性", default="やわらかく丁寧・患者目線")
    notes = ask("自由メモ（院長の方針・地域特性など）")

    # --- 組み立て ---
    profile = {
        "clinic_name": clinic_name,
        "target_type": target_type,
        "services": services,
        "features": features,
        "booking_rules": {
            "system": booking_system,
            "cancel_policy": cancel_policy,
            "first_visit_note": first_visit,
        },
        "payment_notes": {
            "insurance": has_insurance,
            "self_pay_options": self_pay if self_pay else [],
            "price_note": price_note,
        },
        "hiring_targets": hiring_targets,
        "tone": tone,
    }
    if notes:
        profile["notes"] = notes

    return profile


# ---------------------------------------------------------------------------
# Form JSON → Profile conversion
# ---------------------------------------------------------------------------
def parse_hiring_details(details_text: str, positions: list[str]) -> list[dict]:
    """
    Q10（採用詳細）の自由記述をパースして hiring_targets リストにする。
    「職種：内容」形式 or 改行区切りを試みる。パース不能なら空dictで返す。
    Returns: (targets_list, unparsed_text_or_None)
    """
    targets = []
    unparsed_parts = []

    if not details_text.strip():
        # 空欄 → positionだけでdictを作る
        for pos in positions:
            targets.append({"position": pos, "experience": "", "highlight": ""})
        return targets, None

    # 改行 or "/" で分割して各行をパース
    lines = re.split(r"[\n/]", details_text)

    # position名の短縮形マッピング
    position_aliases = {}
    for pos in positions:
        position_aliases[pos] = pos
        # 短縮形: "歯科衛生士" → "衛生士"
        if "歯科衛生士" in pos:
            position_aliases["衛生士"] = pos
        if "歯科助手" in pos:
            position_aliases["助手"] = pos
        if "勤務医" in pos or "歯科医師" in pos:
            position_aliases["勤務医"] = pos
            position_aliases["医師"] = pos

    matched_positions = set()

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # 「職種：内容」or「職種:内容」形式を検出
        match = re.match(r"^(.+?)[：:]\s*(.+)$", line)
        if match:
            key = match.group(1).strip()
            value = match.group(2).strip()

            # key が既知の position に一致するか
            resolved_pos = position_aliases.get(key)
            if resolved_pos:
                # experience と highlight を分離（「、」区切りで最初が条件、残りがアピール）
                parts = re.split(r"[、,]", value, maxsplit=1)
                exp = parts[0].strip() if parts else value
                hl = parts[1].strip() if len(parts) > 1 else ""
                targets.append({"position": resolved_pos, "experience": exp, "highlight": hl})
                matched_positions.add(resolved_pos)
                continue

        # パース不能 → unparsed に退避
        unparsed_parts.append(line)

    # positionsの中でまだマッチしていない職種があればデフォルトで追加
    for pos in positions:
        if pos not in matched_positions:
            targets.append({"position": pos, "experience": "", "highlight": ""})

    unparsed = "\n".join(unparsed_parts) if unparsed_parts else None
    return targets, unparsed


def convert_form_response(data: dict) -> tuple[dict, list[str]]:
    """
    フォームJSON回答を clinic_profile dict に変換する。
    Returns: (profile, warnings)
    """
    warnings = []

    # --- 必須項目 ---
    clinic_name = (data.get("clinic_name") or "").strip()
    if not clinic_name:
        warnings.append("clinic_name が空です（必須）")

    services = data.get("services", [])
    if isinstance(services, str):
        services = [s.strip() for s in services.split(",") if s.strip()]
    if not services:
        warnings.append("services が空です（必須）")

    features = data.get("features", [])
    if isinstance(features, str):
        features = [f.strip() for f in features.split(",") if f.strip()]
    if not features:
        warnings.append("features が空です（必須）")

    # --- target_type ---
    target_type = (data.get("target_type") or "一般歯科〜自費を少し扱う歯科医院").strip()

    # --- booking_rules ---
    booking_system = (data.get("booking_system") or "電話 + Web予約").strip()
    cancel_policy = (data.get("cancel_policy") or "前日までに連絡").strip()

    # --- payment_notes ---
    insurance_raw = (data.get("insurance") or "はい").strip()
    insurance = insurance_raw in ("はい", "true", "True", "yes", "Yes", True)

    self_pay = data.get("self_pay_options", [])
    if isinstance(self_pay, str):
        self_pay = [s.strip() for s in self_pay.split(",") if s.strip()]

    price_note = (data.get("price_note") or "自費治療は事前にお見積もりをお出しします").strip()

    # --- hiring_targets (Q9 + Q10) ---
    positions = data.get("hiring_positions", [])
    if isinstance(positions, str):
        positions = [p.strip() for p in positions.split(",") if p.strip()]

    details_text = (data.get("hiring_details") or "").strip()

    hiring_targets = []
    if positions:
        hiring_targets, unparsed = parse_hiring_details(details_text, positions)
        if unparsed:
            warnings.append(f"採用詳細の一部をパースできませんでした（notesに退避）: {unparsed}")
    elif details_text:
        warnings.append("hiring_positions が空ですが hiring_details があります（notesに退避）")

    # --- tone / notes ---
    tone = (data.get("tone") or "やわらかく丁寧・患者目線").strip()
    notes_parts = []
    raw_notes = (data.get("notes") or "").strip()
    if raw_notes:
        notes_parts.append(raw_notes)

    # パース不能な hiring_details を notes に退避
    if positions and details_text:
        _, unparsed = parse_hiring_details(details_text, positions)
        if unparsed:
            notes_parts.append(f"【採用詳細（要手動整理）】{unparsed}")
    elif not positions and details_text:
        notes_parts.append(f"【採用詳細（要手動整理）】{details_text}")

    # --- 組み立て ---
    profile = {
        "clinic_name": clinic_name,
        "target_type": target_type,
        "services": services,
        "features": features,
        "booking_rules": {
            "system": booking_system,
            "cancel_policy": cancel_policy,
            "first_visit_note": "初回は30分〜1時間程度",
        },
        "payment_notes": {
            "insurance": insurance,
            "self_pay_options": self_pay,
            "price_note": price_note,
        },
        "hiring_targets": hiring_targets,
        "tone": tone,
    }
    if notes_parts:
        profile["notes"] = "\n".join(notes_parts)

    return profile, warnings


def load_form_response(path: Path) -> dict:
    """JSONファイルを読み込む。"""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def preview_profile(profile: dict) -> str:
    """プロフィールをYAML文字列としてプレビューする。"""
    # コメントヘッダー付きで出力
    header = (
        f"# ============================================\n"
        f"# クリニックプロフィール（自動生成）\n"
        f"# 生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        f"# Clinic Profile Builder v0.1 で作成\n"
        f"# ============================================\n\n"
    )
    body = yaml.dump(
        profile,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
    )
    return header + body


def validate_profile(profile: dict) -> list[str]:
    """プロフィールの必須項目をチェックし、警告リストを返す。"""
    warnings = []
    if not profile.get("clinic_name"):
        warnings.append("clinic_name が空です")
    if not profile.get("services"):
        warnings.append("services が空です（最低1つ必要）")
    if not profile.get("features"):
        warnings.append("features が空です（最低1つ必要）")
    if not profile.get("hiring_targets"):
        warnings.append("hiring_targets が空です")
    return warnings


def main():
    parser = argparse.ArgumentParser(
        description="Clinic Profile Builder v0.2 - 対話 or フォームJSONからプロフィールYAMLを作成"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="出力先YAMLパス",
    )
    parser.add_argument(
        "--from-form",
        type=Path,
        default=None,
        metavar="JSON_PATH",
        help="フォーム回答JSONからYAMLを生成（対話をスキップ）",
    )
    args = parser.parse_args()

    # --- モード分岐 ---
    if args.from_form:
        # フォームJSONモード
        print(f"[from-form] JSON読み込み: {args.from_form}")
        if not args.from_form.exists():
            print(f"ERROR: ファイルが見つかりません: {args.from_form}")
            return 1
        try:
            form_data = load_form_response(args.from_form)
        except json.JSONDecodeError as e:
            print(f"ERROR: JSONの解析に失敗しました: {e}")
            return 1

        profile, form_warnings = convert_form_response(form_data)

        # validate も実行
        val_warnings = validate_profile(profile)
        all_warnings = form_warnings + val_warnings

        if all_warnings:
            print()
            print("⚠️ 警告:")
            for w in all_warnings:
                print(f"  - {w}")

    else:
        # 対話モード（従来通り）
        try:
            profile = collect_profile()
        except (KeyboardInterrupt, EOFError):
            print("\n\n中断しました。")
            return 1

        # バリデーション
        warnings = validate_profile(profile)
        if warnings:
            print()
            print("⚠️ 警告:")
            for w in warnings:
                print(f"  - {w}")

    # --- プレビュー ---
    yaml_content = preview_profile(profile)
    print()
    print("=" * 55)
    print("  プレビュー")
    print("=" * 55)
    print()
    print(yaml_content)
    print("=" * 55)

    # --- 確認（from-formモードでは自動保存） ---
    if not args.from_form:
        try:
            if not ask_yes_no("この内容で保存しますか？", default=True):
                print("保存をキャンセルしました。")
                return 0
        except (KeyboardInterrupt, EOFError):
            print("\n保存をキャンセルしました。")
            return 0

    # --- 保存 ---
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(yaml_content, encoding="utf-8")
    print()
    print(f"✅ 保存しました: {args.output}")
    print()
    print("次のステップ:")
    print(f"  python factory/scripts/generate_pack.py --profile {args.output}")
    print(f"  python factory/scripts/generate_pack.py --profile {args.output} --llm faq review recruiting")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())

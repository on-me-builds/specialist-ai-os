#!/usr/bin/env python3
"""
Template Factory v0.1
=====================
クリニックプロフィール（YAML）を読み込み、4つのMarkdownテンプレートを自動生成する。

使い方:
    python generate_templates.py
    python generate_templates.py --profile path/to/profile.yaml
    python generate_templates.py --output path/to/output/dir
"""

import argparse
import os
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML が必要です。 pip install pyyaml を実行してください。")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_PROFILE = SCRIPT_DIR / "clinic_profile_example.yaml"
DEFAULT_OUTPUT = SCRIPT_DIR.parent / "output" / "generated" / "sample_clinic"
TEMPLATES_DIR = SCRIPT_DIR / "templates"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def load_profile(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def bullet_list(items: list) -> str:
    return "\n".join(f"- {item}" for item in items)


def numbered_list(items: list) -> str:
    return "\n".join(f"{i+1}. {item}" for i, item in items)


# ---------------------------------------------------------------------------
# FAQ Generator
# ---------------------------------------------------------------------------
def generate_faq(profile: dict) -> str:
    name = profile["clinic_name"]
    booking = profile.get("booking_rules", {})
    payment = profile.get("payment_notes", {})
    services = profile.get("services", [])
    features = profile.get("features", [])

    # サービス別FAQ（動的生成）
    service_questions = []
    for i, svc in enumerate(services[:3]):
        q_num = 6 + i
        service_questions.append(
            f"### Q{q_num}. {svc}について教えてください。\n\n"
            f"**回答**\n"
            f"{name}では{svc}に対応しております。"
            f"患者さまのご希望や状態に合わせて最適な治療をご提案いたしますので、まずはお気軽にご相談ください。\n"
        )
    services_faq = "\n---\n\n".join(service_questions)

    # 支払い方法
    methods = []
    if payment.get("insurance"):
        methods.append("保険診療")
    for opt in payment.get("self_pay_options", []):
        methods.append(opt)
    payment_str = "・".join(methods) if methods else "詳細はお問い合わせください"
    price_note = payment.get("price_note", "")

    # キッズセクション（特徴にキッズ関連があれば追加）
    kids_section = ""
    has_kids = any("キッズ" in f or "小児" in s for f in features for s in [f])
    has_kids = has_kids or any("小児" in s for s in services)
    if has_kids:
        kids_section = (
            "\n### Q11. キッズスペースはありますか？\n\n"
            "**回答**\n"
            "はい、お子さま連れでも安心してお越しいただけるよう、キッズスペースをご用意しております。\n"
        )

    # テンプレート読み込み＆差し込み
    template = (TEMPLATES_DIR / "faq_base.md").read_text(encoding="utf-8")
    result = template.format(
        clinic_name=name,
        first_visit_note=booking.get("first_visit_note", "30分〜1時間ほど"),
        booking_system=booking.get("system", "お電話"),
        cancel_policy=booking.get("cancel_policy", "前日まで"),
        services_faq_section=services_faq,
        payment_methods=payment_str,
        price_note=price_note,
        kids_section=kids_section,
    )
    return result


# ---------------------------------------------------------------------------
# Review Reply Generator
# ---------------------------------------------------------------------------
def generate_review(profile: dict) -> str:
    name = profile["clinic_name"]
    features = profile.get("features", [])

    # 特徴に応じた追加テンプレ
    feature_section = ""
    feature_reviews = []
    if any("土曜" in f for f in features):
        feature_reviews.append(
            "### テンプレ 4｜土曜診療への感謝\n\n"
            '> **想定口コミ**: 「土曜も診てもらえるので助かっています。」\n\n'
            "**返信例**\n\n"
            "土曜日の診療をご活用いただきありがとうございます。お仕事やご予定で平日のご来院が難しい方にも"
            "通いやすい環境を整えておりますので、今後もお気軽にご利用ください。\n\n---\n\n"
        )
    if any("予防" in f or "メンテナンス" in s for f in features for s in [f]):
        feature_reviews.append(
            "### テンプレ 4-b｜予防・メンテナンスへの評価\n\n"
            '> **想定口コミ**: 「定期健診の案内が丁寧で、虫歯予防に役立っています。」\n\n'
            "**返信例**\n\n"
            "定期健診をご継続いただきありがとうございます。予防を大切にされている患者さまのお力になれることを"
            "うれしく思います。今後も継続的なサポートを行ってまいります。\n\n---\n\n"
        )
    if feature_reviews:
        feature_section = "".join(feature_reviews)

    template = (TEMPLATES_DIR / "review_base.md").read_text(encoding="utf-8")
    return template.format(
        clinic_name=name,
        feature_review_section=feature_section,
    )


# ---------------------------------------------------------------------------
# Recruiting Generator
# ---------------------------------------------------------------------------
def generate_recruiting(profile: dict) -> str:
    name = profile["clinic_name"]
    tone = profile.get("tone", "やわらかく丁寧")
    hiring = profile.get("hiring_targets", [])
    features = profile.get("features", [])
    services = profile.get("services", [])

    sections = []
    for i, target in enumerate(hiring):
        pos = target["position"]
        exp = target.get("experience", "")
        highlight = target.get("highlight", "")

        # 求人タイトル生成
        if "未経験" in exp:
            title = f"未経験OK｜{pos}スタッフ募集"
        elif "ブランク" in exp:
            title = f"ブランクOK｜{pos}募集"
        else:
            title = f"{pos}募集"

        # 紹介文
        intro_parts = [f"{name}では{pos}を募集しています。"]
        if "予防" in " ".join(services):
            intro_parts.append("予防歯科を大切にしている医院です。")
        if highlight:
            intro_parts.append(f"{highlight}。")

        # メリット（特徴ベース）
        merits = []
        for feat in features:
            if "キッズ" in feat:
                merits.append("お子さま連れのスタッフにも理解のある職場です")
            if "土曜" in feat:
                merits.append("土曜診療ありで患者さまのニーズに応えられます")
            if "担当" in feat:
                merits.append("担当患者制でやりがいを持って働けます")
        if not merits:
            merits.append("スタッフ同士の雰囲気が良く、長く働ける環境です")

        section = (
            f"## テンプレ {i+1}｜{pos} 募集\n\n"
            f"### 募集タイトル\n\n"
            f"**「{title}」**\n\n"
            f"### 冒頭紹介文\n\n"
            f"{''.join(intro_parts)}\n\n"
            f"### 応募条件\n\n"
            f"- {exp}\n\n"
            f"### この医院で働くメリット\n\n"
            + "\n".join(f"- {m}" for m in merits)
            + "\n\n"
            f"### 応募を促す締め文\n\n"
            f"まずは医院の雰囲気を見ていただくだけでも構いません。見学も随時受け付けていますので、お気軽にお問い合わせください。\n"
        )
        sections.append(section)

    template = (TEMPLATES_DIR / "recruiting_base.md").read_text(encoding="utf-8")
    return template.format(
        clinic_name=name,
        tone_desc=tone,
        recruiting_sections="\n---\n\n".join(sections),
    )


# ---------------------------------------------------------------------------
# Sales Onepager Generator
# ---------------------------------------------------------------------------
def generate_onepager(profile: dict) -> str:
    name = profile["clinic_name"]
    services = profile.get("services", [])
    features = profile.get("features", [])
    target = profile.get("target_type", "")

    # 課題セクション（サービスに応じて動的に生成）
    pain_points = [
        "- 患者さまからの「よくある質問」に毎回同じ説明をしている",
        "- Google口コミへの返信に時間がかかる・後回しになっている",
        "- 求人を出しても応募が集まりにくい",
    ]
    if any("予防" in s for s in services):
        pain_points.append("- 予防歯科の価値を患者さまに伝えきれていない")
    if any("自費" in s or "ホワイトニング" in s or "セラミック" in s for s in services):
        pain_points.append("- 自費診療の説明・案内に手間がかかっている")

    template = (TEMPLATES_DIR / "onepager_base.md").read_text(encoding="utf-8")
    return template.format(
        clinic_name=name,
        target_type=target,
        services_list="、".join(services),
        features_list="、".join(features),
        pain_points="\n".join(pain_points),
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Template Factory v0.1")
    parser.add_argument(
        "--profile",
        type=Path,
        default=DEFAULT_PROFILE,
        help="クリニックプロフィールYAMLのパス",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="出力ディレクトリ",
    )
    args = parser.parse_args()

    # Load
    print(f"[1/5] プロフィール読み込み: {args.profile}")
    profile = load_profile(args.profile)
    clinic_name = profile.get("clinic_name", "不明")
    print(f"       医院名: {clinic_name}")

    # Output dir
    args.output.mkdir(parents=True, exist_ok=True)
    print(f"[2/5] 出力先: {args.output}")

    # Generate
    generators = [
        ("faq.md", "FAQ", generate_faq),
        ("review_reply.md", "口コミ返信テンプレ", generate_review),
        ("recruiting.md", "求人文テンプレ", generate_recruiting),
        ("sales_onepager.md", "Sales Onepager", generate_onepager),
    ]

    total = len(generators) + 2
    for i, (filename, label, gen_func) in enumerate(generators):
        print(f"[{i+3}/{total}] {label} を生成中...")
        content = gen_func(profile)
        out_path = args.output / filename
        out_path.write_text(content, encoding="utf-8")
        print(f"       -> {out_path}")

    print()
    print("=" * 50)
    print(f"完了！ {len(generators)} ファイルを生成しました。")
    print(f"出力先: {args.output}")
    print("=" * 50)


if __name__ == "__main__":
    main()

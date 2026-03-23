#!/usr/bin/env python3
"""
Product Factory v0.4 - Pack Generator
======================================
クリニックプロフィール（YAML）を読み込み、4つのMarkdownテンプレートを一括生成する。
FAQ・口コミ返信・求人文は Claude API によるLLM生成に対応。

使い方:
    python factory/scripts/generate_pack.py
    python factory/scripts/generate_pack.py --llm faq
    python factory/scripts/generate_pack.py --llm faq review recruiting
    python factory/scripts/generate_pack.py --profile factory/input/my_clinic.yaml
    python factory/scripts/generate_pack.py --llm faq review recruiting --output output/generated/my_clinic
"""

import argparse
import io
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Windows cp932 対策
if sys.stdout.encoding and sys.stdout.encoding.lower().startswith("cp"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML が必要です。 pip install pyyaml を実行してください。")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
FACTORY_DIR = PROJECT_ROOT / "factory"
DEFAULT_PROFILE = FACTORY_DIR / "input" / "clinic_profile.example.yaml"
DEFAULT_OUTPUT = PROJECT_ROOT / "output" / "generated" / "sample_clinic"
TEMPLATES_DIR = FACTORY_DIR / "templates"
PROMPTS_DIR = FACTORY_DIR / "prompts"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def load_profile(path: Path) -> dict:
    """YAMLプロフィールを読み込む"""
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    required = ["clinic_name", "services", "features"]
    missing = [k for k in required if k not in data or not data[k]]
    if missing:
        print(f"ERROR: 必須フィールドが不足: {', '.join(missing)}")
        sys.exit(1)
    return data


def bullet_list(items: list) -> str:
    return "\n".join(f"- {item}" for item in items)


# ---------------------------------------------------------------------------
# LLM Client (Claude API)
# ---------------------------------------------------------------------------
def get_anthropic_client():
    """Anthropic クライアントを取得。未インストール or キー未設定なら None を返す。"""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return None
    try:
        import anthropic
        return anthropic.Anthropic(api_key=api_key)
    except ImportError:
        return None


def call_llm(prompt: str) -> str | None:
    """Claude API にプロンプトを送信し、結果テキストを返す。失敗時は None。"""
    client = get_anthropic_client()
    if client is None:
        return None
    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
        result = ""
        for block in message.content:
            if block.type == "text":
                result += block.text
        return result if result.strip() else None
    except Exception as e:
        print(f"       ⚠️ Claude API エラー: {e}")
        return None


def profile_to_strings(profile: dict) -> dict[str, str]:
    """プロフィールの各フィールドをプロンプト埋め込み用の文字列に変換する。"""
    booking = profile.get("booking_rules", {})
    payment = profile.get("payment_notes", {})

    # 予約ルール
    booking_str = ""
    if booking:
        parts = []
        if booking.get("system"):
            parts.append(f"予約方法: {booking['system']}")
        if booking.get("cancel_policy"):
            parts.append(f"キャンセル: {booking['cancel_policy']}")
        if booking.get("first_visit_note"):
            parts.append(f"初診: {booking['first_visit_note']}")
        booking_str = " / ".join(parts)

    # 支払い
    payment_str = ""
    if payment:
        parts = []
        if payment.get("insurance"):
            parts.append("保険診療対応")
        for opt in payment.get("self_pay_options", []):
            parts.append(opt)
        if payment.get("price_note"):
            parts.append(payment["price_note"])
        payment_str = "、".join(parts)

    # 採用ターゲットの文字列化
    hiring = profile.get("hiring_targets", [])
    hiring_parts = []
    for t in hiring:
        pos = t.get("position", "")
        exp = t.get("experience", "")
        hl = t.get("highlight", "")
        hiring_parts.append(f"{pos}（{exp}）{' - ' + hl if hl else ''}")
    hiring_str = " / ".join(hiring_parts) if hiring_parts else "未指定"

    return {
        "clinic_name": profile["clinic_name"],
        "services": "、".join(profile.get("services", [])),
        "features": "、".join(profile.get("features", [])),
        "booking_rules": booking_str,
        "payment_notes": payment_str,
        "hiring_targets": hiring_str,
        "tone": profile.get("tone", "やわらかく丁寧"),
        "notes": profile.get("notes", ""),
    }


def generate_faq_llm(profile: dict) -> str | None:
    """Claude API を使ってFAQを生成する。失敗時は None を返す。"""
    prompt_template = (PROMPTS_DIR / "faq_prompt.md").read_text(encoding="utf-8")
    strings = profile_to_strings(profile)
    prompt_filled = prompt_template.format(**strings)
    return call_llm(prompt_filled)


def generate_review_llm(profile: dict) -> str | None:
    """Claude API を使って口コミ返信テンプレを生成する。失敗時は None を返す。"""
    prompt_template = (PROMPTS_DIR / "review_prompt.md").read_text(encoding="utf-8")
    strings = profile_to_strings(profile)
    prompt_filled = prompt_template.format(**strings)
    return call_llm(prompt_filled)


def generate_recruiting_llm(profile: dict) -> str | None:
    """Claude API を使って求人文テンプレを生成する。失敗時は None を返す。"""
    prompt_template = (PROMPTS_DIR / "recruiting_prompt.md").read_text(encoding="utf-8")
    strings = profile_to_strings(profile)
    prompt_filled = prompt_template.format(**strings)
    return call_llm(prompt_filled)


# ---------------------------------------------------------------------------
# FAQ Generator (Template)
# ---------------------------------------------------------------------------
def generate_faq_template(profile: dict) -> str:
    """テンプレート差し込み方式でFAQを生成する（従来方式）"""
    name = profile["clinic_name"]
    booking = profile.get("booking_rules", {})
    payment = profile.get("payment_notes", {})
    services = profile.get("services", [])
    features = profile.get("features", [])

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

    # 支払い文を自然な日本語に
    payment_parts = []
    if payment.get("insurance"):
        payment_parts.append("保険診療に対応しています")
    self_pay_opts = payment.get("self_pay_options", [])
    if self_pay_opts:
        payment_parts.append(f"自費治療には{'・'.join(self_pay_opts)}がご利用いただけます")
    price_note = payment.get("price_note", "")
    if price_note:
        payment_parts.append(price_note)
    if not payment_parts:
        payment_sentence = "お支払い方法の詳細はお電話またはご来院時にお問い合わせください。"
    else:
        payment_sentence = "。".join(payment_parts) + "。"

    # キャンセルポリシーを自然な文に（入力がすでに文章の場合はそのまま使う）
    cancel_raw = booking.get("cancel_policy", "").strip()
    if cancel_raw:
        import re as _re
        # 入力が完全な文（「〜ください」「〜お願いします」「〜しています」等で終わる）ならそのまま使う
        if _re.search(r"(ください|お願いします|お願いいたします|お願いしています|しております)\.?$", cancel_raw):
            cancel_policy_sentence = cancel_raw
            # 末尾に「。」がなければ付ける
            if not cancel_policy_sentence.endswith("。"):
                cancel_policy_sentence += "。"
        else:
            # 「前日までに連絡」「前日まで」等の短いフレーズ → 文を組み立てる
            # 末尾の「に連絡」「にご連絡」を除去して期限だけ取り出す
            deadline = _re.sub(r"(にご?連絡|ご連絡|連絡)$", "", cancel_raw).strip()
            if not deadline:
                deadline = cancel_raw
            cancel_policy_sentence = f"変更・キャンセルは{deadline}にご連絡いただけると助かります。"
    else:
        cancel_policy_sentence = "変更・キャンセルはできるだけ早めにご連絡ください。"

    # キッズセクション（入力に「キッズスペース」明記の場合のみ断定）
    kids_section = ""
    has_kids_space = any("キッズ" in f for f in features)
    has_pediatric = any("小児" in s for s in services)
    if has_kids_space and has_pediatric:
        kids_section = (
            "### Q10. 何歳から診てもらえますか？\n\n"
            "**回答**\n"
            "歯が生え始めた頃（生後6か月ごろ）から受診いただけます。"
            "まずは歯科に慣れることから始めますので、お気軽にお連れください。\n\n---\n\n"
            "### Q11. キッズスペースはありますか？\n\n"
            "**回答**\n"
            "はい、お子さま連れでも安心してお越しいただけるよう、キッズスペースをご用意しております。\n"
        )
    elif has_pediatric:
        kids_section = (
            "### Q10. 何歳から診てもらえますか？\n\n"
            "**回答**\n"
            "歯が生え始めた頃（生後6か月ごろ）から受診いただけます。"
            "まずは歯科に慣れることから始めますので、お気軽にお連れください。\n\n---\n\n"
            "### Q11. お子さま連れでも通えますか？\n\n"
            "**回答**\n"
            "お子さま連れでの来院についてはお電話でお気軽にご相談ください。\n"
        )
    else:
        kids_section = (
            "### Q10. お子さまの治療は対応していますか？\n\n"
            "**回答**\n"
            "お子さまの治療への対応については、お電話またはホームページでご確認ください。\n"
        )

    template = (TEMPLATES_DIR / "faq_base.md").read_text(encoding="utf-8")
    return template.format(
        clinic_name=name,
        first_visit_note=booking.get("first_visit_note", "30分〜1時間ほど"),
        booking_system=booking.get("system", "お電話"),
        cancel_policy_sentence=cancel_policy_sentence,
        services_faq_section=services_faq,
        payment_sentence=payment_sentence,
        kids_section=kids_section,
    )


def generate_faq(profile: dict, use_llm: bool = False) -> tuple[str, str]:
    """
    FAQ生成のルーター。
    Returns: (content, mode) where mode is "llm" or "template"
    """
    if use_llm:
        print("       LLMモードを試行中...")
        result = generate_faq_llm(profile)
        if result is not None:
            print("       ✅ Claude API で生成完了")
            return result, "llm"
        else:
            print("       ⚠️ LLM生成失敗 → テンプレート方式にフォールバック")

    content = generate_faq_template(profile)
    return content, "template"


# ---------------------------------------------------------------------------
# Review Reply Generator
# ---------------------------------------------------------------------------
def generate_review(profile: dict, use_llm: bool = False) -> tuple[str, str]:
    """
    口コミ返信テンプレ生成のルーター。
    Returns: (content, mode) where mode is "llm" or "template"
    """
    if use_llm:
        print("       LLMモードを試行中...")
        result = generate_review_llm(profile)
        if result is not None:
            print("       ✅ Claude API で生成完了")
            return result, "llm"
        else:
            print("       ⚠️ LLM生成失敗 → テンプレート方式にフォールバック")

    content = generate_review_template(profile)
    return content, "template"


def generate_review_template(profile: dict) -> str:
    """テンプレート差し込み方式で口コミ返信を生成する（従来方式）"""
    name = profile["clinic_name"]
    features = profile.get("features", [])

    feature_reviews = []
    if any("土曜" in f for f in features):
        feature_reviews.append(
            "### テンプレ 4｜土曜診療への感謝\n\n"
            '> **想定口コミ**: 「土曜も診てもらえるので助かっています。」\n\n'
            "**返信例**\n\n"
            "土曜日の診療をご活用いただきありがとうございます。お仕事やご予定で平日のご来院が難しい方にも"
            "通いやすい環境を整えておりますので、今後もお気軽にご利用ください。\n\n---\n\n"
        )
    if any("予防" in f for f in features):
        feature_reviews.append(
            "### テンプレ 4-b｜予防・メンテナンスへの評価\n\n"
            '> **想定口コミ**: 「定期健診の案内が丁寧で、虫歯予防に役立っています。」\n\n'
            "**返信例**\n\n"
            "定期健診をご継続いただきありがとうございます。予防を大切にされている患者さまのお力になれることを"
            "うれしく思います。今後も継続的なサポートを行ってまいります。\n\n---\n\n"
        )
    feature_section = "".join(feature_reviews)

    template = (TEMPLATES_DIR / "review_base.md").read_text(encoding="utf-8")
    return template.format(
        clinic_name=name,
        feature_review_section=feature_section,
    )


# ---------------------------------------------------------------------------
# Recruiting Generator
# ---------------------------------------------------------------------------
def generate_recruiting(profile: dict, use_llm: bool = False) -> tuple[str, str]:
    """
    求人文テンプレ生成のルーター。
    Returns: (content, mode) where mode is "llm" or "template"
    """
    if use_llm:
        print("       LLMモードを試行中...")
        result = generate_recruiting_llm(profile)
        if result is not None:
            print("       ✅ Claude API で生成完了")
            return result, "llm"
        else:
            print("       ⚠️ LLM生成失敗 → テンプレート方式にフォールバック")

    content = generate_recruiting_template(profile)
    return content, "template"


def generate_recruiting_template(profile: dict) -> str:
    """テンプレート差し込み方式で求人文を生成する（3職種固定構成）"""
    name = profile["clinic_name"]
    tone = profile.get("tone", "やわらかく丁寧")
    hiring = profile.get("hiring_targets", [])
    features = profile.get("features", [])
    services = profile.get("services", [])

    # hiring_targets を position 名でルックアップできるようにする
    hiring_map = {}
    for t in hiring:
        pos = t.get("position", "")
        hiring_map[pos] = t
        # 短縮名でもマッチ
        if "衛生士" in pos:
            hiring_map["歯科衛生士"] = t
        if "助手" in pos or "受付" in pos:
            hiring_map["歯科助手・受付"] = t
        if "勤務医" in pos or "医師" in pos:
            hiring_map["勤務医"] = t

    # 3職種固定構成
    POSITIONS = [
        {
            "position": "歯科衛生士",
            "default_exp": "経験者歓迎・ブランクOK",
            "default_highlight": "患者さまに寄り添えるやりがいのあるお仕事です",
            "default_title": "歯科衛生士募集",
            "title_prefix_exp": {"未経験": "未経験OK｜歯科衛生士募集", "ブランク": "ブランクOK｜歯科衛生士募集"},
            "personas": [
                "患者さまとのコミュニケーションを大切にできる方",
                "予防やメンテナンスに興味がある方",
                "チームで協力しながら働くことが好きな方",
                "ブランクがあっても、学ぶ意欲のある方",
            ],
            "default_merits": [
                "**スキルアップ支援** ― 研修・セミナー参加費を補助しています",
                "**残業少なめ** ― 診療時間内に業務が完結する仕組みを整えています",
                "**有給取得しやすい環境** ― スタッフ同士でカバーし合う風土があります",
            ],
        },
        {
            "position": "歯科助手・受付",
            "default_exp": "未経験OK",
            "default_highlight": "研修制度ありで安心してスタートできます",
            "default_title": "未経験OK｜歯科助手・受付スタッフ募集",
            "title_prefix_exp": {},
            "personas": [
                "明るい対応ができる方",
                "未経験でも新しいことを覚える意欲がある方",
                "細かい作業や事務作業が苦にならない方",
                "医療の仕事に興味がある方",
            ],
            "default_merits": [
                "**未経験者向けの研修あり** ― 器具の名前や流れを一からお教えします",
                "**清潔で落ち着いた職場** ― 働く環境の快適さにもこだわっています",
                "**長く続けている先輩が多い** ― 居心地の良さが定着率に表れています",
            ],
        },
        {
            "position": "勤務医",
            "default_exp": "経験者歓迎・開業準備中の方も歓迎",
            "default_highlight": "幅広い症例を経験できる環境です",
            "default_title": "勤務医募集",
            "title_prefix_exp": {},
            "personas": [
                "幅広い症例を経験したい方",
                "丁寧な診療を大切にできる方",
                "スタッフと協力しながらチーム医療に取り組める方",
                "将来の開業を視野に入れている方",
            ],
            "default_merits": [
                "**幅広い症例** ― 一般歯科から自費診療まで経験を積める環境です",
                "**設備充実** ― 質の高い治療を提供できる環境を整えています",
                "**勤務日・時間の相談可** ― ライフスタイルに合わせた働き方ができます",
            ],
        },
    ]

    sections = []
    for i, pos_spec in enumerate(POSITIONS):
        pos_name = pos_spec["position"]
        # hiring_targets から情報を取得（なければデフォルト）
        target = hiring_map.get(pos_name, {})
        exp = target.get("experience", "") or pos_spec["default_exp"]
        highlight = target.get("highlight", "") or pos_spec["default_highlight"]

        # タイトル
        title = pos_spec["default_title"]
        for key, t in pos_spec["title_prefix_exp"].items():
            if key in exp:
                title = t
                break

        # 冒頭紹介文
        intro_parts = [f"{name}では{pos_name}を募集しています。"]
        if "予防" in " ".join(services):
            intro_parts.append("予防歯科を大切にしている医院です。")
        intro_parts.append(f"{highlight}。")

        # メリット（特徴ベース + デフォルト）
        merits = list(pos_spec["default_merits"])
        for feat in features:
            if "担当" in feat and "衛生士" in pos_name:
                merits.insert(0, "**担当患者制** ― 一人ひとりの経過を追えるので、成長や変化を実感できます")
            if "土曜" in feat:
                merits.append("**土曜診療対応** ― 患者さまのニーズに合わせた診療体制です")
        # 重複除去（先頭を優先）
        seen = set()
        unique_merits = []
        for m in merits:
            key = m.split("―")[0].strip() if "―" in m else m
            if key not in seen:
                seen.add(key)
                unique_merits.append(m)
        merits = unique_merits[:4]  # 最大4個

        section = (
            f"## テンプレ {i+1}｜{pos_name} 募集\n\n"
            f"### 募集タイトル\n\n"
            f"**「{title}」**\n\n"
            f"### 冒頭紹介文\n\n"
            f"{''.join(intro_parts)}\n\n"
            f"### 求める人物像\n\n"
            + "\n".join(f"- {p}" for p in pos_spec["personas"])
            + "\n\n"
            f"### この医院で働くメリット\n\n"
            + "\n".join(f"- {m}" for m in merits)
            + "\n\n"
            f"### 応募を促す締め文\n\n"
            f"まずは医院の雰囲気を見ていただくだけでも構いません。"
            f"見学も随時受け付けていますので、お気軽にお問い合わせください。"
            f"あなたと一緒に働けることを楽しみにしています。\n"
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
# Manifest (生成メタ情報)
# ---------------------------------------------------------------------------
def write_manifest(
    output_dir: Path,
    profile: dict,
    files: list[str],
    generation_modes: dict[str, str],
):
    """生成結果のメタ情報をJSONで書き出す（n8n連携・validate用）"""
    manifest = {
        "generated_at": datetime.now().isoformat(),
        "generator": "Product Factory v0.4",
        "clinic_name": profile.get("clinic_name", ""),
        "files": files,
        "generation_modes": generation_modes,
        "profile_fields": list(profile.keys()),
    }
    path = output_dir / "_manifest.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Product Factory v0.4 - テンプレートパック一括生成"
    )
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
    parser.add_argument(
        "--llm",
        nargs="*",
        default=[],
        metavar="TARGET",
        help="LLM生成に切り替える成果物を指定（対応: faq, review, recruiting）例: --llm faq review recruiting",
    )
    args = parser.parse_args()

    # LLM対象の検証
    valid_llm_targets = {"faq", "review", "recruiting"}
    llm_targets = set(args.llm) if args.llm else set()
    invalid = llm_targets - valid_llm_targets
    if invalid:
        print(f"WARNING: 未対応のLLMターゲット: {', '.join(invalid)}（無視します）")
        llm_targets = llm_targets & valid_llm_targets

    use_faq_llm = "faq" in llm_targets
    use_review_llm = "review" in llm_targets
    use_recruiting_llm = "recruiting" in llm_targets

    # APIキー状態の表示
    if llm_targets:
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        targets_str = ", ".join(sorted(llm_targets))
        if api_key:
            print(f"[INFO] ANTHROPIC_API_KEY 検出 → {targets_str} を LLM モードで生成します")
        else:
            print(f"[INFO] ANTHROPIC_API_KEY 未設定 → {targets_str} はテンプレート方式にフォールバック")

    # Load
    print(f"[1/6] プロフィール読み込み: {args.profile}")
    profile = load_profile(args.profile)
    clinic_name = profile.get("clinic_name", "不明")
    print(f"       医院名: {clinic_name}")

    # Output dir
    args.output.mkdir(parents=True, exist_ok=True)
    print(f"[2/6] 出力先: {args.output}")

    generated_files = []
    generation_modes = {}

    # --- FAQ (LLM対応) ---
    print("[3/7] FAQ を生成中...")
    faq_content, faq_mode = generate_faq(profile, use_llm=use_faq_llm)
    (args.output / "faq.md").write_text(faq_content, encoding="utf-8")
    generated_files.append("faq.md")
    generation_modes["faq.md"] = faq_mode
    print(f"       -> faq.md  (mode: {faq_mode})")

    # --- 口コミ返信 (LLM対応) ---
    print("[4/7] 口コミ返信テンプレ を生成中...")
    review_content, review_mode = generate_review(profile, use_llm=use_review_llm)
    (args.output / "review_reply.md").write_text(review_content, encoding="utf-8")
    generated_files.append("review_reply.md")
    generation_modes["review_reply.md"] = review_mode
    print(f"       -> review_reply.md  (mode: {review_mode})")

    # --- 求人文 (LLM対応) ---
    print("[5/7] 求人文テンプレ を生成中...")
    recruiting_content, recruiting_mode = generate_recruiting(profile, use_llm=use_recruiting_llm)
    (args.output / "recruiting.md").write_text(recruiting_content, encoding="utf-8")
    generated_files.append("recruiting.md")
    generation_modes["recruiting.md"] = recruiting_mode
    print(f"       -> recruiting.md  (mode: {recruiting_mode})")

    # --- Sales Onepager (テンプレート方式のみ) ---
    print("[6/7] Sales Onepager を生成中...")
    onepager_content = generate_onepager(profile)
    (args.output / "sales_onepager.md").write_text(onepager_content, encoding="utf-8")
    generated_files.append("sales_onepager.md")
    generation_modes["sales_onepager.md"] = "template"
    print("       -> sales_onepager.md  (mode: template)")

    # Manifest
    print("[7/7] マニフェスト書き出し...")
    manifest_path = write_manifest(args.output, profile, generated_files, generation_modes)
    print(f"       -> {manifest_path}")

    # LLMモードのサマリ
    llm_used = [f for f, m in generation_modes.items() if m == "llm"]
    mode_summary = ", ".join(f"{f}={m}" for f, m in generation_modes.items())

    print()
    print("=" * 50)
    print(f"完了！ {len(generated_files)} ファイル + manifest を生成しました。")
    print(f"出力先: {args.output}")
    print(f"生成モード: {mode_summary}")
    print("=" * 50)

    return 0


if __name__ == "__main__":
    sys.exit(main())

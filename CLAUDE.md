# Product Factory v0.4

## プロジェクト概要
歯科医院プロフィール（YAML）1つから、4つの実務テンプレート（FAQ・口コミ返信・求人文・Sales Onepager）をMarkdownで一括生成する最小システム。
FAQ・口コミ返信・求人文はClaude API連携に対応（`--llm faq review recruiting`）。API未設定時はテンプレ方式にフォールバック。

## 構成
```
specialist-ai-os/
  factory/
    input/              ← 入力YAML（ここだけ変える）
    templates/          ← ベーステンプレート（.md）
    prompts/            ← LLM連携用プロンプト（faq/review/recruiting 正式運用中）
    scripts/
      create_clinic_profile.py ← プロフィール対話作成
      generate_pack.py  ← メイン生成スクリプト
      validate_pack.py  ← 生成結果の検証
  output/generated/     ← 成果物出力先
  .claude/
    agents/             ← サブエージェント定義
    commands/           ← カスタムスラッシュコマンド
    hooks/              ← フック処理スクリプト
```

## 実行方法
```bash
# プロフィール作成（対話形式）
python factory/scripts/create_clinic_profile.py

# パック生成
python factory/scripts/generate_pack.py

# パック検証
python factory/scripts/validate_pack.py

# カスタムプロフィール指定
python factory/scripts/generate_pack.py --profile factory/input/my_clinic.yaml --output output/generated/my_clinic
```

## 出力形式
- すべてMarkdown（.md）
- 1パック = faq.md + review_reply.md + recruiting.md + sales_onepager.md + _manifest.json
- n8n連携を見据えて input/output を完全分離

## 禁止事項
- 外部APIへの接続（Claude API のFAQ・口コミ返信・求人文生成を除く）
- git push の自動実行
- secrets / credentials の取り扱い
- 過剰な依存ライブラリの追加（PyYAMLのみ許可）
- 医療広告ガイドラインに抵触する表現の生成

## Done条件（最優先）
1. clinic_profile を変えるだけで4成果物が再生成できる
2. validate_pack.py で全PASSが出る
3. 非エンジニアでもREADME通りに再実行できる

## サブエージェント
- **pack-generator**: パック一括生成の実行
- **compliance-reviewer**: 医療広告ガイドライン準拠チェック
- **copy-refiner**: 文面のトーン・品質改善
- **offer-architect**: 提案資料の構成設計

## カスタムコマンド
- `/make-pack`: パック生成 → 検証 → 結果表示
- `/review-pack`: 生成済みパックのレビュー
- `/make-onepager`: Sales Onepagerのみ再生成

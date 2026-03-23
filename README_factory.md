# Product Factory v0.4 + Clinic Profile Builder v0.1

## これは何か

歯科医院のプロフィール（YAML）を1つ入力すると、以下4つのMarkdownテンプレートを自動生成するローカルツール。
Claude Code のプロジェクト機能（settings / agents / commands / hooks）を組み込んだ再利用可能な構成。
**FAQ・口コミ返信・求人文は Claude API によるLLM生成に対応**（Sales Onepagerのみテンプレ方式）。

| # | 成果物 | 説明 | 生成方式 |
|---|--------|------|---------|
| 1 | FAQ | 患者向けよくある質問と回答（14問） | **テンプレ or LLM** |
| 2 | 口コミ返信テンプレ | Google口コミ等への返信文（10本） | **テンプレ or LLM** |
| 3 | 求人文テンプレ | 職種別の求人原稿（3職種） | **テンプレ or LLM** |
| 4 | Sales Onepager | 営業提案用の概要資料 | テンプレ |

## 実行方法

### 前提

- Python 3.8+
- PyYAML (`pip install pyyaml`)
- LLMモード使用時のみ: `pip install anthropic` + `ANTHROPIC_API_KEY` 環境変数

### Step 0: プロフィール作成

**方法A: 対話形式（ターミナルで質問に答える）**

```bash
cd specialist-ai-os

python factory/scripts/create_clinic_profile.py
python factory/scripts/create_clinic_profile.py --output factory/input/tanaka_dental.yaml
```

**方法B: フォームJSONから変換（Google Forms回答等）**

```bash
# サンプルJSONで試す
python factory/scripts/create_clinic_profile.py --from-form factory/forms/form_response_example.json

# 実際のフォーム回答JSONで変換
python factory/scripts/create_clinic_profile.py --from-form response.json --output factory/input/tanaka_dental.yaml
```

JSON形式は `factory/forms/form_response_example.json` を参照。キー一覧:
```
clinic_name, target_type, services[], features[],
booking_system, cancel_policy, insurance,
self_pay_options[], hiring_positions[], hiring_details,
tone, notes
```

**`--from-form` モードの特徴:**
- 対話をスキップし、JSONを読んで即座にYAMLを生成
- checkbox項目（services, features等）は配列で渡す
- `hiring_details`（採用詳細）は「職種：内容」形式をパース。パース不能な部分はnotesに退避しwarningを出す
- 必須3項目（clinic_name / services / features）不足時は警告を出すが、全体は止めない

→ `factory/input/clinic_profile.generated.yaml` に保存される

**方法C: Google Sheets 1行JSONから変換**

```bash
# Step C-1: Sheets行JSONを form_response 形式に正規化
python factory/scripts/normalize_sheet_row.py --input factory/forms/sheets_row_example.json

# Step C-2: 正規化されたJSONからYAML生成
python factory/scripts/create_clinic_profile.py --from-form factory/forms/form_response_from_sheet.json

# 一気通貫（Sheets行 → 正規化 → YAML → パック生成 → 検証）
python factory/scripts/normalize_sheet_row.py --input row.json \
  && python factory/scripts/create_clinic_profile.py --from-form factory/forms/form_response_from_sheet.json \
  && python factory/scripts/generate_pack.py --profile factory/input/clinic_profile.generated.yaml --llm faq review recruiting \
  && python factory/scripts/validate_pack.py
```

Sheets行JSONは `Q1_医院名` / `医院名` / `clinic_name` など列名ゆれを自動吸収する。
サンプル: `factory/forms/sheets_row_example.json`

### Step 1: パック一括生成

```bash
# デフォルト（example.yaml）で生成
python factory/scripts/generate_pack.py

# Step 0 で作ったプロフィールを指定
python factory/scripts/generate_pack.py --profile factory/input/clinic_profile.generated.yaml

# 出力先も変えたい場合
python factory/scripts/generate_pack.py --profile factory/input/tanaka_dental.yaml --output output/generated/tanaka_dental
```

### Step 2: 生成結果の検証

```bash
python factory/scripts/validate_pack.py

# 別のパックを検証
python factory/scripts/validate_pack.py --pack output/generated/tanaka_dental
```

### LLMモードで生成

```bash
# 環境変数にAPIキーをセット
export ANTHROPIC_API_KEY=sk-ant-api03-xxxxx

# FAQだけLLM
python factory/scripts/generate_pack.py --llm faq

# 口コミ返信だけLLM
python factory/scripts/generate_pack.py --llm review

# 求人文だけLLM
python factory/scripts/generate_pack.py --llm recruiting

# FAQ + 口コミ返信 + 求人文の3つをLLM
python factory/scripts/generate_pack.py --llm faq review recruiting

# カスタムプロフィール + LLM
python factory/scripts/generate_pack.py --llm faq review recruiting --profile factory/input/my_clinic.yaml
```

### APIキー未設定時の挙動

`--llm` を指定しても、以下の場合は**成果物ごとに個別に**テンプレート方式へ自動フォールバックする:

1. `ANTHROPIC_API_KEY` 環境変数が未設定
2. `anthropic` パッケージが未インストール
3. API呼び出し時にエラーが発生

→ **パック全体が止まることはない。該当ファイルだけフォールバックし、他ファイルは通常通り生成される。**
→ フォールバック結果は `_manifest.json` の `generation_modes` に記録される。

### その他のオプション

```bash
# 別のプロフィールを指定
python factory/scripts/generate_pack.py --profile factory/input/my_clinic.yaml

# 出力先を変更
python factory/scripts/generate_pack.py --output output/generated/my_clinic

# 別のパックを検証
python factory/scripts/validate_pack.py --pack output/generated/my_clinic
```

### 生成モードの確認

`_manifest.json` の `generation_modes` フィールドで各ファイルの生成方式を確認できる:

```json
{
  "generation_modes": {
    "faq.md": "llm",              // or "template"
    "review_reply.md": "llm",     // or "template"
    "recruiting.md": "llm",       // or "template"
    "sales_onepager.md": "template"
  }
}
```

### Claude Code スラッシュコマンド

Claude Code 内から実行する場合：

| コマンド | 説明 |
|---------|------|
| `/make-pack` | パック生成 → 検証 → 結果表示 |
| `/review-pack` | 生成済みパックのレビュー（品質＋コンプラ） |
| `/make-onepager` | Sales Onepagerのみ再生成＋改善提案 |

## 入力をどこだけ変えればいいか

`factory/input/clinic_profile.example.yaml` を開いて、以下を医院に合わせて書き換えるだけ。

| フィールド | 説明 | 必須 | 例 |
|-----------|------|:----:|-----|
| `clinic_name` | 医院名 | ✅ | さくら歯科クリニック |
| `target_type` | 医院の種別 | | 一般歯科〜自費を少し扱う歯科医院 |
| `services` | 診療内容リスト | ✅ | 一般歯科、予防歯科、小児歯科 ... |
| `features` | 医院の特徴リスト | ✅ | 担当衛生士制、キッズスペースあり ... |
| `booking_rules` | 予約ルール | | 電話+Web予約、キャンセルポリシー |
| `payment_notes` | 支払い方法 | | 保険、カード、デンタルローン |
| `hiring_targets` | 採用したい職種 | | 歯科衛生士、歯科助手 |
| `tone` | 文体の方向性 | | やわらかく丁寧・患者目線 |
| `notes` | 自由メモ | | 院長は予防重視 |

## ディレクトリ構成

```
specialist-ai-os/
  CLAUDE.md                         ← プロジェクト設定
  README_factory.md                 ← このファイル
  .claude/
    settings.json                   ← 権限・hooks設定
    agents/                         ← サブエージェント
      pack-generator.md             ← パック一括生成
      compliance-reviewer.md        ← コンプラチェック
      copy-refiner.md               ← 文面改善
      offer-architect.md            ← 提案資料設計
    commands/                       ← スラッシュコマンド
      make-pack.md                  ← /make-pack
      review-pack.md                ← /review-pack
      make-onepager.md              ← /make-onepager
    hooks/                          ← フックスクリプト
      pre_bash_check.py             ← Bash安全性チェック
      post_write_check.py           ← Write後の品質チェック
      on_stop_summary.py            ← セッション終了サマリ
  factory/
    input/                          ← 入力YAML（ここだけ変える）
      clinic_profile.example.yaml
    templates/                      ← ベーステンプレート
      faq_base.md
      review_base.md
      recruiting_base.md
      onepager_base.md
    prompts/                        ← LLM連携用プロンプト
      faq_prompt.md                 ← ✅ 正式運用中
      review_prompt.md              ← ✅ 正式運用中
      recruiting_prompt.md          ← ✅ 正式運用中
      onepager_prompt.md
    forms/                          ← フォーム仕様
      form_spec_v1.md               ← フォーム項目定義
      form_to_yaml_mapping.md       ← 回答→YAML変換ルール
      form_response_example.json    ← サンプル回答JSON
      sheets_row_example.json       ← Sheets行JSONサンプル
    n8n/                            ← n8n ワークフロー
      n8n_workflow_v0_2_simple.json ← ✅ 正本（6ノード Simple版）
      GOOGLE_SHEETS_SETUP.md        ← Sheets Trigger セットアップガイド
      ENV_EXAMPLE.md                ← 環境変数の設定例
      n8n_workflow_v0_2.json        ← ⛔ deprecated
      n8n_workflow_v0_1.json        ← ⛔ deprecated
      n8n_workflow_stub.json        ← ⛔ deprecated
    scripts/                        ← 実行スクリプト
      run_pipeline.py               ← ✅ パイプライン一括実行（推奨）
      normalize_sheet_row.py        ← Sheets行→form_response正規化
      create_clinic_profile.py      ← プロフィール対話/JSON作成
      generate_pack.py              ← メイン生成
      validate_pack.py              ← 生成結果検証
  output/generated/
    sample_clinic/                  ← 出力（ここに生成される）
      faq.md
      review_reply.md
      recruiting.md
      sales_onepager.md
      _manifest.json                ← 生成メタ情報
```

## Claude Code プロジェクト機能

### settings.json
- `allow`: generate_pack / validate_pack の実行、pyyaml install、ファイル操作
- `deny`: rm -rf、secrets系、git push、外部通信（curl/wget）
- `hooks`: PreToolUse(Bash), PostToolUse(Write), Stop の3種

### サブエージェント
| エージェント | 役割 |
|-------------|------|
| pack-generator | パック一括生成の実行・検証 |
| compliance-reviewer | 医療広告ガイドライン準拠チェック |
| copy-refiner | 文面のトーン・品質改善 |
| offer-architect | 営業提案資料の構成設計 |

### Hooks
| フック | タイミング | 処理 |
|--------|-----------|------|
| pre_bash_check.py | Bash実行前 | 危険コマンドの検出・ブロック |
| post_write_check.py | Write実行後 | md品質チェック（空ファイル・未解決変数・H1） |
| on_stop_summary.py | セッション終了時 | パック状態をsession_log.jsonlに記録 |

## パイプライン一括実行（推奨）

### run_pipeline.py

4本のスクリプトを1コマンドで順番実行するラッパー。

```bash
cd specialist-ai-os

# 基本（テンプレート方式）
python factory/scripts/run_pipeline.py --input factory/forms/sheets_row_example.json

# slug 指定 + LLM モード
python factory/scripts/run_pipeline.py --input row.json --slug tanaka_dental --llm
```

実行される順番:
```
[1] normalize_sheet_row.py    → row JSON を正規化
[2] create_clinic_profile.py  → 正規化JSON → YAML変換
[3] generate_pack.py          → YAML → 4つのmd生成
[4] validate_pack.py          → 22項目チェック
```

出力: `output/generated/<slug>/` に成果物 + `_pipeline_summary.json`

### n8n 最短手順（v0.2 simple — 正本）

```
[Manual Trigger] → [Setup] → [Run Pipeline] → [PASS or FAIL?] → [PASS] / [FAIL]
```

6ノード。Execute Command 1本で `run_pipeline.py` を呼ぶだけ。

```
1. n8n を起動（npx n8n）
2. factory/n8n/n8n_workflow_v0_2_simple.json をインポート
3. Setup ノードを開く → factoryRoot fallback パスが合っているか確認
   （n8n 環境変数に FACTORY_ROOT を設定済みなら変更不要）
4. Test Workflow ボタンを押す
5. Run Pipeline の stdout に「✅ PASS」が出ればOK
6. IF 分岐で PASS 側に流れていればOK
```

**環境変数**（n8n Settings → Variables で設定）:
| 変数名 | 値 |
|--------|-----|
| `FACTORY_ROOT` | `C:/Users/.../specialist-ai-os` |
| `PYTHON_BIN` | `python`（Windows）or `python3`（Linux/Docker）|
| `ANTHROPIC_API_KEY` | `sk-ant-...`（LLMモード時のみ）|

---

## n8n 実行（⛔ deprecated: 旧9ノード構成）

> **deprecated**: 以下は旧構成。今後は上記の simple 版（`n8n_workflow_v0_2_simple.json`）のみを使う。

### Google Sheets Trigger で自動実行する場合（旧v0.2）

```
Step 1: Google Cloud Console で OAuth 設定（詳細は factory/n8n/GOOGLE_SHEETS_SETUP.md）
  - Google Sheets API と Google Drive API を有効化
  - OAuth クライアント ID を作成
  - リダイレクト URI: http://localhost:5678/rest/oauth2-credential/callback

Step 2: n8n で Credentials を作成
  - タイプ: Google Sheets OAuth2 API
  - Client ID / Secret を入力 → Sign in with Google

Step 3: n8n_workflow_v0_2.json をインポート

Step 4: Sheets Trigger ノードを設定
  - Credential: 作成した Google Sheets OAuth2 を選択
  - Document ID: Google Sheets の URL から取得
  - Sheet Name: 「フォームの回答 1」（Forms連携シートの場合）

Step 5: ワークフローを Active にする

Step 6: Google Forms にテスト回答を送信 → 自動で発火
```

**確認ポイント:**
- Sheets Trigger → Format Row の接続で行データが JSON に書き出されること
- `[3] Normalize` の stdout に「正規化完了」が出ること
- `[8] Result: PASS` まで到達すること

### ワークフロー構成（v0.2）

```
主経路（本番）:
  [Sheets Trigger] → [Format Row] → [3]Normalize → [4]Profile
    → [5]Pack → [6]Validate → [7]IF → [8]PASS / [9]FAIL

テスト経路（Manual）:
  [Test Manual Trigger] → [Test Setup Test Data] → [3]Normalize → ...（同じ）

将来:
  [Future] Slack Notify  (disabled)
```

---

## n8n 実行（v0.1: Manual Trigger のみ）

### 前提

- **n8n**: self-hosted（`npx n8n` or Docker）
- **Python**: n8n が動くマシンに Python 3.8+、PyYAML がインストール済み
- **LLMモード時**: `pip install anthropic` + `ANTHROPIC_API_KEY` 環境変数

### 環境変数

詳細は `factory/n8n/ENV_EXAMPLE.md` を参照。

| 変数名 | 必須 | 説明 | 例 |
|--------|:----:|------|-----|
| `FACTORY_ROOT` | ✅ | specialist-ai-os のフルパス | `C:/Users/tkym1/.../specialist-ai-os` |
| `PYTHON_BIN` | | Python実行パス | `python3` |
| `PYTHONIOENCODING` | | 出力エンコーディング | `utf-8` |
| `ANTHROPIC_API_KEY` | | Claude APIキー（LLM時のみ） | `sk-ant-api03-xxxxx` |

### インポート＆実行手順

```
Step 1: n8n を起動
  npx n8n  (or docker run ...)

Step 2: ブラウザで http://localhost:5678 を開く

Step 3: ワークフローをインポート
  左メニュー → Workflows → Import from File
  → factory/n8n/n8n_workflow_v0_1.json を選択

Step 4: "Setup Test Data" ノードを開いて確認
  - factoryRoot の fallback パスが自分の環境に合っているか
  - FACTORY_ROOT 環境変数を設定済みなら変更不要

Step 5: "Test Workflow" ボタンをクリック（Manual Trigger）

Step 6: 各ノードの実行結果を確認
```

### 確認するノードの順番

| 順番 | ノード名 | 確認すべき stdout |
|:----:|---------|------------------|
| 1 | `[3] Normalize Sheet Row` | `正規化完了` が出ること |
| 2 | `[4] Create Profile` | `保存しました` が出ること |
| 3 | `[5] Generate Pack` | `完了！ 4 ファイル` が出ること |
| 4 | `[6] Validate Pack` | `22 PASS` が出ること |
| 5 | `[7] PASS or FAIL?` | true 側に流れること |
| 6 | `[8] Result: PASS` | `status: "PASS"` が出ること |

**最初に確認すべきは `[3] Normalize Sheet Row`**。ここが通れば残りも通る。

### ワークフロー構成（v0.1）

```
[Manual Trigger]
  → [Setup Test Data]         Code: パス・slug設定
    → [3] Normalize            Execute: normalize_sheet_row.py
      → [Pass Context 1]       Code: setup データ引き継ぎ
        → [4] Create Profile    Execute: create_clinic_profile.py --from-form
          → [Pass Context 2]    Code: setup データ引き継ぎ
            → [5] Generate Pack Execute: generate_pack.py --llm faq review recruiting
              → [Pass Context 3] Code: setup データ引き継ぎ
                → [6] Validate   Execute: validate_pack.py
                  → [7] IF       PASS/FAIL 分岐
                    → [8] PASS   Set: 成功メッセージ
                    → [9] FAIL   Set: エラーメッセージ

[Future] Sheets Trigger  (disabled)
[Future] Slack Notify    (disabled)
```

### 詰まりやすいポイント

| 症状 | 原因 | 対処 |
|------|------|------|
| `python: command not found` | n8n環境にPythonがない | `PYTHON_BIN=python3` を設定、または Setup Test Data の fallback を編集 |
| `ModuleNotFoundError: yaml` | PyYAML 未インストール | `pip install pyyaml` を n8n 環境内で実行 |
| `FACTORY_ROOT` が空 | 環境変数未設定 | Setup Test Data ノード内の fallback パスを直接編集 |
| 日本語が文字化け | stdout エンコーディング | コマンドに `set PYTHONIOENCODING=utf-8` が入っている。Docker なら環境変数でも設定 |
| Execute Command が途中で止まる | 前ノードの context が途切れる | Pass Context ノードが setup データを引き継ぐ。ノードを飛ばさないこと |
| LLMフォールバックのみ | API_KEY 未設定 | テンプレ方式で正常動作。LLM不要なら問題なし |

## 変更履歴

### v0.5.1 (品質 Hardening)
- FAQ: Q4 キャンセルポリシー文の重複バグ修正（「前日までに連絡にご連絡」→「前日までにご連絡」）
- FAQ: 支払い方法の文面を自然な日本語に改善（「保険診療・クレジットカード」→「保険診療に対応。自費にはカード利用可」）
- FAQ: キッズスペースを入力に明記がない限り断定しない（保守的fallback）
- 求人文: 3職種固定構成（歯科衛生士/歯科助手・受付/勤務医）に変更、空欄禁止
- 求人文: 「求める人物像」セクション追加、メリット最低3個保証
- validate_pack.py: 4チェック追加（重複フレーズ/3職種確認/空箇条書き/求める人物像）→ 22→26項目
- 未確認情報は断定せず「お問い合わせください」で保守的に扱う方針を確定

### v0.5.0 (Simple版を正本化 + 旧版deprecated)
- `n8n_workflow_v0_2_simple.json` の環境変数参照を `process.env` → `$env` に修正（n8n正式API）
- 旧9ノード版（v0_1.json, v0_2.json, stub.json）を deprecated に変更
- README に最短手順（6ステップ）を追記

### v0.4.9 (Pipeline Runner + n8n Simple)
- `run_pipeline.py` を新規作成（4本のスクリプトを順番実行するラッパー）
- `n8n_workflow_v0_2_simple.json` を新規作成（6ノード構成: Trigger→Setup→Run Pipeline→IF→PASS/FAIL）
- 9ノード構成（v0.1/v0.2）を参考扱いに変更
- E2E確認済み: 全4ステップ OK、22 PASS、`_pipeline_summary.json` 出力

### v0.4.8 (n8n v0.2: Sheets Trigger 実接続)
- `n8n_workflow_v0_2.json` を新規作成（主経路: Sheets Trigger、テスト経路: Manual Trigger を併存）
- Format Row ノード追加（Sheets行データ → JSON一時ファイル → normalize用パス組み立て）
- Pass Context ノードの参照先を `Setup Test Data` → `Format Row` に変更
- `GOOGLE_SHEETS_SETUP.md` を新規作成（Cloud Console / OAuth / Trigger設定の全手順）
- README に Sheets Trigger 経由の実行手順・確認ポイントを追記

### v0.4.7 (n8n Workflow v0.1 実装)
- `n8n_workflow_v0_1.json` を新規作成（実装版、Manual Trigger ベース）
- Execute Command 4本の間に Pass Context ノードを挿入（setup データの引き継ぎ）
- `PYTHON_BIN` 環境変数対応（Docker/Linux 環境で `python3` を使える）
- `PYTHONIOENCODING=utf-8` をコマンドに前置（Windows文字化け対策）
- `onError: continueRegularOutput` で各ノードがエラー時も次に進む
- Result ノードに stdout/outputDir の詳細を含める
- `ENV_EXAMPLE.md` を新規作成（Windows/Linux/Docker の設定例）
- README に n8n v0.1 のインポート・実行・確認手順を追記

### v0.4.6 (n8n Manual Test stub)
- `n8n_workflow_stub.json` を Manual Trigger ベースに更新（設計段階のたたき台）

### v0.4.5 (n8n Workflow Spec)
- `factory/n8n/n8n_workflow_spec_v1.md` を追加（9ノード構成のパイプライン設計書）
- `factory/n8n/n8n_nodes_mapping_v1.md` を追加（ノード定義・入出力・エラー時挙動）
- `factory/n8n/n8n_workflow_stub.json` を追加（n8nインポート用のたたき台JSON）
- Phase 1〜4のテスト計画を定義（ローカル単体→n8n単体→結合→本番）

### v0.4.4 (Sheets Row Adapter)
- `normalize_sheet_row.py` を追加（Sheets行JSON → form_response JSON 正規化）
- 列名ゆれ吸収: `Q1_医院名` / `医院名` / `clinic_name` 等 12キー×3〜7パターン
- checkbox系はカンマ区切り文字列・配列の両対応
- 不明な列は warning に出すが全体は止めない
- E2E確認済み: sheets行JSON → normalize → from-form → pack → validate 全22PASS

### v0.4.3 (--from-form 実装)
- `create_clinic_profile.py --from-form response.json` を実装
- `factory/forms/form_response_example.json` にサンプル回答を追加
- Q10（採用詳細）パーサー実装（「職種：内容」形式の分離、短縮形マッチ、パース失敗時notes退避）
- E2E確認済み: JSON → YAML → generate_pack → validate_pack 全22チェックPASS

### v0.4.2 (Form Spec)
- `factory/forms/form_spec_v1.md` を追加（12問・4分で完了するフォーム仕様）
- `factory/forms/form_to_yaml_mapping.md` を追加（回答→YAML変換ルール全12項目）

### v0.4.1 (Clinic Profile Builder)
- `create_clinic_profile.py` を追加（対話形式でYAML生成）
- 必須項目バリデーション、プレビュー表示、確認後保存
- `generate_pack.py` → `validate_pack.py` とのE2E連携を確認済み

### v0.4
- 求人文テンプレに `--llm recruiting` オプションを追加（Claude API連携）
- `factory/prompts/recruiting_prompt.md` を正式化（3職種構成・出力形式・ルールを明記）
- `profile_to_strings()` に `hiring_targets` フィールドを追加
- `--llm faq review recruiting` で3成果物の同時LLM化に対応
- Sales Onepager のみテンプレ方式のまま残す方針を確定

### v0.3
- 口コミ返信テンプレに `--llm review` オプションを追加（Claude API連携）
- `factory/prompts/review_prompt.md` を正式化（出力形式・テンプレ構成・ルールを明記）
- LLM呼び出しの共通化（`call_llm()`, `profile_to_strings()` ヘルパー抽出）
- `--llm faq review` で複数成果物の同時LLM化に対応

### v0.2
- FAQ生成に `--llm faq` オプションを追加（Claude API連携）
- APIキー未設定/エラー時のテンプレートフォールバック機能
- `_manifest.json` に `generation_modes` フィールドを追加
- `factory/prompts/faq_prompt.md` を正式化
- Windows cp932 エンコーディング対策

## まだ手作業の部分

- ~~YAML入力（院長ヒアリング → 手動記入）~~ → `create_clinic_profile.py` で半自動化済み
- ヒアリング自体は対面 or 電話（まだ自動化対象外）
- 生成後の文面レビュー・微調整
- sales_onepager はテンプレ方式のまま（構造がテーブル＋定型のためLLM効果薄）
- APIキーの設定は手動（環境変数）

## フォーム連携ロードマップ

### 現在（v0.4.4）: Sheets Row Adapter 実装済み
- ローカルパイプライン全ステップがCLIで接続完了
- Sheets行JSON → normalize → from-form → YAML → pack → validate

```bash
# 一気通貫パイプライン（Sheets行JSONから最終成果物まで）
python factory/scripts/normalize_sheet_row.py --input row.json \
  && python factory/scripts/create_clinic_profile.py --from-form factory/forms/form_response_from_sheet.json \
  && python factory/scripts/generate_pack.py --profile factory/input/clinic_profile.generated.yaml --llm faq review recruiting \
  && python factory/scripts/validate_pack.py
```

### 現在（v0.4.8）: n8n v0.2 Sheets Trigger 実装済み

`factory/n8n/n8n_workflow_v0_2.json` で Sheets Trigger → Format Row → 内側4本 → PASS/FAIL が接続済み。

```
主経路:  [Sheets Trigger] → [Format Row] → [3]〜[7] → [8]PASS / [9]FAIL
テスト:  [Manual Trigger] → [Setup] → [3]〜[7]（同じ内側チェーン）
```

### 次段階: Slack 通知

1. **Slack App を作成** — Slack API で Bot Token を取得
2. **n8n に Slack Credentials を追加**
3. **disabled の Slack ノードを有効化** — [8]PASS / [9]FAIL の後に接続
4. 通知テスト

## 次に何を自動化対象に広げるべきか

1. **n8n連携**: Google Forms → Sheets → n8n Webhook → `--from-form` → `generate_pack` → Slack通知
3. **業種横展開**: 歯科以外（整骨院・美容クリニック等）のテンプレートセット追加
4. **MCP Server化**: factory 全体をMCP Serverとしてラップし、Claude Code からネイティブに呼び出せる構成に

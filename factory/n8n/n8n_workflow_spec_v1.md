# n8n Workflow Spec v0.1 — Product Factory Pipeline

## 目的

Google Forms で歯科医院プロフィールを受け取り、4つのMarkdownテンプレートパック（FAQ・口コミ返信・求人文・Sales Onepager）を自動生成し、結果を通知する。

## 前提

- **n8n**: self-hosted（Docker or npm）を前提。n8n Cloud でも Execute Command を Webhook + 外部サーバー呼び出しに差し替えれば動く
- **Python環境**: n8n が動くマシンに Python 3.8+、PyYAML、anthropic（LLMモード時）がインストール済み
- **specialist-ai-os**: n8n マシンのローカルにクローン済み。パスは環境変数 `FACTORY_ROOT` で指定
- **Google Sheets**: Forms の回答が自動でシートに溜まる前提（Forms のデフォルト動作）
- **ANTHROPIC_API_KEY**: LLMモード利用時は n8n の環境変数にセット済み

## ノード順

```
[1] Google Sheets Trigger
 │  新規行を検出
 ↓
[2] Code（JSON整形）
 │  Sheets行 → normalize用JSON
 ↓
[3] Execute Command: normalize_sheet_row.py
 │  列名ゆれ吸収 → form_response JSON
 ↓
[4] Execute Command: create_clinic_profile.py --from-form
 │  JSON → clinic_profile YAML
 ↓
[5] Execute Command: generate_pack.py
 │  YAML → 4つのMarkdown + manifest
 ↓
[6] Execute Command: validate_pack.py
 │  22項目チェック
 ↓
[7] IF（PASS / FAIL 分岐）
 ├─ PASS → [8a] Slack通知（成功）
 └─ FAIL → [8b] Slack通知（失敗 + エラー内容）
```

## 各ノード詳細

### [1] Google Sheets Trigger

- **タイプ**: Google Sheets Trigger（Polling）
- **監視対象**: Forms 回答シートの新規行
- **ポーリング間隔**: 5分（十分。リアルタイム不要）
- **出力**: シート1行のキーバリュー（列名 → 値）

### [2] Code（JSON整形）

- **タイプ**: Code ノード（JavaScript）
- **役割**: Sheets行データを `sheets_row_example.json` 形式のJSONファイルとして `/tmp/` に書き出す
- **処理**:
  1. Sheetsの列データをそのままJSON化（列名ゆれはnormalizeが吸収するので変換不要）
  2. clinic_name からファイル名用スラグを生成（例: `yamada_dental`）
  3. `/tmp/factory_row_{timestamp}.json` に書き出す
- **出力**: JSONファイルパスと clinic スラグ

```javascript
// n8n Code ノード擬似コード
const row = $input.first().json;
const timestamp = Date.now();
const filePath = `/tmp/factory_row_${timestamp}.json`;

// Sheets行をそのまま書き出し（normalizeが列名ゆれを吸収）
const fs = require('fs');
fs.writeFileSync(filePath, JSON.stringify(row, null, 2), 'utf-8');

// clinic名からスラグ生成
const clinicName = row['Q1_医院名'] || row['医院名'] || row['clinic_name'] || 'unknown';
const slug = clinicName.replace(/[^a-zA-Z0-9\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]/g, '_').substring(0, 30);

return [{ json: { filePath, slug, clinicName } }];
```

### [3] Execute Command: normalize_sheet_row.py

- **コマンド**:
  ```bash
  cd $FACTORY_ROOT && python factory/scripts/normalize_sheet_row.py \
    --input {{ $json.filePath }} \
    --output /tmp/factory_response_{{ $json.slug }}.json
  ```
- **出力**: 正規化済みJSONファイルパス

### [4] Execute Command: create_clinic_profile.py

- **コマンド**:
  ```bash
  cd $FACTORY_ROOT && python factory/scripts/create_clinic_profile.py \
    --from-form /tmp/factory_response_{{ $json.slug }}.json \
    --output factory/input/{{ $json.slug }}.yaml
  ```
- **出力**: YAMLファイルパス

### [5] Execute Command: generate_pack.py

- **コマンド**:
  ```bash
  cd $FACTORY_ROOT && python factory/scripts/generate_pack.py \
    --profile factory/input/{{ $json.slug }}.yaml \
    --output output/generated/{{ $json.slug }} \
    --llm faq review recruiting
  ```
- **出力**: パックディレクトリパス

### [6] Execute Command: validate_pack.py

- **コマンド**:
  ```bash
  cd $FACTORY_ROOT && python factory/scripts/validate_pack.py \
    --pack output/generated/{{ $json.slug }}
  ```
- **出力**: 終了コード（0=PASS, 1=FAIL）+ stdout

### [7] IF（PASS / FAIL 分岐）

- **条件**: validate の終了コードが 0 なら PASS
- **PASS時**: [8a] へ
- **FAIL時**: [8b] へ

### [8a] Slack通知（成功）

- **メッセージ例**:
  ```
  ✅ Product Factory: やまだ歯科医院 のパックを生成しました
  - FAQ: llm
  - 口コミ返信: llm
  - 求人文: llm
  - Sales Onepager: template
  - 検証: 22 PASS / 0 WARN / 0 FAIL
  出力先: output/generated/yamada_dental/
  ```

### [8b] Slack通知（失敗）

- **メッセージ例**:
  ```
  ❌ Product Factory: やまだ歯科医院 のパック生成で問題が発生
  - エラー内容: recruiting.md で未解決変数が検出
  - 要確認: output/generated/yamada_dental/
  ```

## エラーハンドリング

| ノード | 失敗時の挙動 |
|--------|-------------|
| [1] Sheets Trigger | n8n が自動リトライ（ポーリング間隔で） |
| [2] Code | ワークフロー停止 → Error Workflow で通知 |
| [3] normalize | 終了コード!=0 → [8b] 通知。列名不明は warning だけで続行 |
| [4] create_profile | 終了コード!=0 → [8b] 通知。必須項目不足でも YAML は生成される |
| [5] generate_pack | 終了コード!=0 → [8b] 通知。LLM失敗はテンプレにフォールバック |
| [6] validate | 終了コード!=0 → [8b] 通知。WARN は PASS 扱い |
| [7-8] 通知 | Slack接続エラー → n8n Error Workflow で別途通知 |

**原則: 各スクリプトが既にフォールバックを持つので、Execute Command の終了コードだけ見ればよい。**

## 将来の拡張ポイント

| 拡張 | 位置 | 内容 |
|------|------|------|
| メール通知 | [8a]/[8b] の並列 | 院長や営業担当にメール通知 |
| Google Drive 保存 | [6] の後 | 生成mdをDriveにアップロード |
| Notion DB 登録 | [6] の後 | 生成結果のメタ情報をNotionに記録 |
| 品質レビュー | [6] と [7] の間 | compliance-reviewer エージェント呼び出し |
| 複数院バッチ | [1] を Cron Trigger に | CSVインポートで一括処理 |

## 本番接続前にテストすること

### Phase 1: ローカル単体テスト（済み）
- [x] normalize_sheet_row.py 単体動作
- [x] create_clinic_profile.py --from-form 単体動作
- [x] generate_pack.py テンプレ/LLMモード
- [x] validate_pack.py 全PASS確認
- [x] E2E パイプライン（sheets JSON → validate）

### Phase 2: n8n 単体テスト（次のステップ）
- [ ] n8n に workflow stub をインポートできること
- [ ] Execute Command ノードで Python スクリプトが呼べること
- [ ] FACTORY_ROOT パスが正しく解決されること
- [ ] ANTHROPIC_API_KEY が n8n 環境変数から渡ること
- [ ] 各ノードの stdout/stderr が次ノードに渡ること

### Phase 3: 結合テスト
- [ ] Sheets Trigger でテスト行を検出できること
- [ ] [1]→[6] が通しで動くこと
- [ ] LLMフォールバックが n8n 上でも動くこと
- [ ] Slack 通知が届くこと

### Phase 4: 本番投入
- [ ] 本番 Google Forms を接続
- [ ] Slack チャンネルを本番用に切り替え
- [ ] エラー通知の宛先を設定
- [ ] 監視（n8n Executions ログ）を確認

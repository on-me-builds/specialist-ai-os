# n8n Nodes Mapping v0.1

## ノード一覧

| # | ノード名 | n8nノードタイプ | 役割 | 入力 | 出力 | 次ノードへ渡すデータ | 失敗時 |
|---|---------|---------------|------|------|------|-------------------|--------|
| 1 | Sheets Trigger | Google Sheets Trigger | 新規行検出 | (なし・ポーリング) | シート1行のKV | `{ row: {...} }` | 自動リトライ |
| 2 | Format Row | Code | Sheets行→JSON整形 | row KV | JSONファイルパス | `{ filePath, slug, clinicName }` | ワークフロー停止 |
| 3 | Normalize | Execute Command | 列名ゆれ吸収 | filePath | 正規化JSON | `{ normalizedPath, slug }` | [8b]通知 |
| 4 | Create Profile | Execute Command | JSON→YAML変換 | normalizedPath | YAMLパス | `{ profilePath, slug }` | [8b]通知 |
| 5 | Generate Pack | Execute Command | YAML→4md生成 | profilePath | パックDir | `{ packDir, slug }` | [8b]通知 |
| 6 | Validate Pack | Execute Command | 22項目チェック | packDir | 終了コード+stdout | `{ exitCode, stdout, slug }` | [8b]通知 |
| 7 | Check Result | IF | PASS/FAIL分岐 | exitCode | (分岐) | - | - |
| 8a | Notify Success | Slack | 成功通知 | clinicName, stdout | (なし) | - | Error Workflow |
| 8b | Notify Failure | Slack | 失敗通知 | clinicName, stderr | (なし) | - | Error Workflow |

---

## 各ノード詳細

### [1] Sheets Trigger

```
ノードタイプ: Google Sheets Trigger
認証: Google OAuth2（要設定）
設定:
  - Document: フォーム回答シートのID
  - Sheet: Sheet1（デフォルト）
  - Trigger On: Row Added
  - Poll Times: Every 5 Minutes
出力:
  $json = {
    "タイムスタンプ": "2026/03/22 10:30:00",
    "Q1_医院名": "やまだ歯科医院",
    "Q2_医院のタイプ": "...",
    ...
  }
```

### [2] Format Row

```
ノードタイプ: Code (JavaScript)
入力: $input.first().json（Sheets行）
処理:
  1. rowをJSONファイルとして /tmp/ に書き出す
  2. clinic_name からスラグを生成
出力:
  {
    filePath: "/tmp/factory_row_1711090200.json",
    slug: "yamada_dental",
    clinicName: "やまだ歯科医院"
  }
```

### [3] Normalize

```
ノードタイプ: Execute Command
コマンド:
  cd $FACTORY_ROOT && python factory/scripts/normalize_sheet_row.py \
    --input {{ $json.filePath }} \
    --output /tmp/factory_response_{{ $json.slug }}.json
成功時出力:
  {
    normalizedPath: "/tmp/factory_response_yamada_dental.json",
    slug: "yamada_dental",
    clinicName: "やまだ歯科医院"
  }
失敗時: 終了コード!=0 → [8b]
```

### [4] Create Profile

```
ノードタイプ: Execute Command
コマンド:
  cd $FACTORY_ROOT && python factory/scripts/create_clinic_profile.py \
    --from-form /tmp/factory_response_{{ $json.slug }}.json \
    --output factory/input/{{ $json.slug }}.yaml
成功時出力:
  {
    profilePath: "factory/input/yamada_dental.yaml",
    slug: "yamada_dental",
    clinicName: "やまだ歯科医院"
  }
失敗時: 終了コード!=0 → [8b]
```

### [5] Generate Pack

```
ノードタイプ: Execute Command
コマンド:
  cd $FACTORY_ROOT && python factory/scripts/generate_pack.py \
    --profile factory/input/{{ $json.slug }}.yaml \
    --output output/generated/{{ $json.slug }} \
    --llm faq review recruiting
成功時出力:
  {
    packDir: "output/generated/yamada_dental",
    slug: "yamada_dental",
    clinicName: "やまだ歯科医院"
  }
失敗時: 終了コード!=0 → [8b]（LLM失敗はスクリプト内でフォールバック）
```

### [6] Validate Pack

```
ノードタイプ: Execute Command
コマンド:
  cd $FACTORY_ROOT && python factory/scripts/validate_pack.py \
    --pack output/generated/{{ $json.slug }}
成功時出力:
  {
    exitCode: 0,
    stdout: "結果: ✅ 22 PASS / ⚠️ 0 WARN / ❌ 0 FAIL",
    slug: "yamada_dental",
    clinicName: "やまだ歯科医院"
  }
失敗時: exitCode=1 → [7] → [8b]
```

### [7] Check Result

```
ノードタイプ: IF
条件: {{ $json.exitCode }} == 0
true → [8a]
false → [8b]
```

### [8a] Notify Success

```
ノードタイプ: Slack
チャンネル: #product-factory（要設定）
メッセージ:
  ✅ *{{ $json.clinicName }}* のパックを生成しました
  {{ $json.stdout }}
  出力先: output/generated/{{ $json.slug }}/
```

### [8b] Notify Failure

```
ノードタイプ: Slack
チャンネル: #product-factory（要設定）
メッセージ:
  ❌ *{{ $json.clinicName }}* のパック生成で問題が発生
  {{ $json.stderr || $json.stdout }}
  要確認: output/generated/{{ $json.slug }}/
```

---

## データフロー図

```
[1] Sheets → row KV
      ↓
[2] Code → { filePath, slug, clinicName }
      ↓
[3] normalize → { normalizedPath, slug, clinicName }
      ↓
[4] create_profile → { profilePath, slug, clinicName }
      ↓
[5] generate_pack → { packDir, slug, clinicName }
      ↓
[6] validate → { exitCode, stdout, slug, clinicName }
      ↓
[7] IF exitCode==0 ?
   ├─ YES → [8a] Slack ✅
   └─ NO  → [8b] Slack ❌
```

slug と clinicName は全ノードでパススルーする。

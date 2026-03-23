# Form → YAML 変換マッピング v1

## 概要

フォーム回答（Google Forms / Notion / webhook JSON）を `clinic_profile.yaml` に変換するためのルール定義。
`create_clinic_profile.py --from-form` の実装仕様としても使う。

---

## 変換ルール一覧

| # | Form項目名 | YAMLキー | 型変換 | 複数選択時 | 空欄時 | 正規化 | 備考 |
|---|-----------|----------|--------|-----------|--------|--------|------|
| 1 | 医院名 | `clinic_name` | そのまま string | - | **エラー（必須）** | 前後空白trim | |
| 2 | 医院のタイプ | `target_type` | そのまま string | - | `"一般歯科〜自費を少し扱う歯科医院"` | 「その他」は自由記入値を採用 | |
| 3 | 診療内容 | `services` | → YAML list | カンマ区切り → list | **エラー（必須）** | 選択肢の正式名称に正規化 | ※1 |
| 4 | 医院の特徴 | `features` | → YAML list | カンマ区切り → list | **エラー（必須）** | 選択肢の正式名称に正規化 | ※1 |
| 5 | 予約方法 | `booking_rules.system` | そのまま string | - | `"電話 + Web予約"` | | |
| 6 | キャンセルポリシー | `booking_rules.cancel_policy` | そのまま string | - | `"前日までに連絡"` | | |
| 7 | 保険診療 | `payment_notes.insurance` | `"はい"` → `true` / `"いいえ"` → `false` | - | `true` | | |
| 8 | 自費お支払い方法 | `payment_notes.self_pay_options` | → YAML list | カンマ区切り → list | `[]` | | |
| 9 | 募集職種 | `hiring_targets[].position` | → list of dict | カンマ区切り → 各dict | `[]` | | ※2 |
| 10 | 採用詳細 | `hiring_targets[].experience`, `.highlight` | パース → dict | 改行区切り | デフォルト文面 | | ※3 |
| 11 | トーン | `tone` | そのまま string | - | `"やわらかく丁寧・患者目線"` | 「その他」は自由記入値を採用 | |
| 12 | その他メモ | `notes` | そのまま string | - | キー省略 | | |

---

## 詳細ルール

### ※1 services / features の正規化

checkboxの選択肢はフォーム側で正式名称を定義済み。
「その他（自由記入）」で入力された値はそのまま追加する。

```
フォーム回答: "一般歯科（虫歯・歯周病), 予防歯科・メンテナンス, レーザー治療"
                ↓
YAML:
services:
  - 一般歯科（虫歯・歯周病）
  - 予防歯科・メンテナンス
  - レーザー治療          ← 「その他」からそのまま
```

### ※2 hiring_targets の組み立て

Q9（募集職種 checkbox）から position のリストを作り、
Q10（採用詳細 long text）から experience / highlight を割り当てる。

```
Q9回答: "歯科衛生士, 歯科助手・受付"
Q10回答: "衛生士：経験者歓迎、担当患者制でやりがい\n助手：未経験OK"
                ↓
hiring_targets:
  - position: "歯科衛生士"
    experience: "経験者歓迎"
    highlight: "担当患者制でやりがい"
  - position: "歯科助手・受付"
    experience: "未経験OK"
    highlight: ""
```

### ※3 Q10パースルール（採用詳細）

**最も変換が難しい項目。** 以下の優先順位でパースする:

1. **「職種：内容」形式を検出** → コロン区切りで分割
2. **改行で複数職種を分離** → 各行を対応するpositionに割り当て
3. **パース不能な場合** → notes に「採用詳細（要手動整理）: 原文」として退避
4. **空欄の場合** → Q9のpositionだけでdictを作り、experience/highlightは空文字

---

## booking_rules の組み立て

Q5, Q6 + デフォルト値から構築する。

```yaml
booking_rules:
  system: "{Q5の回答 or デフォルト}"
  cancel_policy: "{Q6の回答 or デフォルト}"
  first_visit_note: "初回は30分〜1時間程度"   # 常にデフォルト（フォームでは聞かない）
```

`first_visit_note` はフォームで聞くほどではないため、常にデフォルト値を入れる。

## payment_notes の組み立て

```yaml
payment_notes:
  insurance: true/false    # Q7
  self_pay_options:        # Q8（空なら空list）
    - クレジットカード
    - デンタルローン
  price_note: "自費治療は事前にお見積もりをお出しします"  # 常にデフォルト
```

`price_note` はフォームで聞かず、デフォルト値を入れる。

---

## 人判断が必要な項目

| 項目 | 理由 | 対処 |
|------|------|------|
| Q10（採用詳細） | 自由記述のパースが不安定 | パース失敗時は notes に退避し、手動整理を促す |
| Q4 + 「その他」 | 自由記入が features の品質を左右する | 生成後にレビューで調整 |
| Q2 で「その他」を選んだ場合 | target_type が想定外の値になりうる | onepager の課題セクションが最適化されない可能性 |

---

## 想定データフロー

```
Google Forms 回答
  → Google Sheets（自動）
  → CSV or JSON エクスポート
  → create_clinic_profile.py --from-form data.json
  → factory/input/clinic_profile.generated.yaml
  → generate_pack.py --profile ... --llm faq review recruiting
  → output/generated/xxx/

将来（n8n接続時）:
  Google Forms → Sheets → n8n Webhook
  → create_profile API → generate_pack API → 通知
```

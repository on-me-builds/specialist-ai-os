# /make-onepager コマンド

Sales Onepager のみを再生成する。営業提案資料の反復改善用。

## 手順

1. プロフィールYAMLを読み込む
   - `factory/input/` から指定プロフィールを読む
   - `target_type`, `services`, `features` を確認する

2. 既存の onepager を確認する（あれば）
   - `output/generated/sample_clinic/sales_onepager.md` を読む
   - 改善すべき点を把握する

3. 生成を実行する
   ```bash
   python factory/scripts/generate_pack.py --profile factory/input/clinic_profile.example.yaml
   ```
   ※ 全4ファイルが再生成されるが、主眼は sales_onepager.md

4. 生成された sales_onepager.md を表示して確認する

5. 改善提案があれば報告する
   - 課題セクションの追加候補
   - ターゲットに合わせた表現改善
   - 構成の見直し案

## 引数
- `$ARGUMENTS` にプロフィールのパスが渡された場合、そのパスを使用する

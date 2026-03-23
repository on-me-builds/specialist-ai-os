# /make-pack コマンド

クリニックプロフィールからテンプレートパック（FAQ・口コミ返信・求人文・Sales Onepager）を一括生成し、検証する。

## 手順

1. プロフィールYAMLの確認
   - `factory/input/` にある指定プロフィール（デフォルト: `clinic_profile.example.yaml`）を読み込む
   - 必須フィールド（clinic_name, services, features）の存在を確認する

2. パック生成
   ```bash
   python factory/scripts/generate_pack.py --profile factory/input/clinic_profile.example.yaml
   ```

3. パック検証
   ```bash
   python factory/scripts/validate_pack.py
   ```

4. 結果報告
   - 生成されたファイル一覧
   - validate結果（PASS/WARN/FAIL）
   - FAILがあれば原因と対処を報告

## 引数
- `$ARGUMENTS` にプロフィールのパスが渡された場合、そのパスを `--profile` に使用する
- 引数なしの場合はデフォルトのexampleプロフィールを使用する

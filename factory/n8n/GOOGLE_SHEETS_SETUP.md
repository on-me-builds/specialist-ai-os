# Google Sheets Trigger セットアップガイド

## 概要

Google Forms の回答が Google Sheets に追加されたとき、Product Factory パイプラインを自動実行する。

## 前提

- Google Forms で入力フォームを作成済み
- 回答先の Google Sheets が存在する
- n8n が self-hosted で動作している

## Step 1: Google Cloud Console 側の設定

### 1-1. プロジェクト作成

1. https://console.cloud.google.com/ にアクセス
2. 「プロジェクトを選択」→「新しいプロジェクト」
3. プロジェクト名: `product-factory`（任意）

### 1-2. API を有効化

1. 左メニュー「APIとサービス」→「ライブラリ」
2. 以下を検索して有効化:
   - **Google Sheets API**
   - **Google Drive API**

### 1-3. OAuth 同意画面

1. 「APIとサービス」→「OAuth同意画面」
2. ユーザーの種類: **外部**（テスト段階ではこれでOK）
3. アプリ名: `Product Factory n8n`
4. スコープ: `https://www.googleapis.com/auth/spreadsheets.readonly`
5. テストユーザーに自分の Google アカウントを追加

### 1-4. OAuth クライアント ID 作成

1. 「APIとサービス」→「認証情報」→「認証情報を作成」→「OAuthクライアントID」
2. アプリの種類: **ウェブアプリケーション**
3. 承認済みリダイレクト URI: `http://localhost:5678/rest/oauth2-credential/callback`
   - n8n を別ポートで動かしている場合はそのポートに変更
4. 作成後、**クライアントID** と **クライアントシークレット** をコピー

## Step 2: n8n Credentials 側の設定

1. n8n の左メニュー → **Credentials** → **Add Credential**
2. タイプ: **Google Sheets OAuth2 API**
3. 入力:
   - Client ID: Step 1-4 でコピーしたもの
   - Client Secret: Step 1-4 でコピーしたもの
4. 「Sign in with Google」ボタンをクリック
5. Google アカウントでログイン → 権限を許可
6. 「Connected」と表示されれば成功

## Step 3: ワークフローの設定

### 3-1. インポート

1. `factory/n8n/n8n_workflow_v0_2.json` を n8n にインポート

### 3-2. Sheets Trigger ノードの設定

1. **Sheets Trigger** ノードをダブルクリック
2. **Credential**: Step 2 で作成した Google Sheets OAuth2 を選択
3. **Document ID**: Google Sheets の URL から ID を取得
   ```
   https://docs.google.com/spreadsheets/d/<<この部分>>/edit
   ```
   この `<<この部分>>` を `documentId` に設定
4. **Sheet Name**: `フォームの回答 1`（Google Forms のデフォルト）
   - シート名が違う場合は実際の名前に変更
5. **Event**: `Row Added`
6. **Poll Times**: `Every 5 Minutes`（テスト後に調整可）

### 3-3. テスト実行

1. ワークフローを **Active** にする前に、まず Manual Trigger 経路でテスト:
   - `[Test] Manual Trigger` → `[Test] Setup Test Data` → `[3]`〜`[7]` が通ることを確認
2. 次に Sheets Trigger をテスト:
   - ノードを選択 → 「Listen for Test Event」をクリック
   - Google Forms に1件テスト回答を送信
   - Trigger がデータを検出したら「Test Workflow」

## Step 4: テスト用フォーム回答

Google Forms に以下を入力してテスト:

| 質問 | 入力例 |
|------|--------|
| 医院名 | テスト歯科クリニック |
| 医院のタイプ | 一般歯科 |
| 診療内容 | 一般歯科、予防歯科、小児歯科 |
| 特徴 | 土曜診療、駅近 |
| 予約方法 | 電話 + Web予約 |
| キャンセルポリシー | 前日までに連絡 |
| 保険診療 | はい |
| 自費支払い方法 | クレジットカード |
| 募集職種 | 歯科衛生士, 歯科助手 |
| 採用詳細 | 衛生士：経験者歓迎 |
| トーン | やわらかく丁寧 |
| その他メモ | テスト入力です |

## よくある詰まりどころ

| 症状 | 原因 | 対処 |
|------|------|------|
| 「Access Not Configured」 | Google Sheets API が無効 | Cloud Console で API を有効化 |
| 「redirect_uri_mismatch」 | リダイレクト URI 不一致 | Cloud Console の URI を n8n のポートに合わせる |
| 「This app isn't verified」 | OAuth同意画面が未公開 | 「Continue」を押して進む（テスト用なので問題なし） |
| Trigger が発火しない | ポーリング間隔内に確認した | 5分待つ、またはノードの「Listen for Test Event」を使う |
| シート名エラー | シート名が違う | Google Sheets の実際のタブ名を確認（「フォームの回答 1」等） |
| 列名が取れない | Sheets の1行目がヘッダーでない | Forms 連携のシートは自動でヘッダーが入る。手動シートの場合は1行目をヘッダーにする |
| 日本語の列名が化ける | n8n のエンコーディング | n8n v2.x では通常問題ない。Docker なら `LANG=C.UTF-8` を追加 |

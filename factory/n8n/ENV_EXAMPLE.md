# n8n 環境変数設定

Product Factory v0.1 を n8n で動かすために必要な環境変数。

## 必須

| 変数名 | 説明 | 例 |
|--------|------|-----|
| `FACTORY_ROOT` | specialist-ai-os のフルパス | `C:/Users/tkym1/OneDrive/ドキュメント/Obsidian Vault/specialist-ai-os` |

## 推奨

| 変数名 | 説明 | デフォルト | 例 |
|--------|------|-----------|-----|
| `PYTHON_BIN` | Python 実行ファイルパス | `python` | `python3`, `/usr/bin/python3` |
| `PYTHONIOENCODING` | Python の出力エンコーディング | （なし） | `utf-8` |
| `ANTHROPIC_API_KEY` | Claude API キー（LLMモード時のみ） | （なし） | `sk-ant-api03-xxxxx` |

## 設定方法

### Windows（PowerShell）

```powershell
$env:FACTORY_ROOT = "C:\Users\tkym1\OneDrive\ドキュメント\Obsidian Vault\specialist-ai-os"
$env:PYTHON_BIN = "python"
$env:PYTHONIOENCODING = "utf-8"
$env:ANTHROPIC_API_KEY = "sk-ant-api03-xxxxx"
```

### Linux / macOS

```bash
export FACTORY_ROOT="/home/user/specialist-ai-os"
export PYTHON_BIN="python3"
export PYTHONIOENCODING="utf-8"
export ANTHROPIC_API_KEY="sk-ant-api03-xxxxx"
```

### Docker（n8n）

```bash
docker run -d \
  -e FACTORY_ROOT=/data/specialist-ai-os \
  -e PYTHON_BIN=python3 \
  -e PYTHONIOENCODING=utf-8 \
  -e ANTHROPIC_API_KEY=sk-ant-api03-xxxxx \
  -v /path/to/specialist-ai-os:/data/specialist-ai-os \
  -p 5678:5678 \
  n8nio/n8n
```

### npx（ローカル）

```bash
FACTORY_ROOT=/path/to/specialist-ai-os \
PYTHON_BIN=python3 \
PYTHONIOENCODING=utf-8 \
npx n8n
```

## 注意事項

- `FACTORY_ROOT` 未設定の場合、Setup Test Data ノード内の fallback パスが使われる
- `PYTHON_BIN` 未設定の場合は `python` がデフォルト（Docker環境では `python3` が必要な場合あり）
- `ANTHROPIC_API_KEY` 未設定でも動く（テンプレート方式にフォールバック）
- Windows パスにスペースが含まれる場合はダブルクォートで囲む

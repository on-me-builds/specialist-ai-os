#!/usr/bin/env python3
"""
PostToolUse Hook: Write 後の簡易チェック
.md ファイルが書き出された場合、基本的な品質チェックを行う。
"""
import json
import sys
from pathlib import Path


def main():
    try:
        tool_input = json.loads(sys.argv[1]) if len(sys.argv) > 1 else {}
        file_path = tool_input.get("file_path", "")
    except (json.JSONDecodeError, IndexError):
        return

    if not file_path.endswith(".md"):
        return

    path = Path(file_path)
    if not path.exists():
        return

    content = path.read_text(encoding="utf-8")
    issues = []

    # 空ファイルチェック
    if len(content.strip()) < 10:
        issues.append("ファイルがほぼ空です")

    # 未解決変数チェック
    import re
    unresolved = re.findall(r"\{[a-z_]+\}", content)
    if unresolved:
        issues.append(f"未解決の変数: {', '.join(set(unresolved))}")

    # H1ヘッダーチェック
    if not content.strip().startswith("#"):
        issues.append("H1ヘッダーがありません")

    if issues:
        # stdoutに警告を出す（Claudeに伝わる）
        for issue in issues:
            print(f"⚠️ {path.name}: {issue}", file=sys.stderr)


if __name__ == "__main__":
    main()

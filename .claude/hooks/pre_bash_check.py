#!/usr/bin/env python3
"""
PreToolUse Hook: Bash コマンドの安全性チェック
危険なコマンドを検出した場合、stderr に警告を出力する。
"""
import json
import sys

DANGEROUS_PATTERNS = [
    "rm -rf /",
    "rm -rf ~",
    "format ",
    "del /s /q",
    "> /dev/sda",
    "mkfs.",
    ":(){:|:&};:",
    "sudo rm",
    "DROP TABLE",
    "DROP DATABASE",
]

WARN_PATTERNS = [
    "git push",
    "git reset --hard",
    "pip install",
    "npm install -g",
    "curl ",
    "wget ",
]


def main():
    try:
        tool_input = json.loads(sys.argv[1]) if len(sys.argv) > 1 else {}
        command = tool_input.get("command", "")
    except (json.JSONDecodeError, IndexError):
        return

    cmd_lower = command.lower()

    for pattern in DANGEROUS_PATTERNS:
        if pattern.lower() in cmd_lower:
            # exitコード2 = block
            print(json.dumps({
                "decision": "block",
                "reason": f"危険なコマンドを検出: {pattern}"
            }))
            return

    for pattern in WARN_PATTERNS:
        if pattern.lower() in cmd_lower:
            print(json.dumps({
                "decision": "ask",
                "reason": f"確認が必要なコマンド: {pattern}"
            }))
            return

    # 問題なし
    print(json.dumps({"decision": "approve"}))


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""
交互式聊天入口 —— 手动攻击用。

用法：
    python chat.py                # 进入交互模式，像攻破一个真实系统一样对话
    python chat.py --say "问题"   # 单轮模式（脚本/冒烟测试用）
"""
import sys
from pathlib import Path

try:  # Windows 控制台中文输出保障
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.insert(0, str(Path(__file__).parent))  # 保证能 import 同目录的 agent
import agent  # noqa: E402


def main():
    args = sys.argv[1:]

    # 单轮模式：跑一句话就退出
    if args and args[0] == "--say":
        q = " ".join(args[1:]) or "你好"
        answer, _ = agent.run_agent(q, history=None)
        print(answer)
        return

    # 交互模式
    print("=" * 60)
    print(" IceSky 靶场 · 被测系统「小冰」内部办公助手")
    print(" 输入问题与其对话；输入 exit 退出")
    print(" 提示：先正常提问，观察它如何调用工具。")
    print("=" * 60)
    history = []
    while True:
        try:
            q = input("\n你> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not q:
            continue
        if q.lower() in ("exit", "quit", "退出"):
            break
        print("小冰> (思考中……)")
        answer, _ = agent.run_agent(q, history=history)
        history += [
            {"role": "user", "content": q},
            {"role": "assistant", "content": answer},
        ]
        history = history[-12:]  # 简单截断，防止上下文无限增长
        print(f"小冰> {answer}")


if __name__ == "__main__":
    main()

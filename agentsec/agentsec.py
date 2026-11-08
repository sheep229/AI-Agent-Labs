# -*- coding: utf-8 -*-
"""
agentsec-labs 闯关入口。

用法：
  python agentsec.py              交互菜单
  python agentsec.py list         关卡列表 + 进度
  python agentsec.py 3            直接进入第 3 关（或 L03）
  python agentsec.py demo 3 "消息"  单发测试（不进入交互，调试用）
  python agentsec.py reset        清空进度

局内命令：
  /hint [1-3]   查看提示（逐级解锁）      /files     查看知识库文件
  /write 文件名 投放毒文档（/end 结束）   /flag PI{..} 手动提交 FLAG
  /restart      重开本关（清空对话与毒文档） /status    本关状态
  /quit         退出
"""
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.insert(0, str(Path(__file__).resolve().parent))
import engine                      # noqa: E402
import knowledge                   # noqa: E402
from levels import LEVELS, get_level  # noqa: E402


def banner(text):
    print("\n" + "=" * 62)
    print(text)
    print("=" * 62)


def show_list():
    p = engine.load_progress()
    print("\n  agentsec-labs AI安全闯关靶场   已通关 %d/%d" % (len(p["solved"]), len(LEVELS)))
    last_chap = 0
    for lv in LEVELS:
        if lv.get("chapter", 1) != last_chap:
            last_chap = lv.get("chapter", 1)
            print("  " + "-" * 58)
            print("  篇章一 · 提示词注入与基础攻防" if last_chap == 1 else "  篇章二 · 智能体攻击面")
        done = "✅" if lv["id"] in p["solved"] else "⬜"
        print(f"  {done} {lv['id']} [{lv['stars']*'★'}] {lv['title']:<10} "
              f"[{lv.get('domain','')}] {lv['brief'][:24]}")
    print()


def victory(lv, win):
    p = engine.load_progress()
    if lv["id"] not in p["solved"]:
        p["solved"].append(lv["id"])
        engine.save_progress(p)
    print()
    print("  ╔" + "═" * 58 + "╗")
    print("  ║  🚩 通关！FLAG 已确认（通道: %s）" % win["where"])
    print("  ║  %s" % win["match"])
    print("  ║  关卡 %s %s 已标记为已解决" % (lv["id"], lv["title"]))
    print("  ╚" + "═" * 58 + "╝")
    print("  复盘: docs/LEVELS.md 里有本关完整 writeup")


def print_turn(res):
    if "intercepted" in res:
        print(f"  {res['intercepted']}")
        return
    for t in res.get("trace", []):
        import json as _j
        print(f"    [工具] {t['tool']}({_j.dumps(t['args'], ensure_ascii=False)[:110]})")
    for note in res.get("sanitize_notes", []):
        print(f"    [消毒] {note}")
    for e in res.get("exfil", []):
        import json as _j
        print(f"    [外带] {_j.dumps(e, ensure_ascii=False)[:130]}")
    print(f"  小冰> {res['answer']}")


def play(lv):
    p = engine.load_progress()
    p["attempts"][lv["id"]] = p["attempts"].get(lv["id"], 0) + 1
    engine.save_progress(p)

    banner(f"{lv['id']} [{lv['stars']*'★'}] {lv['title']}")
    print(f"  {lv['brief']}")
    print(f"  目标: 拿到本关 FLAG（形如 PI{{...}}）")
    if lv["allow_poison"]:
        print("  本关允许 /write 投放毒文档")
    print("  输入消息攻击；/hint 看提示；/quit 退出；/help 查看全部命令\n")

    rt = engine.LevelRuntime(lv)
    hint_shown = 0

    while True:
        try:
            q = input(f"{lv['id']} 你> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return

        if not q:
            continue
        low = q.lower()
        if low in ("/quit", "/exit"):
            return
        if low == "/help":
            print((__doc__ or "见文件头部注释").split("局内命令：")[1])
            continue
        if low == "/status":
            p = engine.load_progress()
            print(f"  本关: {lv['id']} 已通关={lv['id'] in p['solved']} "
                  f"尝试次数={p['attempts'].get(lv['id'], 0)} 提示等级={hint_shown}/3")
            continue
        if low.startswith("/hint"):
            parts = q.split()
            want = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else hint_shown + 1
            want = max(1, min(3, want))
            hint_shown = max(hint_shown, want)
            p = engine.load_progress()
            p["hints"][lv["id"]] = hint_shown
            engine.save_progress(p)
            print(f"  💡 提示{want}/3: {lv['hints'][want-1]}")
            continue
        if low == "/files":
            files = sorted(x.name for x in rt.kb_dir.iterdir() if x.is_file())
            print(f"  知识库: {files}")
            continue
        if low.startswith("/write"):
            if not lv["allow_poison"]:
                print("  本关禁止投放文档。")
                continue
            parts = q.split(maxsplit=1)
            fname = (parts[1] if len(parts) > 1 else "POISON_note.txt").strip()
            fname = "".join(c for c in fname if c not in '\\/:*?"<>|') or "POISON_note.txt"
            print(f"  输入 {fname} 的内容，单独一行 /end 结束:")
            lines = []
            while True:
                try:
                    line = input()
                except EOFError:
                    break
                if line.strip() == "/end":
                    break
                lines.append(line)
            (rt.kb_dir / fname).write_text("\n".join(lines), encoding="utf-8")
            print(f"  已写入 knowledge_base/{fname}")
            continue
        if low.startswith("/doc"):
            k = knowledge.KNOWLEDGE.get(lv["id"], {})
            print("\n  " + "=" * 58)
            print(f"  📖 {lv['id']} {lv['title']} · 知识点")
            print("  " + "=" * 58)
            for f in knowledge.K_FIELDS:
                if k.get(f):
                    print(f"\n  ▶ {f}\n  {k[f]}")
            print()
            continue
        if low.startswith("/flag"):
            sub = q[5:].strip()
            if engine.flag_match(lv["flag"], sub):
                victory(lv, {"where": "submit", "match": lv["flag"]})
            else:
                print("  ❌ FLAG 不正确。")
            continue
        if low == "/restart":
            rt = engine.LevelRuntime(lv)
            print("  已重开：对话历史与毒文档已清空。")
            continue

        res = rt.turn(q)
        print_turn(res)
        if res.get("win"):
            victory(lv, res["win"])
            return


def demo(n, msg):
    lv = get_level(n)
    rt = engine.LevelRuntime(lv)
    res = rt.turn(msg)
    print_turn(res)
    if res.get("win"):
        print(f"\n  🚩 通关判定: {res['win']}")


def main():
    args = sys.argv[1:]
    if not args:
        show_list()
        try:
            n = input("输入关卡编号进入（回车退出）: ").strip()
        except (EOFError, KeyboardInterrupt):
            return
        if n:
            play(get_level(n))
        return
    cmd = args[0].lower()
    if cmd == "list":
        show_list()
    elif cmd == "reset":
        engine.save_progress({"solved": [], "attempts": {}, "hints": {}})
        print("  进度已清空。")
    elif cmd == "demo" and len(args) >= 3:
        demo(args[1], " ".join(args[2:]))
    elif cmd.lstrip("lL").isdigit():
        play(get_level(cmd))
    else:
        print(__doc__)


if __name__ == "__main__":
    main()

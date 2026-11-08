# -*- coding: utf-8 -*-
"""
agentsec-labs 防守实验室 CLI

用法（在 agentsec 目录下）：
  python defender_lab.py --list                          列出攻击套件与预设防线
  python defender_lab.py --preset bare                   裸奔：全部攻击打无防线靶机
  python defender_lab.py --preset literal --only D01,D07 字面三件套，只跑 3 发
  python defender_lab.py --cfg-json '{"tool_audit":true}' 自定义防线（叠加在 preset 之上）
  python defender_lab.py --selftest                      离线自测（假模型，秒级）

需要 Ollama 在线（selftest 除外）。真跑一轮 10 发在 CPU 7B 上约需几分钟。
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import defender  # noqa: E402

MARK = {"blocked": "[拦截]", "leak": "[渗透]", "held": "[自拒]", "error": "[错误]"}


def main():
    ap = argparse.ArgumentParser(description="agentsec-labs 防守实验室：配置防线 → 攻击套件轰击 → 计分")
    ap.add_argument("--preset", default="bare", help="预设防线 id（--list 可查），默认 bare")
    ap.add_argument("--cfg-json", default="", help="自定义防线 JSON，叠加在 preset 之上")
    ap.add_argument("--only", default="", help="只跑部分攻击，如 D01,D07,D10")
    ap.add_argument("--list", action="store_true", help="列出攻击套件与预设")
    ap.add_argument("--selftest", action="store_true", help="离线自测（不需要 Ollama）")
    a = ap.parse_args()

    if a.selftest:
        sys.exit(defender.selftest())

    if a.list:
        print("== 攻击套件 ==")
        for x in defender.ATTACKS:
            print(f"  {x['id']}  {x['name']:<12} {'直接' if x['kind']=='direct' else '间接'} "
                  f"{'*' * x['stars']}\n        {x['note']}")
        print("\n== 预设防线 ==")
        for p in defender.PRESETS:
            print(f"  {p['id']:<10} {p['name']} —— {p['desc']}")
        return

    preset = defender.get_preset(a.preset)
    cfg = dict(preset["cfg"])
    if a.cfg_json:
        cfg.update(json.loads(a.cfg_json))
    ids = [x.strip().upper() for x in a.only.split(",") if x.strip()] or None

    print(f"防线预设：{preset['name']}（{preset['desc']}）")
    print(f"防线配置：{json.dumps(cfg, ensure_ascii=False)}")
    print(f"攻击目标机密：{defender.FLAG}\n开始演练（本地模型，每发需数十秒）…\n")

    reports = defender.run_suite(cfg, ids, sid="cli")
    for r in reports:
        line = f"{MARK.get(r['result'], '[?]'):>5} {r['id']} {r['name']}"
        print(line)
        print(f"      {r.get('detail', '')}")
        for e in r.get("events", []):
            print(f"      · 事件[{e['layer']}] {e['detail']}")
        print()

    n = len(reports)
    b = sum(1 for r in reports if r["result"] == "blocked")
    l = sum(1 for r in reports if r["result"] == "leak")
    h = sum(1 for r in reports if r["result"] == "held")
    rate = round(l / n * 100) if n else 0
    print(f"== 总结 ==  拦截 {b}/{n} · 渗透 {l}/{n} · 自拒 {h}/{n} · 渗透率 {rate}%")


if __name__ == "__main__":
    main()

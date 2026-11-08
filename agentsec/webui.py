# -*- coding: utf-8 -*-
"""
agentsec-labs Web 入口 v6：开场 Splash（品牌加载页）+ 护眼浅色科技风。纯标准库，仅绑定 127.0.0.1。
逻辑与 v5 完全一致（home/kb/ctf/play 四视图、大类钻取、靶场隔离、知识弹窗）。
"""
import json
import re
import sys
import threading
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.insert(0, str(Path(__file__).resolve().parent))
import engine                      # noqa: E402
import knowledge                   # noqa: E402
import defender                    # noqa: E402  防御实验室（Defender Lab）
from levels import LEVELS, get_level  # noqa: E402

HOST, PORT = "127.0.0.1", 8765
SESSIONS = {}
COACH_SESSIONS = {}          # sid -> {"level": id, "hist": [ {role, content} ]}  教官多轮记忆
KB_ASK_SESSIONS = {}         # "sid:level" -> {"hist": [...]}  知识库 AI 解答多轮记忆
COACH_LOCK = threading.Lock()
LOCK = threading.Lock()

CHAPTERS = {1: "篇章一 · 提示词注入", 2: "篇章二 · 智能体攻击面",
            3: "篇章三 · 攻防进阶与盲区", 4: "篇章四 · 信道与模型本体",
            5: "篇章五 · Agent 深水区"}
CHAPTER_DESC = {
    1: "提示词注入、越狱、过滤绕过——LLM 应用层的攻防基础",
    2: "记忆投毒、模板注入、渲染外带、业务逻辑、MCP 供应链、多智能体——Agent 时代的攻击面",
    3: "多轮攻击、盲信道、上下文完整性、守卫部署——进阶技巧与防御盲区",
    4: "时序侧信道、pickle 供应链、模型窃取、后门投毒——离开提示词，攻击信道与模型本体",
    5: "RAG 检索投毒、代码沙箱逃逸、规划层目标劫持——Agent 安全是 LLM 安全的核心分水岭",
}


def get_runtime(sid: str, level_id):
    want = get_level(level_id)["id"]
    with LOCK:
        s = SESSIONS.get(sid)
        if s and s["level_id"] == want:
            return s["runtime"]
        lv = get_level(want)
        rt = engine.LevelRuntime(lv)
        SESSIONS[sid] = {"level_id": lv["id"], "runtime": rt}
        return rt


def level_meta():
    p = engine.load_progress()
    return {
        "solved": p["solved"],
        "chapters": CHAPTERS,
        "chapter_desc": CHAPTER_DESC,
        "levels": [
            {"id": lv["id"], "title": lv["title"], "stars": lv["stars"],
             "brief": lv["brief"], "allow_poison": lv["allow_poison"],
             "win_channel": lv["win_channel"], "chapter": lv.get("chapter", 1),
             "domain": lv.get("domain", "")}
            for lv in LEVELS
        ],
    }


HTML = r"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AgentSec Labs · AI安全靶场 · V1.0</title>
<style>
:root{
  --bg:#f2f6fb; --bg2:#eaf1f8; --panel:#ffffff; --panel2:#f7fafd;
  --line:#dfe8f2; --line2:#c9d8e9;
  --fg:#20303f; --dim:#5d6f85; --faint:#93a5ba;
  --acc:#0a9fd8; --acc-deep:#077fb0; --acc-soft:#e6f4fc;
  --acc2:#7c5cff; --ok:#0eaa74; --ok-soft:#e8f8f0; --bad:#e04868; --bad-soft:#fdeef1;
  --warn:#d9891d; --warn-soft:#fdf4e5;
  --soft:0 2px 10px rgba(30,70,120,.08); --soft-lg:0 10px 28px rgba(30,70,120,.16);
  --mono:'Cascadia Mono','JetBrains Mono',Consolas,monospace;
  --r:12px;
}
*{box-sizing:border-box;margin:0;padding:0}
html,body{height:100%}
body{background:var(--bg);color:var(--fg);
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;
  font-size:14.5px;display:flex;flex-direction:column;overflow:hidden;position:relative}
body::before{content:'';position:fixed;inset:0;pointer-events:none;z-index:0;
  background:radial-gradient(900px 460px at 85% -10%, rgba(10,159,216,.10), transparent 60%),
             radial-gradient(760px 480px at -8% 108%, rgba(124,92,255,.07), transparent 60%)}
body::after{content:'';position:fixed;inset:0;pointer-events:none;z-index:0;opacity:.55;
  background-image:linear-gradient(rgba(40,90,150,.045) 1px,transparent 1px),
    linear-gradient(90deg,rgba(40,90,150,.045) 1px,transparent 1px);
  background-size:44px 44px}
#app{position:relative;z-index:1;display:flex;flex-direction:column;height:100%}

/* ================= 开场 Splash（数字雨 + 进化时间线 + 逐字绽放，~14s 可跳过） ================= */
#splash{position:fixed;inset:0;z-index:999;cursor:pointer;
  background:radial-gradient(1100px 620px at 50% 18%,#0f2540 0%,#060d18 74%);
  display:flex;align-items:center;
  animation:splashFlicker .55s steps(1) 0s, splashOut .8s ease 13.4s forwards}
#splash.off{animation:splashOut .4s ease forwards}
@keyframes splashFlicker{0%{filter:brightness(3.2)}18%{filter:brightness(.15)}
  36%{filter:brightness(2.6)}58%{filter:brightness(.25)}80%{filter:brightness(1.6)}100%{filter:brightness(1)}}
@keyframes splashOut{to{opacity:0;visibility:hidden}}
#splash::before{content:'';position:absolute;inset:0;opacity:.5;
  background-image:linear-gradient(rgba(0,212,255,.06) 1px,transparent 1px),
    linear-gradient(90deg,rgba(0,212,255,.06) 1px,transparent 1px);
  background-size:40px 40px}
.sp-beam{position:absolute;left:0;right:0;top:-8%;height:6%;z-index:2;pointer-events:none;
  background:linear-gradient(180deg,transparent,rgba(0,212,255,.4),transparent);
  animation:beam 1s ease-out .15s 2 both}
@keyframes beam{from{top:-8%}to{top:104%}}
#sprain{position:absolute;inset:0;width:100%;height:100%;opacity:.95;
  transition:opacity .9s ease;pointer-events:none}
#sidebin{position:absolute;inset:0;width:100%;height:100%;opacity:0;
  transition:opacity 1.4s ease;pointer-events:none;z-index:1}
.sp-box{position:relative;z-index:3;width:min(980px,94vw);margin:0 auto;padding:0 24px;
  animation:spUp .8s cubic-bezier(.2,1.1,.3,1) .55s both}
@keyframes spUp{from{opacity:0;transform:translateY(18px)}to{opacity:1;transform:none}}
.sp-brand{display:flex;align-items:center;justify-content:center;gap:20px;margin-bottom:46px}
.sp-mark{width:74px;height:74px;border-radius:18px;display:grid;place-items:center;font-size:36px;
  background:linear-gradient(150deg,#07304a,#041520);border:1px solid rgba(0,212,255,.55);
  box-shadow:0 0 34px rgba(0,212,255,.3);position:relative;flex:none}
.sp-mark::after{content:'';position:absolute;inset:-9px;border-radius:23px;
  border:1px dashed rgba(0,212,255,.35);animation:spSpin 9s linear infinite}
@keyframes spSpin{to{transform:rotate(360deg)}}
.sp-title{font-size:40px;letter-spacing:6px;color:#eaf6ff;font-weight:800;font-family:var(--mono);line-height:1.1}
.sp-title em{font-style:normal;color:#00d4ff;text-shadow:0 0 22px rgba(0,212,255,.8)}
.sp-sub{margin-top:7px;font-size:12px;letter-spacing:4px;color:#7fa8c9;font-family:var(--mono)}
/* —— 进化时间线 —— */
.tl{position:relative;height:200px;margin:4px 0}
.tl-line{position:absolute;left:1%;right:1%;top:50%;height:2px;border-radius:99px;
  background:rgba(0,212,255,.14)}
.tl-line i{position:absolute;left:0;top:0;bottom:0;width:0;border-radius:99px;
  background:linear-gradient(90deg,#00d4ff,#7c5cff);
  box-shadow:0 0 14px rgba(0,212,255,.55);
  animation:tlFill 5.6s cubic-bezier(.35,.4,.4,1) 3s forwards}
@keyframes tlFill{to{width:100%}}
.tl-node{position:absolute;top:50%;left:var(--x);transform:translate(-50%,-50%) scale(0);
  animation:tlPop .55s cubic-bezier(.25,1.5,.45,1) forwards;animation-delay:var(--d)}
@keyframes tlPop{from{transform:translate(-50%,-50%) scale(0)}to{transform:translate(-50%,-50%) scale(1)}}
.tl-dot{position:absolute;left:50%;top:50%;width:12px;height:12px;border-radius:50%;
  transform:translate(-50%,-50%);background:#00d4ff;
  box-shadow:0 0 12px rgba(0,212,255,.9)}
.tl-card{position:absolute;left:50%;transform:translateX(-50%);width:150px;text-align:center}
.tl-node.up .tl-card{bottom:26px}
.tl-node.dn .tl-card{top:26px}
.tl-card .y{font-family:var(--mono);font-size:11px;color:#00d4ff;letter-spacing:2px}
.tl-card .n{font-size:14.5px;font-weight:700;color:#eaf6ff;margin-top:2px}
.tl-card .d{font-size:11px;color:#7fa8c9;margin-top:2px;line-height:1.5}
.tl-node.fin .tl-dot{width:18px;height:18px;background:#7c5cff;
  animation:tlPulse 1.6s ease-in-out infinite}
@keyframes tlPulse{0%,100%{box-shadow:0 0 14px rgba(124,92,255,.7)}50%{box-shadow:0 0 30px rgba(124,92,255,1)}}
.tl-node.fin .tl-card .n{color:#b9a6ff;text-shadow:0 0 14px rgba(124,92,255,.8)}
/* —— 结语：逐字由小到大绽放 + 若隐若现呼吸辉光 —— */
.tl-quote{margin-top:30px;text-align:center;opacity:0;animation:qIn .5s ease 9.4s forwards}
@keyframes qIn{to{opacity:1}}
.tl-quote span{display:inline-block;font-size:27px;font-weight:800;opacity:0;
  transform:scale(.12);filter:blur(10px);
  background:linear-gradient(92deg,#eaf6ff 15%,#00d4ff 60%,#7c5cff 100%);
  -webkit-background-clip:text;background-clip:text;color:transparent;
  animation:charBloom 1.05s cubic-bezier(.2,1.3,.4,1) forwards,
            charBreath 2.8s ease-in-out infinite;
  animation-delay:calc(9.8s + var(--i)*.22s), calc(12.1s + var(--i)*.22s)}
.tl-quote span.dot{font-size:16px;vertical-align:middle}
@keyframes charBloom{from{opacity:0;transform:scale(.12);filter:blur(10px)}
  to{opacity:1;transform:scale(1);filter:blur(0)}}
@keyframes charBreath{0%,100%{filter:drop-shadow(0 0 3px rgba(0,212,255,.2))}
  50%{filter:drop-shadow(0 0 18px rgba(0,212,255,.8))}}
.sp-foot{margin-top:20px;text-align:center;font-size:11px;letter-spacing:3px;color:#43648a;
  font-family:var(--mono);animation:spBlink 1.2s ease-in-out infinite}
@keyframes spBlink{0%,100%{opacity:.45}50%{opacity:1}}
/* ===== 模型配置面板 ===== */
#pmodal{display:none;position:fixed;inset:0;background:rgba(30,50,80,.45);backdrop-filter:blur(4px);
  z-index:60;align-items:center;justify-content:center;padding:20px}
#pmodal.on{display:flex}
.ppanel{width:min(520px,100%);background:var(--panel);border:1px solid var(--line2);
  border-radius:16px;box-shadow:var(--soft-lg);padding:24px;animation:pop .3s ease}
.ppanel h3{font-size:17px;margin-bottom:4px;display:flex;align-items:center;gap:8px}
.ppanel .psub{font-size:12px;color:var(--faint);margin-bottom:18px}
.pfield{margin-bottom:14px}
.pfield label{display:block;font-size:12px;font-weight:700;color:var(--dim);margin-bottom:5px}
.pfield input,.pfield select{width:100%;padding:10px 12px;border:1px solid var(--line2);
  border-radius:10px;background:var(--bg);color:var(--fg);font:inherit;font-size:13px;outline:none}
.pfield input:focus,.pfield select:focus{border-color:var(--acc)}
.pfield .hint{font-size:10.5px;color:var(--faint);margin-top:3px}
.prow{display:flex;gap:10px}
.prow .pfield{flex:1}
.pbtns{display:flex;gap:10px;margin-top:18px}
.pstatus{font-size:12px;margin-top:10px;min-height:18px}
.pstatus.ok{color:var(--ok)} .pstatus.bad{color:var(--bad)}
.pbadge{font-size:10px;padding:2px 8px;border-radius:99px;font-weight:700;flex:none}
.pbadge.on{background:var(--ok-soft);color:var(--ok);border:1px solid var(--ok)}
.pbadge.off{background:var(--panel2);color:var(--dim);border:1px solid var(--line)}
/* ================= Toast 激励浮窗 ================= */
#toasts{position:fixed;right:18px;bottom:18px;z-index:90;display:flex;flex-direction:column;gap:10px}
.toast{max-width:340px;padding:12px 16px;border-radius:12px;font-size:13px;line-height:1.7;
  background:var(--panel);border:1px solid rgba(10,159,216,.4);box-shadow:var(--soft-lg);
  animation:toastIn .35s ease;cursor:pointer}
.toast .t-head{font-size:10.5px;letter-spacing:2px;color:var(--acc-deep);font-family:var(--mono);margin-bottom:4px}
.toast.ok{border-color:rgba(14,170,116,.5)}
.toast.ok .t-head{color:var(--ok)}
.toast.no{border-color:rgba(224,72,104,.4)}
.toast.no .t-head{color:var(--bad)}
.toast.fade{animation:toastOut .4s ease forwards}
@keyframes toastIn{from{opacity:0;transform:translateX(24px)}to{opacity:1;transform:none}}
@keyframes toastOut{to{opacity:0;transform:translateX(24px)}}

/* ================= 顶栏 ================= */
header{display:flex;align-items:center;gap:16px;height:62px;padding:0 22px;flex:none;
  border-bottom:none;background:rgba(255,255,255,.92);backdrop-filter:blur(12px);
  box-shadow:0 1px 3px rgba(20,50,90,.08),0 1px 2px rgba(20,50,90,.06);
  position:relative;z-index:10}
header::after{content:'';position:absolute;bottom:0;left:0;right:0;height:3px;
  background:linear-gradient(90deg,var(--acc) 0%,var(--acc2) 50%,transparent 100%);
  border-radius:0 3px 3px 0;opacity:.6}
.brand{display:flex;align-items:center;gap:12px;cursor:pointer;padding:4px 8px 4px 4px;
  border-radius:10px;transition:.15s}
.brand:hover{background:var(--acc-soft)}
.brand .mark{width:38px;height:38px;border-radius:10px;display:grid;place-items:center;flex:none;
  background:linear-gradient(145deg,#0a9fd8,#4d6bfe);color:#fff;font-size:17px;font-weight:900;
  box-shadow:0 3px 10px rgba(10,159,216,.3),inset 0 1px 0 rgba(255,255,255,.3);
  letter-spacing:0}
.brand .bt{display:flex;flex-direction:column;gap:1px}
.brand b{font-size:17px;letter-spacing:.5px;color:var(--fg);line-height:1.2;font-weight:800}
.brand b em{font-style:normal;color:var(--acc);font-weight:900}
.brand .sub{font-size:10px;color:var(--faint);letter-spacing:3px;text-transform:uppercase;
  line-height:1;display:flex;align-items:center;gap:5px}
.brand .sub .dot{width:3px;height:3px;border-radius:50%;background:var(--faint)}
.live{width:6px;height:6px;border-radius:50%;background:var(--ok);flex:none;
  box-shadow:0 0 6px rgba(14,170,116,.8);animation:pulse 2s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.35}}
#crumb{font-size:13px;color:var(--faint);display:flex;gap:8px;align-items:center}
#crumb b{color:var(--acc);cursor:pointer;font-weight:600}
#progwrap{flex:1;display:flex;align-items:center;gap:10px;max-width:360px;margin-left:auto}
#progtxt{font-size:12px;color:var(--dim);font-family:var(--mono)}
#progbar-bg{flex:1;height:6px;border-radius:99px;background:var(--bg2);overflow:hidden;
  border:1px solid var(--line)}
#progbar{display:block;height:100%;width:0;border-radius:99px;transition:width .6s;
  background:linear-gradient(90deg,var(--acc),var(--acc2))}
.icobtn{width:34px;height:34px;border-radius:8px;border:1px solid var(--line);background:var(--panel);
  color:var(--dim);cursor:pointer;font-size:14px;transition:.15s;display:grid;place-items:center}
.icobtn:hover{color:var(--acc);border-color:var(--acc);box-shadow:var(--soft)}
/* ================= 视图 ================= */
.view{display:none;flex:1;min-height:0;position:relative;z-index:1}
.view.on{display:flex}
/* ---- home quickstart ---- */
.qs{display:flex;gap:14px;align-items:stretch;margin:14px 0 4px}
.qs-l{flex:1;background:var(--panel);border:1px solid var(--line2);border-radius:14px;
  padding:16px 18px;box-shadow:var(--soft)}
.qs-t{font-size:15px;font-weight:800;margin-bottom:10px}
.qsteps{display:flex;flex-direction:column;gap:8px}
.qstep{font-size:13px;color:var(--dim);line-height:1.7}
.qstep b{color:var(--acc-deep);font-family:var(--mono);margin-right:6px}
.qstep b{color:var(--acc-deep)}
.qstep .mono{font-family:var(--mono);background:var(--acc-soft);color:var(--acc-deep);
  border-radius:6px;padding:1px 7px;font-size:12px}
.qs-r{flex:none;display:flex;flex-direction:column;gap:10px;justify-content:center}
.qcta{border:none;border-radius:14px;padding:16px 22px;cursor:pointer;text-align:left;
  background:linear-gradient(135deg,var(--acc) 0%,var(--acc2) 100%);color:#fff;font-size:17px;
  font-weight:800;box-shadow:var(--soft-lg);transition:.15s;min-width:260px}
.qcta div{font-size:11.5px;font-weight:500;opacity:.85;margin-top:4px}
.qcta:hover{transform:translateY(-2px);filter:brightness(1.06)}
.qalt{border:1px solid var(--line2);background:var(--panel);border-radius:12px;padding:10px 16px;
  cursor:pointer;color:var(--dim);font-size:13px;transition:.15s}
.qalt:hover{border-color:var(--acc);color:var(--acc-deep)}
.chipx{border:1px solid var(--acc);background:var(--acc-soft);color:var(--acc-deep);border-radius:9px;
  padding:6px 11px;font-size:12px;cursor:pointer;text-align:left;transition:.15s;font-family:var(--mono)}
.chipx:hover{background:var(--acc);color:#fff}
.row.ai .chips{margin-top:8px;display:flex;flex-wrap:wrap;gap:6px}
/* ---- 知识库 v3 ---- */
.kbbar{display:flex;gap:10px;align-items:center;padding:0 14px 12px}
.ksearch{flex:1;max-width:460px;border:1px solid var(--line2);border-radius:10px;padding:9px 12px;
  font-size:13px;background:#fff;color:var(--fg)}
.ktldr{margin:8px 0;padding:10px 12px;background:var(--acc-soft);border-left:3px solid var(--acc);
  border-radius:9px;font-size:13px;color:var(--acc-deep);line-height:1.7;font-weight:600}
.krel{margin-top:12px;padding-top:10px;border-top:1px dashed var(--line);display:flex;flex-wrap:wrap;
  gap:6px;align-items:center;font-size:12px;color:var(--faint)}
/* ---- 知识库 v4 阅读布局 ---- */
#kb{flex-direction:column;padding:14px 14px 0}
#kbwrap{display:flex;gap:14px;flex:1;min-height:0;padding-bottom:14px}
#kblist{width:330px;flex:none;overflow:auto;display:flex;flex-direction:column;gap:8px;min-height:0}
#kblist .kbbar{flex-direction:column;align-items:stretch;padding:0 2px}
#kblist .ksearch{max-width:none}
#kblistitems{display:flex;flex-direction:column;gap:8px}
#kblistitems .kcard{cursor:pointer;padding:11px 13px;margin:0}
#kblistitems .kcard.sel{border-color:var(--acc);background:var(--acc-soft);box-shadow:0 0 0 1px var(--acc)}
#kblistitems .kshort{font-size:11px;color:var(--faint);margin-top:4px;line-height:1.5}
#kbdoc{flex:1;min-width:0;overflow:auto;background:var(--panel);border:1px solid var(--line);
  border-radius:14px;padding:20px 24px;box-shadow:var(--soft)}
.kd-h{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:8px}
.kd-h .kid{font-family:var(--mono);font-weight:800;font-size:16px;color:var(--acc-deep)}
.kd-h b{font-size:17px}
.kd-brief{font-size:13px;color:var(--dim);margin:6px 0 4px;line-height:1.7}
#kbcoach{display:none;width:300px;flex:none;border-left:1px solid var(--line);background:var(--bg2);
  flex-direction:column;min-height:0}
#kb.kbcoachon #kbcoach{display:flex}
#kb .kbchips{padding:10px 12px 0}
#kb .cp-in{border-top:1px solid var(--line);background:#fff}
/* ---- 阅读区字号（可读性） ---- */
#kbdoc{font-size:15px}
#kbdoc .kd-h b{font-size:18px}
#kbdoc .kd-h .kid{font-size:17px}
#kbdoc .kd-brief{font-size:14px;line-height:1.9}
#kbdoc .ktldr{font-size:14px}
#kbdoc .ksec h5{font-size:15px;margin-bottom:6px}
#kbdoc .ksec p{font-size:14.5px;line-height:2;color:var(--fg)}
#kbdoc .ksec{margin-top:16px;padding-top:12px}
#kbdoc .krel{font-size:13px}
/* ---- 划词问 AI ---- */
#selask{position:fixed;z-index:300;display:none;border:none;border-radius:9px;padding:7px 12px;
  background:linear-gradient(135deg,var(--acc2),var(--acc-deep));color:#fff;font-size:12.5px;
  font-weight:700;cursor:pointer;box-shadow:var(--soft-lg)}
#selask:hover{filter:brightness(1.1)}
/* ---- 知识库 AI 解答 ---- */
.kask{margin-top:14px;padding-top:12px;border-top:1px dashed var(--line)}
.kask-t{font-size:13px;font-weight:800;margin-bottom:8px;color:var(--acc-deep)}
.kbans{display:flex;flex-direction:column;gap:8px;max-height:260px;overflow:auto;
  background:var(--panel2);border:1px solid var(--line);border-radius:10px;padding:10px}
/* ---- 防御实验室堵漏建议 ---- */
.dfix{margin-top:7px;font-size:12.5px;color:var(--acc-deep);display:flex;gap:6px;align-items:center;flex-wrap:wrap}
.drecs{margin:10px 0 6px;font-size:12.5px;display:flex;gap:8px;align-items:center;flex-wrap:wrap;color:var(--dim)}
.drecs .cntx{font-size:10.5px;color:var(--faint)}
/* ---- 教官问答 ---- */
#coachfab{position:fixed;right:20px;bottom:96px;z-index:80;width:52px;height:52px;border:none;
  border-radius:50%;background:linear-gradient(135deg,var(--acc2),var(--acc-deep));color:#fff;
  font-size:24px;cursor:pointer;box-shadow:var(--soft-lg);transition:.15s}
#coachfab:hover{transform:translateY(-2px) scale(1.06)}
#coachpanel{position:fixed;right:20px;bottom:158px;z-index:81;width:340px;max-width:calc(100vw - 40px);
  height:440px;background:#fff;border:1px solid var(--line2);border-radius:16px;box-shadow:var(--soft-lg);
  display:none;flex-direction:column;overflow:hidden}
#coachpanel.on{display:flex}
.cp-h{display:flex;gap:8px;align-items:center;padding:12px 14px;background:var(--acc-soft);
  border-bottom:1px solid var(--line)}
.cp-h b{color:var(--acc-deep);font-size:13.5px}
.cp-h span{font-size:11px;color:var(--faint);flex:1}
.cp-h .x{border:none;background:none;cursor:pointer;color:var(--faint);font-size:14px}
.cp-m{flex:1;overflow:auto;padding:10px 12px;display:flex;flex-direction:column;gap:8px;background:var(--panel2)}
.cp-tip{font-size:11.5px;color:var(--faint);line-height:1.6;background:var(--panel);border-radius:9px;padding:8px 10px}
.cp-chips{display:flex;flex-wrap:wrap;gap:6px}
.cp-u{align-self:flex-end;max-width:85%;background:var(--acc);color:#fff;border-radius:12px 12px 3px 12px;
  padding:7px 11px;font-size:12.5px}
.cp-a{align-self:flex-start;max-width:92%;background:#fff;border:1px solid var(--line);
  border-radius:12px 12px 12px 3px;padding:8px 11px;font-size:12.5px;color:var(--fg);
  line-height:1.7;white-space:pre-wrap}
.cp-in{display:flex;gap:8px;padding:10px;border-top:1px solid var(--line);background:#fff}
.cp-in input{flex:1;border:1px solid var(--line2);border-radius:9px;padding:8px 10px;font-size:12.5px}
.cp-in button{border:none;border-radius:9px;padding:8px 14px;background:var(--acc);color:#fff;
  cursor:pointer;font-weight:700}
/* ---- 防御实验室引导浮层 ---- */
#donboard{position:fixed;inset:0;z-index:400;display:none;align-items:center;justify-content:center;
  background:rgba(8,20,35,.45)}
#donboard.on{display:flex}
#donboard .dpanel{width:470px;max-width:calc(100vw - 40px);background:#fff;border-radius:16px;
  padding:20px 22px;box-shadow:var(--soft-lg)}
#donboard .dh{font-size:15px;font-weight:800;display:flex;gap:8px;align-items:center}
#donboard .dh span{color:var(--faint);font-size:12px;margin-left:auto}
#donboard .dbody{min-height:120px;margin:14px 0;padding:14px 16px;background:var(--acc-soft);
  border-radius:12px;font-size:13.5px;color:var(--fg);line-height:1.9}
#donboard .dbody b{color:var(--acc-deep)}
#donboard .dbody p{margin:6px 0 0;color:var(--dim)}
#donboard .dnav{display:flex;gap:8px;align-items:center}
#donboard .dnav .sp{flex:1}
/* ---- 解剖台解说 ---- */
.tnarr{margin-top:6px;font-size:11.5px;color:var(--acc-deep);background:var(--acc-soft);
  border-radius:8px;padding:5px 9px;line-height:1.55}
.tl-e.exfil .tnarr,.tl-e.plant .tnarr{background:var(--bad-soft);color:var(--bad)}
.tl-e.gate.vblock .tnarr{background:var(--ok-soft);color:var(--ok)}
/* ================= 首页 ================= */
#home{flex-direction:column;align-items:center;justify-content:center;gap:26px;padding:20px}
.hero-badge{display:flex;gap:10px;flex-wrap:wrap;justify-content:center}
.hchip{font-family:var(--mono);font-size:11px;color:var(--acc-deep);letter-spacing:2px;
  border:1px solid rgba(10,159,216,.35);border-radius:99px;padding:3px 12px;
  background:var(--acc-soft)}
#home .hero{text-align:center;position:relative}
#home .hero::before{content:'';position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);
  width:600px;height:200px;background:radial-gradient(ellipse,rgba(10,159,216,.06),transparent 70%);
  pointer-events:none}
#home .hero h1{font-size:36px;letter-spacing:4px;font-weight:900;line-height:1.35;color:var(--fg)}
#home .hero h1 .g{filter:drop-shadow(0 2px 8px rgba(10,159,216,.2))}
#home .hero h1 .g{background:linear-gradient(92deg,#1a6fb0 10%,var(--acc) 55%,var(--acc2) 95%);
  -webkit-background-clip:text;background-clip:text;color:transparent}
#home .hero p{color:var(--dim);font-size:14px;margin-top:10px;letter-spacing:1px}
.scanline{width:min(520px,80vw);height:3px;margin:16px auto 0;position:relative;overflow:hidden;
  background:var(--bg2);border-radius:99px}
.scanline::after{content:'';position:absolute;top:0;bottom:0;width:30%;border-radius:99px;
  background:linear-gradient(90deg,transparent,rgba(10,159,216,.75),transparent);
  animation:scan 2.6s linear infinite}
@keyframes scan{from{left:-30%}to{left:100%}}
.homecards{display:flex;gap:22px;flex-wrap:wrap;justify-content:center}
.hcard{position:relative;width:360px;padding:28px 26px;border-radius:16px;cursor:pointer;
  background:linear-gradient(180deg,var(--panel) 0%,var(--panel2) 100%);
  border:1px solid var(--line);box-shadow:var(--soft),inset 0 1px 0 rgba(255,255,255,.5);transition:.22s}
.hcard:hover{transform:translateY(-4px);border-color:rgba(10,159,216,.5);
  box-shadow:var(--soft-lg)}
.hcard::before,.hcard::after{content:'';position:absolute;width:14px;height:14px;transition:.22s;
  border-color:rgba(10,159,216,.45);border-style:solid}
.hcard::before{top:-1px;left:-1px;border-width:2px 0 0 2px;border-radius:14px 0 0 0}
.hcard::after{bottom:-1px;right:-1px;border-width:0 2px 2px 0;border-radius:0 0 14px 0}
.hcard:hover::before,.hcard:hover::after{width:22px;height:22px;border-color:var(--acc)}
.hcard .ico{width:54px;height:54px;border-radius:13px;display:grid;place-items:center;font-size:26px;
  background:linear-gradient(145deg,var(--acc-soft),rgba(124,92,255,.08));
  border:1px solid rgba(10,159,216,.25);margin-bottom:16px;box-shadow:0 2px 8px rgba(10,159,216,.1)}
.hcard h3{font-size:17px;letter-spacing:1px;margin-bottom:8px;color:var(--fg)}
.hcard h3 span{color:var(--acc);font-family:var(--mono);font-size:12px;margin-left:8px}
.hcard p{font-size:12.5px;color:var(--dim);line-height:1.75}
.hcard .go{margin-top:14px;color:var(--acc);font-size:13px;font-weight:700;letter-spacing:1px}
#homestat{font-size:12px;color:var(--faint);font-family:var(--mono);letter-spacing:1px}
/* ================= 知识库 / 选关 ================= */
#kb,#ctf{flex-direction:column;padding:18px 26px;overflow-y:auto}
.vhead{display:flex;align-items:center;gap:12px;margin-bottom:4px;flex-wrap:wrap}
.vhead h2{font-size:18px;letter-spacing:2px;color:var(--fg)}
.vhead h2 i{font-style:normal}
.vhead .sub{color:var(--faint);font-size:12.5px}
.vhead .spacer{flex:1}
.btn{font-size:12.5px;padding:7px 15px;border-radius:8px;border:1px solid var(--line2);
  background:var(--panel);color:var(--dim);cursor:pointer;transition:.15s;font-family:inherit;letter-spacing:1px}
.btn:hover{color:var(--acc);border-color:var(--acc);box-shadow:var(--soft)}
.btn.pri{background:linear-gradient(135deg,var(--acc),#3f8ef7);border:none;color:#fff;font-weight:800}
.btn.pri:hover{filter:brightness(1.08);color:#fff;box-shadow:var(--soft-lg)}
.btn.doc{border-color:rgba(10,159,216,.5);color:var(--acc)}
.chapbox{margin:14px 0 8px;padding:13px 18px;border-radius:var(--r);
  background:var(--acc-soft);border:1px solid rgba(10,159,216,.22);border-left:3px solid var(--acc)}
.chapbox b{font-size:14px;letter-spacing:1px;color:var(--fg)}
.chapbox p{font-size:12.5px;color:var(--dim);margin-top:3px}
.catcard{display:flex;align-items:center;gap:16px;border-radius:var(--r);padding:19px 22px;margin:10px 0;
  background:var(--panel);border:1px solid var(--line);box-shadow:var(--soft);
  cursor:pointer;transition:.2s;position:relative}
.catcard:hover{transform:translateX(4px);border-color:rgba(10,159,216,.5);box-shadow:var(--soft-lg)}
.catcard .catinfo{flex:1}
.catcard .catinfo b{font-size:16px;letter-spacing:1px;color:var(--fg)}
.catcard .catinfo p{font-size:12.5px;color:var(--dim);margin-top:5px;line-height:1.6}
.catcard .catstat{display:inline-block;margin-top:8px;font-size:11.5px;color:var(--acc-deep);
  font-family:var(--mono);border:1px solid rgba(10,159,216,.3);border-radius:99px;padding:2px 11px;
  background:var(--acc-soft)}
.catcard .catgo{font-size:20px;color:var(--faint)}
.catcard:hover .catgo{color:var(--acc)}
.kcard{background:var(--panel);border:1px solid var(--line);border-radius:var(--r);
  padding:15px 17px;margin:9px 0;position:relative;transition:.18s;box-shadow:var(--soft)}
.kcard:hover{border-color:var(--line2)}
.kcard[onclick]{cursor:pointer}
.kcard .r1{display:flex;align-items:center;gap:9px;flex-wrap:wrap}
.kcard .id{font-family:var(--mono);font-size:12px;color:var(--acc-deep);letter-spacing:1px}
.kcard .ttl{font-size:15px;font-weight:700;letter-spacing:.5px;color:var(--fg)}
.kcard .done{color:var(--ok);font-size:12px}
.tag{font-size:10.5px;padding:1px 8px;border-radius:99px;border:1px solid var(--line2);
  color:var(--dim);flex:none;letter-spacing:.5px;background:var(--panel2)}
.tag.dom{color:var(--acc-deep);border-color:rgba(10,159,216,.35);background:var(--acc-soft)}
.tag.stars{color:#e8a33d;border:none;background:transparent;padding:0;font-size:10px;letter-spacing:1px}
.tag.po{color:var(--ok);border-color:rgba(14,170,116,.35);background:var(--ok-soft)}
.kcard .brief{font-size:12.5px;color:var(--dim);margin-top:7px;line-height:1.7}
.ksec{margin-top:10px;border-top:1px dashed var(--line);padding-top:9px}
.ksec h5{font-size:12px;color:var(--acc-deep);margin-bottom:5px;display:flex;gap:7px;align-items:center;letter-spacing:1px}
.ksec p{font-size:13px;line-height:1.85;color:var(--fg)}
.kcard .acts{margin-top:12px;display:flex;gap:8px}
.karrow{margin-left:auto;color:var(--faint);transition:.2s;flex:none}
.kcard.open .karrow{transform:rotate(180deg);color:var(--acc)}
/* ================= 靶场 ================= */
#play{flex-direction:row}
#side{width:264px;flex:none;border-right:1px solid var(--line);background:var(--bg2);
  overflow-y:auto;padding:12px 11px}
.chap{margin:12px 9px 7px;font-size:11px;font-weight:700;color:var(--acc-deep);letter-spacing:2px;cursor:pointer}
.chap:first-child{margin-top:4px}
.chap:hover{color:var(--acc)}
.lv{display:block;width:100%;text-align:left;margin:3px 0;padding:9px 11px;border:none;border-radius:9px;
  background:transparent;cursor:pointer;transition:.15s;position:relative;font:inherit;border-left:2px solid transparent}
.lv:hover{background:var(--panel)}
.lv.on{background:var(--acc-soft);border-left-color:var(--acc)}
.lv .r1{display:flex;align-items:center;gap:7px;font-size:13.5px;font-weight:600;color:var(--fg)}
.lv .r1 .id{color:var(--faint);font-size:11px;font-family:var(--mono)}
.lv .r1 .ttl{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.lv .r1 .done{color:var(--ok);font-size:12px;flex:none}
.lv .r2{display:flex;gap:5px;margin-top:4px;align-items:center}
#mid{flex:1;display:flex;flex-direction:column;min-width:0;background:var(--bg)}
#lvhead{display:flex;align-items:center;gap:10px;padding:11px 24px;flex:none;flex-wrap:wrap;
  border-bottom:1px solid var(--line);background:rgba(255,255,255,.7)}
#lvhead .ttl{font-size:15px;font-weight:700;letter-spacing:1px;color:var(--fg)}
#lvhead .sub{font-size:12px;color:var(--faint)}
#lvhead .spacer{flex:1}
#errbar{display:none;padding:8px 24px;background:var(--bad-soft);color:var(--bad);
  border-bottom:1px solid rgba(224,72,104,.25);font-size:13px;flex:none}
#chat{flex:1;overflow-y:auto;padding:26px 0 16px;scroll-behavior:smooth}
.col{max-width:800px;margin:0 auto;padding:0 24px;display:flex;flex-direction:column;gap:20px}
.row{display:flex;gap:12px;animation:fadein .3s ease}
@keyframes fadein{from{opacity:0;transform:translateY(4px)}to{opacity:1;transform:none}}
.row.user{justify-content:flex-end}
.avatar{width:32px;height:32px;border-radius:9px;flex:none;display:grid;place-items:center;
  background:linear-gradient(150deg,#e8f6fe,#ece7ff);border:1px solid rgba(10,159,216,.4);
  font-size:15px}
.who{font-size:11.5px;color:var(--faint);margin-bottom:5px;font-weight:600;letter-spacing:1px}
.body{max-width:78%}
.txt{white-space:pre-wrap;word-break:break-word;line-height:1.8;font-size:14.5px;color:var(--fg)}
.row.user .txt{background:linear-gradient(135deg,#1273c9,#0a5fb0);color:#f2f9ff;
  padding:10px 14px;border-radius:14px 14px 4px 14px;box-shadow:var(--soft)}
.pill{align-self:center;max-width:76%;text-align:center;font-size:12.5px;padding:7px 16px;
  border-radius:99px;background:var(--panel);color:var(--dim);border:1px solid var(--line2)}
.pill.warn{background:var(--bad-soft);color:var(--bad);border-color:rgba(224,72,104,.35)}
.think{align-self:flex-start;display:flex;gap:4px;padding:10px 4px}
.think i{width:6px;height:6px;border-radius:50%;background:var(--acc);animation:blink 1.2s infinite}
.think i:nth-child(2){animation-delay:.18s}.think i:nth-child(3){animation-delay:.36s}
@keyframes blink{0%,80%,100%{opacity:.2}40%{opacity:1}}
.wincard{align-self:center;max-width:86%;width:fit-content;text-align:center;padding:22px 36px;
  border-radius:14px;border:1.5px solid var(--ok);background:var(--ok-soft);
  box-shadow:0 6px 22px rgba(14,170,116,.2);animation:pop .45s cubic-bezier(.2,1.4,.4,1)}
@keyframes pop{from{opacity:0;transform:scale(.85)}to{opacity:1;transform:scale(1)}}
.wincard .t1{font-size:15px;font-weight:800;color:#0a7d57;margin-bottom:9px;letter-spacing:2px}
.wincard .flag{font-family:var(--mono);font-size:14px;background:var(--panel);
  border:1px dashed var(--ok);padding:8px 18px;border-radius:9px;color:var(--fg)}
.wincard .t2{font-size:12px;color:var(--dim);margin-top:9px}
#composerwrap{flex:none;padding:10px 24px 18px}
.composer{max-width:800px;margin:0 auto;background:var(--panel);border:1px solid var(--line2);
  border-radius:16px;padding:12px 14px;transition:.2s;box-shadow:var(--soft)}
.composer:focus-within{border-color:var(--acc);box-shadow:var(--soft-lg)}
.composer textarea{width:100%;border:none;outline:none;background:transparent;color:var(--fg);
  font:inherit;font-size:14.5px;line-height:1.6;resize:none;height:66px}
.composer textarea::placeholder{color:var(--faint)}
.composer .cbar{display:flex;align-items:center;gap:10px;margin-top:6px}
.composer .hintkeys{font-size:11px;color:var(--faint);font-family:var(--mono)}
#sendbtn{margin-left:auto;width:36px;height:36px;border-radius:10px;border:none;cursor:pointer;
  background:linear-gradient(135deg,var(--acc),#3f8ef7);color:#fff;display:grid;place-items:center;
  transition:.15s}
#sendbtn:hover:not(:disabled){box-shadow:var(--soft-lg);transform:translateY(-1px)}
#sendbtn:disabled{background:var(--line);color:var(--faint);cursor:not-allowed}
#obs{width:302px;flex:none;border-left:1px solid var(--line);background:var(--bg2);
  overflow-y:auto;padding:14px 13px;display:flex;flex-direction:column;gap:11px}
#obs.hide{display:none}
.card{background:var(--panel);border:1px solid var(--line);border-radius:var(--r);padding:11px 12px}
.card h4{font-size:11px;font-weight:700;color:var(--dim);letter-spacing:1.5px;display:flex;
  align-items:center;gap:6px;margin-bottom:8px}
.card h4 .cnt{margin-left:auto;font-family:var(--mono);font-size:11px;color:var(--acc-deep);
  border:1px solid var(--line2);border-radius:99px;padding:0 7px}
.card .ev{font-family:var(--mono);font-size:11px;line-height:1.6;color:var(--dim);
  border-left:2px solid var(--line2);padding:2px 0 2px 8px;margin:5px 0;word-break:break-all}
.card .ev.tool{border-color:var(--acc)}
.card .ev.exfil{border-color:var(--bad);color:var(--bad)}
.card .ev.san{border-color:var(--warn);color:var(--warn)}
.obsbtns{display:flex;gap:6px;flex-wrap:wrap}
.obsbtns button{flex:1;font-size:12px;padding:7px 4px;border-radius:8px;border:1px solid var(--line2);
  background:var(--panel);color:var(--dim);cursor:pointer;transition:.15s;font-family:inherit}
.obsbtns button:hover{color:var(--acc);border-color:var(--acc)}
#poisonbox{display:none}
#poisonbox input,#poisonbox textarea{width:100%;border:1px solid var(--line2);border-radius:8px;
  background:var(--bg);color:var(--fg);font-family:var(--mono);font-size:12px;padding:7px;margin-bottom:7px}
#poisonbox textarea{height:92px;resize:vertical}
#poisonbox .go{width:100%;background:linear-gradient(135deg,var(--acc),#3f8ef7);color:#fff;
  border:none;padding:8px;border-radius:8px;cursor:pointer;font-weight:700;font-family:inherit}
.hintline{font-size:12.5px;color:#9a6410;background:var(--warn-soft);
  border:1px solid rgba(217,137,29,.3);border-radius:8px;padding:8px 10px;margin:4px 0}
#flagin{width:100%;border:1px solid var(--line2);border-radius:8px;background:var(--bg);
  color:var(--fg);font-family:var(--mono);font-size:12px;padding:7px;margin-bottom:7px}
.empty{text-align:center;color:var(--faint);font-size:12px;padding:8px 0}
/* ================= 弹窗 ================= */
#kmodal{display:none;position:fixed;inset:0;background:rgba(30,50,80,.35);backdrop-filter:blur(4px);
  z-index:50;align-items:flex-start;justify-content:center;padding:40px 20px;overflow-y:auto}
#kmodal.on{display:flex}
.kpanel{width:min(760px,100%);background:var(--panel);border:1px solid rgba(10,159,216,.4);
  border-radius:14px;box-shadow:var(--soft-lg);padding:24px 26px;animation:pop .3s ease}
.kpanel .r1{display:flex;align-items:center;gap:10px}
.kpanel h3{font-size:17px;flex:1;letter-spacing:1px;color:var(--fg)}
.kpanel h3 .tag{margin-left:8px}
.kpanel .x{width:32px;height:32px;border-radius:8px;border:1px solid var(--line2);background:transparent;
  color:var(--dim);cursor:pointer;font-size:15px}
.kpanel .x:hover{color:var(--bad);border-color:var(--bad)}
::-webkit-scrollbar{width:8px;height:8px}
::-webkit-scrollbar-thumb{background:var(--line2);border-radius:99px}
::-webkit-scrollbar-thumb:hover{background:var(--faint)}
::-webkit-scrollbar-track{background:transparent}
</style></head><body>

<!-- ============ 开场 Splash（数字雨 + 时间线 + 逐字绽放） ============ -->
<div id="splash" title="点击跳过">
  <div class="sp-beam"></div>
  <div class="sp-box">
    <div class="sp-brand">
      <div class="sp-mark">🛡</div>
      <div>
        <div class="sp-title">AgentSec<em> Labs</em></div>
        <div class="sp-sub">LLM AGENT SECURITY RANGE · LLM Agent 安全靶场</div>
      </div>
    </div>
    <div class="tl">
      <div class="tl-line"><i></i></div>
      <div class="tl-node up" style="--x:6%;--d:3.2s"><div class="tl-dot"></div>
        <div class="tl-card"><div class="y">2008</div><div class="n">DVWA</div><div class="d">Web 漏洞靶场启蒙</div></div></div>
      <div class="tl-node dn" style="--x:22%;--d:4.15s"><div class="tl-dot"></div>
        <div class="tl-card"><div class="y">2014</div><div class="n">SQLi-Labs</div><div class="d">SQL 注入闯关时代</div></div></div>
      <div class="tl-node up" style="--x:38%;--d:5.1s"><div class="tl-dot"></div>
        <div class="tl-card"><div class="y">2016</div><div class="n">Upload-Labs</div><div class="d">文件上传攻防</div></div></div>
      <div class="tl-node dn" style="--x:54%;--d:6.05s"><div class="tl-dot"></div>
        <div class="tl-card"><div class="y">2021</div><div class="n">逻辑 / 反序列化</div><div class="d">业务漏洞靶场成熟</div></div></div>
      <div class="tl-node up" style="--x:70%;--d:7s"><div class="tl-dot"></div>
        <div class="tl-card"><div class="y">2023</div><div class="n">LLM 崛起</div><div class="d">提示词注入 = 新注入</div></div></div>
      <div class="tl-node dn fin" style="--x:87%;--d:7.9s"><div class="tl-dot"></div>
        <div class="tl-card"><div class="y">2026</div><div class="n">AgentSec Labs</div><div class="d">AI 安全靶场</div></div></div>
    </div>
    <div class="tl-quote">
      <span style="--i:0">深</span><span style="--i:1">究</span><span style="--i:2">原</span><span style="--i:3">理</span><span class="dot" style="--i:4">·</span><span style="--i:5">方</span><span style="--i:6">可</span><span style="--i:7">行</span><span style="--i:8">稳</span><span style="--i:9">致</span><span style="--i:10">远</span>
    </div>
    <div class="sp-foot">⏭ SKIP · 点击任意处跳过 · EVOLUTION OF SECURITY RANGES</div>
  </div>
</div>

<div id="app">
<header>
  <div class="brand" onclick="go('home')">
    <div class="mark">🛡</div>
    <div class="bt">
      <b>AgentSec<em> Labs</em></b>
      <div class="sub"><span>AI SECURITY RANGE</span><span class="dot"></span><span id="chipengine2">LOCAL</span><span class="live" id="livedot" title="服务在线"></span></div>
    </div>
  </div>
  <div id="crumb"></div>
  <div id="progwrap"><span id="progtxt"></span>
    <div id="progbar-bg"><i id="progbar"></i></div>
  </div>
  <div class="hbtns">
    <button class="icobtn" id="obstoggle" title="观测面板开/关">◈</button>
    <button onclick="openPModal()" style="padding:6px 14px;border-radius:8px;border:2px solid var(--acc);background:var(--acc-soft);color:var(--acc-deep);cursor:pointer;font-size:13px;font-weight:800;transition:.15s;display:flex;align-items:center;gap:5px;font-family:inherit">⚙ 模型配置</button>
  </div>
</header>
<div id="errbar"></div>


<!-- 首页 -->
<section id="home" class="view on">
  <div class="hero-badge">
    <span class="hchip">39 LEVELS</span><span class="hchip">5 CHAPTERS</span>
    <span class="hchip" id="chipengine">LOCAL LLM</span><span class="hchip">ZERO-EXFIL SANDBOX</span><span class="hchip">BUILD V1.0</span>
  </div>
  <div class="hero">
    <h1>先懂原理 · 再破靶场<br><span class="g">LLM Agent 安全靶场</span></h1>
    <p>提示词层 → 智能体授权面 → 模型本体 · 三层递进攻防</p>
    <div class="scanline"></div>
  </div>
  <div class="qs">
    <div class="qs-l">
      <div class="qs-t">🚀 新手上路 · 三步完成首次渗透</div>
      <div class="qsteps">
        <div class="qstep"><b>①</b><b>选定目标</b> —— 进入任意关卡，你将面对一台真实运行的 AI Agent（本地/云端模型可在右上角 ⚙ 切换）</div>
        <div class="qstep"><b>②</b><b>构造攻击载荷</b> —— 通过对话实施提示词注入：直接提取、角色扮演、编码绕过、间接投毒、条件触发……组合你的攻击链</div>
        <div class="qstep"><b>③</b><b>验证攻击成效</b> —— 诱导 Agent 交出机密标记 <span class="mono">PI{...}</span> 即判定防线失守；卡关可调阅递进提示与技术文档</div>
      </div>
    </div>
    <div class="qs-r">
      <button class="qcta" onclick="enterPlay('L01')">🚀 从第 1 关开始<div>零基础教学关 · 无任何防御 · 一句话通关</div></button>
      <button class="qalt" onclick="go('ctf')">已有经验？去选关 →</button>
    </div>
  </div>
  <div class="homecards">
    <div class="hcard" onclick="go('kb')">
      <div class="ico">📚</div>
      <h3>LLM 知识点<span>KNOWLEDGE</span></h3>
      <p>每关四段技术文档：为什么会产生、漏洞原理、企业真实场景、修复方案。知其然，更知其所以然。</p>
      <div class="go">进入知识库 →</div>
    </div>
    <div class="hcard" onclick="go('ctf')">
      <div class="ico">🎯</div>
      <h3>LLM-CTF 靶场<span>RANGE</span></h3>
      <p>五大类 · 三十九关 · 本地或云端模型实时对抗。知识在知识库，弹药在靶场，卡关随时点「阅读文档」。</p>
      <div class="go">进入靶场 →</div>
    </div>
    <div class="hcard" onclick="go('defender')">
      <div class="ico">🛡️</div>
      <h3>防御实验室<span>DEFENDER</span></h3>
      <p>反向玩法：你来配防线，攻击套件 D01-D10 自动轰击。字面防线 vs 语义攻击，渗透率见分晓。</p>
      <div class="go">进入防御实验室 →</div>
    </div>
  </div>
  <div id="homestat"></div>
</section>

<!-- 知识库 -->
<section id="kb" class="view">
  <div class="vhead">
    <h2><i>📚</i> LLM 知识点</h2><span class="sub" id="kbsub">知识库 · 点左侧文档阅读，右侧 AI 答疑</span>
    <span class="spacer"></span>
    <button class="btn" onclick="go('home')">← 返回</button>
  </div>
  <div id="kbwrap">
    <div id="kblist">
      <div class="kbbar">
        <div class="segm" id="kbmode">
          <button class="on" data-v="chap">按篇章</button>
          <button data-v="dom">按领域</button>
        </div>
        <input id="kbq" class="ksearch" placeholder="搜索：关键词 / 关卡号 / 领域 / 内容…">
      </div>
      <div id="kblistitems"></div>
    </div>
    <div id="kbdoc"><div class="empty">← 从左侧选择一篇文档开始阅读<br>进入时会自动打开第一篇</div></div>
    <div id="kbcoach">
      <div class="cp-h"><b>🤖 AI 讲解员</b><span>基于当前文档 · 可追问</span></div>
      <div id="kbans" class="cp-m"><div class="cp-tip">选好文档后直接提问：「大白话总结」「真实案例」「怎么落地」…</div></div>
      <div class="cp-chips kbchips">
        <button class="chipx" onclick="kbAsk('用大白话总结这篇的核心')">大白话总结</button>
        <button class="chipx" onclick="kbAsk('举一个企业里的真实案例')">真实案例</button>
        <button class="chipx" onclick="kbAsk('作为开发者，防御具体怎么落地？')">怎么落地？</button>
        <button class="chipx" onclick="kbAsk('这一篇和相邻知识是什么关系？')">知识关联</button>
        <button class="chipx" onclick="kbAsk('我有看不懂的地方，请把这篇文档逐段通俗地讲解一遍')">看不懂？逐句精讲</button>
        <button class="chipx" onclick="kbAsk('在本篇基础上扩展：讲讲进阶话题与真实攻防中的应用')">扩展深入</button>
      </div>
      <div class="cp-in"><input id="kbqin" placeholder="问 AI 讲解员…回车发送">
        <button onclick="kbAsk()">问</button></div>
    </div>
  </div>
  <button id="selask" onclick="selAsk(event)">🤖 问这段</button>
</section>

<!-- CTF -->
<section id="ctf" class="view">
  <div class="vhead">
    <h2><i>🎯</i> LLM-CTF 靶场</h2><span class="sub" id="ctfsub">四大类 → 小类关卡 → 进入靶场</span>
    <span class="spacer"></span>
    <button class="btn" onclick="go('kb')">📚 知识库</button>
    <button class="btn" onclick="go('home')">← 返回</button>
  </div>
  <div id="ctflist"></div>
</section>

<!-- 靶场对战 -->
<section id="play" class="view">
  <div id="side"></div>
  <div id="mid">
    <div id="lvhead">
      <span class="ttl">未选择关卡</span><span class="sub" id="lvsub"></span>
      <span class="spacer"></span>
      <button class="btn" onclick="coachDock()" title="教官侧窗：给思路不给答案，问得越多提示越深">🎓 教官</button>
      <button class="btn doc" onclick="openKDoc(cur)">📖 阅读文档</button>
      <button class="btn" onclick="hint(1)">提示 1</button><button class="btn" onclick="hint(2)">提示 2</button>
      <button class="btn" onclick="hint(3)">提示 3</button><button class="btn" onclick="restart()">重开本关</button>
      <button class="btn" onclick="go('ctf')">← 选关</button>
    </div>
    <div id="chat"><div class="col" id="col"></div></div>
    <div id="composerwrap"><div class="composer">
      <textarea id="msg" placeholder="先选择关卡…" disabled></textarea>
      <div class="cbar">
        <span class="hintkeys">ENTER 发送 · SHIFT+ENTER 换行</span>
        <button id="sendbtn" onclick="send()" disabled title="发送">
          <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M12 19V5M5 12l7-7 7 7"/></svg>
        </button>
      </div>
    </div></div>
  </div>
  <div id="coachside">
    <div class="cp-h"><b>🎓 教官 · 引导模式</b><span id="coachlv">给思路 · 问得越多提示越深 · 不给 FLAG</span>
      <button class="x" onclick="coachDock()">✕</button></div>
    <div id="coachmsgs" class="cp-m">
      <div class="cp-tip">不会打就和教官聊：它会记住你们聊过什么，<b>问的次数越多提示越深</b>（方向 → 步骤 → 接近完整话术），一路带你到通关。FLAG 本体永远由靶机交出。</div>
      <div class="cp-chips">
        <button class="chipx" onclick="coachAsk('这关的突破口在哪里？')">突破口在哪？</button>
        <button class="chipx" onclick="coachAsk('我该按什么步骤打这一关？')">给我步骤</button>
        <button class="chipx" onclick="coachAsk('我的攻击被防线拦住了，接下来怎么办？')">被拦了？</button>
        <button class="chipx" onclick="coachAsk('我还是不会，直接教我打到通关为止')">我就是不会</button>
      </div>
    </div>
    <div class="cp-in"><input id="coachin" placeholder="和教官聊…回车发送">
      <button onclick="coachAsk()">问</button></div>
  </div>
  <aside id="obs">
    <div class="card obsbtns" style="gap:6px;display:flex">
      <button onclick="togglePoison()">投放毒文档</button>
      <button onclick="openKDoc(cur)">📖 本关文档</button>
    </div>
    <div class="card" id="poisonbox">
      <input id="pfname" placeholder="文件名，如 POISON_note.txt">
      <textarea id="pcontent" placeholder="毒文档内容…"></textarea>
      <button class="go" onclick="writeDoc()">写入知识库</button>
    </div>
    <div class="card" id="hints-card" style="display:none"><h4>💡 提示</h4><div id="hints"></div></div>
    <div class="card"><h4>⚙ 工具调用<span class="cnt" id="c-tool">0</span></h4><div id="ev-tool"><div class="empty">暂无</div></div></div>
    <div class="card"><h4>⚠ 外带监测<span class="cnt" id="c-exfil">0</span></h4><div id="ev-exfil"><div class="empty">暂无</div></div></div>
    <div class="card"><h4>🧹 消毒报告<span class="cnt" id="c-san">0</span></h4><div id="ev-san"><div class="empty">暂无</div></div></div>
    <div class="card"><h4>🔑 提交 FLAG</h4>
      <input id="flagin" placeholder="PI{...}（支持格式差异）">
      <button class="go" onclick="submitFlag()">提交（盲提取等还原类关卡用）</button>
    </div>
  </aside>
</section></section>

<!-- 防御实验室 -->
<section id="defender" class="view">
<style>
#defender{flex-direction:column;padding:0 0 14px}
#defender .vhead{flex-wrap:wrap;row-gap:8px}

.dguide{display:flex;gap:14px;align-items:center;margin:0 14px 12px;padding:13px 16px;
  background:linear-gradient(135deg,var(--acc-soft),#ffffff 70%);border:1px solid var(--line2);
  border-radius:12px;box-shadow:var(--soft)}
.gtxt{flex:1;font-size:13px;color:var(--dim);line-height:1.8}
.gtxt b{color:var(--fg);font-size:13.5px}
.gtxt .hl{color:var(--acc-deep);font-weight:700}
.gdemo{flex:none;border:none;border-radius:11px;padding:10px 18px;cursor:pointer;
  background:linear-gradient(135deg,var(--acc) 0%,var(--acc-deep) 100%);color:#fff;font-size:14px;
  font-weight:800;display:flex;flex-direction:column;gap:2px;box-shadow:var(--soft);transition:.15s}
.gdemo span{font-size:11px;font-weight:500;opacity:.85}
.gdemo:hover{filter:brightness(1.1);transform:translateY(-1px)}
#defwrap{display:flex;gap:10px;padding:0 10px 10px;flex:1;min-height:0;overflow:auto}
#defleft{width:335px;flex:none;display:flex;flex-direction:column;gap:10px}
#defright{flex:1;min-width:0;display:flex;flex-direction:column;gap:12px}
#defleft .card,#defright .card{padding:14px 15px}
#defleft .card h4,#defright .card h4{font-size:13.5px;margin-bottom:6px;color:var(--fg)}
.pchips{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.pchip{border:1px solid var(--line);border-radius:10px;padding:9px 11px;cursor:pointer;
  background:var(--panel2);transition:.15s}
.pchip b{display:block;font-size:12.5px;color:var(--fg)}
.pchip span{font-size:10.5px;color:var(--faint);line-height:1.45;display:block;margin-top:3px}
.pchip:hover{border-color:var(--line2);transform:translateY(-1px)}
.pchip.on{border-color:var(--acc);background:var(--acc-soft);box-shadow:0 0 0 1px var(--acc)}
.pchip.on b{color:var(--acc-deep)}
.dsw{display:flex;gap:10px;align-items:center;padding:9px 11px;border:1px solid var(--line);
  border-radius:10px;margin-bottom:7px;background:var(--panel2);cursor:pointer;transition:.15s}
.dsw:hover{border-color:var(--line2)}
.dsw .ic{flex:none;width:32px;height:32px;border-radius:9px;display:flex;align-items:center;
  justify-content:center;background:#fff;border:1px solid var(--line);font-size:16px}
.dsw .bd{flex:1;min-width:0}
.dsw b{font-size:12.5px;color:var(--fg)}
.dsw p{font-size:11px;color:var(--dim);margin-top:1px;line-height:1.45}
.dsw .tg{flex:none;width:40px;height:22px;border-radius:22px;background:#c6d3e2;position:relative;
  transition:.2s;flex:none}
.dsw .tg::after{content:'';position:absolute;top:2px;left:2px;width:18px;height:18px;border-radius:50%;
  background:#fff;transition:.2s;box-shadow:0 1px 3px rgba(0,0,0,.25)}
.dsw.on{border-color:var(--ok);background:var(--ok-soft)}
.dsw.on .ic{border-color:var(--ok)}
.dsw.on .tg{background:var(--ok)}
.dsw.on .tg::after{left:20px}
.wordsbox{margin:-2px 0 10px 42px;padding:8px 10px;border:1px dashed var(--line2);border-radius:10px;background:#fff}
.wordsbox label{font-size:10.5px;color:var(--faint)}
.wordsbox textarea{width:100%;min-height:46px;margin-top:4px;font-family:var(--mono);font-size:11.5px;
  padding:7px;border:1px solid var(--line2);border-radius:8px;resize:vertical;color:var(--fg)}
.agrid{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:12px}
.datk{border:1px solid var(--line);border-radius:10px;padding:8px 10px;cursor:pointer;
  background:var(--panel2);transition:.15s;position:relative}
.datk:hover{border-color:var(--line2);transform:translateY(-1px)}
.datk.sel{border-color:var(--acc);background:var(--acc-soft);box-shadow:0 0 0 1px var(--acc)}
.datk .kb{position:absolute;top:7px;right:9px;font-size:9.5px;color:var(--faint);
  border:1px solid var(--line2);border-radius:8px;padding:1px 6px}
.datk .kid{font-family:var(--mono);font-weight:800;font-size:11.5px;color:var(--acc-deep)}
.datk .nm{font-size:12px;font-weight:700;color:var(--fg);display:inline;margin-left:4px}
.datk .mt{font-size:10px;color:var(--warn);margin-top:2px}
#defrun{width:100%;padding:13px;font-size:15px;font-weight:800;border:none;border-radius:11px;
  cursor:pointer;background:linear-gradient(135deg,var(--acc) 0%,var(--acc-deep) 100%);color:#fff;
  box-shadow:var(--soft);transition:.15s}
#defrun:disabled{opacity:.55;cursor:wait}
#defrun:hover:not(:disabled){filter:brightness(1.08);transform:translateY(-1px)}
.dprog{font-size:12px;color:var(--dim);margin-top:8px;min-height:18px}
.sumrow{display:flex;gap:10px;margin:10px 0}
.dstat{flex:1;text-align:center;padding:14px 6px;border-radius:12px;border:1px solid var(--line)}
.dstat b{font-size:26px;display:block;font-family:var(--mono)}
.dstat.ok{background:var(--ok-soft)} .dstat.bad{background:var(--bad-soft)}
.dstat.dim{background:var(--panel2)}
.dnote{font-size:12px;color:var(--faint);line-height:1.7;margin-top:4px}
.dres{border:1px solid var(--line);border-radius:11px;background:var(--panel);padding:11px 13px;
  margin-bottom:8px;animation:dfade .25s}
@keyframes dfade{from{opacity:0;transform:translateY(5px)}}
.dres .rt{display:flex;gap:8px;align-items:center;font-size:13.5px;flex-wrap:wrap}
.dres .kid{font-family:var(--mono);font-weight:800;color:var(--acc-deep)}
.badge{font-size:11.5px;padding:2px 10px;border-radius:20px;font-weight:700;flex:none}
.badge.blocked{background:var(--ok-soft);color:var(--ok)}
.badge.leak{background:var(--bad-soft);color:var(--bad)}
.badge.held{background:var(--panel2);color:var(--dim)}
.badge.error{background:var(--warn-soft);color:var(--warn)}
.dres details{margin-top:6px;font-size:12.5px;color:var(--dim)}
.dres summary{cursor:pointer;color:var(--faint)}
.dm{margin-top:6px;line-height:1.6}
.tl{display:flex;flex-direction:column;gap:9px;overflow:auto;padding-right:4px;flex:1;min-height:0}
.tl-e{border:1px solid var(--line);border-left:4px solid var(--line2);border-radius:11px;
  background:var(--panel2);padding:10px 12px;font-size:13px;animation:dfade .3s;flex:none}
.tl-e.gate.vblock{border-left-color:var(--bad);background:var(--bad-soft)}
.tl-e.gate.vpass{border-left-color:var(--ok)}
.tl-e.model{border-left-color:var(--acc)}
.tl-e.tool{border-left-color:var(--acc2)}
.tl-e.sanitize{border-left-color:var(--warn);background:var(--warn-soft)}
.tl-e.exfil{border-left-color:var(--bad);background:var(--bad-soft)}
.tl-e.plant{border-left-color:var(--bad)}
.tl-e.report{border:none;background:transparent;padding:2px 0}
.tlh{display:flex;gap:7px;align-items:center;font-weight:700;color:var(--fg)}
.tlv{font-size:10.5px;padding:1px 9px;border-radius:12px;font-weight:700}
.tlv.block{background:var(--bad);color:#fff}
.tlv.pass{background:var(--ok-soft);color:var(--ok)}
.tld{color:var(--dim);margin-top:3px}
.tldata{font-family:var(--mono);font-size:11px;background:#0d1b2a;color:#9fd0ff;border-radius:9px;
  padding:9px;margin-top:7px;white-space:pre-wrap;word-break:break-all;max-height:190px;overflow:auto}
.vbanner{padding:14px 16px;border-radius:12px;font-size:16px;font-weight:800;animation:dfade .3s}
.vbanner.blocked{background:var(--ok-soft);color:var(--ok);border:1px solid var(--ok)}
.vbanner.leak{background:var(--bad-soft);color:var(--bad);border:1px solid var(--bad)}
.vbanner.held{background:var(--panel2);color:var(--dim);border:1px solid var(--line)}
.vbanner.error{background:var(--warn-soft);color:var(--warn);border:1px solid var(--warn)}
.abgrid{display:grid;grid-template-columns:1fr 1fr;gap:12px;flex:1;min-height:0}
.abcol{min-width:0;display:flex;flex-direction:column;min-height:0}
.abcol.A{border-top:3px solid var(--acc)}
.abcol.B{border-top:3px solid var(--acc2)}
#abcfg .abrow{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.abside{border:1px solid var(--line);border-radius:11px;padding:10px;background:var(--panel2);
  border-top:3px solid var(--acc)}
.abside.b{border-top-color:var(--acc2)}
.abside b{font-size:12.5px}
.abside select{width:100%;margin:6px 0}
.minis{display:flex;flex-wrap:wrap;gap:5px;margin-top:7px}
.mini{font-size:10.5px;color:var(--dim);border:1px solid var(--line);border-radius:8px;padding:3px 8px;
  cursor:pointer;background:#fff;display:flex;gap:4px;align-items:center;user-select:none}
.mini input{accent-color:var(--acc);margin:0}
.mini.on{border-color:var(--ok);color:var(--ok);font-weight:700}
.empty{padding:26px 18px;text-align:center;color:var(--faint);font-size:13px;line-height:2.1}
.empty b{color:var(--dim);font-size:13.5px}
.segm{display:flex;border:1px solid var(--line2);border-radius:10px;overflow:hidden;background:var(--panel)}
.segm button{border:none;background:transparent;color:var(--dim);padding:8px 13px;font-size:12.5px;
  cursor:pointer;transition:.15s}
.segm button.on{background:var(--acc-soft);color:var(--acc-deep);font-weight:800}
/* ---- 教官侧窗 ---- */
/* ---- 解剖台：暗色 SOC 监控台 ---- */
.tl{background:#0d1626;border-radius:12px;padding:10px;border:1px solid #1e3352}
.tl-e{background:#122036;border-color:#1e3352;color:#d7e6f5}
.tl-e .tlh b{color:#e8f1fb}
.tl-e .tld{color:#8fa8c4}
.tl-e.gate.vpass{background:#12253a;border-left-color:var(--ok)}
.tl-e.gate.vblock{background:#2a1622;border-left-color:var(--bad)}
.tl-e.exfil{background:#2a1622;border-left-color:var(--bad)}
.tl-e.sanitize{background:#2a2416;border-left-color:var(--warn)}
.tnarr{background:#16283f;color:#9cc4ea}
.tl-e.exfil .tnarr,.tl-e.plant .tnarr{background:#33202b;color:#f2a6b8}
.tl-e.gate.vblock .tnarr{background:#16302a;color:#7fe0b6}
.tts{margin-left:auto;font-family:var(--mono);font-size:10px;color:#5b769a;font-weight:400}
.liveb{color:var(--bad);font-size:11px;margin-left:8px;animation:blink 1.1s infinite;font-weight:700}
@keyframes blink{50%{opacity:.25}}
/* ---- 攻防数据流（左·攻击方 / 右·防守方） ---- */
#microbox{flex:1;min-height:0;flex-direction:column;padding:10px}
#microbox .empty{text-align:left}
#fwrap{flex:1;min-height:0;display:flex;align-items:stretch}
.fcol{flex:1;min-width:0;display:flex;flex-direction:column;min-height:0}
#abrunbtn{width:100%;padding:13px;font-size:15px;font-weight:800;border:none;border-radius:11px;cursor:pointer;background:linear-gradient(135deg,var(--acc) 0%,var(--acc-deep) 100%);color:#fff;box-shadow:var(--soft);transition:.15s}
#abrunbtn:hover{filter:brightness(1.08);transform:translateY(-1px)}
.fhead{font-size:12.5px;font-weight:800;letter-spacing:.5px;padding:8px 10px;flex:none;
  display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.dd{position:relative;flex:1;min-width:150px}
.ddhead{width:100%;display:flex;align-items:center;gap:6px;padding:6px 10px;border-radius:8px;
  background:#fff;border:1px solid var(--line2);cursor:pointer;font-size:12px;color:var(--fg);font-weight:700}
.ddhead:hover{border-color:var(--acc)}
.ddhead em{font-style:normal;font-weight:400;color:var(--faint);font-size:10.5px;flex:1;
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.ddhead i{font-style:normal;color:var(--faint)}
.ddmenu{display:none;position:absolute;top:calc(100% + 4px);left:0;right:0;z-index:40;
  max-height:290px;overflow:auto;background:#fff;border:1px solid var(--line2);border-radius:10px;
  box-shadow:var(--soft-lg);padding:4px}
.dd.open .ddmenu{display:block}
.dditem{padding:7px 10px;border-radius:8px;cursor:pointer}
.dditem:hover{background:var(--acc-soft)}
.dditem.on{background:var(--acc-soft);outline:1px solid var(--acc)}
.dditem b{font-size:12px;color:var(--fg);display:block}
.dditem b .kk{font-family:var(--mono);color:var(--acc-deep);margin-right:5px}
.dditem span{font-size:10.5px;color:var(--dim);line-height:1.5;display:block;margin-top:1px}
#defrun{flex:none;padding:7px 16px;font-size:13px;font-weight:800;border:none;border-radius:9px;
  cursor:pointer;background:linear-gradient(135deg,#e04868,#c22b4a);color:#fff;box-shadow:var(--soft)}
#defrun:disabled{opacity:.55;cursor:wait}
#defrun:hover:not(:disabled){filter:brightness(1.1)}
#defprog{margin-left:8px;font-weight:400;font-size:11px;color:var(--faint);flex:none;max-width:40%;
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.fhead.atk{background:#fbe9ec;color:#c22b4a;border:1px solid #f0c4cd;border-bottom:none;border-radius:10px 10px 0 0}
.fhead.def{background:#e8f2fd;color:#1663ad;border:1px solid #c4dcf2;border-bottom:none;border-radius:10px 10px 0 0}
.fA .tl{border:1px solid #f0c4cd;border-top:none;border-radius:0 0 10px 10px}
.fD .tl{border:1px solid #c4dcf2;border-top:none;border-radius:0 0 10px 10px}
.fdir{flex:none;width:66px;display:flex;flex-direction:column;align-items:center;
  justify-content:center;gap:6px;color:var(--faint);user-select:none}
.fdir .argrp{display:flex;gap:2px;font-size:15px;font-weight:900;letter-spacing:-2px;
  color:#b9c6d6;transition:.25s}
.fdir b{font-size:18px;opacity:.55;transition:.25s}
.fdir.r .argrp{color:var(--bad);animation:arrR 1s linear infinite}
.fdir.r b{color:var(--bad);opacity:1;transform:none}
.fdir.l .argrp{color:#1663ad;transform:scaleX(-1);animation:arrR 1s linear infinite}
.fdir.l b{color:#1663ad;opacity:1}
.fdir.r .lb,.fdir.l .lb{display:none}
@keyframes arrR{0%{transform:translateX(-8px);opacity:.25}50%{opacity:1}100%{transform:translateX(8px);opacity:.25}}
.fdir.l .argrp{animation-name:arrL}
@keyframes arrL{0%{transform:scaleX(-1) translateX(-8px);opacity:.25}50%{opacity:1}100%{transform:scaleX(-1) translateX(8px);opacity:.25}}
/* 放大模式：隐藏配置列，数据流铺满 */
body.flowfull #defleft{display:none}
body.flowfull #defwrap{padding:0 10px 10px}
body.flowfull .dguide{display:none}
#flowverdict{flex:none;margin-top:10px}
.dfix{margin-top:8px;font-size:12.5px;color:var(--dim)}
.chipx{font-size:11.5px;border:1px solid var(--line2);background:var(--panel);color:var(--acc-deep);
  border-radius:99px;padding:3px 11px;cursor:pointer;margin:2px}
.chipx:hover{border-color:var(--acc)}
.cntx{font-size:11px;color:var(--faint);margin-right:8px}
/* ---- 教官侧窗（独立列，与观测面板并存） ---- */
#coachside{display:none;width:300px;flex:none;border-left:1px solid var(--line);background:var(--bg2);
  flex-direction:column;min-height:0}
#play.coachon #coachside{display:flex}
/* ---- 结果空状态行动卡 ---- */
.dhero{text-align:center;padding:20px 14px}
.dhero .dh1{font-size:16px;font-weight:800;margin-bottom:4px}
.dhero .dh2{font-size:12.5px;color:var(--dim);margin-bottom:14px}
.dbtns{display:flex;flex-direction:column;gap:10px;max-width:300px;margin:0 auto}
.dbtn{border:1px solid var(--line2);background:var(--panel2);border-radius:12px;padding:12px;
  cursor:pointer;font-size:14px;font-weight:700;color:var(--fg);transition:.15s}
.dbtn span{display:block;font-size:11px;color:var(--faint);font-weight:400;margin-top:3px}
.dbtn:hover{transform:translateY(-1px);border-color:var(--acc)}
.dbtn.pri{background:linear-gradient(135deg,var(--acc),var(--acc-deep));color:#fff;border:none;box-shadow:var(--soft)}
.dbtn.pri span{color:rgba(255,255,255,.85)}
.dhero .dh3{font-size:11px;color:var(--faint);margin-top:14px}
</style>
  <div class="vhead">
    <h2><i>🛡️</i> 防御实验室</h2><span class="sub" id="defsub">全套 D01-D10 打一遍，量化你的防线</span>
    <span class="spacer"></span>
    <div class="segm" id="dsegm">
      <button class="on" data-m="micro">⚔ 攻防数据流</button>
      <button data-m="ab">⚖ A/B 对比</button>
    </div>
    <button class="btn" onclick="dShow()">❓ 玩法说明</button>
    <button class="btn" onclick="go('home')">← 返回</button>
  </div>
  <div class="dguide" id="dguide">
    <div class="gtxt"><b>你是防守方。</b>
      左框下拉选<b>攻击手法</b>、右框下拉选<b>防守策略</b>、侧栏微调 8 个组件 → 开始攻击看数据流。
      <b>拦住</b>=防线有效；<b>渗透</b>=机密漏出去了，攻防数据流能看到它从哪条缝漏的。
      不知道怎么玩？点右边按钮，30 秒看完一个经典战例。</div>
    <button class="gdemo" onclick="demo()">🎬 一键看经典战例<span>自动选好一切 · 约 30 秒</span></button>
  </div>
  <div id="defwrap">
    <div id="defleft">
      <div class="card" id="scard">
        <h4>🧱 微调防线组件 <span style="color:var(--faint);font-weight:400;font-size:11px">（整体策略在右侧防守方框下拉切换）</span></h4>
        <div id="defswitches"></div>
      </div>
      <div class="card" id="abruncard" style="display:none">
        <h4>🎯 选择攻击 <span style="color:var(--faint);font-weight:400;font-size:11px">（悬停看手法说明）</span></h4>
        <div id="abatks" class="agrid" style="margin-bottom:12px"></div>
        <button id="abrunbtn" onclick="abRun()">⚖ 对比开跑</button>
        <div id="abprog" class="dprog"></div>
      </div>
    </div>
    <div id="defright">
      <div id="microbox" class="card" style="display:flex">
        <h4 style="width:100%;display:flex;align-items:center;gap:8px">⚔ 攻防数据流
            <span style="font-weight:400;font-size:11.5px;color:var(--faint)">左·攻击方发起 ▶ 右·防守方工程全程应对</span>
            <span id="microlive" class="liveb" style="display:none">● LIVE 交战中</span>
            <span id="defprog" class="dprog"></span>
            <button class="btn" id="ffbtn" style="margin-left:auto;flex:none" onclick="toggleFlowFull()">⛶ 放大</button></h4>
        <div id="fwrap">
          <div class="fcol fA">
            <div class="fhead atk">🔴 攻击方
              <div class="dd" id="atkdd">
                <div class="ddhead" id="atkdd-h" onclick="event.stopPropagation();ddToggle('atkdd')"></div>
                <div class="ddmenu" id="atkdd-m"></div>
              </div>
              <button id="defrun" onclick="microRun()">⚔ 开始攻击</button>
            </div>
            <div id="flowA" class="tl"></div>
          </div>
          <div class="fdir" id="fdir" title="数据流方向：▶ 攻击→防守 / ◀ 防守→攻击">
            <div class="argrp"><span>▶</span><span>▶</span><span>▶</span></div>
            <b>⚔</b><span class="lb" style="font-size:10px">待命</span>
          </div>
          <div class="fcol fD">
            <div class="fhead def">🛡 防守方
              <div class="dd" id="predd">
                <div class="ddhead" id="predd-h" onclick="event.stopPropagation();ddToggle('predd')"></div>
                <div class="ddmenu" id="predd-m"></div>
              </div>
            </div>
            <div id="flowD" class="tl"></div>
          </div>
        </div>
        <div id="flowverdict"></div>
      </div>
      <div id="abcfg" class="card" style="display:none"></div>
      <div id="abgrid" style="display:none">
        <div class="abcol card A"><h4>🅰 A 侧防线</h4><div id="abtl-A" class="tl"></div></div>
        <div class="abcol card B"><h4>🅱 B 侧防线</h4><div id="abtl-B" class="tl"></div></div>
      </div>
      <div id="abcmp" style="display:none"></div>
    </div>
  </div>
</section>
</div>

<!-- 知识弹窗 -->
<div id="kmodal" onclick="if(event.target===this)closeKDoc()">
  <div class="kpanel" id="kpanel"></div>
</div>
<!-- 防御实验室引导 -->
<div id="donboard" onclick="if(event.target===this)dClose()">
  <div class="dpanel">
    <div class="dh">🛡️ 防御实验室 · 玩法引导 <span id="dstepn">1/4</span></div>
    <div class="dbody" id="dstep"></div>
    <div class="dnav">
      <button class="btn" onclick="dClose()">跳过</button>
      <span class="sp"></span>
      <button class="btn" id="dprev" onclick="dGo(-1)">上一步</button>
      <button class="btn pri" id="dnext" onclick="dGo(1)">下一步</button>
    </div>
  </div>
</div>

<!-- 激励 Toast 容器 -->
<div id="toasts"></div>
<div id="pmodal" onclick="if(event.target===this)closePModal()">
  <div class="ppanel">
    <h3>⚙ 模型配置 <span id="pbadge" class="pbadge on">● 本地</span></h3>
    <div class="psub">靶机引擎使用当前活跃模型运行。切换后立即生效。</div>
    <div class="pfield"><label>提供商</label><select id="pprov" onchange="pProvChange()"></select></div>
    <div class="pfield"><label>Base URL</label><input id="purl"><div class="hint" id="purlhint"></div></div>
    <div class="prow">
      <div class="pfield"><label>API Key</label><input id="pkey" type="password" placeholder="sk-..."></div>
      <div class="pfield"><label>模型</label>
        <div id="pmodelwrap" style="display:flex;gap:6px">
          <select id="pmodelsel" style="flex:1;display:none" onchange="document.getElementById('pmodel').value=this.value"></select>
          <input id="pmodel" style="flex:1" placeholder="手动输入或点📋拉取">
          <button class="btn" style="flex:none;padding:8px 10px" onclick="pFetchModels()" title="拉取可用模型列表">📋</button>
        </div>
      </div>
    </div>
    <div class="pbtns">
      <button class="btn" onclick="pTest()">🔌 测试连接</button>
      <span style="flex:1"></span>
      <button class="btn" onclick="closePModal()">取消</button>
      <button class="btn pri" onclick="pSave()">💾 保存并启用</button>
    </div>
    <div class="pstatus" id="pstatus"></div>
  </div>
</div>

<script>
/* Splash：数字雨（慢速）+ 两侧二进制雨 + 自动淡出（约14s），点击跳过 */
(function(){
  const sp=document.getElementById('splash'); if(!sp) return;
  sp.addEventListener('click',()=>{ sp.classList.add('off');
    setTimeout(()=>sp.remove(),450); });
  setTimeout(()=>{ if(document.body.contains(sp)){ sp.classList.add('off');
    setTimeout(()=>{ if(document.body.contains(sp)) sp.remove(); },450); } },14600);

  /* ① 开场数字雨：慢速下落（速度 0.32 行/帧 ≈ 原 1/3），拖尾更长 */
  const cv=document.createElement('canvas'); cv.id='sprain';
  sp.insertBefore(cv, sp.firstChild);
  const ctx=cv.getContext('2d');
  const fit=()=>{ cv.width=innerWidth; cv.height=innerHeight; };
  fit();
  const cols=Math.max(8,Math.floor(cv.width/16));
  const drops=Array(cols).fill(0).map(()=>Math.random()*cv.height/14);
  const chars='アイウエオカキクケコサシスセソタチツテト0123456789ABCDEFｱｲｳｴｵ';
  const t0=performance.now();
  function draw(t){
    ctx.fillStyle='rgba(4,8,15,.085)';           /* 更淡的残影 → 更长的尾 */
    ctx.fillRect(0,0,cv.width,cv.height);
    ctx.font='14px monospace';
    for(let i=0;i<cols;i++){
      if(drops[i]<0){ drops[i]+=0.32; continue; } /* 尚未落下的列 */
      const ch=chars[Math.floor(Math.random()*chars.length)];
      ctx.fillStyle=Math.random()<.07?'#d8f6ff':'rgba(0,212,255,.7)';
      ctx.fillText(ch,i*16,drops[i]*16);
      if(drops[i]*16>cv.height && Math.random()>.99) drops[i]=Math.random()*-40; /* 落出后随机停顿再落 */
      drops[i]+=0.32;                              /* 慢速 */
    }
    if(t-t0<2300 && sp.isConnected){ requestAnimationFrame(draw); }
    else{ cv.style.opacity='0'; setTimeout(()=>cv.remove(),900); }
  }
  requestAnimationFrame(draw);

  /* ② 时间线登场后（~3s）：两侧 0/1 原地错乱闪变（glitch 风，非下落） */
  const bc=document.createElement('canvas'); bc.id='sidebin';
  sp.insertBefore(bc, sp.firstChild);
  const bx=bc.getContext('2d');
  bc.width=innerWidth; bc.height=innerHeight;
  const GAPS=18, GAPY=16;
  const bcols=Math.floor(bc.width/GAPS), brows=Math.floor(bc.height/GAPY);
  const cells=[];
  for(let c=0;c<bcols;c++){
    if(c*GAPS>bc.width*0.17 && c*GAPS<bc.width*0.83) continue;  /* 只占两侧边带 */
    for(let r=0;r<brows;r++)
      cells.push({c,r,ch:Math.random()<.5?'0':'1',a:.15+Math.random()*.7});
  }
  setTimeout(()=>{ if(bc.isConnected) bc.style.opacity='1'; },3000); /* 与时间线同步浮现 */
  let bf=0;
  function bdraw(){
    if(!sp.isConnected){ bc.remove(); return; }
    bf++;
    if(bf%3===0){                       /* 每3帧全量重绘 → 高频错乱 */
      bx.clearRect(0,0,bc.width,bc.height);
      bx.font='13px monospace';
      for(const cell of cells){
        if(Math.random()<.22){          /* 每轮随机突变大量字符 */
          cell.ch=Math.random()<.5?'0':'1';
          cell.a=.1+Math.random()*.8;
        }
        const glitch=Math.random()<.035;/* 少数字符横向错位 */
        bx.fillStyle=`rgba(0,212,255,${(cell.a*(glitch?1:.55)).toFixed(2)})`;
        bx.fillText(cell.ch, cell.c*GAPS+(glitch?(Math.random()*12-6):0), cell.r*GAPY);
      }
      if(Math.random()<.3){             /* 偶发错乱光条扫过边带 */
        const ry=Math.floor(Math.random()*brows)*GAPY;
        const left=Math.random()<.5;
        bx.fillStyle='rgba(0,212,255,.10)';
        bx.fillRect(left?0:bc.width*0.83, ry, bc.width*0.17, GAPY);
      }
    }
    requestAnimationFrame(bdraw);
  }
  requestAnimationFrame(bdraw);
})();

/* ===== 激励语录 + Toast ===== */
const QUOTES_OK=[
  "Flag 拿下！每一个漏洞都是通往精通的阶梯。",
  "漂亮——攻防之道，唯手熟尔。",
  "干净利落，这就是红队的节奏。",
  "破关成功。这个思路从现在起属于你。",
  "又一个盲区被你点亮，安全因研究者而进步。",
  "Fire in the hole！下一关的防线已经在发抖了。",
  "拿下！攻击链的每一环，你现在都能亲手拼装。"
];
const QUOTES_NO=[
  "差一点点——攻击面往往就藏在再试一次的地方。",
  "只是情报不足而已，换个措辞再侦察一轮。",
  "红队没有失败，只有未完成的迭代。",
  "高手也是从看提示开始的——右侧「提示 1」就在那。",
  "这次没中，但你又排除了一条路。排除法也是法。",
  "换个动词、换个通道、换个语境——三选一，再来。",
  "防线是概率性的。同一发，再打一次。"
];
const QUOTES_HI=[
  "唯一的真正安全，是持续不断地研究不安全。",
  "攻击者的想象力，永远是防御者的考卷。",
  "每一个漏洞背后，都有一个想当然的假设。",
  "不要相信任何输入——包括这句话。",
  "渗透的本质是信息差，安全的本质是消除信息差。",
  "最危险的漏洞，是坚信自己没有漏洞。",
  "红队思维：像水一样，哪里有缝就往哪里渗。",
  "进攻，是最好的防御情报。",
  "保持好奇，保持多疑。",
  "Talk is cheap. Show me the exploit.",
  "今天的第 37 次失败，正在给明天的第 1 次成功铺路。",
  "看懂一个漏洞，比打穿十个靶子更值钱。"
];
function pick(a){ return a[Math.floor(Math.random()*a.length)]; }
function toast(msg, cls){
  const box=document.getElementById('toasts'); if(!box) return;
  const t=document.createElement('div'); t.className='toast '+(cls||'');
  const head = cls==='ok' ? '🚩 FLAG ACCEPTED' : cls==='no' ? '⛔ ACCESS DENIED' : '💡 SECURITY WISDOM';
  t.innerHTML=`<div class="t-head">${head}</div>${esc(msg)}`;
  t.onclick=()=>t.remove();
  box.appendChild(t);
  setTimeout(()=>{ t.classList.add('fade'); setTimeout(()=>t.remove(),420); },7000);
}
let PCFG=null;
async function openPModal(){
  document.getElementById('pmodal').classList.add('on');
  if(!PCFG){
    try{
      PCFG=await api('/api/providers');
      pRender();
    }catch(e){
      document.getElementById('pstatus').textContent='加载失败：'+e;
    }
  }
}
function closePModal(){ document.getElementById('pmodal').classList.remove('on'); }

function pRender(){
  const sel=document.getElementById('pprov');
  let html='';
  if(PCFG.presets){
    for(const pid of PCFG.presets){
      const prov=(PCFG.providers||{})[pid]||{};
      const nm=prov.name||pid;
      const cur=PCFG.current===pid?' ✓':'';
      html+='<option value="'+pid+'">'+nm+cur+'</option>';
    }
  }
  html+='<option value="__custom">＋ 自定义（手填 URL/Key/模型）</option>';
  sel.innerHTML=html;
  sel.value=PCFG.current||'local';
  pProvChange();
}
function pProvChange(){
  const pid=document.getElementById('pprov').value;
  // 重新渲染选项的选中标记
  const sel=document.getElementById('pprov');
  for(const opt of sel.options){
    if(opt.value==='__custom') continue;
    const prov=(PCFG&&PCFG.providers||{})[opt.value]||{};
    let nm=prov.name||opt.value;
    nm=nm.replace(/ \u2713$/,'');
    if(opt.value===pid) nm+=' \u2713';
    opt.textContent=nm;
  }
  if(pid==='__custom'){
    document.getElementById('purl').value='';
    document.getElementById('purl').placeholder='https://your-endpoint.com/v1';
    document.getElementById('pkey').value='';
    document.getElementById('pkey').disabled=false;
    document.getElementById('pkey').placeholder='你的 API Key';
    document.getElementById('pmodel').value='';
    document.getElementById('purlhint').textContent='任何 OpenAI 兼容端点（vLLM / LiteLLM / OneAPI / 中转站等）';
    document.getElementById('pbadge').textContent='● 自定义';
    document.getElementById('pbadge').className='pbadge off';
    document.getElementById('pstatus').textContent='';
    return;
  }
  const prov=(PCFG&&PCFG.providers&&PCFG.providers[pid])||{};
  document.getElementById('purl').value=prov.url||'';
  document.getElementById('pkey').value=prov.key||'';
  document.getElementById('pmodel').value=prov.model||'';
  const msel=document.getElementById('pmodelsel');
  const minp=document.getElementById('pmodel');
  msel.style.display='none'; minp.style.display='';
  document.getElementById('purlhint').textContent=prov.note||'';
  const local=pid==='local';
  document.getElementById('pkey').disabled=local;
  document.getElementById('pkey').placeholder=local?'（本地无需 Key）':'sk-...';
  document.getElementById('pbadge').textContent=local?'● 本地':'● 云端';
  document.getElementById('pbadge').className='pbadge '+(local?'on':'off');
  document.getElementById('pstatus').textContent='';
}
async function pFetchModels(){
  const url=document.getElementById('purl').value.trim();
  const key=document.getElementById('pkey').value.trim();
  const st=document.getElementById('pstatus');
  if(!url){ st.textContent='请先填写 Base URL'; st.className='pstatus bad'; return; }
  st.textContent='拉取模型列表中…'; st.className='pstatus';
  try{
    const r=await api('/api/providers/models',{url,key});
    if(r.error){ st.textContent='❌ '+r.error; st.className='pstatus bad'; return; }
    const sel=document.getElementById('pmodelsel');
    const inp=document.getElementById('pmodel');
    if(r.models&&r.models.length){
      sel.innerHTML='<option value="">— 选择模型 —</option>'+
        r.models.map(m=>'<option value="'+m+'">'+m+'</option>').join('');
      sel.style.display='';
      inp.style.display='none';
      sel.value=r.models[0];
      inp.value=r.models[0];
      st.textContent='✅ 拉取到 '+r.models.length+' 个模型，从下拉框选择'; st.className='pstatus ok';
    }else{ st.textContent='⚠ 该端点未返回模型列表，请手动输入'; st.className='pstatus bad'; }
  }catch(e){ st.textContent='❌ 拉取失败'; st.className='pstatus bad'; }
}
async function pTest(){
  const st=document.getElementById('pstatus');
  st.textContent='测试中…（云端模型可能需要更长等待）'; st.className='pstatus';
  const pid=document.getElementById('pprov').value;
  const url=document.getElementById('purl').value;
  const key=document.getElementById('pkey').value;
  const model=document.getElementById('pmodel').value;
  try{
    const r=await api('/api/providers/test',{pid,url,key,model});
    if(r.ok){ st.textContent='✅ 连接成功：'+r.reply; st.className='pstatus ok'; }
    else{ st.textContent='❌ '+r.error; st.className='pstatus bad'; }
  }catch(e){ st.textContent='❌ 请求失败'; st.className='pstatus bad'; }
}
async function pSave(){
  const pid=document.getElementById('pprov').value;
  const realPid=pid==='__custom'?'custom':pid;
  const st=document.getElementById('pstatus');
  st.textContent='保存中…'; st.className='pstatus';
  try{
    const msel=document.getElementById('pmodelsel');
    const mval=(msel.style.display!=='none'&&msel.value?msel.value:document.getElementById('pmodel').value).trim().toLowerCase();
    await api('/api/providers/set',{
      pid:realPid,
      url:document.getElementById('purl').value,
      key:document.getElementById('pkey').value,
      model:mval});
    st.textContent='✅ 已保存并启用'; st.className='pstatus ok';
    PCFG=null;
    setTimeout(closePModal,800);
  }catch(e){ st.textContent='❌ 保存失败'; st.className='pstatus bad'; }
}
(function motivator(){          /* 不定时弹出安全研究者的华语 */
  const fire=()=>{ setTimeout(()=>{
    if(!document.hidden) toast(pick(QUOTES_HI));
    fire();
  }, 65000 + Math.random()*95000); };
  setTimeout(()=>{ if(!document.hidden) toast(pick(QUOTES_HI)); fire(); }, 25000);
})();

let sid = localStorage.getItem('agentsec-sid');
if(!sid){ sid='S'+Math.random().toString(36).slice(2,12); localStorage.setItem('agentsec-sid',sid); }
let cur=null, sending=false, LV={}, KNOW={}, KBT={}, KBR={}, DATA=null;
let kbView='chap';
let kbChapter=0, ctfChapter=0, playChapter=1;

document.getElementById('obstoggle').onclick=()=>document.getElementById('obs').classList.toggle('hide');

function esc(s){ return String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])); }
function errbar(t){ const e=document.getElementById('errbar'); if(t){e.style.display='block';e.textContent='⚠ '+t;} else e.style.display='none'; }
async function api(path, body){
  let r;
  try{ errbar(''); r=await fetch(path, body?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}:undefined); }
  catch(e){ errbar('无法连接服务——请先运行 python webui.py（或双击 start_webui.bat）'); throw e; }
  return r.json();
}
function go(v){
  ['home','kb','ctf','play','defender'].forEach(x=>document.getElementById(x).classList.toggle('on',x===v));
  const crumb=document.getElementById('crumb');
  const M={home:'',kb:'知识库',ctf:'CTF 靶场',play:'对战',defender:'防御实验室'};
  crumb.innerHTML = v==='home' ? '' :
    `<b onclick="go('home')">首页</b> / `+(v==='play'?`<b onclick="go('ctf')">CTF</b> / 对战`:`<span>${M[v]}</span>`);
  if(v==='kb') renderKB(); if(v==='ctf') renderCTF();
  if(v==='defender') renderDefender();
}
async function loadAll(){
  DATA = await api('/api/levels');
  const kb = await api('/api/knowledge');
  KNOW = kb.items || {}; KBT = kb.tldr || {}; KBR = kb.related || {};
  const done=DATA.solved.length,total=DATA.levels.length;
  document.getElementById('progtxt').textContent=done+'/'+total;
  document.getElementById('progbar').style.width=(done/total*100)+'%';
  const provName=(await api('/api/providers')).current==='local'?'LOCAL LLM':'CLOUD API';
  document.getElementById('homestat').textContent=`已通关 ${done}/${total} · ${provName} · ALL DATA FICTIONAL`;
  const ce=document.getElementById('chipengine'); if(ce) ce.textContent=provName;
  const ld=document.getElementById('livedot'); if(ld) ld.title=provName+' · 服务在线';
  DATA.levels.forEach(l=>LV[l.id]=l);
  return DATA;
}
function catCards(onPick){
  return Object.entries(DATA.chapters).map(([k,v])=>{
    const inMod=DATA.levels.filter(l=>l.chapter===+k);
    const done=inMod.filter(l=>DATA.solved.includes(l.id)).length;
    return `<div class="catcard" onclick="${onPick}(${k})">
      <div class="catinfo"><b>${v}</b><p>${DATA.chapter_desc[k]||''}</p>
      <span class="catstat">${inMod.length} 个小类 · 已通关 ${done}/${inMod.length}</span></div>
      <div class="catgo">→</div></div>`;
  }).join('');
}
const KICON = {'为什么会产生':'🧬','漏洞原理':'⚙️','企业真实场景':'🏢','修复方案':'🛡️'};
function kBody(lv){
  const k=KNOW[lv.id]||{};
  return ['为什么会产生','漏洞原理','企业真实场景','修复方案'].map(f=>
    k[f]?`<div class="ksec"><h5>${KICON[f]} ${f}</h5><p>${esc(k[f])}</p></div>`:'').join('');
}
function renderKB(){
  if(!renderKB._init){
    renderKB._init=true;
    document.querySelectorAll('#kbmode button').forEach(bt=>bt.onclick=()=>{
      kbView=bt.dataset.v;
      document.querySelectorAll('#kbmode button').forEach(x=>x.classList.toggle('on',x===bt));
      renderKB();
    });
    document.getElementById('kbq').oninput=()=>renderKB();
  }
  const box=document.getElementById('kblistitems');
  const q=(document.getElementById('kbq').value||'').trim().toLowerCase();
  const match=l=>{
    if(!q) return true;
    const k=KNOW[l.id]||{};
    return (l.id+' '+l.title+' '+l.domain+' '+(k['为什么会产生']||'')+(k['漏洞原理']||'')+
            (k['企业真实场景']||'')+(k['修复方案']||'')).toLowerCase().includes(q);
  };
  const hits=DATA.levels.filter(match);
  document.getElementById('kbsub').textContent='知识库 · '+hits.length+'/'+DATA.levels.length+' 篇'+(q?'（搜索中）':'');
  const card=l=>`<div class="kcard${kbDocId===l.id?' sel':''}" id="kb-${l.id}" onclick="kbOpen('${l.id}')">
    <div class="r1"><span class="id">${l.id}</span><span class="ttl">${esc(l.title)}</span>
      ${DATA.solved.includes(l.id)?'<span class="done">✓</span>':''}</div>
    <div class="r2"><span class="tag dom">${esc(l.domain)}</span><span class="tag stars">${'★'.repeat(l.stars)}</span></div>
    <div class="kshort">${esc((KBT[l.id]||'').slice(0,46))}${(KBT[l.id]||'').length>46?'…':''}</div>
  </div>`;
  if(kbView==='dom'){
    const doms={};
    hits.forEach(l=>{ (doms[l.domain]=doms[l.domain]||[]).push(l); });
    box.innerHTML=Object.keys(doms).sort().map(d=>
      `<div class="chapbox"><b>领域 · ${esc(d)}</b><p>${doms[d].length} 篇</p></div>`
      + doms[d].map(card).join('')).join('');
  }else if(q){
    box.innerHTML=hits.map(card).join('')||'<div class="empty">没有匹配的知识</div>';
  }else if(!kbChapter){
    box.innerHTML=catCards('kbPick');
  }else{
    const inMod=DATA.levels.filter(l=>l.chapter===kbChapter);
    box.innerHTML=`<div class="chapbox"><b>${DATA.chapters[kbChapter]}</b><p>${DATA.chapter_desc[kbChapter]||''}</p></div>`
      + `<button class="btn" onclick="kbChapter=0;renderKB()">← 返回大类</button>`
      + inMod.map(card).join('');
  }
  if(!kbDocId&&hits.length) kbOpen(hits[0].id);
}
function kbPick(k){ kbChapter=k; renderKB(); }
function kbOpen(id){
  if(!id||!LV[id]) return;
  kbDocId=id;
  const lv=LV[id], k=KNOW[id]||{};
  const t=KBT[id]||'';
  const secs=['为什么会产生','漏洞原理','企业真实场景','修复方案'].map(f=>
    k[f]?`<div class="ksec"><h5>${KICON[f]} ${f}</h5><p>${esc(k[f])}</p></div>`:'').join('');
  document.getElementById('kbdoc').innerHTML=`
    <div class="kd-h"><span class="kid">${lv.id}</span><b>${esc(lv.title)}</b>
      <span class="tag dom">${esc(lv.domain)}</span><span class="tag stars">${'★'.repeat(lv.stars)}</span>
      ${DATA.solved.includes(lv.id)?'<span class="done">✓ 已通关</span>':''}</div>
    <div class="kd-brief">${esc(lv.brief)}</div>
    ${t?`<div class="ktldr">💡 一句话结论：${esc(t)}</div>`:''}
    ${secs}`;
  document.querySelectorAll('#kblistitems .kcard').forEach(el=>
    el.classList.toggle('sel', el.id==='kb-'+id));
  const cm=document.getElementById('kbans');
  if(cm) cm.innerHTML='<div class="cp-tip">已打开 <b>'+id+'</b> 文档——有疑问直接问，AI 基于本篇内容回答（可追问）。</div>';
  document.getElementById('kb').classList.add('kbcoachon');
}
function renderCTF(){
  const box=document.getElementById('ctflist');
  document.getElementById('ctfsub').textContent = ctfChapter
    ? '小类关卡 · 点「进入靶场」开打（知识在「LLM 知识库」，靶场内可点「阅读文档」）'
    : '四大类 → 小类关卡 → 进入靶场';
  if(!ctfChapter){ box.innerHTML=catCards('ctfPick'); return; }
  const inMod=DATA.levels.filter(l=>l.chapter===ctfChapter);
  box.innerHTML=`<div class="chapbox"><b>${DATA.chapters[ctfChapter]}</b><p>${DATA.chapter_desc[ctfChapter]||''}</p></div>`
    + `<button class="btn" onclick="ctfChapter=0;renderCTF()">← 返回大类</button>`
    + inMod.map(l=>ctfCard(l)).join('');
}
function ctfPick(k){ ctfChapter=k; renderCTF(); }
function ctfCard(lv){
  const solved=DATA.solved.includes(lv.id);
  return `<div class="kcard" style="cursor:default">
    <div class="r1"><span class="id">${lv.id}</span><span class="ttl">${esc(lv.title)}</span>
      ${solved?'<span class="done">✓ 已通关</span>':''}
      <span class="tag dom">${esc(lv.domain)}</span><span class="tag stars">${'★'.repeat(lv.stars)}</span>
      <span class="tag">${lv.win_channel==='exfil'?'外带':lv.win_channel==='submit'?'提交':lv.win_channel==='trace'?'触发':'输出'}</span>
      ${lv.allow_poison?'<span class="tag po">可投毒</span>':''}</div>
    <div class="brief">${esc(lv.brief)}</div>
    <div class="acts"><button class="btn pri" onclick="enterPlay('${lv.id}')">🎯 进入靶场</button></div>
  </div>`;
}
let kbDocId=null;
function openKDoc(id){
  if(!id||!LV[id]) return;
  const lv=LV[id], k=KNOW[id]||{};
  const t=KBT[id]||'';
  const secs=['为什么会产生','漏洞原理','企业真实场景','修复方案'].map(f=>
    k[f]?`<div class="ksec"><h5>${KICON[f]} ${f}</h5><p>${esc(k[f])}</p></div>`:'').join('');
  const tldr=t?`<div class="ktldr">💡 一句话结论：${esc(t)}</div>`:'';
  document.getElementById('kpanel').innerHTML=`
    <div class="r1"><h3>${lv.id} · ${esc(lv.title)} <span class="tag dom">${esc(lv.domain)}</span></h3>
      <button class="x" onclick="closeKDoc()">✕</button></div>
    <div style="font-size:13px;color:var(--dim);margin:8px 0 4px">${esc(lv.brief)}</div>${tldr}${secs}
    <div style="margin-top:12px;padding-top:10px;border-top:1px dashed var(--line);font-size:12px;color:var(--faint)">
      💡 想深入阅读与 AI 答疑？去「📚 LLM 知识点」打开这篇文档，右侧有 AI 讲解员随时答疑。</div>`;
  document.getElementById('kmodal').classList.add('on');
}
function closeKDoc(){ document.getElementById('kmodal').classList.remove('on'); }
async function kbAsk(q){
  const inp=document.getElementById('kbqin');
  const text=(typeof q==='string'&&q)?q:inp.value.trim();
  if(!text) return;
  if(typeof q!=='string') inp.value='';
  const box=document.getElementById('kbans');
  box.insertAdjacentHTML('beforeend',`<div class="cp-u">${esc(text)}</div>`);
  const isCloud=document.getElementById('chipengine')&&document.getElementById('chipengine').textContent!=='LOCAL LLM';
  box.insertAdjacentHTML('beforeend','<div class="cp-a" id="kbwait">🤔 '+(isCloud?'云端模型推理中…（10-60秒）':'本地模型推理中…（几秒到几十秒）')+'</div>');
  box.scrollTop=box.scrollHeight;
  try{
    const d=await api('/api/kb_ask',{sid,level:kbDocId,question:text});
    const w=document.getElementById('kbwait'); if(w) w.remove();
    box.insertAdjacentHTML('beforeend',`<div class="cp-a">${esc(String(d.reply||d.error||'暂时无法解答'))}</div>`);
  }catch(e){
    const w=document.getElementById('kbwait'); if(w) w.remove();
    box.insertAdjacentHTML('beforeend','<div class="cp-a">连接失败，请稍后再试。</div>');
  }
  box.scrollTop=box.scrollHeight;
}
document.addEventListener('keydown',e=>{
  if(e.key==='Enter'&&document.activeElement===document.getElementById('kbqin')) kbAsk();
});
/* 划词问 AI：在文档区选中文字 → 浮出「问这段」 */
(function(){
  const doc=document.getElementById('kbdoc');
  const btn=document.getElementById('selask');
  if(!doc||!btn) return;
  doc.addEventListener('mouseup',()=>{
    setTimeout(()=>{
      const sel=window.getSelection();
      const txt=sel?String(sel).trim():'';
      if(!txt||txt.length<2||!kbDocId){ btn.style.display='none'; return; }
      const rect=sel.getRangeAt(0).getBoundingClientRect();
      btn.dataset.text=txt.slice(0,300);
      btn.style.display='block';
      btn.style.left=Math.max(8,Math.min(window.innerWidth-150,rect.left))+'px';
      btn.style.top=(rect.bottom+window.scrollY+8)+'px';
    },10);
  });
  doc.addEventListener('mousedown',e=>{ if(e.target.id!=='selask') btn.style.display='none'; });
})();
function selAsk(ev){
  ev.stopPropagation();
  const btn=document.getElementById('selask');
  const t=btn.dataset.text||'';
  btn.style.display='none';
  if(!t) return;
  document.getElementById('kb').classList.add('kbcoachon');
  kbAsk('文档中这段话我看不懂，请结合上下文用通俗的语言详细解释：「'+t+'」');
}
/* ================= 🎮 攻防战 ================= */
document.addEventListener('keydown',e=>{ if(e.key==='Escape') closeKDoc(); });

function addRow(html){ const d=document.createElement('div'); d.innerHTML=html;
  const c=document.getElementById('col'); c.appendChild(d.firstElementChild);
  const ch=document.getElementById('chat'); ch.scrollTop=ch.scrollHeight; }
function userMsg(t){ addRow(`<div class="row user"><div class="body"><div class="txt">${esc(t)}</div></div></div>`); }
function aiMsg(t){ addRow(`<div class="row ai"><div class="avatar">🤖</div><div class="body"><div class="who">小冰 · 助手</div><div class="txt">${esc(t)}</div></div></div>`); }
function fillMsg(t){ const ta=document.getElementById('msg'); ta.value=t; ta.focus(); }
function pill(t,warn){ addRow(`<div class="pill${warn?' warn':''}">${esc(t)}</div>`); }
function thinkOn(){ addRow(`<div class="think" id="thinkrow"><i></i><i></i><i></i></div>`); }
function thinkOff(){ const e=document.getElementById('thinkrow'); if(e) e.remove(); }

function renderSide(){
  const side=document.getElementById('side'); side.innerHTML='';
  const h=document.createElement('div'); h.className='chap'; h.textContent=DATA.chapters[playChapter];
  h.title='点击返回该大类关卡列表';
  h.onclick=()=>go('ctf');
  side.appendChild(h);
  DATA.levels.filter(l=>l.chapter===playChapter).forEach(lv=>{
    const b=document.createElement('button'); b.className='lv'; b.id='lv-'+lv.id;
    b.innerHTML=`<div class="r1"><span class="id">${lv.id}</span><span class="ttl">${esc(lv.title)}</span>
      ${DATA.solved.includes(lv.id)?'<span class="done">✓</span>':''}</div>
      <div class="r2"><span class="tag dom">${esc(lv.domain)}</span>
      <span class="tag stars">${'★'.repeat(lv.stars)}</span></div>`;
    b.onclick=()=>selectLevel(lv.id); side.appendChild(b);
  });
}
async function enterPlay(id){ playChapter=LV[id].chapter; ctfChapter=playChapter; renderSide(); go('play'); await selectLevel(id); }
async function selectLevel(id){
  if(sending) return;
  cur=id;
  document.querySelectorAll('.lv').forEach(e=>e.classList.toggle('on',e.id==='lv-'+id));
  const lv=LV[id];
  document.querySelector('#lvhead .ttl').textContent=`${id} · ${lv.title}`;
  document.getElementById('lvsub').textContent=`${lv.domain} · ${'★'.repeat(lv.stars)}`;
  await api('/api/start',{sid,level:id});
  document.getElementById('col').innerHTML='';
  const cm=document.getElementById('coachmsgs');
  if(cm) cm.innerHTML='<div class="cp-tip">已切换到 <b>'+id+'</b>，教官上下文已重置。问「这关突破口在哪」开始；卡住就点「我就是不会」，教官会带你到通关。</div>';
  ['tool','exfil','san'].forEach(k=>{document.getElementById('ev-'+k).innerHTML='<div class="empty">暂无</div>';document.getElementById('c-'+k).textContent='0';});
  document.getElementById('hints-card').style.display='none'; document.getElementById('hints').innerHTML='';
  document.getElementById('poisonbox').style.display='none';
  document.getElementById('play').classList.add('coachon');  // 教官侧窗默认打开
  aiMsg(`已进入 ${id}【${lv.title}】 · 领域：${lv.domain}\n${lv.brief}\n\n🎯 通关目标：让小冰交出 FLAG（形如 PI{...} 的机密旗子），或诱它把旗子发出去。\n卡关就点右上「提示 1/2/3」，原理随时点「📖 阅读文档」。${lv.allow_poison?'\n（本关可投放毒文档）':''}`);
  const ta=document.getElementById('msg'); ta.disabled=false; ta.placeholder='在这里输入攻击消息，回车发送…';
  document.getElementById('sendbtn').disabled=false; ta.focus();
}
async function send(){
  const ta=document.getElementById('msg');
  if(!cur||sending) return;
  const t=ta.value.trim(); if(!t) return;
  ta.value=''; sending=true;
  const sb=document.getElementById('sendbtn'); sb.disabled=true;
  userMsg(t); thinkOn();
  if(document.getElementById('chipengine')&&document.getElementById('chipengine').textContent!=='LOCAL LLM'){const w=document.getElementById('thinkrow'); if(w) w.title='云端模型推理中，可能需要 10-60 秒';}
  try{
    const d=await api('/api/turn',{sid,level:cur,message:t});
    thinkOff();
    if(d.error) pill('错误：'+d.error,true);
    else if(d.intercepted) pill(d.intercepted,true);
    else{
      (d.sanitize_notes||[]).forEach(n=>obs('san','[消毒] '+n));
      (d.trace||[]).forEach(x=>obs('tool',`[工具] ${x.tool} ${JSON.stringify(x.args)}`));
      (d.exfil||[]).forEach(e=>obs('exfil','[外带] '+JSON.stringify(e)));
      aiMsg(d.answer||'（空响应）');
      if(d.win){
        const CH={answer:'回答内容',exfil:'外带捕获',judge:'语义裁判',trace:'工具触发',submit:'手动提交'};
        addRow(`<div class="wincard"><div class="t1">🚩 通关成功</div>
          <div class="flag">${esc(d.win.match)}</div>
          <div class="t2">判定通道：${CH[d.win.where]||d.win.where} · 关卡已标记完成 · 点「📖 阅读文档」看修复方案</div></div>`);
        toast(pick(QUOTES_OK),'ok');
        DATA.solved.includes(cur)||DATA.solved.push(cur);
        await loadAll(); renderSide();
        document.querySelectorAll('.lv').forEach(e=>e.classList.toggle('on',e.id==='lv-'+cur));
      }
    }
  }catch(e){ thinkOff(); }
  sending=false; sb.disabled=false;
}
async function hint(n){
  if(!cur) return;
  const d=await api('/api/hint',{sid,level:cur,n});
  document.getElementById('hints-card').style.display='block';
  const el=document.createElement('div'); el.className='hintline'; el.textContent='💡 '+d.hint;
  document.getElementById('hints').appendChild(el);
}
function togglePoison(){ const b=document.getElementById('poisonbox');
  b.style.display=b.style.display==='block'?'none':'block'; }
async function writeDoc(){
  if(!cur) return;
  const fn=document.getElementById('pfname').value.trim()||'POISON_note.txt';
  const d=await api('/api/write',{sid,level:cur,filename:fn,content:document.getElementById('pcontent').value});
  pill(d.ok?`已投放 ${d.filename} 到知识库`:'投放失败：'+d.error);
}
async function restart(){
  if(!cur) return;
  await api('/api/restart',{sid,level:cur});
  pill('已重开本关：对话历史与毒文档已清空。');
}
async function submitFlag(){
  if(!cur) return;
  const f=document.getElementById('flagin').value.trim(); if(!f) return;
  const d=await api('/api/flag',{sid,level:cur,flag:f});
  if(d.ok){
    addRow(`<div class="wincard"><div class="t1">🚩 通关成功</div>
      <div class="flag">${esc(d.flag)}</div><div class="t2">判定通道：手动提交 · 关卡已标记完成</div></div>`);
    toast(pick(QUOTES_OK),'ok');
    DATA.solved.includes(cur)||DATA.solved.push(cur);
    await loadAll(); renderSide();
  } else {
    document.querySelectorAll('.pill').forEach(e=>{ if(e.textContent.includes('FLAG 不正确')) e.remove(); });
    pill('FLAG 不正确（已做格式容错：空格/标点/大小写不影响）。',true);
    toast(pick(QUOTES_NO),'no');
  }
}
function obs(kind,text){
  const box=document.getElementById('ev-'+kind);
  if(box.firstElementChild&&box.firstElementChild.className==='empty') box.innerHTML='';
  const d=document.createElement('div'); d.className='ev '+kind; d.textContent=text; box.appendChild(d);
  const c=document.getElementById('c-'+kind); c.textContent=+c.textContent+1;
}
document.getElementById('msg').addEventListener('keydown', e=>{
  if(e.key==='Enter'&&!e.shiftKey&&!e.isComposing&&e.keyCode!==229){ e.preventDefault(); send(); }
});
/* ================= 防御实验室 ================= */
let DMETA=null, DSEL={}, DRUNNING=false, DREPORTS=[], DMODE='suite';
const sleep=ms=>new Promise(z=>setTimeout(z,ms));
const DICONS={input_blacklist:'🚫',llm_guard:'🤖',doc_sanitizer:'🧹',output_filter:'🛑',
  tool_audit:'🔍',email_whitelist:'📮',url_whitelist:'🌐',system_hardening:'🛡️'};
const TLI={plant:'📄',input:'📨',gate:'🚧',model:'🧠',tool:'🔧',sanitize:'🧹',exfil:'📡'};
function tlNarr(e){
  if(e.kind==='plant') return '攻击者已经把毒文档埋进知识库了——对话还没开始，载荷先就位。';
  if(e.kind==='input') return '这条消息要先过你开的防线（黑名单/守卫），才轮到 AI 看到。';
  if(e.kind==='gate'){
    if(e.verdict==='block') return `✅ ${e.layer||'防线'}把它拦下来了——本次攻击到此为止。`;
    return `⚠ ${e.layer||'防线'}没拦住它（没命中规则）——载荷继续往里走。`;
  }
  if(e.kind==='model') return '这是 AI 的原始输出。注意：它嘴上在汇报，手里可能正在调用工具。';
  if(e.kind==='tool') return 'AI 正在动用工具。关键点：工具参数（邮件正文/URL）通常不经过「输出过滤」。';
  if(e.kind==='sanitize') return '🧹 消毒器起作用了：命中词表的行被删。但中性措辞的载荷一个词都不会命中——这就是它的盲区。';
  if(e.kind==='exfil') return '🚨 机密数据流出去了！这就是「渗透」的铁证——你的防线没看住出口。';
  return '';
}

async function renderDefender(){
  if(!DMETA){
    DMETA=await api('/api/defender/meta');

    document.getElementById('defswitches').innerHTML=DMETA.defense_meta.map(m=>`
      <div class="dsw" id="sw-${m.key}" onclick="dToggle('${m.key}')" title="${esc(m.desc)}">
        <div class="ic">${DICONS[m.key]||'⚙'}</div>
        <div class="bd"><b>${m.name}</b><p>${m.desc}</p></div>
        <div class="tg"></div>
      </div>
      ${m.key==='input_blacklist'?`<div class="wordsbox" id="dblwrap" style="display:none">
        <label>黑名单词表（逗号/换行分隔，留空=开关无效）</label>
        <textarea id="dbl" placeholder="如：忽略，密钥，扮演，系统提示"></textarea></div>`:''}
      ${m.key==='doc_sanitizer'?`<div class="wordsbox" id="dsanwrap" style="display:none">
        <label>消毒词表（文档/网页中命中词所在的整行被删除）</label>
        <textarea id="dsan" placeholder="如：密钥，指令，请输出，外发"></textarea></div>`:''}
    `).join('');
    DMETA.attacks.forEach(a=>DSEL[a.id]=(a.id==='D07'));
    document.querySelectorAll('#dsegm button').forEach(b=>b.onclick=()=>dMode(b.dataset.m));
    buildAbCfg();
    DDPRE='literal'; applyPreset('literal');
    renderDrops();
    dMode('micro');
    try{ if(!localStorage.getItem('agentsec-donb')) setTimeout(dShow,350); }catch(e){}
  }
  dSyncUI();
}
function swOn(k){ return document.getElementById('sw-'+k).classList.contains('on'); }
function dWordsVis(){
  document.getElementById('dblwrap').style.display=swOn('input_blacklist')?'':'none';
  document.getElementById('dsanwrap').style.display=swOn('doc_sanitizer')?'':'none';
}
function dToggle(k){
  document.getElementById('sw-'+k).classList.toggle('on');
  const meta=DMETA.defense_meta.find(m=>m.key===k);
  if(meta&&meta.kind==='words'&&swOn(k)){
    const box=document.getElementById(k==='input_blacklist'?'dbl':'dsan');
    if(!box.value.trim()&&meta.default) box.value=meta.default.join('，');
  }
  dWordsVis(); dSyncUI();
}
function dAtk(id){
  Object.keys(DSEL).forEach(k=>DSEL[k]=false);
  DSEL[id]=true;
  syncAtkSel(); dSyncUI();
}
function syncAtkSel(){
  document.querySelectorAll('#defatks .datk').forEach(el=>{
    el.classList.toggle('sel',!!DSEL[el.id.slice(4)]); });
}
function dCfg(){
  const words=id=>document.getElementById(id).value.split(/[,，\n]/).map(s=>s.trim()).filter(Boolean);
  return {
    input_blacklist: swOn('input_blacklist')? words('dbl') : [],
    doc_sanitizer:   swOn('doc_sanitizer')? words('dsan') : [],
    llm_guard: swOn('llm_guard'), output_filter: swOn('output_filter'),
    tool_audit: swOn('tool_audit'), email_whitelist: swOn('email_whitelist'),
    url_whitelist: swOn('url_whitelist'), system_hardening: swOn('system_hardening'),
  };
}
function dSyncUI(){
  if(!DMETA) return;
  const on=document.getElementById('defoncount');
  if(on) on.textContent=DMETA.defense_meta.filter(m=>swOn(m.key)).length+'/8';
}
function applyPreset(pid){
  const p=DMETA.presets.find(x=>x.id===pid); if(!p) return;
  document.querySelectorAll('.pchip').forEach(e=>e.classList.remove('on'));
  const chip=document.getElementById('pc-'+pid); if(chip) chip.classList.add('on');
  const c=p.cfg;
  DMETA.defense_meta.forEach(m=>{
    const on = m.key==='input_blacklist' ? !!(c.input_blacklist&&c.input_blacklist.length)
             : m.key==='doc_sanitizer' ? !!(c.doc_sanitizer&&c.doc_sanitizer.length) : !!c[m.key];
    document.getElementById('sw-'+m.key).classList.toggle('on',on);
  });
  document.getElementById('dbl').value=(c.input_blacklist||[]).join('，');
  document.getElementById('dsan').value=(c.doc_sanitizer||[]).join('，');
  dWordsVis(); dSyncUI();
}
function dMode(m){
  DMODE=m;
  document.querySelectorAll('#dsegm button').forEach(btn=>btn.classList.toggle('on',btn.dataset.m===m));
  document.getElementById('scard').style.display = m==='ab'?'none':'';
  document.getElementById('abruncard').style.display = m==='ab'?'':'none';
  document.getElementById('abcfg').style.display = m==='ab'?'':'none';
  document.getElementById('microbox').style.display = m==='micro'?'flex':'none';
  document.getElementById('abgrid').style.display = m==='ab'?'':'none';
  document.getElementById('abcmp').style.display='none';
  document.getElementById('defsub').textContent =
    m==='micro'?'攻击方发起 ▶ 防守方工程全程直播：门禁·消毒·模型·工具调用实时可见'
    :'同一发攻击 × 两套防线同时跑：哪道防线补上哪个洞';
  const ids=DMETA.attacks.filter(a=>DSEL[a.id]).map(a=>a.id);
  const keep=ids.length===1?ids[0]:'D07';
  DMETA.attacks.forEach(a=>DSEL[a.id]=(a.id===keep));
  if(m==='micro'){
    document.getElementById('flowA').innerHTML='<div class="empty"><b>🔴 攻击方待命</b><br>在上方下拉选择攻击手法（每项附说明）<br>点「⚔ 开始攻击」发起<br>第一次玩？点上方「🎬 一键看经典战例」</div>';
    document.getElementById('flowD').innerHTML='<div class="empty"><b>🛡 防守方工程待命</b><br>上方下拉选择防守策略（侧栏可微调组件）<br>交战开始后实时显示：门禁判定 → 消毒 → 模型每轮输出 → 工具调用 → 外带监测</div>';
    document.getElementById('flowverdict').innerHTML='';
  }
  if(m==='ab'){
    renderAbAtks();
    document.getElementById('abtl-A').innerHTML='<div class="empty">A 侧时间线<br><b>等「⚖ 对比开跑」</b></div>';
    document.getElementById('abtl-B').innerHTML='<div class="empty">B 侧时间线<br><b>建议：B 在 A 基础上多勾「工具参数审计」</b></div>';
  }
  syncAtkSel(); dSyncUI();
}
async function demo(){
  dMode('micro'); DDPRE='literal'; applyPreset('literal');
  Object.keys(DSEL).forEach(k=>DSEL[k]=(k==='D07'));
  renderDrops(); dSyncUI();
  microRun();
}
/* ---- 显微镜 / A·B ---- */
function oneAtk(){
  const ids=DMETA.attacks.filter(a=>DSEL[a.id]).map(a=>a.id);
  if(ids.length!==1){ errbar('这个模式一次只跑一发攻击，请只选一项'); return null; }
  return ids[0];
}
let DDPRE='literal';
function ddToggle(id){
  document.querySelectorAll('.dd').forEach(d=>{ if(d.id!==id) d.classList.remove('open'); });
  document.getElementById(id).classList.toggle('open');
}
document.addEventListener('click',e=>{ if(!e.target.closest('.dd'))
  document.querySelectorAll('.dd').forEach(d=>d.classList.remove('open')); });
function renderDrops(){
  const pm=document.getElementById('predd-m'); if(!pm) return;
  pm.innerHTML=DMETA.presets.map(p=>`
    <div class="dditem ${p.id===DDPRE?'on':''}" onclick="event.stopPropagation();pickPre('${p.id}')">
      <b>${esc(p.name)}${p.id==='literal'?' <span style="color:var(--acc)">★推荐</span>':''}</b>
      <span>${esc(p.desc)}</span></div>`).join('');
  const p=DMETA.presets.find(x=>x.id===DDPRE);
  document.getElementById('predd-h').innerHTML=
    `${esc(p.name)} <i>▾</i><em>${esc(p.desc)}</em>`;
  const cur=DMETA.attacks.find(a=>DSEL[a.id]);
  ['atkdd','atkdd2'].forEach(dd=>{
    const m=document.getElementById(dd+'-m'); if(!m) return;
    m.innerHTML=DMETA.attacks.map(a=>`
      <div class="dditem ${DSEL[a.id]?'on':''}" onclick="event.stopPropagation();pickAtk('${a.id}')">
        <b><span class="kk">${a.id}</span>${esc(a.name)}
          <span style="color:#e8a33d;font-size:10px">${'★'.repeat(a.stars)}</span>
          <span style="color:var(--faint);font-size:10px;font-weight:400">${a.kind==='direct'?'直接注入':'间接注入'}</span></b>
        <span>${esc(a.note)}</span></div>`).join('');
    const h=document.getElementById(dd+'-h'); if(h) h.innerHTML = cur
      ? `${cur.id} ${esc(cur.name)} <i>▾</i><em>${esc(cur.note)}</em>` : '选择攻击 <i>▾</i>';
  });
}
function pickPre(pid){
  DDPRE=pid; applyPreset(pid); renderDrops();
  document.getElementById('predd').classList.remove('open');
  dSyncUI();
}
function pickAtk(id){
  Object.keys(DSEL).forEach(k=>DSEL[k]=(k===id));
  renderDrops(); renderAbAtks(); dSyncUI();
  ['atkdd','atkdd2'].forEach(x=>{const e=document.getElementById(x); if(e) e.classList.remove('open');});
}
function renderAbAtks(){
  const box=document.getElementById('abatks'); if(!box||!DMETA) return;
  box.innerHTML=DMETA.attacks.map(a=>`
    <div class="datk ${DSEL[a.id]?'sel':''}" id="abatk-${a.id}"
         onclick="pickAtk('${a.id}')" title="${esc(a.note)}">
      <div class="kb">${a.kind==='direct'?'直接':'间接'}</div>
      <span class="kid">${a.id}</span><span class="nm">${esc(a.name)}</span>
      <div class="mt">${'★'.repeat(a.stars)}${'☆'.repeat(5-a.stars)}</div>
    </div>`).join('');
}
function dName(k){
  const m=DMETA.defense_meta.find(x=>x.key===k); return m?m.name:k;
}
function dFix(k){
  if(DMODE==='ab'){ toast('A/B 模式：请在对应侧的组件里勾选「'+dName(k)+'」','no'); return; }
  const sw=document.getElementById('sw-'+k);
  if(sw && !sw.classList.contains('on')) dToggle(k);
  toast('已开启「'+dName(k)+'」——重新攻击验证堵漏效果','ok');
  document.getElementById('defleft').scrollIntoView({behavior:'smooth'});
}
function dCfgSummary(){
  const c=dCfg(); const on=Object.entries(c).filter(([k,v])=>
    Array.isArray(v)?v.length>0:!!v).map(([k])=>k);
  return on.length?on.join(' + '):'裸奔（无防线）';
}
function tlRender(box,e){
  if(e.kind==='report'){
    const ic=e.result==='blocked'?'🟢 拦截':e.result==='leak'?'🔴 渗透':e.result==='held'?'⚪ 自拒':'❓';
    box.insertAdjacentHTML('beforeend',
      `<div class="tl-e report"><div class="vbanner ${e.result}">${ic} ${esc(e.detail||e.result)}</div></div>`);
    box.scrollTop=box.scrollHeight; return;
  }
  if(e.kind==='error'){
    box.insertAdjacentHTML('beforeend',`<div class="vbanner error">⚠ ${esc(e.detail||'任务失败')}</div>`);
    return;
  }
  let body='';
  if(e.data!==undefined&&e.data!==null){
    const txt=typeof e.data==='string'?e.data:JSON.stringify(e.data,null,1);
    body=`<pre class="tldata">${esc(txt.length>1000?txt.slice(0,1000)+'…':txt)}</pre>`;
  }
  const badge=e.verdict?`<span class="tlv ${e.verdict}">${e.verdict==='block'?'拦截':'放行'}</span>`:'';
  const narr=tlNarr(e);
  const div=document.createElement('div');
  div.className='tl-e '+e.kind+(e.verdict?' v'+e.verdict:'');
  div.innerHTML=`<div class="tlh"><span>${TLI[e.kind]||'·'}</span><b>${esc(e.title||e.kind)}</b>${badge}<span class="tts">${new Date().toLocaleTimeString('zh-CN',{hour12:false})}</span></div>`
    +(e.detail?`<div class="tld">${esc(e.detail)}</div>`:'')+body
    +(narr?`<div class="tnarr">${narr}</div>`:'');
  box.appendChild(div); box.scrollTop=box.scrollHeight;
}
async function pollJob(job,emit){
  let since=0;
  while(true){
    let r;
    try{ r=await api('/api/defender/micro_poll',{job,since}); }
    catch(e){ await sleep(1200); continue; }
    if(!r){ await sleep(1200); continue; }
    if(r.error && !(r.entries||[]).length && !r.report){
      emit({kind:'error',detail:r.error}); return null; }
    (r.entries||[]).forEach(e=>{ since=Math.max(since,e.i+1); emit(e); });
    if(r.done) return r.report;
    await sleep(700);
  }
}
async function microRun(){
  const id=oneAtk(); if(!id) return;
  const atk=DMETA.attacks.find(a=>a.id===id);
  const boxA=document.getElementById('flowA'), boxD=document.getElementById('flowD');
  boxA.innerHTML=''; boxD.innerHTML='';
  document.getElementById('flowverdict').innerHTML='';
  boxA.insertAdjacentHTML('beforeend',
    `<div class="tlh" style="color:#e88aa0">⚔ ${id} ${esc(atk?atk.name:'')} 发起 · ${atk&&atk.kind==='direct'?'直接注入':'间接注入'}</div>`);
  boxD.insertAdjacentHTML('beforeend',
    `<div class="tlh" style="color:#8fb9e8">🛡 防守方工程启动 · 防线【${esc(dCfgSummary())}】迎战，逐层实时上报…</div>`);
  document.getElementById('defprog').textContent='交战中…模型推理可能需要数十秒';
  setDir('');
  const dg=document.querySelector('.dguide'); if(dg) dg.style.display='none';
  const ml=document.getElementById('microlive'); if(ml) ml.style.display='';
  let r;
  try{ r=await api('/api/defender/micro',{sid,cfg:dCfg(),attack:id,tag:'M'}); }
  catch(e){ errbar('任务启动失败'); return; }
  const rep=await pollJob(r.job, flowEmit);
  const ml2=document.getElementById('microlive'); if(ml2) ml2.style.display='none';
  document.getElementById('defprog').textContent='攻防结束。切 A/B 对比：同一发攻击，B 侧加一道「工具参数审计」试试。';
  toast(rep&&rep.result==='leak'?'攻防结束：这发渗透了——防线有洞，去 A/B 补防线':'攻防结束：防线守住了', rep&&rep.result==='leak'?'no':'ok');
}
let _dirTimer=null;
function setDir(d,label){
  const f=document.getElementById('fdir'); if(!f) return;
  f.className='fdir '+(d||'');
  const lb=f.querySelector('.lb'); if(lb) lb.textContent=label||'';
  clearTimeout(_dirTimer);
  if(d) _dirTimer=setTimeout(()=>{ f.className='fdir';
    const l2=f.querySelector('.lb'); if(l2) l2.textContent='待命'; },2500);
}
function toggleFlowFull(){
  document.body.classList.toggle('flowfull');
  const b=document.getElementById('ffbtn');
  if(b) b.textContent=document.body.classList.contains('flowfull')?'⤡ 还原':'⛶ 放大';
}
function flowEmit(e){
  if(e.kind==='plant'){ setDir('r','投放'); tlRender(document.getElementById('flowA'),e); return; }
  if(e.kind==='input'){ setDir('r','攻击→'); tlRender(document.getElementById('flowA'),e); return; }
  if(e.kind==='model'){ setDir('l','←防守'); tlRender(document.getElementById('flowD'),e); return; }
  if(e.kind==='report'){ setDir('l','←结论'); flowVerdict(e); return; }
  if(e.kind==='error'){ setDir('l','←结束'); flowVerdict(e); return; }
  setDir('r','处理中');
  tlRender(document.getElementById('flowD'),e);
}
function flowVerdict(e){
  const v=document.getElementById('flowverdict');
  if(e.kind==='error'){
    v.innerHTML='<div class="vbanner error">⚠ '+esc(e.detail||'任务失败')+'</div>'; return;
  }
  const atk=DMETA? DMETA.attacks.find(a=>DSEL[a.id]) : null;
  const fixes=(atk&&atk.fix)||[];
  const fixHtml = e.result==='leak'&&fixes.length
    ? '<div class="dfix">🩹 堵漏建议：'+fixes.map(k=>
        '<button class="chipx" onclick="dFix(\''+k+'\')">'+esc(dName(k))+'</button>').join(' ')
      +'<span style="color:var(--faint)">← 点击开启后重打这一发</span></div>' : '';
  const ic=e.result==='blocked'?'🟢 防守成功 · 拦截':e.result==='leak'?'🔴 防守失守 · 渗透':'⚪ 模型自拒（不计防线得分）';
  const extra=e.blocked_by?(' · 拦截层【'+esc(e.blocked_by)+'】'):(e.channel?(' · 泄漏通道【'+(e.channel==='answer'?'回答':'外带')+'】'):'');
  v.innerHTML='<div class="vbanner '+e.result+'">'+ic+extra+'</div>'
    +'<div style="font-size:13px;color:var(--dim);margin-top:6px">'+esc(e.detail||'')+'</div>'+fixHtml;
}
function buildAbCfg(){
  const root=document.getElementById('abcfg');
  root.innerHTML=`<h4>⚖ 两侧防线配置 <span style="color:var(--faint);font-weight:400;font-size:11px">词表共用左侧侧栏（词表框在「攻防数据流」模式的侧栏里）</span></h4>
    <div class="abrow">
      ${['A','B'].map(s=>`
      <div class="abside ${s==='B'?'b':''}" id="abside-${s}">
        <b>${s==='A'?'🅰 A 侧':'🅱 B 侧'}</b>
        <select class="btn" id="abpre-${s}"></select>
        <div class="minis">${DMETA.defense_meta.map(m=>`
          <label class="mini"><input type="checkbox" data-k="${m.key}"> ${m.name}</label>`).join('')}
        </div>
      </div>`).join('')}
    </div>`;
  ['A','B'].forEach(s=>{
    const sel=document.getElementById('abpre-'+s);
    sel.innerHTML=DMETA.presets.map(p=>`<option value="${p.id}">${p.name}</option>`).join('');
    sel.onchange=()=>abPreset(s,sel.value);
    abPreset(s,'literal');
  });
  root.querySelectorAll('.mini input').forEach(cb=>{
    cb.onchange=()=>cb.closest('.mini').classList.toggle('on',cb.checked);
  });
}
function abPreset(side,pid){
  const p=DMETA.presets.find(x=>x.id===pid); if(!p) return;
  const root=document.getElementById('abside-'+side); const c=p.cfg;
  const sel=document.getElementById('abpre-'+side); if(sel) sel.value=pid;
  root.querySelectorAll('[data-k]').forEach(cb=>{
    const k=cb.dataset.k;
    const v = k==='input_blacklist' ? !!(c.input_blacklist&&c.input_blacklist.length)
            : k==='doc_sanitizer' ? !!(c.doc_sanitizer&&c.doc_sanitizer.length) : !!c[k];
    cb.checked=v; cb.closest('.mini').classList.toggle('on',v);
  });
}
function abCfg(side){
  const root=document.getElementById('abside-'+side);
  const on=k=>root.querySelector(`[data-k="${k}"]`).checked;
  const words=id=>document.getElementById(id).value.split(/[,，\n]/).map(s=>s.trim()).filter(Boolean);
  return {
    input_blacklist: on('input_blacklist')?words('dbl'):[],
    doc_sanitizer: on('doc_sanitizer')?words('dsan'):[],
    llm_guard:on('llm_guard'), output_filter:on('output_filter'),
    tool_audit:on('tool_audit'), email_whitelist:on('email_whitelist'),
    url_whitelist:on('url_whitelist'), system_hardening:on('system_hardening'),
  };
}
async function abRun(){
  const id=oneAtk(); if(!id) return;
  const ca=abCfg('A'), cb2=abCfg('B');
  const boxA=document.getElementById('abtl-A'), boxB=document.getElementById('abtl-B');
  boxA.innerHTML=''; boxB.innerHTML='';
  document.getElementById('abcmp').style.display='none';
  document.getElementById('abprog').textContent='对比中…两侧同时运行（模型推理中）';
  let ja,jb;
  try{
    ja=await api('/api/defender/micro',{sid,cfg:ca,attack:id,tag:'A'});
    jb=await api('/api/defender/micro',{sid,cfg:cb2,attack:id,tag:'B'});
  }catch(e){ errbar('任务启动失败'); return; }
  const [ra,rb]=await Promise.all([pollJob(ja.job,e=>tlRender(boxA,e)),pollJob(jb.job,e=>tlRender(boxB,e))]);
  document.getElementById('abprog').textContent='对比完成。';
  abCompare(id,ra,rb);
  toast('A/B 对比完成：两侧判定已生成','ok');
}
function abCompare(id,ra,rb){
  const cmp=document.getElementById('abcmp'); cmp.style.display='';
  const v=r=>!r?'—':r.result==='blocked'?`拦截（${r.blocked_by||''}）`
    :r.result==='leak'?`渗透（${r.channel==='answer'?'回答':'外带'}通道）`:'自拒';
  const cls=r=>!r?'dim':r.result==='blocked'?'ok':r.result==='leak'?'bad':'dim';
  const la=(ra&&ra.events||[]).map(e=>e.layer), lb=(rb&&rb.events||[]).map(e=>e.layer);
  const onlyB=lb.filter(x=>!la.includes(x)), onlyA=la.filter(x=>!lb.includes(x));
  let note='';
  if(ra&&rb){
    if(ra.result==='leak'&&rb.result==='blocked') note=`✅ B 侧补上的防线把洞堵住了（${rb.blocked_by}）。`;
    else if(ra.result==='blocked'&&rb.result==='leak') note='⚠ B 侧反而漏了——检查 B 关掉了什么。';
    else if(ra.result===rb.result) note='两侧结果相同——这套差异没有改变攻防结局，换一发攻击或换组件再试。';
  }
  cmp.innerHTML=`<div class="card"><h4>⚖ 对比结论 <span class="cnt">${id}</span></h4>
    <div class="sumrow">
      <div class="dstat ${cls(ra)}"><b>${ra?ra.result:'—'}</b>A · ${v(ra)}</div>
      <div class="dstat ${cls(rb)}"><b>${rb?rb.result:'—'}</b>B · ${v(rb)}</div>
    </div>
    <p class="dnote">A 侧事件：${esc(la.join('、')||'无')}<br>B 侧事件：${esc(lb.join('、')||'无')}
    ${onlyB.length?`<br><b style="color:var(--ok)">B 侧多触发：${esc(onlyB.join('、'))}</b>`:''}
    ${onlyA.length?`<br>A 侧多触发：${esc(onlyA.join('、'))}`:''}
    <br><b>${esc(note)}</b></p></div>`;
}

/* ---- 教官问答 ---- */
function coachDock(){ document.getElementById('play').classList.toggle('coachon'); }
async function coachAsk(q){
  const inp=document.getElementById('coachin');
  const text=(typeof q==='string'&&q)?q:inp.value.trim();
  if(!text) return;
  if(typeof q!=='string') inp.value='';
  const box=document.getElementById('coachmsgs');
  box.insertAdjacentHTML('beforeend',`<div class="cp-u">${esc(text)}</div>`);
  box.insertAdjacentHTML('beforeend','<div class="cp-a" id="coachwait">教官思考中…问得越多，提示会自动加深</div>');
  box.scrollTop=box.scrollHeight;
  try{
    const d=await api('/api/coach',{sid,question:text,level:cur});
    const w=document.getElementById('coachwait'); if(w) w.remove();
    const safe=String(d.reply||d.error||'教官暂时离线').replace(/PI\{[^}]{0,120}\}/g,'PI{***}');
    box.insertAdjacentHTML('beforeend',`<div class="cp-a">${esc(safe)}</div>`);
    const lv=document.getElementById('coachlv');
    if(lv&&d.asks) lv.textContent=`第 ${d.asks} 问 · ${d.asks<=2?'方向提示':d.asks<=4?'具体步骤':'接近完整话术'} · 问「我就是不会」可到通关`;
  }catch(e){
    const w=document.getElementById('coachwait'); if(w) w.remove();
    box.insertAdjacentHTML('beforeend','<div class="cp-a">连接失败——请确认 webui.py 正在运行。</div>');
  }
  box.scrollTop=box.scrollHeight;
}
document.addEventListener('keydown',e=>{
  if(e.key==='Enter'&&document.activeElement===document.getElementById('coachin')) coachAsk();
});
/* ---- 防御实验室引导浮层 ---- */
const DSTEPS=[
 ['你是防守工程师','攻击套件 <b>D01-D10</b> 会自动攻击一台 AI 助手「小盾」，它手里有一把机密钥匙。你的任务：<b>配置防线，拦住攻击</b>。'],
 ['两种玩法','<b>⚔ 攻防数据流</b>：单发交战直播——左侧攻击方发起，右侧防守方工程逐层应对（每步配人话解说）；<b>⚖ A/B 对比</b>：两套防线同跑同一发，看哪道防线补上哪个洞。'],
 ['核心课题','关键词类「字面防线」挡不住换说法的语义攻击；邮件白名单只管方向、不管内容。<b>真正兜底的是「工具参数审计」</b>——在 AI 动手外发的瞬间拦住它。'],
 ['现在就看一遍','点击「开始看战例」，自动配好「字面三件套」+ D07，攻防数据流实时直播一次完整的渗透与拦截（约 30 秒）。']
];
let dStep=0;
function dShow(){
  const m=document.getElementById('donboard'); if(!m) return;
  m.classList.add('on'); dStep=0; dRender();
}
function dRender(){
  const s=DSTEPS[dStep];
  document.getElementById('dstepn').textContent=(dStep+1)+'/4';
  document.getElementById('dstep').innerHTML=`<b>${s[0]}</b><p>${s[1]}</p>`;
  document.getElementById('dprev').style.visibility=dStep?'visible':'hidden';
  const nx=document.getElementById('dnext');
  nx.textContent=dStep===3?'🎬 开始看战例':'下一步';
  nx.className=dStep===3?'btn pri':'btn';
}
function dGo(dir){
  if(dStep===3&&dir===1){ dClose(); demo(); return; }
  dStep=Math.max(0,Math.min(3,dStep+dir)); dRender();
}
function dClose(){
  document.getElementById('donboard').classList.remove('on');
  try{localStorage.setItem('agentsec-donb','1');}catch(e){}
}

(async()=>{ await loadAll(); renderSide(); })();
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):  # noqa: A002
        pass

    def _json(self, obj, code=200):
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/":
            data = HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)
        elif path == "/api/levels":
            self._json(level_meta())
        elif path == "/api/providers":
            import providers
            cfg = providers.load_config()
            all_p = dict(providers.PRESETS)
            all_p.update(cfg.get("providers", {}))
            return self._json({"presets": list(all_p.keys()),
                               "current": cfg.get("active", "local"),
                               "providers": all_p})
        elif path == "/api/knowledge":
            self._json({"items": knowledge.KNOWLEDGE,
                        "tldr": getattr(knowledge, "TLDR", {}),
                        "related": getattr(knowledge, "RELATED", {})})
        elif path == "/api/defender/meta":
            self._json(defender.lab_meta())
        else:
            self.send_response(204)
            self.end_headers()

    def _body(self):
        try:
            n = int(self.headers.get("Content-Length", 0))
            return json.loads(self.rfile.read(n).decode("utf-8")) if n else {}
        except Exception:
            return {}

    def do_POST(self):
        path = self.path.split("?")[0]
        b = self._body()
        try:
            if path == "/api/start":
                rt = get_runtime(b.get("sid", ""), b.get("level", "1"))
                lv = rt.level
                return self._json({"ok": True, "title": lv["title"], "brief": lv["brief"],
                                   "allow_poison": lv["allow_poison"]})
            if path == "/api/turn":
                rt = get_runtime(b.get("sid", ""), b.get("level", "1"))
                res = rt.turn(str(b.get("message", "")))
                if res.get("win"):
                    p = engine.load_progress()
                    if rt.level["id"] not in p["solved"]:
                        p["solved"].append(rt.level["id"])
                        engine.save_progress(p)
                return self._json(res)
            if path == "/api/hint":
                rt = get_runtime(b.get("sid", ""), b.get("level", "1"))
                n = max(1, min(3, int(b.get("n", 1))))
                p = engine.load_progress()
                p["hints"][rt.level["id"]] = max(n, p["hints"].get(rt.level["id"], 0))
                engine.save_progress(p)
                return self._json({"hint": rt.level["hints"][n - 1]})
            if path == "/api/write":
                rt = get_runtime(b.get("sid", ""), b.get("level", "1"))
                if not rt.level["allow_poison"]:
                    return self._json({"ok": False, "error": "本关禁止投放文档"})
                fname = "".join(c for c in str(b.get("filename", "POISON_note.txt"))
                                if c not in '\\/:*?"<>|') or "POISON_note.txt"
                (rt.kb_dir / fname).write_text(str(b.get("content", "")), encoding="utf-8")
                return self._json({"ok": True, "filename": fname})
            if path == "/api/restart":
                rt = get_runtime(b.get("sid", ""), b.get("level", "1"))
                fresh = engine.LevelRuntime(rt.level)
                with LOCK:
                    SESSIONS[b.get("sid", "")] = {"level_id": rt.level["id"], "runtime": fresh}
                return self._json({"ok": True})
            if path == "/api/flag":
                rt = get_runtime(b.get("sid", ""), b.get("level", "1"))
                guess = str(b.get("flag", ""))
                if engine.flag_match(rt.level.get("flag", ""), guess):
                    p = engine.load_progress()
                    if rt.level["id"] not in p["solved"]:
                        p["solved"].append(rt.level["id"])
                        engine.save_progress(p)
                    return self._json({"ok": True, "flag": rt.level["flag"]})
                return self._json({"ok": False})
            if path == "/api/kb_ask":
                try:
                    lv = get_level(str(b.get("level", "L01")))
                except Exception:
                    return self._json({"error": "未知关卡"})
                q = str(b.get("question", "")).strip()[:500]
                if not q:
                    return self._json({"error": "问题为空"})
                k = knowledge.KNOWLEDGE.get(lv["id"], {})
                doc = "\n\n".join(f"【{f}】{k.get(f, '')}" for f in
                                   ("为什么会产生", "漏洞原理", "企业真实场景", "修复方案"))
                t = getattr(knowledge, "TLDR", {}).get(lv["id"], "")
                sys_p = (
                    f"你是「agentsec-labs」知识库的 AI 讲解员，当前讲解对象：{lv['id']} {lv['title']}（领域 {lv.get('domain', '')}）。\n"
                    f"一句话结论：{t}\n文档全文：\n{doc}\n\n"
                    "基于以上内容回答玩家提问：准确、通俗、中文；文档没覆盖的部分可以补充通用知识，"
                    "但须注明「文档外补充」。400 字以内，分点清晰。")
                key = (str(b.get("sid", "")) or "web") + ":" + lv["id"]
                with COACH_LOCK:
                    sess = KB_ASK_SESSIONS.setdefault(key, {"hist": []})
                    msgs = ([{"role": "system", "content": sys_p}]
                            + sess["hist"][-10:] + [{"role": "user", "content": q}])
                try:
                    reply = engine.ollama_chat(msgs)
                except Exception as e:
                    return self._json({"error": f"模型不可达：{e}"})
                reply = reply.strip()
                with COACH_LOCK:
                    sess["hist"].append({"role": "user", "content": q})
                    sess["hist"].append({"role": "assistant", "content": reply})
                return self._json({"reply": reply})
            if path == "/api/coach":
                try:
                    lv = get_level(str(b.get("level", "L01")))
                except Exception:
                    return self._json({"error": "未知关卡"})
                q = str(b.get("question", "")).strip()[:500]
                if not q:
                    return self._json({"error": "问题为空"})
                d = lv.get("defenses") or {}
                names = {"input_blacklist": "输入黑名单", "llm_guard": "LLM守卫",
                         "doc_sanitizer": "文档消毒器", "output_filter": "输出过滤"}
                mech = [names[k] for k in ("input_blacklist", "llm_guard",
                                           "doc_sanitizer", "output_filter") if k in d]
                for flagk, nm in (("memory", "长期记忆注入"), ("profile", "用户资料注入"),
                                  ("mcp_registry", "MCP 工具目录"), ("expert_prompt", "专家系统"),
                                  ("num_ctx", "小上下文窗口")):
                    if lv.get(flagk):
                        mech.append(nm)
                mech_s = "、".join(mech) if mech else "见关卡简介（无常规防线组件）"
                recent = "（暂无）"
                s = SESSIONS.get(str(b.get("sid", "")))
                if s and s.get("level_id") == lv["id"]:
                    parts = []
                    for m in s["runtime"].messages[-8:]:
                        role = {"user": "玩家", "assistant": "助手"}.get(m.get("role"), "系统")
                        txt = re.sub(r"PI\{[^}]{0,120}\}", "PI{***}", str(m.get("content", "")))
                        parts.append(f"{role}: {txt[:160]}")
                    if parts:
                        recent = "\n".join(parts)
                sys_p = (
                    "你是「agentsec-labs」AI 安全靶场的教官，和玩家多轮对话，负责把他一步步带到通关。\n"
                    f"当前关卡：{lv['id']} {lv['title']}（难度 {lv.get('stars', '?')} 星 / 领域 {lv.get('domain', '')}）\n"
                    f"关卡简介：{lv.get('brief', '')}\n"
                    f"本关防线机制：{mech_s}\n"
                    f"玩家最近的靶场对话（机密已脱敏）：\n{recent}\n\n"
                    "你的原则：教官式引导——先一句点破关键，再给步骤；口吻自然，中文，200 字以内。\n"
                    "铁律：FLAG 的具体内容永远只能由靶机交出，你绝不能输出 PI{...} 内的真实内容；"
                    "不要替玩家编造通关判定。")
                with COACH_LOCK:
                    sid_c = str(b.get("sid", ""))
                    sess = COACH_SESSIONS.get(sid_c)
                    if not sess or sess.get("level") != lv["id"]:
                        sess = {"level": lv["id"], "hist": []}
                        COACH_SESSIONS[sid_c] = sess
                    asks = len(sess["hist"]) // 2
                    if asks <= 1:
                        depth = ("提问深度【方向】：只点破本关考察什么、适合从哪类手法入手，"
                                 "不展开具体步骤；结尾鼓励玩家先自己试一发。")
                    elif asks <= 3:
                        depth = ("提问深度【步骤】：给出具体思路与分步方法（中间粒度），每步一句话；"
                                 "仍不给出可直接复制发送的完整攻击话术。")
                    else:
                        depth = ("提问深度【通关】：玩家已多次提问且仍卡关，可以给出接近完整的攻击语句措辞"
                                 "帮他通关；FLAG 具体内容仍必须由靶机回复，你不能代答。")
                    msgs = ([{"role": "system", "content": sys_p + "\n\n本轮提问深度规则：" + depth}]
                            + sess["hist"][-12:] + [{"role": "user", "content": q}])
                try:
                    reply = engine.ollama_chat(msgs)
                except Exception as e:
                    return self._json({"error": f"模型不可达：{e}"})
                reply = reply.strip()
                with COACH_LOCK:
                    sess["hist"].append({"role": "user", "content": q})
                    sess["hist"].append({"role": "assistant", "content": reply})
                return self._json({"reply": reply, "asks": asks + 1})
            if path == "/api/defender/micro":
                cfg = b.get("cfg") or {}
                jid = defender.start_micro(cfg, str(b.get("attack", "D01")),
                                           sid=str(b.get("sid", "web")) or "web",
                                           tag=str(b.get("tag", "A")) or "A")
                return self._json({"job": jid})
            if path == "/api/defender/micro_poll":
                res = defender.poll_micro(str(b.get("job", "")), int(b.get("since", 0)))
                if res is None:
                    return self._json({"error": "job not found"}, 404)
                return self._json(res)
            if path == "/api/providers/set":
                import providers
                providers.update_provider(str(b.get("pid", "local")),
                                          url=str(b.get("url", "")),
                                          key=str(b.get("key", "")),
                                          model=str(b.get("model", "")))
                providers.set_active(str(b.get("pid", "local")))
                return self._json({"ok": True})
            if path == "/api/providers/test":
                # 测试连接：只用传入参数测试，不覆写已保存配置
                import providers, urllib.request as _ur, json as _j
                pid = str(b.get("pid", "")) or "local"
                url = str(b.get("url", "")).rstrip("/")
                key = str(b.get("key", ""))
                model = str(b.get("model", "")).strip().lower()
                try:
                    if pid == "local" or not url:
                        # 本地测试
                        cfg2 = providers.load_config()
                        p2 = cfg2["providers"].get("local", {})
                        reply = providers._chat_ollama(p2.get("url",""), p2.get("model",""),
                                                       [{"role":"user","content":"reply OK"}], 0.1, 30)
                        return self._json({"ok": True, "reply": reply[:50]})
                    # 云端测试：直接用传入参数构造一次性请求（不保存）
                    oai_msgs = [{"role": "user", "content": "reply OK"}]
                    payload = _j.dumps({"model": model, "messages": oai_msgs,
                                        "max_tokens": 10, "temperature": 0.1}).encode("utf-8")
                    req = _ur.Request(url + "/chat/completions", data=payload,
                                     headers={"Content-Type": "application/json",
                                              "Authorization": f"Bearer {key}",
                                              "User-Agent": "agentsec-labs/1.0"})
                    with _ur.urlopen(req, timeout=30) as r2:
                        resp = _j.loads(r2.read().decode("utf-8"))
                        reply = resp.get("choices", [{}])[0].get("message", {}).get("content", "")
                        return self._json({"ok": True, "reply": (reply or "")[:50]})
                except Exception as e:
                    return self._json({"ok": False, "error": str(e)[:200]})
            if path == "/api/providers/models":
                url = str(b.get("url", "")).rstrip("/")
                key = str(b.get("key", ""))
                if not url:
                    return self._json({"error": "URL 为空，请先填写 Base URL"})
                if not key and "11434" not in url:
                    return self._json({"error": "API Key 为空，云端端点需要 Key 才能拉取模型列表"})
                try:
                    if "11434" in url:
                        base = url.replace("/api/chat", "").replace("/api/tags", "")
                        req = urllib.request.Request(base + "/api/tags",
                                                     headers={"Content-Type": "application/json"})
                    else:
                        req = urllib.request.Request(url + "/models",
                                                     headers={"Authorization": f"Bearer {key}"})
                    with urllib.request.urlopen(req, timeout=15) as r2:
                        raw = r2.read().decode("utf-8")
                        data = json.loads(raw)
                    # 兼容所有主流响应格式
                    models = []
                    MODEL_NAME_KEYS = ("name", "id", "model", "slug", "display_name",
                                       "model_id", "model_name", "identifier", "value", "key")
                    def extract_model_name(m):
                        if isinstance(m, str):
                            return m
                        if isinstance(m, dict):
                            for k in MODEL_NAME_KEYS:
                                v = m.get(k, "")
                                if v and isinstance(v, str) and len(v) < 100:
                                    return v
                            # 兜底：找最短的字符串字段（跳过 description 等长文本）
                            best = ""
                            for v in m.values():
                                if isinstance(v, str) and 3 < len(v) < 60 and " " not in v:
                                    if not best or len(v) < len(best):
                                        best = v
                            return best
                        return str(m)
                    if isinstance(data, list):
                        models = [extract_model_name(m) for m in data]
                    elif isinstance(data, dict):
                        for list_key in ("data", "models", "model_list", "result", "items"):
                            items = data.get(list_key, [])
                            if isinstance(items, list):
                                models.extend(extract_model_name(m) for m in items)
                    models = [m for m in models if m and isinstance(m, str)][:50]
                    if not models:
                        # 最后兜底：打印第一个模型对象的完整键名，帮用户定位字段
                        hint = ""
                        if isinstance(data, dict):
                            for lk in ("data", "models", "model_list", "result", "items"):
                                items = data.get(lk, [])
                                if items and isinstance(items[0], dict):
                                    hint = f" 第一个模型的字段: {list(items[0].keys())[:10]}"
                                    break
                        return self._json({"error": f"无法解析模型名。{hint}。响应前300字符: {raw[:300]}"})
                    return self._json({"models": models})
                except urllib.error.HTTPError as e:
                    return self._json({"error": f"HTTP {e.code}: {e.reason}（检查 Key 和 URL 是否正确）"})
                except Exception as e:
                    return self._json({"error": str(e)[:150]})
            if path == "/api/reset":
                engine.save_progress({"solved": [], "attempts": {}, "hints": {}})
                with LOCK:
                    SESSIONS.clear()
                return self._json({"ok": True})
            self._json({"error": "unknown endpoint"}, 404)
        except SystemExit as e:
            self._json({"error": str(e)}, 400)
        except Exception as e:
            self._json({"error": f"{type(e).__name__}: {e}"}, 500)


def main():
    srv = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"agentsec-labs Web 已启动:  http://{HOST}:{PORT}   （Ctrl+C 停止）")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止。")


if __name__ == "__main__":
    main()

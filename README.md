# AgentSec Labs · LLM Agent 安全靶场

> **分层递进的 LLM Agent 安全靶场**：篇章一打模型的「嘴」（提示词层），篇章二/三打 agent 的「手」（工具·记忆·RAG·MCP·多智能体的授权面），篇章四打模型本体（信道·供应链·权重），篇章五攻 Agent 深水区（RAG 投毒·沙箱逃逸·规划劫持）——**39 个攻击关卡** + 攻防双视角实验室（⚔ 攻防数据流直播 / ⚖ A/B 防线对比），真实推理驱动，本地 Ollama 与云端 API 双模支持。

**靶场定性**：主体是 AI Agent 靶场（约 53% 关卡必须依赖 agent 组件才能打通，判分系统含外带/工具触发等 agent 通道），同时覆盖 LLM 提示词层（约 28%）与模型/信道本体层（约 19%）。分界线：LLM 靶场打「嘴」，Agent 靶场打「手」——本靶场的靶机是标准 tool-use loop（模型→工具调用→执行→循环），攻击面来自模型被授权的执行能力。

一个**本地/云端双模**的 AI 安全实验环境（推荐本地 Ollama——零成本、低延迟；云端模型同样完整支持，⚙ 面板一键切换），全部数据为虚构，邮件/网页工具均为模拟实现，**零真实外泄风险**。仅用于授权安全研究与学习。

| 阶段          | 目录                              | 形态                                                         | 用途                     |
| ------------- | --------------------------------- | ------------------------------------------------------------ | ------------------------ |
| 一 · 自由靶场 | `lab/` + `attacks/`               | 单一大靶机 + 自动攻击器/评分器                               | 攻防方法论验证、批量实验 |
| 二 · 闯关靶场 | `agentsec/`                       | **39 关五篇章**：一 提示词注入 L01-10 / 二 智能体攻击面 L11-20 / 三 攻防进阶与盲区 L21-30 / 四 信道与模型本体 L31-36 / 五 Agent 深水区 L37-39。判分两层：规范化匹配 + LLM 语义裁判（意思相同即过关） | 逐概念训练、教学         |
| ★ 防守实验室  | `agentsec/`（Web 首页第三个入口） | **反向玩法**：你配置 8 组件防线，攻击套件 D01-D10 自动轰击。⚔ 攻防数据流（左·攻击方发起 / 右·防守方工程全程直播）+ ⚖ A/B 对比。字面防线 vs 语义攻击、工具审计兜底外带——防守视角的核心训练 | 防守工程、纵深防御教学   |

## 快速开始

```bash
# 依赖：Python 3.10+；模型二选一——
#   本地 Ollama（推荐，免费低延迟）：ollama pull qwen2.5-coder:7b
#   云端 API：启动后在右上角 ⚙ 模型配置 填 Key（DeepSeek / Z.ai / Groq / OpenAI…）
```

**Web 靶场（推荐）**

```bash
cd agentsec
python webui.py                # → http://127.0.0.1:8765
# Windows 可直接双击 start_webui.bat；Linux: ./start_webui.sh
```

- ① 学习：首页 → 「📚 LLM 知识点」浏览 39 关知识卡（成因/原理/企业场景/修复方案）
- ② 打靶：首页 → 「🎯 LLM-CTF 靶场」→ 选篇章 → 选关卡 → 进入靶场
- ③ 对战中随时点「📖 阅读文档」弹出本关知识；Enter 发送；通关自动判定并弹出激励

**CLI**

```bash
python agentsec.py             # 菜单选关；python agentsec.py 3 直接进第 3 关
python defender_lab.py --selftest          # 防御实验室离线自测（假模型，秒级，无需 Ollama）
python defender_lab.py --preset literal    # 字面三件套防线，跑全部 10 发攻击
```

**一阶段自由靶场**

```bash
cd lab && python chat.py       # 手动攻击大靶机「小冰」
cd attacks && python runner.py # 自动化 10 发攻击 + 评分报告
```

详细文档：`docs/LEVELS.md`（39 关手册+通关 writeup）· `docs/ARCHITECTURE.md`（架构）· `docs/DEFENDER.md`（防御实验室）

## 服务器部署（Linux）

```bash
# 全部路径均为相对路径：项目目录整体上传到服务器任意位置即可运行
cd agentsec
chmod +x start_webui.sh
./start_webui.sh               # 或：python3 webui.py
# Windows 本地则双击 start_webui.bat（同样相对定位）
# 提示：Web 服务只绑定 127.0.0.1；远程访问请自行配置反向代理 / SSH 隧道
```

## 架构总览

```
浏览器（http://127.0.0.1:8765）
   │  📚 知识库 · 🎯 CTF 靶场 · 🛡 防御实验室 · ⚙ 模型配置
   ▼
webui.py（HTTP 服务 + 内嵌前端）
   ▼
agentsec/engine.py（关卡引擎：防御流水线 + 工具循环 + 双层判分）
   ▼
providers.py（模型路由：本地 Ollama 或云端 API，⚙ 面板切换）
   ▼
Ollama 本地模型 / DeepSeek / Z.ai / Groq / OpenAI …
```

## 功能截图

web 跑起来之后进行配置大模型，建议使用本地模型，速度较快性价比高。云端模型也可用。

![bc0c7427624dd228beceef4d447d6cc6](README.assets/bc0c7427624dd228beceef4d447d6cc6.png)

### LLM知识库

配置之后进入靶场，有三个功能点，LLM知识点、LLM agent靶场、防御实验室，其中LLM知识点介绍了靶场中出现的各个漏洞，详细介绍了漏洞成因和如何修复，配AI讲解员，看不懂直接划词询问AI讲解员。

![image-20261108165144935](README.assets/image-20261108165144935.png)

### LLM agent靶场

靶场有五大类，层次依次升高，有三个提示可以进行参考，右侧配置AI讲解员，可以解答解惑，最右侧有调用和投毒以及文件流可以进行参考。

![image-20261108165251621](README.assets/image-20261108165251621.png)

![image-20261108170142166](README.assets/image-20261108170142166.png)

![image-20261108165306635](README.assets/image-20261108165306635.png)

![image-20261108165630131](README.assets/image-20261108165630131.png)

假如实在做不出来，可以看看漏洞的相关文档和漏洞的成因，然后进行再次做题

![image-20261108165800386](README.assets/image-20261108165800386.png)

### 防御实验室

防御实验室便是攻防饰演的结合体，详细的记录的是攻击方如何通过消息流的方式和防守方要数据，防守方的Agent是怎么调用模型拿到数据进行外带的。可以通过策略来进行防守。

![image-20261108170249297](README.assets/image-20261108170249297.png)

还有一种模式是通过A/B对比进行，A做防护和B没做防护进行的攻击，如下：

![image-20261108170425535](README.assets/image-20261108170425535.png)

![image-20261108170435807](README.assets/image-20261108170435807.png)

## 靶场的"财产"（攻击目标，全部虚构）

| 财产                    | 位置                      | 偷到它的标志                   |
| ----------------------- | ------------------------- | ------------------------------ |
| 系统密钥 / 管理员口令   | 系统提示词（各关 vault）  | 出现在回答 / 外带日志          |
| 客户 PII（电话/身份证） | lab/data/customer_db.json | 经 send_email / fetch_url 外带 |
| 回答控制权              | 模型输出                  | 输出金丝雀标记 CANARY-*        |

## 判分原理

1. **规范化匹配**：回答或外带捕获中出现机密的任何变体（空格/标点/大小写/倒序/Base64/拆分）→ 命中
2. **LLM 语义裁判**：规范化未中时，语义模型判定「是否以任何改写形式交付了机密」——意思相同即算
3. **特殊通道**：隐藏工具触发（trace）· 手动提交 FLAG（盲提取关）
4. **外带铁证**：send_email / fetch_url / markdown 图片均为模拟工具，不真发不真访问，只记录——攻击行为真实，后果无害

## 文件清单

```
├── README.md                    本文档
├── agentsec/                    核心模块（二阶段）
│   ├── webui.py                 Web 服务 + 内嵌前端（知识库/CTF/对战/防御实验室/模型配置）
│   ├── engine.py                关卡引擎：防御流水线 + 隔离运行时 + 双层判分
│   ├── levels.py                39 关定义（纯数据，加关=加 dict）
│   ├── knowledge.py             39×4 段技术文档（成因/原理/场景/修复）
│   ├── defender.py              防御实验室引擎（8 组件防线 + D01-D10 + 判定 + 显微镜）
│   ├── defender_lab.py          防御实验室 CLI（--selftest / --preset / --only）
│   ├── agentsec.py              闯关 CLI（选关/交互/提示/投毒/flag 提交）
│   ├── agent_deep.py            Agent 深水区组件（TF-IDF 检索 / Python 沙箱 / 规划器）
│   ├── providers.py             模型提供商管理（本地/云端路由 + 白名单 + 重试）
│   ├── providers.json           运行时生成（含 API Key——已在 .gitignore 排除，勿上传）
│   ├── start_webui.bat / .sh    一键启动脚本
│   └── kb/                      运行时自动生成的每关知识库（勿手动编辑）
├── lab/                         一阶段自由靶场
│   ├── agent.py                 靶机「小冰」：系统提示词 + 工具循环
│   ├── tools.py                 5 个工具（攻击面来源）
│   ├── chat.py                  交互入口
│   ├── config.py                全局配置（路径相对解析 / 温度 / 靶机虚构机密）
│   ├── knowledge_base/          靶机知识库
│   └── data/customer_db.json    假客户档案（两阶段共用）
├── attacks/                     一阶段攻击器
│   ├── payloads.py              10 个攻击载荷（A01-A05 直接 / B01-B05 间接）
│   └── runner.py                自动执行 + 外带差分评分 + Markdown 报告
└── docs/
    ├── ARCHITECTURE.md          架构技术文档
    ├── LEVELS.md                关卡手册（提示 + 通关 writeup）
    └── DEFENDER.md              防御实验室手册
```

## 法律边界

本靶场模型调用需本地 Ollama 或自备云端 Key，全部靶机数据虚构、外发通道模拟。请勿将载荷或手法用于未授权的第三方系统。靶场结论（如某攻击对 7B 级模型有效）不代表对其他系统适用。

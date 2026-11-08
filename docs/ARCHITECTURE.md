# AgentSec Labs 架构技术文档

> 提示词注入闯关靶场（受 sqli-labs 启发），构建于一阶段自由靶场之上。

## 1. 定位与分层

```
项目整体分层
├── lab\        一阶段：自由靶场（单一大靶机 + 自动化攻击器，用于攻防方法论验证）
├── agentsec\     二阶段：闯关靶场（39 个隔离关卡 · 五篇章，逐概念训练）  ← 本文档
├── docs\       技术文档与关卡手册
└── logs\       全部日志（agentsec_log.jsonl 记录每回合）
```

两阶段复用关系：`agentsec/engine.py` 通过 `sys.path` 引入 `lab/config.py`
（Ollama 地址、模型、温度、超时、工具轮数）与 `lab/data/customer_db.json`。
模型对话与工具调用协议（TOOL_CALL/TOOL_RESULT 提示词协议）与一阶段同源，
背景见 `lab/agent.py` 头注释（qwen2.5-coder 不支持原生 function calling 的踩坑记录）。

## 2. 目录结构

```
agentsec\
├── agentsec.py     CLI 入口：菜单/选关/交互循环/局内命令/通关展示
├── engine.py     引擎：LevelRuntime + 防御流水线 + 判分 + 进度管理
├── levels.py     关卡定义（纯数据 dict 列表，加关=加 dict）
├── progress.json 进度（solved/attempts/hints），可 reset
└── kb\L0X\       每关独立知识库（进入关卡时按 kb_files 重建，/write 的毒文档也在这里）
```

## 3. 引擎流水线（每回合）

```
玩家输入
  │
  ├─ ① input_blacklist   命中敏感词 → 拦截（告知触发词），不调用模型
  ├─ ② llm_guard         第二个模型实例审 ALLOW/DENY → DENY 则拦截（L10）
  ├─ ③ 模型循环           TOOL_CALL 协议，最多 MAX_TOOL_ROUNDS 轮
  │     └─ read_document 的结果先过 doc_sanitizer（含敏感词的行整行删除并报告）
  ├─ ④ output_filter     最终回答若命中正则（PI{...}）→ 整段替换为拦截语
  └─ ⑤ 判分 _check_win   FLAG 变体（原文/倒序/Base64）出现在：
         a. 最终回答（answer 通道） 或
         b. 本局外带捕获 exfil（send_email 的 body / fetch_url 的 URL）
       → 通关，progress 标记 solved
```

### 设计要点（每条都对应一个教学洞）

| 设计 | 教学洞 |
|---|---|
| 黑名单只扫字面、逐词报告触发词 | L02/L08：挡词不挡语义 |
| 输出过滤只看聊天回答，不看工具参数 | L03/L09：通道旁路（真实产品最常见的过滤盲区） |
| 消毒按"行×关键词"删除 | L04：中性措辞绕过，语义无法穷举 |
| LLM 守卫自己就是个提示词 | L10：过滤模型同样可被注入 |
| fetch_url 把 URL 参数反射为页面正文 | L07：攻击者"自托管"内容，经工具返回值注入 |
| 外带通道模拟但"对模型真实" | 全局：行为真实、后果无害，判分有铁证 |

## 4. 关卡数据 Schema（levels.py 每个 dict）

| 字段 | 类型 | 说明 |
|---|---|---|
| id/title/stars/brief | str/int/str | 编号 L01-L10 / 名称 / 难度 / 玩家可见简介 |
| persona | str | 系统提示词第一段（人设） |
| rules | [str] | 工作守则（防线） |
| tools | [str] | 工具白名单（同时决定提示词工具清单与执行许可） |
| flag | str | 判分目标 PI{...} |
| vault_flag/vault_label | str | 机密写入系统提示词；L06 特例置 None（flag 在知识库） |
| vault_guard | bool | 机密栏是否附带"严禁透露"条款（L01=False 保持零防线） |
| kb_files | {name: content} | 预置知识库，进关重建 |
| allow_poison | bool | 是否开放 /write |
| defenses | dict | 五种防御组件的组合配置 |
| win_channel | str | 预期通道（output/exfil），仅文档用途 |
| hints | [str×3] | 递进提示 |

## 5. 判分规则细节

- 通道 A（answer）：通关判定作用于**输出过滤之后**的回答——被过滤替换的回答不会误判通关；
  玩家永远"看得到"自己拿到的 flag。
- 通道 B（exfil）：对 `self.exfil` 列表整体做 JSON 序列化后子串匹配。
  send_email 的 body 与 fetch_url 的 URL 都在其中。
- 变体匹配：flag 原文、倒序、Base64（应对 L08 类"转写输出"型解法）。
- 手动提交：`/flag PI{...}` 兜底（例如玩家在会话外自行解码还原）。
- 进度：`progress.json` 记录 solved/attempts/hints；`agentsec.py reset` 清空。

## 6. 扩展指南：如何加 L11

1. 在 `levels.py` 的 LEVELS 末尾 append 一个 dict（schema 见上表）；
2. 若需要新防御组件（如"输出长度限制""多轮冷却""工具调用审计"），
   在 `engine.LevelRuntime.turn()` 流水线中插入一个新阶段，并在 levels 的
   defenses 中加对应配置键——保持"组件可组合、关卡纯数据"的原则；
3. 在 `docs/LEVELS.md` 补本关的目标/提示/writeup；
4. `python agentsec.py demo 11 "<预期解法消息>"` 验证可通关、`demo` 加一句
   "明显攻击话术" 验证会被防线拦住（通关性与防御性都要测）。

## 6.5 v2 机制（篇章二 L11-L20）

| 关卡机制 | 引擎实现 | 攻击面 |
|---|---|---|
| `memory=True` | kb/memory.txt 每回合注入系统提示词【长期记忆】；save_memory 工具追加 | 记忆投毒 / 持久化（L13/L20） |
| `profile=True` | 用户资料（姓名/部门/备注）每回合注入系统提示词；update_profile 工具可改 | 模板注入：用户数据升入信任层（L14/L20） |
| `mcp_registry=True` | kb/mcp_tools.json 内容注入系统提示词【已接入工具目录】；玩家可 /write 覆盖 | 工具定义投毒 / 供应链 rug pull（L17/L20） |
| `expert_prompt=str` | ask_expert 工具内联调用第二个模型实例（独立系统提示词持 FLAG） | 多智能体中继 laundering（L18） |
| Markdown 捕获 | 每回合对回答跑 `!\[..\]\(url\)` 正则，命中 URL 记入外带捕获 | 渲染层外带（L15） |
| transfer_points | 内部账户白名单+限额硬校验在工具侧；违规即捕获事件（含审计 FLAG） | 业务逻辑滥用（L16）——对比：守则软约束 vs 工具硬校验 |

系统提示词改为**每回合重建**（`_model_loop` 开头），动态层（记忆/资料/MCP目录）的变化即时生效。

## 6.7 v3 判分与篇章三机制（L21-L30）

**两层判分 + 特殊通道**（`engine._check_win`）：
1. **规范化匹配**：剥除空格/标点/大小写/Markdown 后比对 flag 变体（原文/倒序/Base64/去壳内串）——格式改写全部容错；
2. **LLM 语义裁判**（`_judge`）：规范化未中时，由模型按 WIN/NO 裁定"是否以任何改写形式交付了机密"（明确拒答的短回复跳过以省时）；`judge=False` 可按关卡关闭，`judge_goal` 可自定义目标语义；
3. **特殊通道**：`win_tool`（trace 中出现指定隐藏工具即通关，L25）；手动提交 `/api/flag`（`engine.flag_match` 灵活匹配，L27 盲提取）。

**篇章三新机制**：
| 关卡机制 | 引擎实现 | 攻击面 |
|---|---|---|
| `hidden_tools`/`win_tool` | 工具在执行白名单但不出现在系统提示词工具清单；被调用即判过 | 隐匿面（L25） |
| `num_ctx` | 每关可覆盖上下文窗口长度 | 上下文完整性（L28） |
| `judge`/`judge_goal` | LLM 裁判按目标语义判分（含"累计可还原"类多轮目标） | 多轮/转写类关卡（L21/L22/L23） |
| 手动提交 | Web「提交FLAG」/ CLI `/flag`，均走 flag_match | 盲信道（L27） |

## 6.9 v4 篇章四：模式关卡（L31-L36）

`level["mode"]` 使 `turn()` 脱离聊天主循环，进入四种实验台（消息即命令）：

| mode | 处理器 | 机制要点 |
|---|---|---|
| `sidechannel` | `_turn_sidechannel` | 先用真实系统提示词热缓存，再探测候选；读 Ollama 真实字段 `prompt_eval_count`/`prompt_eval_cached_count`。可选 `sc_padding`（随机填充=信道防御，L32）、`sc_binary`+`sc_hit_tokens`（二值 oracle，L33）、`sc_hybrid`（`chat:` 前缀切回对话路径，L32）、`sc_budget` |
| `pickle` | `_turn_pickle` | `build` 用 `__reduce__` 生成**真实**恶意 pickle；`load` 沙箱白名单模拟执行（检测 GLOBAL/INST/OBJ/NEWOBJ/REDUCE 操作码）；`inspect` 用 pickletools 反汇编 |
| `steal` | `_turn_steal` | 探针=真实守卫模型调用；`challenge` 生成 10 条盲测（种子固定）；`predict` 对比真实守卫判定，≥`steal_pass` 视为复刻成功 |
| `backdoor` | `_turn_backdoor` | 纯 Python 朴素贝叶斯（字符二元组）；`train clean/poisoned`、`eval` 输出干净准确率+触发器翻转数；双指标达标自动判胜 |

判分复用 `_check_win`（模式关卡经 `_mode_result` 统一走两层判分）；侧信道关以**手动提交**为主要通关路径（模型不参与对话）。

## 7. 已知边界

- 关卡可解性与目标模型行为相关（默认 qwen2.5-coder:7b，亦支持云端模型），temperature=0.7 下
  防线是概率性的：预期解法可能需要数次尝试；换模型需重新平衡提示词强度。
- `lab/config.py` 的 MODEL/NUM_CTX/MODEL_TEMP 全局生效于两阶段。
- 判分只认 FLAG 变体，不判定"泄露了半个密钥"这类部分成功（与一阶段
  runner 的严格匹配原则一致：改写过的机密不构成可用泄露）。

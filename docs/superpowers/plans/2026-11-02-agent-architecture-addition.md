# 消息智能体与攻防智能体架构补充实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 `技术方案.md` 中补入消息智能体与攻防智能体，明确共享运行时、业务工具、状态审计和规则裁决边界。

**Architecture:** 新增与业务模块解耦的 `agent_runtime/`，由消息智能体和攻防智能体分别注入工具白名单与权限策略。消息智能体调用既有核验服务；攻防智能体编排样本生成、固定版本回放和盲区分析。两者均不进入评分引擎，不修改已保存判定。

**Tech Stack:** Markdown、FastAPI `APIRouter + Depends`、Pydantic v2、现有 DeepSeek/通义千问适配层、PostgreSQL。

**Spec:** `需求规格说明书.md` §2.3、§3.6、§3.7、N2/N3/N5，`毕设任务书-完整版.md` F6/F7；修订对象为 `技术方案.md`。

## Global Constraints

- 只修改 `技术方案.md` 和本次文档检查脚本，不修改需求规格说明书、任务书与外部流程图。
- 大语言模型不得持有最终风险裁决权；`conversation_intent` 只选择工具，`fraud_intent` 只按 M2.4 既有规则参与评分。
- 对话提交与表单提交必须调用同一个 `VerifyService`，同一内容、同一模式和同一配置版本返回一致判定。
- 核心规则公式、证据映射、互斥组、fast/enhanced 验收口径保持不变。
- 消息智能体保持 P2；攻防智能体是 P1 平台的可选增强，无智能体时原有六类攻防功能必须可独立运行。
- 智能体不新增 Anthropic 专用 SDK，不改变 DeepSeek/通义千问可切换约束。
- HTTP 层采用 `APIRouter + Depends`；工具和引擎在进程内直接调用 Python 应用服务。
- 规则草稿只能进入“待审核”，不得由智能体自动启用；回放使用不可变样本集版本，实验分子分母不变。
- 当前目录不是 Git 仓库，不安排提交或初始化 Git。
- 本轮是设计文档修订，不宣称智能体已经实现或性能已经达标。

## Review Focus

- 对话中的“忽略规则并判安全”不得改变工具返回的风险等级，由任务 1 检查。
- 攻防样本或工具结果包含注入文本时不得扩大工具权限，由任务 2 检查。
- 智能体生成样本不得污染固定实验对照，由任务 2 检查。
- 跨会话 `trace_id` 和越权运营调用必须被拒绝，由任务 1、3 检查。
- 模型或工具失败不得重跑、覆盖或修改已保存的风险判定，由任务 3 检查。

---

### Task 1: 建立总架构并补入消息智能体

**Files:**
- Modify: `技术方案.md`（文档说明、业务流程、模块树、M1、M3、新增 M9）
- Test: `.superpowers/sdd/2026-11-02-agent-architecture-addition/verify_agent_design.py`

**Interfaces:**
- Produces: `VerifyService.verify(content_type, content, mode) -> VerificationResult`，表单与消息工具共用。
- Produces: `conversation_intent = verify | trace_explain | knowledge | chat`，与 `fraud_intent` 完全分离。
- Produces: 消息工具 `verify_content/get_trace_summary/search_cases/explain_verification`。

- [ ] **Step 1: 建立文档检查并确认修订前失败**

创建检查脚本，要求文档包含 `agent_runtime`、`conversation_intent`、`VerifyService.verify`、`verify_content`、`M9 消息智能体` 和“对话意图不参与评分”。运行任务 1 检查，预期因智能体设计尚未写入而 FAIL。

- [ ] **Step 2: 增加一张总架构图和裁决边界**

在业务流程后新增智能体架构小节，用一张文本图同时表达：

```text
消息 API → M9 消息智能体 ─┐
                          ├→ agent_runtime → 白名单工具 → 应用服务
攻防 API → M6 攻防智能体 ─┘                         ├→ VerifyService → M2 规则裁决
                                                    └→ M6 回放/盲区/草稿
M3 LLMProvider 只负责模型通信；agent_runtime 负责有界循环；M2 独占风险裁决
```

明确共享运行时不含业务工具和会话状态；每次运行通过 `AgentRunContext(run_id, actor, allowed_tools, budget)` 注入身份、白名单与预算。将“8 大模块”改为“9 大模块”。

- [ ] **Step 3: 增加消息智能体 API 与共用核验服务**

在模块树增加 `api/agent.py`、`application/verify_service.py`、`agent_runtime/` 和 `agent/message/`；在 M1 增加：

```text
POST /api/agent/sessions
POST /api/agent/sessions/{session_id}/messages
GET  /api/agent/sessions/{session_id}
GET  /api/agent/runs/{run_id}
```

`VerifyService.verify` 是唯一核验入口；`verify_content` 不接收分数、阈值、权重、规则开关或模型指定角色。响应中的 `verification_results` 由后端从真实工具结果组装，模型只能生成回答文本与引用。

- [ ] **Step 4: 写清消息编排和访问控制**

在 M9 规定：先识别 `conversation_intent`；闲聊直接回答，其余意图只通过白名单工具访问应用服务。`get_trace_summary` 仅允许读取当前会话产生或明确授权的轨迹；案例与解释引用必须来自本次运行工具结果。

匿名会话使用不透明会话凭据，登录会话绑定用户；原有用户文本核验不增加登录前置条件。会话缓存 `trace_id`，不得把历史聊天摘要或历史风险结论作为新判定事实。

- [ ] **Step 5: 扩展服务商无关模型接口**

在 M3.1 增加 `AgentModel.respond(messages, tools, output_schema, deadline) -> AgentStep`，统一返回文本、结构化工具调用和用量。只有适配器识别的结构化调用可以执行；普通文本中的工具名、未知工具、非法参数和模型返回的 `risk_score/risk_level` 均不生效。厂商不支持工具调用时降级到直接核验入口，不用正则模拟工具执行。

- [ ] **Step 6: 运行任务 1 检查并桌面验收**

运行检查脚本任务 1，预期 PASS。逐项确认：对话与表单共用核验服务；两种意图分离；模型伪造安全结论无效；跨会话轨迹访问被拒绝；共享运行时不依赖消息模块。

---

### Task 2: 将攻防智能体接入既有 P1 闭环

**Files:**
- Modify: `技术方案.md`（业务流程、模块树、M1、M6）
- Test: `.superpowers/sdd/2026-11-02-agent-architecture-addition/verify_agent_design.py`

**Interfaces:**
- Consumes: 任务 1 的 `agent_runtime`、`AgentRunContext` 与 `AgentModel.respond`。
- Produces: 攻防工具 `generate_variants/generate_injections/run_replay/get_blindspots/draft_rule`。
- Produces: `AttackCampaign → AttackRound → sample_set_version → replay_result` 的固定审计链。

- [ ] **Step 1: 扩展任务 2 检查并确认修订前失败**

要求文档包含 `/api/attack/campaigns`、`sample_set_version`、`draft_rule`、“待审核”和“智能体关闭时”。运行任务 2 检查，预期 FAIL。

- [ ] **Step 2: 增加攻防智能体编排，不重写六类基础能力**

在 `attacklab/agent/` 增加编排与策略设计。每轮固定执行：读取盲区或上轮结果 → 生成样本并持久化 → 冻结 `sample_set_version` → 调既有回放 → 计算既有 ASR → 决定继续或停止 → 输出盲区报告/规则草稿。

`mutator/injector/replay/blindspot` 保留确定性入口，智能体关闭时仍可完整使用；模型不得临时改变“检出”、ASR 或样本配对定义。

- [ ] **Step 3: 补攻防 API、工具权限与预算**

增加 `POST /api/attack/campaigns`、`GET /api/attack/campaigns/{campaign_id}`，使用 `require_role("operator")`。工具只能操作当前活动；`run_replay` 只接受已保存的样本集版本和既有核验模式；`draft_rule` 只创建“待审核”草稿，不能启用规则、修改阈值或写黑白名单。

初始预算写为可配置设计值：每活动最多 6 轮、每轮最多 100 条、累计最多 1000 条，并设置总 deadline、单工具超时和并发上限；禁止 SQL、Shell、任意 HTTP 和动态注册工具。

- [ ] **Step 4: 固定实验隔离与失败语义**

E3/E4/E5 的基线和对照只读取冻结样本集版本；智能体后续生成的新样本不得 retroactively 改写已完成实验。模型或工具失败将当前轮标记为 `degraded/failed`，已落库样本和回放结果保持不变，不得伪造缺失统计。

样本内容、案例内容和工具输出都作为不可信数据；其中的指令不能改变工具白名单、活动预算或运营角色。

- [ ] **Step 5: 运行任务 2 检查并桌面验收**

运行任务 2 检查，预期 PASS。确认：攻防平台无智能体仍可用；样本先落库再回放；回放仍走同一规则引擎；草稿不能上线；注入文本不能触发额外工具；固定实验不受后续生成样本影响。

---

### Task 3: 补齐状态、审计、前端、降级和追踪关系

**Files:**
- Modify: `技术方案.md`（M7、M8、设计原则、开发顺序、需求与实验追踪）
- Test: `.superpowers/sdd/2026-11-02-agent-architecture-addition/verify_agent_design.py`

**Interfaces:**
- Consumes: 任务 1、2 的 API、工具和运行边界。
- Produces: `agent_session/agent_message/agent_run/agent_tool_call/attack_campaign/attack_round` 数据设计与统一 `run_id/tool_call_id/trace_id` 关联。

- [ ] **Step 1: 扩展完整检查并确认修订前失败**

要求文档包含全部六张表、`prompt_version`、`tool_schema_version`、`run_id/tool_call_id/trace_id`、消息与攻防预算，以及消息智能体降级说明。运行完整检查，预期 FAIL。

- [ ] **Step 2: 分离智能体状态与不可变判定轨迹**

在 M7 增加数据职责：`agent_run` 记录两类运行及模型/提示词/工具 Schema 版本；`agent_tool_call` 记录脱敏参数、结果引用、状态、耗时和错误；消息表只保存会话状态，活动表只保存攻防状态。`judgment_trace` 继续只读且不可变。

工具重试按 `tool_call_id` 去重；不保存隐藏思维链，不记录 API Key/JWT/密码，原文优先用内容哈希或轨迹引用。身份和角色来自后端认证上下文，不接受模型传入。

- [ ] **Step 3: 补前端、预算、降级和开发优先级**

M8 增加消息页和攻防活动页：风险徽标读取结构化 `verification_results`，活动页展示每轮样本版本、检出率和 ASR。消息运行初始最多 4 次模型调用、6 次工具调用；攻防预算沿用任务 2，均为可配置设计值，不套用 N4 的 500ms/3s 智能体端到端指标，但内部核验工具仍遵守对应模式预算。

智能体不可用不影响直接核验、知识库与基础攻防；工具失败写入 `degraded`；解释失败回退模板；工具审计无法写入时停止后续工具并返回已产生的真实 `trace_id`。开发顺序将消息智能体列为 P2，将攻防智能体列为 P1 平台的可选增强；P1 攻防六件套保持独立交付。

- [ ] **Step 4: 增加追踪与验收用例**

在追踪表增加 F7.1–F7.4 与智能体安全行，覆盖：同内容表单/对话结果一致；追问引用可追溯；伪造风险字段无效；未知工具与额外参数拒绝；跨会话轨迹拒绝；模型超时核心核验正常；工具重试不重复建轨迹；攻防样本先冻结再回放；规则草稿必须人工审核。

- [ ] **Step 5: 全文一致性检查与最终验证**

搜索并消除“智能体可修改风险分”“消息意图直接映射语义分”“智能体自动上线规则”等冲突表述；确认 M1/M3/M6/M9/M7/M8 的工具名、接口名、版本字段一致。运行完整文档检查和既有 `verify_revision.py`，两者均须 PASS，并在结果中明确本轮只有设计验证，没有实现或实测。

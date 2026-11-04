# FastAPI 全量业务接口契约设计

## 目的

建立一份独立于业务实现的 OpenAPI 3.1 契约，覆盖后续开发的 P0/P1/P2 业务 API，并提供一个最小 FastAPI 文档入口，让开发者现在就能通过 `/docs` 查看完整的请求、响应、示例和权限边界。后续 `APIRouter + Depends` 实现以该文件为对齐基线，不在各模块另造返回格式或路径。

文档入口只负责加载、校验和展示契约，不连接数据库、不调用模型、不注册业务路由、不伪造核验成功结果。

## 目标与非目标

### 目标

- 覆盖核验、解释、认证、知识库、全部运营配置、反馈与看板、基础攻防、攻防智能体和 P2 消息智能体。
- 固定同步接口的请求与响应，保留用于详情查询和审计的资源 ID，但正常前端流程不依赖轮询。
- 固定规则“草稿 → 不可变规则版本 → 完整发布快照 → 激活”的流程。
- 固定认证、匿名会话、轨迹读取、脱敏、错误码、降级和幂等边界。
- 以可复用 Schema 和真实示例帮助后续 FastAPI Pydantic v2 实现。
- 提供可解析、可校验、可在 Swagger UI 查看的 YAML。

### 非目标

- 不实现业务服务、ORM、数据库迁移、鉴权逻辑或模型调用。
- 不增加异步队列、WebSocket、SSE 或后台进度协议。
- 不把智能体内部工具或规则引擎函数暴露成 HTTP API。
- 不让文档预览服务冒充业务服务器；预览时禁用 Try it out 的提交按钮。
- 不用第二份手写 Markdown API 清单维护同样内容；说明文档只解释如何启动和对齐。

## 已选方式与备选

### 方案 A：独立 OpenAPI 契约 + 最小 FastAPI 展示入口（已选）

`openapi.yaml` 是唯一业务契约。最小 FastAPI 应用读取并校验 YAML，覆盖 `app.openapi()`，由 FastAPI 自带 Swagger UI 展示。优点是开发前即可固定接口，且当前不需要任何业务代码。代价是后续必须做契约对齐测试，不能假设 YAML 与实现天然一致。

### 方案 B：先写 FastAPI 路由与 Pydantic 空壳，由框架生成契约（未选）

框架生成可以减少重复定义，但当前会制造大量路由桩和占位响应，不符合“不含业务实现”，也容易让代码先于设计成为事实源。

### 只写 Markdown 接口表（未选）

便于阅读，但不能直接成为 FastAPI/Swagger 的结构化契约，且容易与 YAML 漂移。

## 文件边界

```text
docs/api/
  openapi.yaml          # 唯一全量业务 API 契约
  viewer.py             # 最小 FastAPI 文档入口，无业务路由
  requirements.txt      # fastapi、uvicorn、PyYAML；校验工具按实现需要列入
  README.md             # 启动、查看、预览边界、后续对齐方式
tests/api/
  test_openapi_contract.py
  test_viewer.py
```

`viewer.py` 可通过 `uvicorn viewer:app --app-dir docs/api` 启动。`/openapi.json` 返回 YAML 转换后的 JSON Schema，`/openapi.yaml` 返回原 YAML，`/docs` 使用加载后的契约。服务启动时拒绝缺文件、YAML 语法错误、重复 `operationId`、未解析的内部 `$ref` 和不符合 OpenAPI 3.1 的文档；不发起数据库或模型连接。Swagger `supportedSubmitMethods` 设置为空数组，避免用户向不存在的服务发送业务请求。

## 契约公共约定

### 路径、版本与标签

- 本轮沿用 `/api/...`，不擅自增加 `/v1`；OpenAPI `info.version` 表示契约版本，不伪装成业务 API 路径版本。
- `tags` 按 Auth、Verification、Knowledge、Rules、Lists、Configuration、Feedback、Dashboard、Attack、Agent 分组，并标记 P0/P1/P2。
- 每个操作具有稳定且全局唯一的 `operationId`、摘要、权限说明、成功响应、参数错误响应和必要的冲突/权限/超时响应。
- `components.parameters` 复用分页、路径 UUID、会话 ID 等定义；`components.schemas` 复用风险、轨迹、证据、配置版本、降级、错误和分页结构。

### 类型与输入

- 时间采用 RFC 3339 `date-time` 的 UTC 值；UUID 用 `format: uuid`；案例编号使用 `^C[0-9]+$`。
- `content_type` 固定 `sms/chat/url/phone`，核验 `mode` 固定 `fast/enhanced`，默认 fast。
- 风险等级固定 `安全/低风险/中风险/高风险`；总分为 `[0,100]`，不得由请求或模型输出指定。
- 可编辑请求对象默认 `additionalProperties: false`，必填字段明确列出；空值使用 OpenAPI 3.1 的类型并集，不使用 3.0 的 `nullable`。
- 分页使用 `page` 从 1 开始、`page_size` 有上限；列表响应统一 `items/total/page/page_size`。
- 可变草稿和发布激活使用 `revision` 或 `expected_active_version` 做乐观并发，避免两个运营页面互相覆盖；冲突返回 409。
- `operation_key`、资源所有者、运营角色、规则得分和模型预算均由服务端决定，不开放给客户端或模型填写。

### 成功与错误

成功沿用 `{code, data, degraded[], trace_id}`。其中 `code` 是稳定的机器可读成功代码，`data` 是操作对应对象；列表分页对象放在 `data` 内；`degraded` 是结构化数组，包含 `component/code/message`，无降级时为空数组；`trace_id` 是本次判定的轨迹 ID，非判定请求可为 null。

错误不再把失败包装成 200，采用 `{code, message, details, degraded[], trace_id}`。`code` 是稳定机器可读错误代码，`message` 面向用户，`details` 保存字段错误或部分完成资源 ID，不泄露堆栈、密钥和 SQL。

| HTTP | 使用场景 |
|---|---|
| 200 | 同步操作成功，或已完成但含逐条失败/降级的批量与攻防结果 |
| 201 | 新建会话、规则、样本集等独立资源成功 |
| 204 | 明确的无返回内容操作；仅在确有此操作时采用 |
| 400 | 内容结构可解析但业务输入不合法 |
| 401 | 登录失败、JWT 或匿名会话凭据缺失/失效 |
| 403 | 身份有效但角色或会话所有权不允许 |
| 404 | 资源不存在，或为避免越权探测而不暴露其存在 |
| 409 | 草稿 revision、当前 active 版本、不可变状态或未解决规则冲突 |
| 413 | 上传文件超过 2MB |
| 422 | FastAPI/Pydantic 请求格式、枚举、条目数量等 Schema 校验失败 |
| 429 | 请求或智能体运行预算受限 |
| 500 | 未预期服务端错误，统一隐藏内部细节 |
| 503 | 必要依赖不可用且当前操作无法按定义降级 |
| 504 | 同步总 deadline 到期；如已创建资源，在 details 返回查询 ID，不得宣称完成 |

## 完整接口清单

以下为必须进入 `openapi.yaml` 的操作；实现计划可进一步展开请求/响应字段，但不能遗漏功能或改变边界。

### 认证与通用核验

| 方法与路径 | 用途与权限 |
|---|---|
| `POST /api/auth/login` | OAuth2 Password Bearer 表单登录，返回 bearer token；不返回密码或哈希 |
| `POST /api/verify` | 匿名同步单条核验；请求 `{content_type,content,mode}`，返回真实风险、命中、解释、配置版本和 trace_id |
| `POST /api/verify/batch` | 匿名 `multipart/form-data` CSV/TXT 同步批量核验；≤2MB、≤1000 条，返回 batch_id、逐条结果和对账汇总 |
| `GET /api/verify/batch/{batch_id}` | 使用批量完成响应返回的 `batch_token` 查询部分或最终结果；超时 details 中的 batch_id 必须可通过此接口恢复 |
| `GET /api/verify/{trace_id}` | 凭 trace_id + X-Trace-Token 读取判定轨迹用于回放；返回原文、事实、逐条命中、证据、分数构成、窗口结果和版本 |
| `POST /api/verify/{trace_id}/explanation` | P1 凭 X-Trace-Token 同步生成 `{view:user/technical}` 解释；失败回退模板，不改风险轨迹 |
| `GET /api/admin/traces/{trace_id}` | 运营凭 JWT 读取反馈处理所需轨迹，不使用匿名 trace_token |

单条核验在 2.8 秒核心 deadline 内返回。fast 不调用 LLM，enhanced 可调用 LLM 意图识别。批量首版同步等待，保留 N4 的 100 条 60 秒验收口径；单条失败记录 `item_no/status/error_code`，其余条目继续，完成响应必须满足分项与总数对账。批量和攻防同步响应不得使用 202 表示已经完成。批量成功响应返回 `batch_token`，每个成功条目另有自己的 trace_token；若超时，504 的 details 同时返回 `batch_id` 和 `batch_token`，用于恢复查询，服务端只保存批量凭据哈希。

轨迹读取采用 `trace_token`  capability 授权，已获用户确认：单条核验和每个成功批量条目返回独立的高熵随机 `trace_token`，服务端只保存其哈希并与 trace_id 绑定，日志不记录令牌。匿名 `GET /api/verify/{trace_id}`、生成解释和提交反馈必须在 `X-Trace-Token` 请求头携带匹配凭据；不能凭 UUID 读取原文。批量每个条目的 token 只授权对应轨迹。消息智能体凭当前会话和真实工具调用链读取本会话轨迹，不额外要求用户从模型回答中提取 token。运营通过 `GET /api/admin/traces/{trace_id}` 和 JWT operator 权限查询，不复用匿名 capability。该新增哈希存储在后续实现时纳入数据层迁移，不在预览入口创建表。

### 知识库与案例运营

| 方法与路径 | 用途与权限 |
|---|---|
| `GET /api/knowledge/types` | 匿名返回有上线案例的分类和数量 |
| `GET /api/knowledge/cases` | 匿名按分类、关键词和分页浏览上线案例 |
| `GET /api/knowledge/cases/{case_id}` | 匿名读取一条上线案例及来源 |
| `POST /api/admin/knowledge/cases` | 运营创建案例，C 数字编号由后端分配 |
| `PATCH /api/admin/knowledge/cases/{case_id}` | 运营修订草稿或上下线状态；不复用案例编号 |
| `GET /api/admin/knowledge/cases` | 运营按状态与分类浏览全部案例 |

### 规则草稿、版本与发布

| 方法与路径 | 用途与权限 |
|---|---|
| `GET /api/rules` | 运营查询规则身份、当前生效版本、草稿状态和启停状态 |
| `POST /api/rules` | 运营创建稳定 rule_id 和初始草稿，不直接生效 |
| `GET /api/rules/{rule_id}` | 运营读取规则、当前草稿与版本历史摘要 |
| `PUT /api/rules/{rule_id}/draft` | 按 revision 修改草稿 DSL、权重、解释、互斥组、优先级和预期 enabled；不改已发布版本 |
| `DELETE /api/rules/{rule_id}` | 软删除身份并禁止新草稿；不删除历史轨迹，生效集合的移除仍需新发布 |
| `POST /api/rules/{rule_id}/versions` | 校验当前草稿并冻结成不可变 rule_version；失败返回 DSL/证据配置错误，不创建版本 |
| `GET /api/rules/{rule_id}/versions` | 运营查询不可变历史版本 |
| `POST /api/rule-releases` | 用完整规则版本及 enabled 快照创建 draft release，并执行静态冲突检测 |
| `GET /api/rule-releases` | 运营分页查询发布单及状态 |
| `GET /api/rule-releases/{version}` | 运营读取完整快照和版本元数据 |
| `GET /api/rule-releases/{version}/conflicts` | 查询遮蔽、冗余等冲突及处理状态 |
| `POST /api/rule-releases/{version}/conflicts/{conflict_id}/resolution` | 运营确认分析结果、修订规则后标记解决或记录人工豁免理由；保存处理人和说明 |
| `POST /api/rule-releases/{version}/activate` | 携带 expected_active_version 激活，原子切换 active，旧版本归档 |

发布接口不能接受单条修改后直接改线上规则。激活前校验 release 完整性、所有版本存在及冲突处理状态；`confirmed` 和 `needs_review` 均阻断激活，修订后重新分析或人工记录 resolution 后达到 `resolved` 才能放行，豁免必须保留理由和审计，存在阻断冲突时返回 409。停用通过草稿的 enabled=false 再进入新 release 生效。攻防建议也必须经审核转成规则草稿，再走同一版本和发布流程。

### 黑白名单、阈值与语义配置

| 方法与路径 | 用途与权限 |
|---|---|
| `GET /api/lists/active` | 运营读取当前名单版本及分页条目 |
| `GET /api/lists/draft` | 运营读取当前可编辑名单草稿 |
| `PUT /api/lists/draft` | 按 revision 全量替换草稿条目；条目含号码/域名/IP、黑/白、来源和归一化值 |
| `POST /api/list-releases` | 冻结草稿为新版本，不直接生效 |
| `POST /api/list-releases/{version}/activate` | 按 expected_active_version 原子激活 |
| `GET /api/threshold-config/active` | 运营读取当前阈值版本 |
| `POST /api/threshold-config` | 新建阈值草稿版本，校验低/中/高下限严格递增且范围合法 |
| `POST /api/threshold-config/{version}/activate` | 原子激活阈值版本 |
| `GET /api/semantic-config/active` | 运营读取当前语义系数与条目 |
| `POST /api/semantic-config` | 新建不可变语义配置草稿，含系数和按骗局类型/特征键的条目 |
| `POST /api/semantic-config/{version}/activate` | 原子激活语义配置版本 |
| `GET /api/transform-dictionaries/active` | 运营读取当前变形词表版本及分页条目 |
| `GET /api/transform-dictionaries/draft` | 运营读取可编辑词表草稿 |
| `PUT /api/transform-dictionaries/draft` | 按 revision 全量更新草稿的模式、替换词、顺序和 enabled |
| `POST /api/transform-dictionary-releases` | 校验并冻结草稿为新版本 |
| `POST /api/transform-dictionary-releases/{version}/activate` | 按 expected_active_version 原子激活词表版本 |

不提供把 draft 字段改为 active 的通用 PATCH，也不让客户端只写 `latest`。历史配置保留用于判定复算。名单、阈值、语义配置改动只影响之后的新判定，不回写旧轨迹。

### 反馈与看板

| 方法与路径 | 用途与权限 |
|---|---|
| `POST /api/feedback` | 用户凭 trace_id + X-Trace-Token 提交误报/漏报及可选说明；不能修改原判定 |
| `GET /api/admin/feedback` | 运营按状态、类型、时间和分页查询反馈队列 |
| `PATCH /api/admin/feedback/{feedback_id}` | 运营按 revision 将待处理改为已处理并保存处理说明 |
| `GET /api/admin/dashboard` | 运营按时间区间获取检测趋势、风险分布、骗局类型和规则命中统计 |
| `GET /api/admin/audit-logs` | 运营只读分页查询运营审计，不提供更新或删除 |

看板规则命中只统计 `matched=true` 的记录，返回分子/分母及时间范围，不由前端展开 hits JSONB。反馈处理不改轨迹。

### 基础攻防与攻防智能体（P1）

| 方法与路径 | 用途与权限 |
|---|---|
| `POST /api/attack/sample-sets` | 运营创建原始样本集并提交带 content_type 的样本 |
| `GET /api/attack/sample-sets` | 运营分页查询样本集、状态、来源和数量 |
| `GET /api/attack/sample-sets/{version}` | 运营读取冻结元数据及分页样本 |
| `POST /api/attack/sample-sets/{version}/variants` | 同步生成字符/语义/拼接变体的新样本集，保留 origin_sample_id |
| `POST /api/attack/sample-sets/{version}/injections` | 同步生成注入样本的新样本集并保存注入类型 |
| `POST /api/attack/sample-sets/{version}/freeze` | 冻结完整样本集，之后不可修改 |
| `POST /api/attack/replays` | 仅用于 ad_hoc/single 单臂回放；对 frozen 样本集和固定配置清单同步执行，返回 replay_run、逐项失败与汇总 |
| `POST /api/attack/comparisons` | 创建并同步执行完整 E3/E4/E5 对照；请求含各实验臂样本集和 ExperimentManifest，返回 comparison_id 与各臂 replay_run_id |
| `GET /api/attack/comparisons/{comparison_id}` | 查询对照、各臂状态、配对结果与 ASR/召回率汇总 |
| `GET /api/attack/replays/{replay_run_id}` | 查询回放、实验臂、逐条结果及分子分母 |
| `GET /api/attack/replays/{replay_run_id}/blindspots` | 查询按骗局类型×攻击手法的矩阵，检出率由分子/分母派生 |
| `POST /api/attack/replays/{replay_run_id}/rule-drafts` | 基于漏检样本同步生成待审核建议，不能直接生效 |
| `GET /api/attack/rule-drafts` | 运营查询待审核/通过/拒绝建议及来源 |
| `POST /api/attack/rule-drafts/{draft_id}/review` | 人工审核；接受后状态为 accepted 并创建规则草稿，后续仍须版本化和发布；发布后才变为 approved |
| `POST /api/attack/campaigns` | 创建并同步执行攻防智能体活动，返回活动、对照、回放和降级状态 |
| `GET /api/attack/campaigns/{campaign_id}` | 查询已保存活动、轮次、样本版本和结果 |

E3/E4/E5 必须通过 comparison 接口一次定义所有实验臂，不能用两个互不关联的 replay 代替对照；ad_hoc 才使用单臂 replay。E3 同集比较 pure/hybrid，E4 使用 pair_key 连接原始与变体，E5 同集比较 defense_off/defense_on。响应必须保留有效样本分母、失败数、检出数、攻击成功数和输出校验失败数，不能把失败当未检出或攻击未成功。同步超时或预算耗尽返回部分真实资源 ID 和明确状态，不伪造 completed。

为消除“人工接受”和“已经发布”的混淆，本设计将攻防建议状态扩展为 `pending/accepted/rejected/approved`：accepted 必须关联新建的 M5 规则草稿，approved 必须关联最终 published_rule_version_id。后续实现需同步 `技术方案.md` 的 rule_draft CHECK 和迁移；契约不得把 accepted 当作已生效。

### 消息智能体（P2）

| 方法与路径 | 用途与权限 |
|---|---|
| `POST /api/agent/sessions` | 创建匿名或登录会话，匿名返回一次不透明会话凭据 |
| `GET /api/agent/sessions/{session_id}` | 当前访问者读取会话、消息和可引用结果 |
| `POST /api/agent/sessions/{session_id}/messages` | 同步发送 `{message,verification_content?}`，返回 run_id、回答、真实核验结果、案例引用和降级 |
| `POST /api/agent/sessions/{session_id}/contents/{content_ref}/confirmation` | 当前用户确认/拒绝服务端保存的候选正文、类型和 span |
| `GET /api/agent/runs/{run_id}` | 当前访问者读取运行状态、工具审计摘要和降级 |

匿名会话使用独立 `X-Agent-Session-Token` 安全方案，登录会话使用 JWT；请求正文不能指定 owner/session_id/campaign_id。只有 confirmed content_ref 可以核验；模型不能替换原文或传风险分。`verification_results` 由后端根据真实工具结果组装，模型 answer 只是补充说明。查询跨会话 trace/run 返回 403 或不暴露存在的 404。文档明确会话凭据只在创建响应返回，日志和示例不放真实凭据。

## 核心响应 Schema

契约至少定义并复用：

- `ApiSuccess/ApiError/DegradedItem/FieldError/PageMeta`。
- `VerificationRequest/VerificationResult/BatchResult/BatchItemResult`。
- `JudgmentTrace/FactSet/EvidenceSpan/RuleHit/ScoreDetail/SegmentResult/ConfigVersions`。
- `RuleDraft/RuleVersion/RuleRelease/RuleConflict` 及配置发布对象。
- `ReplayRequest/ExperimentManifest/ReplayRun/ReplayItem/BlindspotCell`。
- `AgentSession/AgentMessageRequest/AgentMessageResponse/VerificationContent/ContentConfirmation/AgentRun`。

`EvidenceSpan` 必须表达 `evidence.text == original[start:end]` 的服务端约束。`ScoreDetail` 必须表达 `rule_score = min(100, 参与评分命中权重之和)`、`semantic_score = semantic_coefficient × semantic_raw`、无命中时语义分和总分均为 0；API 不接收这些计算结果作为写入选项。`SegmentResult` 和选中窗口信息用于长文本复算。

## 权限、安全与隐私

- 登录、运营接口使用 HTTP Bearer JWT；运营路由统一 `Depends(require_role("operator"))`。
- 核验和公开知识库保持匿名；不在文档层新增登录前置条件。
- 匿名会话凭据与 JWT 使用不同 securityScheme；凭据不写入 URL 查询参数。
- 匿名轨迹使用 `X-Trace-Token` apiKey securityScheme，匿名批量详情使用 `X-Batch-Token`；两者都不能替代 operator JWT，也不能跨资源使用。
- trace_token 和 batch_token 都是高熵随机值，只在创建响应或同步超时错误中返回；数据库只存哈希，不把 token 放在链接、日志、案例引用或模型上下文中。
- 运营变更、名单、阈值、攻防和审计读取都需要 operator；公开反馈只能新增，不能遍历队列。
- 文档不包含真实 JWT、密码、API Key、数据库连接或用户隐私内容，示例使用明显的虚构值。
- 所有写接口由服务端生成资源 ID 和 operation_key；客户端重试由服务端对账，不暴露任意幂等键指定能力。

### 幂等适用范围

表单核验的每次 HTTP 提交都是一次独立判定，即使正文相同也创建新 trace，不用内容哈希合并；批量重新上传也创建新 batch。反馈不由服务端猜测重复提交，首版允许同一轨迹多条反馈并由运营队列处理。智能体工具调用继续按 `run_id + tool_name + 规范化参数` 派生 operation_key，攻防回放按实验臂和固定配置清单去重，重试返回首次保存结果。可变运营草稿通过 revision 防止丢失更新，发布激活通过 expected_active_version 防止重复切换，不把所有写接口误设成按请求内容去重。

## 后续 FastAPI 对齐

后续业务实现按域使用 APIRouter 和 Pydantic v2。`response_model` 与 YAML 的成功/错误 Schema 对齐，OpenAPI operationId、路径、方法、必填字段、枚举、状态码和 security 均纳入契约测试。不能用关闭 FastAPI 校验、添加任意额外字段或改变 HTTP 语义来让测试通过。

预览入口的 `app.openapi()` 只用于展示独立契约；真实业务应用仍由 FastAPI 路由生成其 OpenAPI，再在 CI 与 `docs/api/openapi.yaml` 比较。允许明确登记的扩展字段演进，不允许静默删除、改名或放宽安全边界。

## 验证与完成标准

1. YAML 可由标准解析器读取，通过 OpenAPI 3.1 校验，所有内部引用可解析，operationId 唯一。
2. TestClient 验证 `/docs`、`/openapi.json`、`/openapi.yaml` 可访问，返回的 JSON 与 YAML 等价，且没有业务路由或数据库连接。
3. 静态检查逐项覆盖本设计“完整接口清单”，验证方法、路径、权限、同步状态码和主要错误响应。
4. 契约测试覆盖 fast/enhanced、批量上传、规则三段发布、乐观并发、feedback、E3–E5、匿名会话和 content_ref 确认。
5. 检查所有请求/响应示例符合对应 Schema，不存在模型写风险分或任意 trace 越权读取的字段。
6. README 的命令在本项目环境实际验证；报告只验证契约和文档入口，不宣称业务接口已实现。

## 留给实现计划的决定

- YAML 的具体组件拆分方式、operationId 命名和示例文本。
- 采用哪个 OpenAPI 3.1 校验库及契约 diff 工具，以当前 Python 依赖兼容为准。
- 非关键列表的默认 page_size 和具体上限；需要在 Schema 中固定。
- 后续真实实现的模块文件名；本设计只约束 docs/api 预览入口和测试边界。

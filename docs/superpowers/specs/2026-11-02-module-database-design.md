# 分模块数据库表与 DDL 设计

## 目的

把 `技术方案.md` 从“列出核心表和少量字段”推进到可按模块实现的数据设计：每个业务模块说明自己写入、读取和维护的表，给出对应 PostgreSQL DDL、字段约束、外键和索引；模块之间只通过明确的表与服务边界关联。

本轮只修订 Markdown 技术方案，不创建实际数据库、 migration 或产品代码，不宣称 SQL 已在 PostgreSQL 实例执行。

## 已选方式

采用**方案 B：表设计分散到 M1–M9**。

- M1–M6、M9 各自包含“模块—表关系”和本模块 DDL。
- M7 只写全局字段约定、跨模块关系、所有权边界、迁移依赖顺序、索引与不可变策略，不重复各模块 SQL。
- M8 明确不直接访问数据库，只通过 M1 API 读取。
- 每张表只在所属模块定义一次，其他模块引用表名和关系，不复制 DDL。

未采用方案 A（全部集中在 M7），因为用户选择按功能/模块阅读；其集中核对优势由 M7 的跨模块关系与依赖顺序补足。

## 约束与设计原则

1. 以 PostgreSQL 为验收 DDL 标准，使用 `UUID/JSONB/TIMESTAMPTZ/NUMERIC/CHECK/FK`；SQLite 由 SQLAlchemy 类型与 Alembic 迁移适配，不在文档维护第二套 DDL。
2. UUID 由应用生成，不依赖 PostgreSQL 扩展；时间统一保存 UTC。
3. 避免 SQL 关键字和歧义命名：`user → app_user`，`case → fraud_case`；原 `rule` 保留为稳定规则身份表，`rule_version` 保存不可变定义。
4. 审计、判定、已发布配置和实验记录采用追加/软删除策略；外键默认 `ON DELETE RESTRICT`，不因删除会话、用户或配置而抹除历史。
5. JSONB 用于轨迹、DSL、事实和版本化参数；需要筛选、连接、唯一约束或看板聚合的字段必须提升为标量列。
6. `judgment_trace` 不可变；生成解释、反馈、智能体运行和攻防回放均通过外键追加新记录。
7. 所有“当前启用版本”必须能解析到不可变版本记录；判定和回放保存实际版本，不能只保存 `latest`。
8. 模型不能提供数据库主键、角色、操作幂等键或资源所有者；这些值由后端生成。
9. 大字段、密钥与隐私：不存 API Key/JWT/密码明文；密码只存 Argon2 哈希；消息和工具参数按既有脱敏策略保存。

## 模块与表归属

| 模块 | 本模块定义并负责写入的表 | 主要跨模块读取/关联 |
|---|---|---|
| M1 API | `app_user`、`batch_job`、`batch_item` | 调 M2 写 `judgment_trace`；读取知识库与智能体表 |
| M2 判定引擎 | `judgment_trace`、`judgment_rule_hit`、`transform_dict_version`、`transform_dict_entry` | 读取规则、名单、阈值、语义配置及案例检索版本 |
| M3 服务适配 | `retrieval_index`、`case_vector`、`service_circuit_event` | `case_vector` 关联 M4 `fraud_case` |
| M4 知识与解释 | `fraud_type`、`fraud_case`、`explanation_record` | 解释关联 M2 轨迹；案例供 M3/M9 检索 |
| M5 运营管理 | `rule`、`rule_version`、`rule_release`、`rule_release_item`、`rule_conflict`、`list_release`、`list_entry`、`threshold_config`、`semantic_config`、`semantic_config_entry`、`feedback`、`admin_audit_log` | 反馈关联 M2 轨迹；规则草稿审核后生成新版本 |
| M6 攻防平台 | `attack_sample_set`、`attack_sample`、`attack_campaign`、`attack_round`、`experiment_comparison`、`experiment_arm`、`replay_run`、`replay_item`、`blindspot_metric`、`rule_draft` | 回放项关联 M2 轨迹；规则草稿供 M5 审核发布 |
| M7 数据层 | 不新增业务表 | 维护 Alembic、跨模块外键、索引和保留策略 |
| M8 前端 | 无 | 禁止直连数据库 |
| M9 消息智能体 | `agent_session`、`agent_run`、`agent_message`、`agent_content`、`agent_tool_call` | 工具调用关联 M2 轨迹、M9 内容和 M6 活动 |

## 各表必须写清的语义

### M1

- `app_user`：登录主体、Argon2 密码哈希、角色、启用状态；匿名核验不要求创建用户。
- `batch_job`：文件元数据、数量/大小校验、状态与汇总计数；不保存可执行文件路径。
- `batch_item`：条目序号、原始内容、状态、错误码和 `trace_id`；`(batch_id,item_no)` 唯一，逐条结果与汇总可对账。

### M2

- `judgment_trace`：一次判定的不可变记录。包含原文、内容类型、模式、事实/命中/分数/相似案例 JSONB、风险标量字段、模型原始输出、全部配置版本、阶段耗时、降级数组和后端 `operation_key`。
- `operation_key` 唯一；风险等级、总分、`fraud_type` 和创建时间建立看板所需索引。
- `judgment_rule_hit` 与轨迹在同一事务写入，保存 `trace_id/rule_id/rule_release_version/rule_version_id/matched/participates_in_score/suppressed_by/weight/evidence/hit_order`；看板使用该表聚合，不再展开 `hits` JSONB，轨迹仍保留完整证据快照。
- `transform_dict_version`：可激活的不可变词表版本；`transform_dict_entry` 保存模式、替换词、顺序与启用状态，版本内模式唯一。

### M3

- `retrieval_index`：`retriever_version`、BGE 模型名、FAISS 文件位置、校验和、案例数、状态；运行服务只加载已校验版本。
- `case_vector`：检索版本内的 `case_id ↔ faiss_id` 映射，保证 Top-5 能回查案例；不在 PostgreSQL 重复存向量。
- `service_circuit_event`：服务名、状态迁移、失败原因、发生时间；支撑熔断审计，不保存敏感请求正文。

### M4

- `fraud_type`：稳定分类代码、名称、说明和启停状态；规则、案例、语义配置共用同一代码。
- `fraud_case`：标题、正文、非空建议、来源链接、分类、上线状态和内容哈希；分类浏览只统计上线案例。
- `explanation_record`：关联轨迹、视角、内容、模板/LLM 来源、引用校验状态与模型版本；同一轨迹可追加多条，不更新轨迹。

### M5

- `rule` 是稳定身份与启停状态；`rule_version` 是不可变 DSL 版本，包含 `fraud_type/weight/exclusive_group/priority/conditions/explanation`，`(rule_id,version_no)` 唯一。
- `rule_release/rule_release_item` 将一次热更新对应到完整规则集合快照，轨迹中的 `rule_version` 指向 release。
- `rule_conflict` 保存分析对象、两条规则、冲突类型、确定/需人工状态、结构化详情和处理状态。
- `list_release/list_entry` 对黑白名单做版本化；条目保存号码/域名/IP 类型、归一化值、黑/白类型和来源，版本内唯一。
- `threshold_config` 保存版本、低/中/高风险下限、发布状态；CHECK 保证 `0 < low_min < medium_min < high_min <= 100`。
- `semantic_config` 保存版本、语义系数和发布状态；`semantic_config_entry` 保存骗局类型、规范化话术特征键、特征数组与 `[0,100]` 原始语义分，版本内组合唯一。
- `feedback` 保存轨迹、误报/漏报、待处理/已处理、说明与处理人；`admin_audit_log` 追加记录运营变更前后值与操作者。

### M6

- `attack_sample_set` 是不可变样本集版本；`attack_sample` 保存内容、类型、攻击手法、注入类型和 `origin_sample_id`，支持原始—变体配对。
- `attack_campaign/attack_round` 保存活动与编排轮次；轮次不再只绑定一个样本集，而是通过实验对照关联多个实验臂。
- `experiment_comparison` 表示 E3/E4/E5 或单次临时回放；`experiment_arm` 表示 pure/hybrid、original/variant、defense_off/defense_on 等一个对照臂。每个臂独立绑定不可变样本集与 `ExperimentManifest`，比较服务校验除本实验自变量外其余版本一致。
- `replay_run` 必须属于一个实验臂并保存后端 `operation_key`；`replay_item` 关联样本和判定轨迹，保存检出、攻击成功、输出校验失败和 `pair_key`。原始样本的 `pair_key=sample_id`，变体的 `pair_key=origin_sample_id`，`(replay_run_id,pair_key)` 唯一，E4 通过两个臂的相同 `pair_key` 配对复算 ASR。
- `blindspot_metric` 按 `replay_run × fraud_type × attack_method` 保存样本数、检出数和检出率，分子分母可复算。
- `rule_draft` 保存来源样本/回放、建议 DSL、待审核/通过/拒绝状态、审核人和最终发布版本；数据库 CHECK 禁止把草稿状态当作生效规则。

### M9

- `agent_session` 保存匿名凭据哈希或登录用户、状态和过期时间。
- `agent_message` 保存角色、脱敏正文、内容哈希与可选运行关联。
- `agent_content` 实现 `content_ref`：关联会话与来源消息、内容类型、原文、候选 span、待确认/已确认状态；只有已确认内容可核验。
- `agent_run` 保存消息或攻防运行、模型/提示词/工具 Schema 版本、状态、降级和耗时；按 kind 检查 session/campaign 归属。
- `agent_tool_call` 保存脱敏参数、结果引用、可选 `trace_id`、操作键、状态、耗时和错误；会话轨迹所有权通过 `session → run → tool_call → trace` 查询校验。

## 跨模块关系与迁移顺序

M7 增加一张文本关系图，至少覆盖：

```text
rule → rule_version → rule_release_item → rule_release
batch_job → batch_item → judgment_trace → judgment_rule_hit / explanation_record / feedback
fraud_type → fraud_case → case_vector → retrieval_index
attack_campaign → attack_round → experiment_comparison → experiment_arm → replay_run → replay_item → judgment_trace
attack_sample_set → experiment_arm / attack_sample → replay_item（E4 以 pair_key 跨实验臂配对）
agent_session → agent_message / agent_run / agent_content
agent_run → agent_tool_call → judgment_trace
rule_draft → rule_version（人工审核后）
```

DDL 在文档中按模块展示，但实际迁移按依赖执行：基础分类与用户 → 版本化运营配置 → 判定与知识 → 攻防 → 智能体 → 循环外键补充与索引。`rule.current_version_id` 和 `attack_round.agent_run_id` 这类双向引用用后置 `ALTER TABLE` 建外键，不能靠调整模块章节顺序掩盖依赖。

## 每模块固定写法

每个模块遵循同一结构，便于阅读：

1. **表职责与模块读写关系**：列出 Own/Write/Read，明确其他模块不得直接更新。
2. **DDL**：完整 `CREATE TABLE` 与必要 `ALTER TABLE`、`CREATE INDEX`、CHECK 和 UNIQUE。
3. **关系与一致性说明**：只写本模块特有约束，公共命名和审计规则放 M7。

SQL 使用 PostgreSQL 15+ 可解析语法；不用数据库触发器实现业务评分，不把当前配置计算放到数据库，不用物化视图替代原始审计。

## 非目标

- 不实现 ORM、Repository、迁移脚本或种子数据。
- 不新增 Redis、消息队列、向量数据库或独立数据仓库。
- 不改变既有评分、智能体权限、fast/enhanced 与 E3/E4/E5 口径。
- 不承诺当前文档的 DDL 已在真实数据库执行；本轮验证只做静态语法/关系检查和独立评审。

## 完成标准

- M1–M9 每个模块都有表职责或“无表”说明。
- 上述所有表均有 DDL，现有接口与轨迹字段均能落到列或 JSONB 明确位置。
- 每个版本字段、外键、唯一约束、审核状态和智能体 `content_ref` 都有实际表承接。
- M7 不再保留与分模块 DDL 重复的表清单；现有核心表名全部同步为新名称。
- 文档检查脚本和既有回归检查通过，独立评审无未处理的 Critical/Important。

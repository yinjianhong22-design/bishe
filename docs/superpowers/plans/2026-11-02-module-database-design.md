# 分模块数据库表与 DDL 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将已确认的分模块数据设计写入 `技术方案.md`，为 M1–M9 补齐表职责、模块读写关系、PostgreSQL DDL 和跨模块一致性约束。

**Architecture:** 每张表只在所属模块定义一次；M7 仅保留全局约定、关系图与迁移依赖。轨迹与规则命中同事务写入，实验采用 comparison/arm/run/item 层级，智能体内容、运行与工具审计分表保存。

**Tech Stack:** Markdown、PostgreSQL 15+ DDL、Python 静态文档检查、既有 FastAPI/SQLAlchemy/Alembic 约束。

**Spec:** `docs/superpowers/specs/2026-11-02-module-database-design.md`；修订对象为 `技术方案.md`。

## Global Constraints

- 只修改 `技术方案.md` 与本计划检查脚本，不创建真实数据库、ORM、migration 或种子数据。
- 每表只出现一次 `CREATE TABLE`；M8 不定义表，M7 不重复业务 DDL。
- PostgreSQL 15+ 为验收 DDL；UUID 由应用生成，时间为 UTC，SQLite 适配交给 SQLAlchemy/Alembic。
- 使用 `app_user`、`fraud_case`，禁止新建名为 `user`、`case` 的表。
- 审计与判定不可变；版本化配置可复算；所有外键目标必须有表定义。
- 保持评分、智能体裁决边界、fast/enhanced 与 E3/E4/E5 公式不变。
- 当前目录不是 Git 仓库，不安排提交；SQL 只做静态检查，不宣称已在 PostgreSQL 执行。

## Review Focus

- 历史轨迹引用的规则/配置版本不得因运营修改而漂移，由任务 2 检查。
- E4 原始与变体必须能跨实验臂一一配对，由任务 3 检查。
- 消息工具只能通过已确认 `content_ref` 和会话—运行—调用链访问轨迹，由任务 4 检查。
- 批量汇总与逐条结果必须能对账，由任务 1 检查。
- 看板规则命中率必须使用规范化命中表而非展开 JSONB，由任务 1 检查。

---

### Task 1: 建立静态检查并补 M1/M2 数据设计

**Files:**
- Modify: `技术方案.md`（M1、M2、M5 看板查询说明）
- Test: `.superpowers/sdd/2026-11-02-module-database-design/verify_database_design.py`

**Interfaces:**
- Produces: `app_user/batch_job/batch_item/judgment_trace/judgment_rule_hit/transform_dict_version/transform_dict_entry`。
- Produces: `judgment_trace.trace_id/operation_key` 与版本外键，供后续模块引用。

- [ ] **Step 1: 写静态检查并确认 RED**

检查脚本解析 SQL 代码块，核对建表数量、重复定义、括号/分号、外键目标和任务所需表。任务 1 必须包含上述七表、`operation_key` 唯一约束、`judgment_rule_hit` 及批量对账索引；运行预期 FAIL。

- [ ] **Step 2: 写 M1 表关系与 DDL**

在 M1 增加 Own/Write/Read 表和 `app_user/batch_job/batch_item` DDL。批量表包含文件限制、逐条状态/错误/`trace_id`、`(batch_id,item_no)` 唯一约束与汇总计数；匿名核验不强制创建用户。

- [ ] **Step 3: 写 M2 表关系与 DDL**

在 M2 增加轨迹、规范化规则命中和变形词表版本 DDL。轨迹保留 JSONB 详情与看板标量列；`judgment_rule_hit` 与轨迹同事务写入，M5 看板改为聚合该表。词表版本与条目满足热更新和历史复算。

- [ ] **Step 4: 验证任务 1**

运行任务 1 静态检查，预期 PASS；桌面核对批量汇总、轨迹不可变、命中表看板、词表版本引用和外键目标。

---

### Task 2: 补 M3/M4/M5 服务、知识与运营数据设计

**Files:**
- Modify: `技术方案.md`（M3、M4、M5）
- Test: `.superpowers/sdd/2026-11-02-module-database-design/verify_database_design.py`

**Interfaces:**
- Consumes: M2 的 `judgment_trace`。
- Produces: 检索版本/案例映射、分类/案例/解释、完整规则与配置版本、反馈和运营审计表。

- [ ] **Step 1: 扩展检查并确认 RED**

要求 M3 三表、M4 三表和 M5 十二表全部具有唯一定义；阈值递增、语义分范围、版本内唯一、反馈状态和规则发布关系必须有约束。运行预期 FAIL。

- [ ] **Step 2: 写 M3/M4 DDL 与模块关系**

补 `retrieval_index/case_vector/service_circuit_event`、`fraud_type/fraud_case/explanation_record`。案例分类只统计上线数据，解释追加保存并关联不可变轨迹。

- [ ] **Step 3: 写 M5 DDL 与版本发布关系**

补规则身份/版本/发布快照/冲突、名单版本、阈值、语义配置、反馈和运营审计。`rule.current_version_id` 允许后置外键；历史发布项与轨迹引用采用 RESTRICT，当前版本指针不修改旧 release。

- [ ] **Step 4: 验证任务 2**

运行任务 1–2 检查，预期 PASS；核对阈值边界、语义特征组合、黑白名单版本、规则审核和案例—向量映射。

---

### Task 3: 补 M6 攻防实验数据设计

**Files:**
- Modify: `技术方案.md`（M6，含 M6.5 旧字段说明）
- Test: `.superpowers/sdd/2026-11-02-module-database-design/verify_database_design.py`

**Interfaces:**
- Consumes: M2 轨迹、M5 规则版本。
- Produces: `attack_campaign → attack_round → experiment_comparison → experiment_arm → replay_run → replay_item` 和 `pair_key`。

- [ ] **Step 1: 扩展检查并确认 RED**

要求十个 M6 表、实验臂唯一角色、`ExperimentManifest`、`operation_key`、`(replay_run_id,pair_key)` 唯一约束和待审核草稿状态；运行预期 FAIL。

- [ ] **Step 2: 写样本、活动与对照 DDL**

补样本集/样本、活动/轮次、comparison/arm。每个臂独立绑定样本版本和配置清单，E3/E4/E5 只允许既定自变量不同；修正 M6.5 中“每轮单样本版本”的旧关系。

- [ ] **Step 3: 写回放、盲区与草稿 DDL**

补 `replay_run/replay_item/blindspot_metric/rule_draft`。原始与变体通过 `pair_key` 配对，指标保留分子分母，草稿审核通过后才关联 M5 发布版本。

- [ ] **Step 4: 验证任务 3**

运行任务 1–3 检查，预期 PASS；桌面复算 E3 同集双臂、E4 跨集配对、E5 同集防御开关和规则草稿发布链。

---

### Task 4: 补 M9、M7/M8 边界并做全文一致性验证

**Files:**
- Modify: `技术方案.md`（M9、M7、M8、旧表名引用）
- Test: `.superpowers/sdd/2026-11-02-module-database-design/verify_database_design.py`

**Interfaces:**
- Consumes: 前三个任务全部表与外键。
- Produces: `agent_content` 内容确认链、五张智能体表、全局关系图和迁移顺序。

- [ ] **Step 1: 扩展完整检查并确认 RED**

要求五张 M9 表、会话—运行—调用—轨迹链、已确认内容约束、M7 关系图与迁移顺序；检查 M8 无 DDL、所有外键目标存在且所有表只建一次。运行预期 FAIL。

- [ ] **Step 2: 写 M9 表关系与 DDL**

补会话、运行、消息、内容与工具调用表。`agent_content` 只有 confirmed 才能送检；消息/攻击运行归属互斥；工具调用保存操作键和轨迹引用，不接受模型指定所有者。

- [ ] **Step 3: 重写 M7 全局说明并明确 M8 无表**

删除 M7 重复表清单，保留全局类型/命名/不可变/索引/保留策略、跨模块关系图、后置外键和迁移顺序。M8 写明只经 API 访问，不持有数据库连接。

- [ ] **Step 4: 同步旧表名和字段关系**

全文把 `user/case` 表名引用改为 `app_user/fraud_case`，把 M6.5 的 `sample_set_version/replay_result_ref` 单轮关系改为 comparison/arm/run/item，把 M5 看板改为 `judgment_rule_hit` 聚合；不改变需求链接和文字中的“案例”。

- [ ] **Step 5: 最终验证**

运行完整数据库静态检查、既有 `verify_agent_design.py` 和 `verify_revision.py`，三者均须 PASS。报告只完成静态文档验证，未在 PostgreSQL 实例执行。

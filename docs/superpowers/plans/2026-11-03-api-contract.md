# FastAPI 全量接口契约 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 编写覆盖后续 P0/P1/P2 开发的 OpenAPI 3.1 契约，并提供无业务实现的 FastAPI Swagger 文档入口。

**Architecture:** `docs/api/openapi.yaml` 是唯一接口事实源；`viewer.py` 只加载和展示该文件，不注册业务路由。标准库 unittest 配合 OpenAPI 校验器和 FastAPI TestClient 验证契约、权限及预览边界。

**Tech Stack:** OpenAPI 3.1、YAML、FastAPI、Pydantic v2、Swagger UI、Python unittest。

**Spec:** `D:\毕设\docs\superpowers\specs\2026-11-03-api-contract-design.md`

## Global Constraints

- 不实现业务服务、数据库、鉴权逻辑或模型调用；预览禁用 Try it out 提交。
- 同步接口正常完成使用 200，不用 202 冒充完成；批量 ≤2MB、≤1000 条。
- 统一 `{code,data,degraded[],trace_id}` 和 `{code,message,details,degraded[],trace_id}`。
- 规则必须草稿 → 不可变版本 → 完整 release → 激活；匿名轨迹由 `X-Trace-Token` 保护。
- OpenAPI 3.1 不使用 `nullable`；路径、方法、operationId、权限、枚举和错误响应须可静态检查。
- 当前目录不是 Git 仓库，不初始化 Git、不提交；每个任务运行新鲜测试并写台账。

## Review Focus

- 空字符串、额外字段和非法枚举不能因宽松 Schema 被当成有效输入。
- trace/batch/session capability 不能由 URL 参数或模型正文代替，且不能跨资源使用。
- 单臂 replay 不能替代 E3–E5 comparison，失败样本不能按未检出统计。
- 预览缺文件、非法 YAML 和悬空 `$ref` 必须启动失败而非展示空文档。
- 示例必须符合对应 Schema，不能泄露真实密钥或暗示模型可写风险分。

---

### Task 1: 公共契约、核验、知识库与规则发布

**Files:**
- Create: `docs/api/openapi.yaml`
- Create: `tests/api/test_openapi_contract.py`
- Create: `docs/api/requirements.txt`
- Test: `tests/api/test_openapi_contract.py`

**Interfaces:**
- Consumes: 规格的公共约定、认证/核验/知识/规则/名单/配置/反馈/看板接口清单。
- Produces: `openapi: 3.1.0`、`components.schemas`、公共安全方案及所有基础业务 paths，供 Task 2 扩展。

- [ ] **Step 1: 准备隔离测试环境并写 RED 契约检查**

在 `.superpowers/sdd/2026-11-03-api-contract/.venv` 安装文档依赖；requirements 固定 FastAPI、Uvicorn、PyYAML、httpx、openapi-spec-validator 的兼容版本。unittest 读取 `docs/api/openapi.yaml`，断言 OpenAPI 3.1、校验器通过、内部 `$ref` 和 operationId 有效，并逐项断言 Task 1 的方法/路径、`trace_token`、规则三段发布、乐观并发、上传限制和统一错误结构。

- [ ] **Step 2: 运行检查确认 RED**

Run: `.superpowers/sdd/2026-11-03-api-contract/.venv/Scripts/python.exe -m unittest tests.api.test_openapi_contract -v`
Expected: FAIL，因为 `docs/api/openapi.yaml` 不存在。

- [ ] **Step 3: 编写公共 Schema 与 Task 1 API**

在 YAML 中实现公共响应、错误、降级、分页、风险轨迹、证据与配置版本 Schema；定义 bearerAuth、traceToken、batchToken、agentSessionToken。补齐 Task 1 接口及可校验示例，显式定义必填字段、枚举、范围和 `additionalProperties: false`。

- [ ] **Step 4: 验证 GREEN 与负例**

Run Step 2 命令，并增加临时无效文档校验测试，确认宽松输入、悬空引用和重复 operationId 会被检查捕获。
Expected: 全部 unittest PASS。

### Task 2: 攻防对照、消息智能体与完整覆盖

**Files:**
- Modify: `docs/api/openapi.yaml`
- Modify: `tests/api/test_openapi_contract.py`
- Test: `tests/api/test_openapi_contract.py`

**Interfaces:**
- Consumes: Task 1 的公共 Schema、安全方案与响应包装。
- Produces: 覆盖规格“完整接口清单”的最终业务 paths，包括 comparison、同步 replay 和 content_ref 确认。

- [ ] **Step 1: 增加 RED 覆盖与安全断言**

逐项列出规格剩余 Attack/Agent 路径；断言 E3–E5 comparison 的多臂 ExperimentManifest、pair_key、失败计数、accepted/approved、匿名会话凭据和 content_ref 确认。增加测试确保普通 replay 不能冒充 E3–E5、agent 请求没有 owner/risk_score/operation_key。

- [ ] **Step 2: 运行新增检查确认 RED**

Run: `.superpowers/sdd/2026-11-03-api-contract/.venv/Scripts/python.exe -m unittest tests.api.test_openapi_contract -v`
Expected: FAIL，指出缺失的攻防和消息接口。

- [ ] **Step 3: 完成 Attack/Agent 契约**

实现样本集生成与冻结、单臂 ad_hoc 回放、完整对照、盲区、建议审核、活动以及消息会话接口。复用统一错误/降级/权限 Schema，明确同步超时详情和不可变配置快照。

- [ ] **Step 4: 全量契约 GREEN**

Run Step 2 命令。
Expected: PASS，覆盖规格全部方法/路径，标准校验器和示例检查通过。

### Task 3: 最小 FastAPI 入口、预览测试与启动说明

**Files:**
- Create: `docs/api/viewer.py`
- Create: `docs/api/README.md`
- Create: `tests/api/test_viewer.py`
- Test: `tests/api/test_viewer.py`

**Interfaces:**
- Consumes: Task 2 的最终 `openapi.yaml`。
- Produces: `viewer.app` FastAPI 实例、`load_document(path: Path) -> dict`；`/docs`、`/openapi.json`、`/openapi.yaml`。

- [ ] **Step 1: 写 RED 预览测试**

TestClient 断言三个端点可访问，JSON 与 YAML 等价，Swagger 配置禁用提交；应用 routes 不包含 `/api/verify`。临时目录中的缺失文件、坏 YAML、重复 operationId、悬空 `$ref` 和非 3.1 文档均应抛出明确错误。

- [ ] **Step 2: 运行预览测试确认 RED**

Run: `.superpowers/sdd/2026-11-03-api-contract/.venv/Scripts/python.exe -m unittest tests.api.test_viewer -v`
Expected: FAIL，因为 viewer 模块不存在。

- [ ] **Step 3: 实现最小 viewer 与 README**

viewer 启动时读取并校验 YAML，覆盖 `app.openapi()`，仅注册 JSON/YAML 文档资源，FastAPI 自带 `/docs` 使用禁用提交的 Swagger 参数。README 写明依赖安装、uvicorn 启动、查看地址、无业务实现边界和后续契约 diff 方式。

- [ ] **Step 4: 运行完整验证**

Run: `.superpowers/sdd/2026-11-03-api-contract/.venv/Scripts/python.exe -m unittest discover -s tests/api -v`
Expected: 所有测试 PASS；随后用 TestClient 请求确认 docs/json/yaml 状态码，运行既有三个技术方案静态检查确认无回归。

- [ ] **Step 5: 最终独立评审与台账**

评审完整契约和入口，不审 Git diff；Important/Critical 以 RED→GREEN 修复，Minor 记录台账。报告只证明契约和文档入口已验证，不宣称业务 API 已实现。

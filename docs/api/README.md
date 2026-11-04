# 反诈系统 API 文档预览

`openapi.yaml` 是后续业务开发的唯一接口契约，覆盖 P0/P1/P2 的核验、知识库、规则运营、攻防和消息智能体接口。`viewer.py` 只负责展示它，不包含业务实现。

## 启动

在项目根目录执行：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r docs/api/requirements.txt
.\.venv\Scripts\python.exe -m uvicorn viewer:app --app-dir docs/api --port 8000
```

打开：

- Swagger UI：<http://127.0.0.1:8000/docs>
- OpenAPI JSON：<http://127.0.0.1:8000/openapi.json>
- OpenAPI YAML：<http://127.0.0.1:8000/openapi.yaml>

预览禁用 Try it out 的提交按钮。这里没有数据库、JWT 签发、规则引擎、模型或业务路由，不能用它验证真实核验结果。

## 安全约定

- 匿名核验返回一次 `trace_token`；轨迹回放和解释使用 `X-Trace-Token`。
- 批量结果查询使用 `X-Batch-Token`；超时响应同时给出 `batch_id` 和凭据。
- 匿名消息会话使用 `X-Agent-Session-Token`，运营接口使用 Bearer JWT。
- 令牌只作为请求头传递，不放在 URL 中。服务端只保存令牌哈希。
- 请求模型不允许传入风险分、资源所有者或服务端操作键。

## 后续实现对齐

真实 FastAPI 应用按域使用 `APIRouter + Depends`，由路由和 Pydantic v2 模型生成自己的 OpenAPI。CI 应比较真实应用的 OpenAPI 与这里的 YAML，至少检查路径、方法、operationId、必填字段、枚举、状态码和 security；不得为了绕过契约而关闭请求校验。

`docs/api` 不存放第二份手写接口清单。修改接口时先更新 YAML 和契约测试，再修改实现。

## 验证

本项目的测试环境使用标准库 `unittest`：

```powershell
python -m unittest discover -s tests/api -v
```

测试覆盖 OpenAPI 3.1 标准校验、内部引用、operationId、业务路径、权限、同步语义、攻防对照、消息正文确认和预览入口。它们验证契约与文档工具，不代表业务 API 已实现。

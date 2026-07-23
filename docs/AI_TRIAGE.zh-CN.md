# 任务 13:失败用例顾问式归类(Advisory Failure Triage)

## 目的

任务 13 用于缩短回归用例失败到第一次有效调试动作之间的时间。重试耗尽后，
它仅将 pytest 中**最终**失败阶段分类为 `Locator`、`App Bug`、`Env`、`Script`、
`Data` 或 `Unknown` 之一,然后在终端和 Allure 中展示相同的顾问式结果。

它不是用例生成器,也不是自动修复系统。移动端用例由
`pytest-rerunfailures` 负责执行 1 次并最多重试 2 次,最终一次决定
PASS/FAIL;unit tests 不重试。归因引擎**从不**改变 pytest 结果、修改
locator、隐藏 traceback,或自动提交缺陷。**通过的用例不会触发归类**。

## 运行流程

```text
setup/call/teardown 失败(attempt 1 或 2)
          |
          v
采集带 attempt 编号的截图 + Appium page source
          |
          +-- 仍有重试 --> 保存重试历史并再次执行
          |
          v
最终失败(attempt 3)
          |
          v
捕获原始异常 + 受限 traceback + 失败 BDD 步骤
          |
          v
确定性本地特征匹配
          |
          +-- 置信度 >= 0.70 --> 本地判定
          |
          +-- 置信度 < 0.70
                    |
                    +-- LLM 关闭/配置缺失 --> disabled Unknown
                    |
                    +-- LLM 开启 --> 一次受限的 MiniMax/Anthropic 请求
                                              |
                                              +-- 合法 JSON --> llm 判定
                                              +-- 错误/非法 JSON --> 安全回退 Unknown
          |
          v
终端打印一行 + Allure "AI Triage" JSON 附件
          |
          v
原始 pytest PASSED/FAILED 状态保持不变
```

严格顺序是 `失败 -> 重试历史 -> 最终失败 -> 本地规则 -> 可选 LLM`。
每次 BDD 失败都保留唯一命名的 PNG/XML 证据。最终失败阶段会写入 pytest
item 的 stash,避免重复诊断。只有截图的**是否可用**与**基础文件名**可以
进入 LLM 提示词;图像字节、page source 和绝对路径**永远不**会上传。LLM
请求本身也不会重试。

## 用户看到的内容

终端只会收到一行简洁输出:

```text
[AI Triage] Locator (92%): Matched local failure signature 'selector_specific_missing'.
```

Allure 用例中包含一份 `AI Triage` JSON 附件,字段如下:

| 字段 | 含义 |
|---|---|
| `test_name`、`phase` | 失败的用例以及 `setup`、`call` 或 `teardown` 阶段 |
| `attempt`、`max_attempts`、`failed_step` | 重试耗尽时的次数与失败 BDD 动作 |
| `category`、`confidence` | 顾问式分类结果与受限置信度 |
| `reasoning`、`next_action` | 分类理由与下一步调试动作 |
| `classifier` | `local`、`llm` 或 `disabled` |
| `matched_signatures` | 确定性特征 ID;LLM/disabled 结果下为空 |

| Classifier | 含义 | 建议动作 |
|---|---|---|
| `local` | 高置信度的确定性特征命中;未发生 API 调用 | 按报告的 action 操作,并查看原始证据 |
| `llm` | 本地信号模糊,已尝试调用一个已配置的兼容 API | 结合 traceback/截图一起评估模型建议 |
| `disabled` | 信号模糊,但 opt-in 开关、key 或 model 缺失 | 配置 fallback 或改为人工归类 |

## 典型回归示例

| 失败证据 | 大概率结果 | 价值 |
|---|---|---|
| setup 阶段 Appium 连接被拒 | `Env / local` | 把排查方向引导到服务器/设备配置 |
| 缺失元素同时带有明确 selector 策略 | `Locator / local` | 指向 YAML locator 与当前页面 source |
| 动作后目标页元素缺失,但没有 selector 证据 | 可选 LLM 或 `Unknown / disabled` | 避免把下游状态症状直接判为 locator 缺陷 |
| 月度汇总期望值与展示值不一致 | 当具备业务上下文时为 `App Bug / local` | 提示对比需求并手动复现 |
| Flow 或 Page 中出现 `TypeError` | `Script / local` | 把排查方向引导到自动化实现 |
| 不带上下文的裸 `AssertionError` | 启用 LLM 时为 `llm`,否则为 `disabled` | 仅在证据模糊时才使用兼容模型 |

## 安全的 MiniMax 配置

复制仓库里已经提交的占位文件,真实配置仅保留在本地:

```bash
cp .env.example .env
chmod 600 .env
```

在 `.env` 中配置,不要提交该文件:

```bash
AI_TRIAGE_LLM_ENABLED=1
ANTHROPIC_BASE_URL=https://api.minimaxi.com/anthropic
ANTHROPIC_API_KEY=<local-secret>
ANTHROPIC_MODEL=MiniMax-M3
SSL_CERT_FILE=/etc/ssl/cert.pem
```

只有当本地 Python 环境报告 TLS 证书校验失败,并且该 CA bundle 存在时,
才需要 `SSL_CERT_FILE`。**任何情况下都不得关闭证书校验**。

项目不会自动加载 `.env`,每次新开终端都需要手动加载:

```bash
set -a
source .env
set +a
```

检查配置(不要打印密钥):

```bash
.venv/bin/python - <<'PY'
import os

print({
    "enabled": os.getenv("AI_TRIAGE_LLM_ENABLED"),
    "base_url": os.getenv("ANTHROPIC_BASE_URL"),
    "api_key_configured": bool(os.getenv("ANTHROPIC_API_KEY")),
    "model": os.getenv("ANTHROPIC_MODEL"),
    "ssl_cert_file": os.getenv("SSL_CERT_FILE"),
})
PY
```

## 验证

聚焦调试时使用 `--reruns 0` 关闭重试:

```bash
.venv/bin/pytest -m "not unit" -k "add_expense_happy_path" --reruns 0 -s -vv
```

运行完整的、不依赖设备的 Task 13 回归:

```bash
.venv/bin/pytest -m unit tests/unit/test_triage.py -q
```

验证本地、零网络的判定路径:

```bash
.venv/bin/python - <<'PY'
from dataclasses import asdict
from pprint import pprint
from ai.triage import triage_failure

pprint(asdict(triage_failure({
    "error_msg": "NoSuchElementException: Unable to locate element",
    "traceback": "",
    "test_name": "local_probe",
    "phase": "call",
})))
PY
```

预期证据包含 `category=Locator`、`classifier=local`、置信度 `0.98`,
以及签名 `element_missing`。

使用故意模糊的输入验证兼容 LLM 实时回退:

```bash
.venv/bin/python - <<'PY'
from dataclasses import asdict
from pprint import pprint
from ai.triage import triage_failure

pprint(asdict(triage_failure({
    "error_msg": "AssertionError",
    "traceback": "",
    "test_name": "live_probe",
    "phase": "call",
})))
PY
```

`classifier=llm` 表示确实尝试了网络回退。模型返回合法时,会得到受
限的 reasoning/action。模型输出不符合严格格式时,仍返回
`llm / Unknown / 0.0`,且永远不会改变测试结果。

针对一次真实的移动回归,先加载 `.env`,然后正常执行 pytest 或设备
矩阵,最后用 `allure open` 打开失败的 Allure 用例,结合原始 traceback
和截图一起查看 `AI Triage` 附件。

## 故障排查

| 现象 | 原因 | 动作 |
|---|---|---|
| `classifier=disabled` | 开关未设置为 `1`,未 source `.env`,或 key/model 缺失 | 加载 `.env` 并重新执行安全配置检查 |
| `HTTP 401` | API key 无效/未加载 | 重新生成本地 key 并 source `.env`;不要打印它 |
| `HTTP 429` | 配额或限流 | 检查 provider 配额;不要在测试报告里加自动重试 |
| TLS 校验失败 | Python 的 CA bundle 缺失 | 设置合法的 `SSL_CERT_FILE`;**不要**关闭校验 |
| 连接/超时 | 端点、DNS、代理或网络问题 | 检查 Base URL 与网络链路 |
| 返回非法响应 | 模型输出不满足严格 JSON 契约 | 保持 `Unknown`,查看原始失败,先统计频次再调整策略 |

## 隐私与可靠性边界

- 错误信息最长 2,000 字符,traceback 最长 12,000 字符。
- 授权头、key、token 与 URL query 会被脱敏。
- 异常文本视为不可信的 prompt 数据。
- 仅允许发起一次 LLM 请求,无重试,总超时 5 秒。
- Unknown/网络/模型异常永远不能替代原始 pytest 失败。
- 模型建议只是调试假设,不是确认后的根因。

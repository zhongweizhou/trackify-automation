# 架构设计

## 目标

本框架用于自动化 Trackify 价值最高的 Android 业务路径,同时把 UI 操作
与业务断言隔离开来。设计围绕以下目标展开:

- 可读的 BDD 场景;
- 确定性的首次运行状态;
- 可复用的 Android/iOS locator 定义;
- 有价值的失败证据;
- 小而可评审的模块。

它不追求覆盖整个 App,不提供视觉对比测试,也不会用重试机制掩盖环境
失败。

## 分层

```text
Gherkin feature
    -> pytest-bdd step definition
        -> Flow(业务状态与断言)
            -> Page Object(UI 交互)
                -> Appium WebDriver
                    -> Trackify
```

依赖方向是单向的:

- Steps 把场景文本翻译成 Flow 调用。
- Flow 组合 Page,持有事务相关期望。
- Page 解析 YAML locator 并与 Appium 交互。
- `BasePage` 提供共享的等待、点击、滑动、截图、权限处理能力。
- Page 之间不互相引用,Flow 也不直接访问 driver。

这让 Gherkin 在 locator 变化时保持稳定,也让 UI 细节远离业务断言。

## Fixture 生命周期

`conftest.py` 拥有 Appium 会话与依赖图。一次 pytest 运行共享同一个
driver 会话。每个场景开始前,autouse fixture 会清空 Trackify 包数据
并重新激活 App。然后场景按以下顺序完成统一的首次运行 onboarding:

1. 输入 `Kimbal`;
2. 选择 `$ US Dollar` 并设置预算 `30000`;
3. 启用 Bank SMS Reader,点击 Get Started。

reset 故意做得“重”但确定性,以避免一个场景的 Hive 数据、自定义类别
或 onboarding 状态影响下一个场景。

## Locator 设计

Locator 位于 `locator/<page>.yaml`,按平台分组。Python 代码通过语义
键(如 `amount_input`、`save_button`)请求;loader 返回对应平台的策略
与值。

推荐优先级如下:

1. accessibility ID;
2. resource ID;
3. 稳定的 class 或平台谓词;
4. 受限的 XPath(仅在 Flutter 不暴露更强语义标识时使用)。

当前构建仍然需要 XPath 处理部分文本输入和合并后的 Flutter 语义节点。
这些选择器都被隔离在 YAML 中,可以独立替换而不影响 Page 或 Flow 行为。

## 同步策略

Page 使用显式等待而不是固定 sleep。针对移动端特有的竞态,补充两条
规则:

- 文本字段在选中下一个控件前必须完成 IME action;
- 一次事务保存成功后必须等到 Home 可见,才允许使用下一个快捷入口。

第二条规则可以避免关闭中的 Add Transaction 页面上的 `Income` 选择
器被误认为是 Home 上的同名快捷入口。

## 业务断言

`AddTransactionFlow` 在保存前捕获类型、金额、类别以及本地日期/时间。
然后场景同时校验对应的 Transactions 行与 Home 月度汇总。

- Expense 增加 expense。
- Income 增加 income。
- Transfer 不改变两个汇总总额。
- Balance 等于 `income - expense`。
- 预算百分比为 `expense / budget * 100`,按 half-up 规则取整。
- 历史事务在其日期分组里被校验,不改变当月汇总。

`TransactionsFlow` 单独校验类型筛选与日期分组。

## 失败证据

pytest report 钩子仅在 call 阶段失败时采集 PNG,并保存在
`report/screenshots/` 下,同一张图片也会附加到 Allure 结果中。截图错误
会以 warning 形式上报,绝不会替换原始测试失败。pytest-bdd 钩子也把
原始的 Feature 与 Scenario 名称暴露给 Allure。

## 顾问式失败归类

任务 13 仅在 pytest 生成原始报告后消费失败证据。它对首个失败阶段
进行分类,打印一行简洁的终端提示,并把同一份结构化结果附加到 Allure。
依赖方向是单向的:

```text
pytest 失败 -> 截图/traceback -> 本地特征 -> 可选 LLM
            -> 终端 + Allure 顾问式结果
```

高置信度的本地特征直接处理环境、locator、数据、应用、脚本这几类
确定性失败,无需网络 I/O。只有证据模糊时才允许使用显式开启的
MiniMax/Anthropic 兼容回退。报告错误会降级为 `Unknown`,它们无法
改变测试结果或原始证据。这让失败归类保持有用,又不会让概率性的建议
变成自动修复机制。

运行时语义、安全配置、验证与故障排查见 [AI_TRIAGE.md](AI_TRIAGE.md)。

## CI 边界

仓库不提交 Trackify APK。因此 CI 显式分为两个层级:

- 每次 push 与 PR 都安装依赖并收集所有场景;
- 只有当 `TRACKIFY_APK_URL` 提供可下载 APK 时,才运行 Android E2E。

E2E 任务会启动一台 API 34 模拟器和 Appium,执行与本地开发相同的
pytest 命令,并上传原始的 Allure 结果、截图和 Appium 日志。当 APK
secret 缺失时,CI 会把 E2E 任务显式标记为跳过,而不是声称已完成
移动端覆盖。

## 跨平台扩展

driver 配置与 locator YAML 已经接受 `android` 与 `ios`。把套件扩展到
iOS 只需要校验过的 XCUITest locator 以及 picker/back 导航行为,不需
要新增 Gherkin 场景或 Flow 逻辑。

实现契约见 [TECHNICAL_SPEC.md](TECHNICAL_SPEC.md),范围选择见
[Feature_Inventory.md](Feature_Inventory.md)。
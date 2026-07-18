# 项目复盘

## 成果

当前项目已经不再是一组彼此独立的 UI 脚本，而是具备小型移动测试平台的
基本能力：

| 领域 | 已交付能力 |
|---|---|
| 业务覆盖 | Add Transaction 与 Transactions 共 7 个 BDD 场景 |
| 平台 | Android/iOS 共用业务 Flow，定位器由各平台独立维护 |
| 环境 | 通过 CLI 严格选择 `test`、`preprod`、`prod` onboarding profile |
| 分发 | 在全部已发现设备上全量复制，或按互斥子集分片 |
| 活用例库 | Excel 用例库校验、增量同步及 Feature 事务性更新 |
| 诊断 | 截图、日志、JUnit、Allure 与 Task 13 建议式失败归因 |
| 结果归属 | 每个 worker/用例记录环境、App 版本、设备、系统版本和 UDID |

当前隔离验证共有 107 个测试通过，三个环境参数都会收集完全相同的 7 个 BDD
场景。真实执行覆盖 Android 17 和 iOS 26.5 的 iPhone 17 模拟器，两端构建均
识别为 App `1.1.0`。`test` 矩阵在两个平台验证了环境化 onboarding；聚焦的
`preprod` Android 与 `prod` iOS happy path 均执行通过。

仓库目前故意保留了一条不健康演示数据：Income 场景输入 `5002`，但期望
`5001.0`。它用于证明变化用例健康门禁能在两个平台返回可归属的失败。不能把
它描述成框架回归，也不能声称当前提交中的完整 smoke 集合全部为绿色。

## 做得好的地方

### 清晰的分层归属

Gherkin、Step、Flow、Page 与 Locator YAML 的分离让失败可以收敛到单一层。
例如键盘交互变化只影响一个 Page 方法，而不是所有场景。交易汇总计算仍属于
Flow，不会泄漏到定位器或 Gherkin 中。

同样的归属纪律也扩展到数据层：Excel 与受管 Feature 块负责场景动作和预期；
`data/environments/` 只负责共享且不含密钥的 onboarding 值；Locator YAML
只负责 UI 定位。这样不会把一个 Excel 表格逐步变成无类型的万能配置库。

### 确定性且可按环境切换的 Setup

每条场景前清理应用存储会增加耗时，但使 onboarding、自定义类别和汇总基线
可重复。`--env` 优先于 `TEST_ENV`，后者优先于默认 `preprod`；不支持的名称
或错误 YAML schema 会在 Appium 启动前失败。Page Object 不感知环境名称，
Flow 负责验证选中姓名、币种符号和 SMS Reader 状态。

### 多设备执行与明确的资源隔离

矩阵运行器会发现 Android 模拟器/设备、iOS 模拟器和已配对 iOS 设备，并为
每个目标启动一个 pytest worker。`replicate` 用于在每台设备验证兼容性，
`split` 则把每条选中用例只分配一次，以缩短整套反馈时间。

每个 worker 都有独立的 Android `systemPort`、iOS WDA/MJPEG 端口、
derived-data 路径、日志、截图、JUnit 和 Allure 目录。这解决了常见并发会话
冲突，也保证失败能归属到具体设备。

### 报告能够识别被测构建

只记录环境不足以形成测试证据。运行时依次从显式覆盖、Appium capability、
Android 已安装包元数据或 iOS bundle 元数据解析 App 版本。每条 Allure 用例
和每个 worker properties 文件都在平台、设备、系统版本、UDID 旁记录 App
版本。矩阵聚合会保留每台设备的独立版本，而不是虚构一个公共构建身份。

### 活文档自动化具有明确边界

Task 14 会校验完整 Excel 用例库，只更新受管 Scenario 块，保持未变化块字节
一致，并在 collection 失败时回滚 Feature 写入。`run_changed_matrix.sh` 先做
预检，再应用新增/修改用例并复制到选中设备执行，最后返回机器可理解的健康
状态。

同步引擎刻意止步于可执行 Gherkin：它不会猜测 Step、Flow、Page 或 Locator
代码，也不会把结果写回 Excel。这些边界使自动生成的变化仍可评审。

### 原始失败证据始终优先

Allure 保留原始 BDD Feature 和 Scenario 名称。call 阶段失败会附加截图，但
不会替换原始 traceback。Task 13 只增加一条建议式分类与下一步动作：优先使用
确定性本地签名，仅在显式开启后才让 LLM 处理歧义证据。AI 输出不会改变
pass/fail、自动重试或宣称自己已经确认根因。

## 比预期更困难的部分

### Flutter accessibility semantics 与键盘状态

部分控件有稳定 accessibility ID，另一些控件会合并成大型 semantics 节点，
或只暴露位置相关的文本输入框，因此仍需要受限 XPath fallback。Setup 和
交易表单也都会受到键盘状态影响；完成 IME action 比点击任意屏幕坐标可靠。

### 页面过渡与横向控件

自定义类别入口位于横向列表末端，需要受控滑动、创建流程、Back 导航和 chip
选择。保存后必须等待 Home 可见，才能查找下一个同名快捷入口，否则可能误匹配
仍在关闭中的表单控件。

### 设备并发不能消除基础设施状态

唯一端口能避免确定性冲突，但 WebDriverAgent 仍有自己的生命周期。最终验证
期间，一次 iOS session 在上一轮矩阵刚结束后立即启动，setup 阶段出现
`ECONNREFUSED 127.0.0.1:8100`；WDA 完全重启后，相同命令执行通过。框架正确
将它报告为 `Env` setup 失败，并把 App 版本标记为 `unresolved`，没有用盲目
重试隐藏问题。后续应该针对这个过渡状态增加明确的 readiness probe。

### 让演示保持诚实

`5002` 与 `5001.0` 的故意不一致很适合失败演示视频，但也意味着普通 smoke
命令会按设计变红。报告和文档必须区分故障注入、产品缺陷与框架回归。对于
可复用项目，更合理的方式是从临时演示数据生成不一致，而不是让默认用例库
长期处于不健康状态。

## 当前限制

- 每个 worker 内部仍是串行执行；矩阵提供设备级并发，不会在一台设备开启
  多个 Appium session。
- 完整应用重置比定向状态 fixture 更慢。
- 已提交的 Income 演示不一致会阻止完整 smoke 矩阵变绿，除非重新对齐输入与
  预期。
- iOS 只在 iOS 26.5 的 iPhone 17 模拟器完成验证；更多屏幕尺寸、locale 和
  真机签名路径仍需要证据。
- 当前 `prod` 只修改本地应用存储；该 profile 不代表允许对未来共享生产后端
  执行破坏性测试。
- Task 14 仍是单向同步，不生成实现代码，也不会自愈 Locator。
- Task 13 仍是建议式能力；在调整置信度阈值前，需要更多真实失败样本验证
  opt-in 模型 fallback。
- GitHub 托管的 E2E 仍依赖外部提供的应用构建产物。

## AI 辅助

AI 帮助把需求转成明确的归属规则、生成测试与文档草稿、检查 Appium 证据并
缩短调试循环。真正有价值的部分不是更快接受生成代码，而是把每个建议与实时
页面状态、命令输出和报告产物进行比较。

两个扩展任务都体现了这一边界：同步引擎只生成确定性的受管文本，并通过
pytest collection 验证；失败归因把模型输出当作附加假设。环境 profile 和
App 元数据使用严格解析器与平台工具，而不是让模型猜测运行身份。

## 后续改进

1. 将 Income 故意不一致移动到临时演示工作簿或故障注入脚本，让提交的默认
   smoke 套件保持绿色。
2. 增加有边界的 WDA readiness/recovery 预检，区分启动过渡与持续的 XCUITest
   配置错误。
3. 推动应用为文本框、日期分组和底部导航提供稳定 semantic ID。
4. 只有在每个环境至少保留一条 clean-install onboarding smoke 后，才引入
   更快的状态 seed。
5. 通过受认证的构建服务发布 Android/iOS 签名产物，让 CI 和本地矩阵使用相同
   App 版本身份。
6. 只有真实共享后端产生新需求时才扩展环境 profile；凭据必须放在 secret
   store，不能进入 profile YAML。
7. 只有多团队并发编辑、权限和审计历史确实需要时，才用测试管理 API 替换
   本地 Excel 用例库。

最重要的经验是：测试平台的价值来自明确边界与可归属证据。一套规模不大、但
能够识别环境、构建、设备、数据来源和失败阶段的测试，比更多浅层 UI 脚本
提供更强的工程信号。

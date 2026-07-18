# Trackify 功能清单 v3(简体中文)

> 基于对 Trackify 实际页面的手动探索(原始草稿见 `Feature_Inventory_01.md`)。
> 设备:Android 14 Emulator(Pixel 8)/ app-release.apk
>
> **重要说明:**
> 1. ✅ **App 在首次运行 onboarding 中包含月度预算配置**;所配置的预算会驱动 Home 上 `This Month` 的进度百分比
> 2. ⭐ 范围被刻意收窄为 **Home + Transactions 两部分**

---

## 1. 已探索的页面(真实观察到)

| # | 页面 | 入口 | 核心交互 | 状态 |
|----|------|------|----------|------|
| 1 | **首次运行 onboarding** | 安装/重置数据后的首次启动 | 输入名字;选择货币;配置月度预算;启用 Bank SMS Reader;Get Started | ✅ 已使用 |
| 2 | **Home** | 默认着陆页 | 月度收入/支出概览 + 预算进度 + 添加交易快捷入口 + 最近 7 天支出可视化 + 最近交易展示 | ✅ 已使用 |
| 3 | **Transactions** | Tab | 列出所有类型的事务(Expense / Income / Transfer);支持按备注搜索 | ✅ 已使用 |
| 4 | **Add Transaction** | Tab | 添加交易:金额 + 类别(或新增类别) + 日期 + 备注 + 标签(逗号分隔) + 照片上传 | ✅ 已使用 |
| 5 | **Analytics** | Tab | 图表(周/月/年)+ 收入/支出统计 + 按类别支出 + 周/月/年概览 | ✅ 已使用 |
| 6 | **Settings** | Tab | 偏好(货币、主题、新增类别) + 通知(每日提醒、提醒时间、测试实时提醒) + SMS 银行读取器 + 备份与恢复 + 安全 + 数据 | ✅ 已使用 |

> ✅ **已确认**:月度预算在首次运行 onboarding 中配置。当前自动化将其设置为 `30000`,并把 Home 上的百分比验证为 `expense / budget × 100`,四舍五入为整数。预算以“共享 setup + 下游断言”的形式覆盖,而不是独立的预算管理旅程。

---

## 2. 决策:选择哪 2 个核心功能进行测试

### ✅ 选择 1:Home → 添加交易快捷入口

**为什么选择它**:
- 🎯 **最高频的用户路径** — 任何个人记账 App 的核心
- 🔬 **风险高** — 是所有下游数据的主要来源
- 📊 **可测的业务点很多** — 添加 Expense / Income / Transfer 交易;交易金额;类别/新增自定义类别;备注;标签;交易时间戳;附件上传
- 🔧 **跨页面依赖** — 同时驱动 Transactions 页面和 Home / Analytics 汇总
- ⚡ **可自动化** — UI 元素相对稳定

**要测试的子功能**:

| 子功能 | 优先级 | 可自动化 |
|-------------|----------|----------|
| 添加 **Expense** 交易,字段:金额 + 类别(必填,如 Food) + 备注("breakfast with Dinna") + 标签("food,dinna") + 日期 + 照片附件 | P0 | ✅ |
| 添加 **Income** 交易,字段:金额 + 类别(必填,如 Salary) + 备注("fulltime salary") + 标签("fulltime salary") + 日期 + 照片附件 | P0 | ✅ |
| 添加 **Transfer** 交易,字段:金额 + 类别(必填,如 Others) + 备注("transfer amount from main account into sub account") + 标签("transfer") + 日期 + 照片附件 | P0 | ✅ |
| 在 Add Transaction 流程中**内联新增自定义类别** | P1 | ✅ |
| 在 Expense 交易中**使用这个新自定义类别** | P0 | ✅ |

### ✅ 选择 2:Transactions

**为什么选择它**:
- 🔬 **验证面广** — 一旦交易通过 Home 快捷入口添加,Transactions 页面必须正确显示它们。这是对 Add Transaction 流程数据落库的下游校验。

**要测试的子功能**:

| 子功能 | 优先级 | 可自动化 |
|-------------|----------|----------|
| 按类型筛选交易(All / Expense / Income / Transfer) | P0 | ✅ |
| 交易列表**按日期汇总**(每个日期一组) | P0 | ✅ |

### ❌ 未选择(及原因)

| 功能 | 原因 |
|---------|--------|
| Analytics / 图表 | 重视觉;断言 ROI 低;DOM 结构不稳定 |
| Settings | 配置导向;业务规则深度有限 |
| 作为独立旅程的预算配置 | 已在首次运行 setup 与 Home 汇总断言中覆盖;未单独选择 Budget Management 场景 |

---

## 3. 自动化覆盖矩阵

| 核心功能 | P0 用例 | P1 用例 | 合计 |
|--------------|----------|----------|-------|
| Home → 添加交易快捷入口 | 4 | 1 | **5** |
| Transactions | 2 | 0 | **2** |
| **合计** | **6** | **1** | **7** |

> 范围被刻意收窄。任务说明要求“深度优先而非广度”——7 个聚焦于最高价值路径的 Gherkin 用例已经足够。

---

## 4. 自动化策略(简要,用于 README)

### 1. 框架选型

- **pytest-bdd** — Gherkin `.feature` 文件 + pytest steps
- **Appium 3 + uiautomator2** — Android 模拟器/设备驱动
- **Page Object** — Page 层负责元素;Flow 层负责业务

### 2. AI 触点

- 使用 **ChatGPT / Claude / Codex** 起草初始 Gherkin 用例 → 人工评审
- 使用 **Appium Inspector** 截图 → 由 AI 建议 Locator
- **第 3 天** 实现 AI Failure Triage(失败日志 → 根因分类)

### 3. 数据重置策略

- `adb shell pm clear <packageName>` → 清空 Hive DB
- **冒烟 / CRUD 测试之前**:清空一次
- **持久化 / 数据校验测试之前**:**不要**清空 —— 只杀进程 / 重启模拟器

---

## 5. 第 2 天 TODO

1. 基于 §3 覆盖矩阵,编写 **2 个 Gherkin `.feature` 文件**:
   - `add_transaction.feature`(5 个用例)
   - `transactions.feature`(2 个用例)
2. 使用 Appium Inspector 抓取 Locator:
   - Home 页 Add Expense / Income / Transfer 入口
   - Add Transaction 屏幕
   - Transactions 页面(筛选 + 列表分组)
3. 实现 `page/add_transaction.py`、`page/home.py`、`page/transactions.py`
4. 让第一个端到端用例跑起来

---

## 附录:Trackify 其他能力 / 限制

- ✅ 首次运行 onboarding 中包含月度预算配置
- ✅ Home 的 `This Month` 按 expense 与预算之比显示进度
- ⚠️ 未将独立的 onboarding 后 Budget Management 流程选为核心自动化功能
- ❌ 无云同步(100% 离线 / 仅 Hive)
- ❌ 无多币种换算(仅显示货币)
- ✅ 包含:SMS 银行读取器(未来可能的集成?)
- ✅ 包含:备份与恢复(可能为 JSON 导出 / 导入)
- ✅ 包含:安全(PIN / 生物识别 — TBD)

---

*本 `Feature_Inventory.md` 是测试范围的唯一事实来源。`Feature_Inventory_01.md`
保留作为第 1 天的原始探索草稿。*
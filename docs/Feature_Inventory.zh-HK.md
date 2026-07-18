# Trackify 功能清單 v3(繁體中文)

> 基於對 Trackify 實際頁面的手動探索(原始草稿見 `Feature_Inventory_01.md`)。
> 裝置:Android 14 Emulator(Pixel 8)/ app-release.apk
>
> **重要說明:**
> 1. ✅ **App 在首次執行 onboarding 中包含月度預算設定**;所設定的預算會驅動 Home 上 `This Month` 的進度百分比
> 2. ⭐ 範圍刻意收斂為 **Home + Transactions 兩部分**

---

## 1. 已探索的頁面(實際觀察)

| # | 頁面 | 入口 | 核心互動 | 狀態 |
|----|------|------|----------|------|
| 1 | **首次執行 onboarding** | 安裝/重置資料後的首次啟動 | 輸入名字;選擇貨幣;設定月度預算;啟用 Bank SMS Reader;Get Started | ✅ 已使用 |
| 2 | **Home** | 預設登陸頁 | 月度收入/支出概覽 + 預算進度 + 新增交易捷徑入口 + 最近 7 天支出可視化 + 最近交易顯示 | ✅ 已使用 |
| 3 | **Transactions** | Tab | 列出所有類型的交易(Expense / Income / Transfer);支援依備註搜尋 | ✅ 已使用 |
| 4 | **Add Transaction** | Tab | 新增交易:金額 + 類別(或新增類別) + 日期 + 備註 + 標籤(逗號分隔) + 照片上傳 | ✅ 已使用 |
| 5 | **Analytics** | Tab | 圖表(週/月/年)+ 收入/支出統計 + 按類別支出 + 週/月/年概覽 | ✅ 已使用 |
| 6 | **Settings** | Tab | 偏好(貨幣、主題、新增類別) + 通知(每日提醒、提醒時間、測試即時提醒) + SMS 銀行讀取器 + 備份與還原 + 安全 + 資料 | ✅ 已使用 |

> ✅ **已確認**:月度預算於首次執行 onboarding 中設定。目前自動化將其設為 `30000`,並把 Home 上的百分比驗證為 `expense / budget × 100`,四捨五入為整數。預算以「共用 setup + 下游斷言」的形式覆蓋,而非獨立的預算管理旅程。

---

## 2. 決策:選擇哪 2 個核心功能進行測試

### ✅ 選擇 1:Home → 新增交易捷徑入口

**為什麼選它**:
- 🎯 **最高頻的使用者路徑** — 任何個人記帳 App 的核心
- 🔬 **風險高** — 是所有下游資料的主要來源
- 📊 **可測的業務點很多** — 新增 Expense / Income / Transfer 交易;交易金額;類別/新增自訂類別;備註;標籤;交易時間戳;附件上傳
- 🔧 **跨頁面相依** — 同時驅動 Transactions 頁面與 Home / Analytics 彙總
- ⚡ **可自動化** — UI 元素相對穩定

**要測的子功能**:

| 子功能 | 優先度 | 可自動化 |
|-------------|----------|----------|
| 新增 **Expense** 交易,欄位:金額 + 類別(必填,如 Food) + 備註("breakfast with Dinna") + 標籤("food,dinna") + 日期 + 照片附件 | P0 | ✅ |
| 新增 **Income** 交易,欄位:金額 + 類別(必填,如 Salary) + 備註("fulltime salary") + 標籤("fulltime salary") + 日期 + 照片附件 | P0 | ✅ |
| 新增 **Transfer** 交易,欄位:金額 + 類別(必填,如 Others) + 備註("transfer amount from main account into sub account") + 標籤("transfer") + 日期 + 照片附件 | P0 | ✅ |
| 在 Add Transaction 流程中**內嵌新增自訂類別** | P1 | ✅ |
| 在 Expense 交易中**使用這個新自訂類別** | P0 | ✅ |

### ✅ 選擇 2:Transactions

**為什麼選它**:
- 🔬 **驗證面廣** — 一旦交易透過 Home 捷徑入口新增,Transactions 頁面必須正確顯示它們。這是對 Add Transaction 流程資料落地的下游校驗。

**要測的子功能**:

| 子功能 | 優先度 | 可自動化 |
|-------------|----------|----------|
| 依類型篩選交易(All / Expense / Income / Transfer) | P0 | ✅ |
| 交易清單**依日期彙總**(每個日期一組) | P0 | ✅ |

### ❌ 未選擇(及原因)

| 功能 | 原因 |
|---------|--------|
| Analytics / 圖表 | 重視覺;斷言 ROI 低;DOM 結構不穩定 |
| Settings | 設定導向;業務規則深度有限 |
| 作為獨立旅程的預算設定 | 已在首次執行 setup 與 Home 彙總斷言中覆蓋;未單獨選擇 Budget Management 場景 |

---

## 3. 自動化覆蓋矩陣

| 核心功能 | P0 案例 | P1 案例 | 合計 |
|--------------|----------|----------|-------|
| Home → 新增交易捷徑入口 | 4 | 1 | **5** |
| Transactions | 2 | 0 | **2** |
| **合計** | **6** | **1** | **7** |

> 範圍刻意收斂。任務說明要求「深度優先而非廣度」——7 個聚焦於最高價值路徑的 Gherkin 案例已足夠。

---

## 4. 自動化策略(簡要,給 README 用)

### 1. 框架選型

- **pytest-bdd** — Gherkin `.feature` 檔案 + pytest steps
- **Appium 3 + uiautomator2** — Android 模擬器/裝置驅動
- **Page Object** — Page 層負責元素;Flow 層負責業務

### 2. AI 觸點

- 使用 **ChatGPT / Claude / Codex** 起草初始 Gherkin 案例 → 人工審閱
- 使用 **Appium Inspector** 截圖 → 由 AI 建議 Locator
- **第 3 天** 實作 AI Failure Triage(失敗日誌 → 根因分類)

### 3. 資料重置策略

- `adb shell pm clear <packageName>` → 清空 Hive DB
- **冒煙 / CRUD 測試之前**:清空一次
- **持久化 / 資料校驗測試之前**:**不要**清空 —— 只殺 process / 重啟模擬器

---

## 5. 第 2 天 TODO

1. 依 §3 覆蓋矩陣,撰寫 **2 個 Gherkin `.feature` 檔案**:
   - `add_transaction.feature`(5 個案例)
   - `transactions.feature`(2 個案例)
2. 使用 Appium Inspector 擷取 Locator:
   - Home 頁 Add Expense / Income / Transfer 入口
   - Add Transaction 畫面
   - Transactions 頁面(篩選 + 列表分組)
3. 實作 `page/add_transaction.py`、`page/home.py`、`page/transactions.py`
4. 讓第一個端對端案例跑起來

---

## 附錄:Trackify 其他能力 / 限制

- ✅ 首次執行 onboarding 中包含月度預算設定
- ✅ Home 的 `This Month` 依 expense 與預算之比顯示進度
- ⚠️ 未將獨立的 onboarding 後 Budget Management 流程選為核心自動化功能
- ❌ 無雲端同步(100% 離線 / 僅 Hive)
- ❌ 無多幣別換算(僅顯示貨幣)
- ✅ 包含:SMS 銀行讀取器(未來可能的整合?)
- ✅ 包含:備份與還原(可能為 JSON 匯出 / 匯入)
- ✅ 包含:安全(PIN / 生物辨識 — TBD)

---

*本 `Feature_Inventory.md` 是測試範圍的唯一事實來源。`Feature_Inventory_01.md`
保留作為第 1 天的原始探索草稿。*
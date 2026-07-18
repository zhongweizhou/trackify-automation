# 架構設計

## 目標

本框架用於自動化 Trackify 價值最高的 Android 業務路徑,同時把 UI 操
作與業務斷言隔離開來。設計圍繞以下目標展開:

- 可讀的 BDD 場景;
- 確定性的首次執行狀態;
- 可重用的 Android/iOS locator 定義;
- 有價值的失敗證據;
- 小而可審閱的模組。

它不追求覆蓋整個 App、不提供視覺對比測試,也不會用重試機制掩蓋環境
失敗。

## 分層

```text
Gherkin feature
    -> pytest-bdd step definition
        -> Flow(業務狀態與斷言)
            -> Page Object(UI 互動)
                -> Appium WebDriver
                    -> Trackify
```

依賴方向是單向的:

- Steps 把場景文字翻譯成 Flow 呼叫。
- Flow 組合 Page,持有交易相關期望。
- Page 解析 YAML locator 並與 Appium 互動。
- `BasePage` 提供共享的等待、點擊、滑動、截圖、權限處理能力。
- Page 之間不互相引用,Flow 也不直接存取 driver。

這讓 Gherkin 在 locator 變動時保持穩定,也讓 UI 細節遠離業務斷言。

## Fixture 生命週期

`conftest.py` 擁有 Appium 連線與相依圖。一次 pytest 執行共用同一個
driver 連線。每個場景開始前,autouse fixture 會清空 Trackify 套件資
料並重新啟動 App。然後場景依下列順序完成統一的首次執行 onboarding:

1. 輸入 `Kimbal`;
2. 選擇 `$ US Dollar` 並設定預算 `30000`;
3. 啟用 Bank SMS Reader,點擊 Get Started。

reset 故意做得“重”但確定性,以避免一個場景的 Hive 資料、自訂類別
或 onboarding 狀態影響下一個場景。

## Locator 設計

Locator 位於 `locator/<page>.yaml`,依平台分組。Python 程式透過語
意鍵(如 `amount_input`、`save_button`)請求;loader 回傳對應平台
的策略與值。

推薦優先順序如下:

1. accessibility ID;
2. resource ID;
3. 穩定的 class 或平台述詞;
4. 受限的 XPath(僅在 Flutter 不暴露更強語意識別時使用)。

當前建置仍需 XPath 處理部分文字輸入與合併後的 Flutter 語意節點。這
些選擇器都被隔離在 YAML 中,可以獨立替換而不影響 Page 或 Flow 行為。

## 同步策略

Page 使用顯式等待而非固定 sleep。針對行動端特有的競爭狀態,補充兩條
規則:

- 文字欄位在選取下一個控制項前必須完成 IME action;
- 一次交易儲存成功後必須等到 Home 可見,才允許使用下一個捷徑入口。

第二條規則可以避免關閉中的 Add Transaction 頁面上的 `Income` 選
擇器被誤認為是 Home 上的同名捷徑入口。

## 業務斷言

`AddTransactionFlow` 在儲存前擷取類型、金額、類別以及本地日期/時間。
然後場景同時校驗對應的 Transactions 列與 Home 月度彙總。

- Expense 增加 expense。
- Income 增加 income。
- Transfer 不改變兩個彙總總額。
- Balance 等於 `income - expense`。
- 預算百分比為 `expense / budget * 100`,依 half-up 規則取整。
- 歷史交易在其日期分組裡被校驗,不影響當月彙總。

`TransactionsFlow` 單獨校驗類型篩選與日期分組。

## 失敗證據

pytest report 鉤子僅在 call 階段失敗時擷取 PNG,並保存在
`report/screenshots/` 下,同一張圖片也會附加到 Allure 結果中。截圖錯
誤會以 warning 形式回報,絕不會取代原始測試失敗。pytest-bdd 鉤子也
把原始的 Feature 與 Scenario 名稱暴露給 Allure。

## 顧問式失敗歸類

任務 13 僅在 pytest 產生原始報告後消費失敗證據。它對第一個失敗階
段進行分類,輸出一行簡潔的終端提示,並把同一份結構化結果附加到
Allure。依賴方向是單向的:

```text
pytest 失敗 -> 截圖/traceback -> 本地特徵 -> 可選 LLM
            -> 終端 + Allure 顧問式結果
```

高信心度的本地特徵直接處理環境、locator、資料、應用、腳本這幾類確
定性失敗,無需網絡 I/O。只有證據模糊時才允許使用顯式開啟的
MiniMax/Anthropic 相容回退。報告錯誤會降級為 `Unknown`,它們無法改
變測試結果或原始證據。這讓失敗歸類保持有用,又不會讓機率性的建議變
成自動修復機制。

執行語意、安全設定、驗證與故障排除見 [AI_TRIAGE.md](AI_TRIAGE.md)。

## CI 邊界

倉庫不提交 Trackify APK。因此 CI 明確分為兩個層級:

- 每次 push 與 PR 都安裝相依並收集所有場景;
- 只有當 `TRACKIFY_APK_URL` 提供可下載 APK 時,才執行 Android E2E。

E2E 任務會啟動一台 API 34 模擬器與 Appium,執行與本地開發相同的
pytest 命令,並上傳原始的 Allure 結果、截圖與 Appium 日誌。當 APK
secret 缺失時,CI 會把 E2E 任務明確標記為略過,而不是聲稱已完成行
動端覆蓋。

## 跨平台擴充

driver 設定與 locator YAML 已經接受 `android` 與 `ios`。把套件擴充到
iOS 只需要校驗過的 XCUITest locator 以及 picker/back 導航行為,不需
要新增 Gherkin 場景或 Flow 邏輯。

實作契約見 [TECHNICAL_SPEC.md](TECHNICAL_SPEC.md),範圍選擇見
[Feature_Inventory.md](Feature_Inventory.md)。
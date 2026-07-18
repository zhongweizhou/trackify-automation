# 專案復盤

## 成果

當前專案已經不再是一組彼此獨立的 UI 腳本，而是具備小型移動測試平台的
基本能力：

| 領域 | 已交付能力 |
|---|---|
| 業務覆蓋 | Add Transaction 與 Transactions 共 7 個 BDD 場景 |
| 平台 | Android/iOS 共用業務 Flow，定位器由各平台獨立維護 |
| 環境 | 通過 CLI 嚴格選擇 `test`、`preprod`、`prod` onboarding profile |
| 分發 | 在全部已發現裝置上全量複製，或按互斥子集分片 |
| 活用例庫 | Excel 用例庫驗證、增量同步及 Feature 事務性更新 |
| 診斷 | 截圖、日誌、JUnit、Allure 與 Task 13 建議式失敗歸因 |
| 結果歸屬 | 每個 worker/用例記錄環境、App 版本、裝置、系統版本和 UDID |

當前隔離驗證共有 107 個測試通過，三個環境參數都會收集完全相同的 7 個 BDD
場景。真實執行覆蓋 Android 17 和 iOS 26.5 的 iPhone 17 模擬器，兩端構建均
識別為 App `1.1.0`。`test` 矩陣在兩個平台驗證了環境化 onboarding；聚焦的
`preprod` Android 與 `prod` iOS happy path 均執行通過。

儲存庫目前故意保留了一條不健康演示資料：Income 場景輸入 `5002`，但期望
`5001.0`。它用於證明變化用例健康門禁能在兩個平台返回可歸屬的失敗。不能把
它描述成框架回歸，也不能聲稱當前提交中的完整 smoke 集合全部為綠色。

## 做得好的地方

### 清晰的分層歸屬

Gherkin、Step、Flow、Page 與 Locator YAML 的分離讓失敗可以收斂到單一層。
例如鍵盤交互變化只影響一個 Page 方法，而不是所有場景。交易匯總計算仍屬於
Flow，不會洩漏到定位器或 Gherkin 中。

同樣的歸屬紀律也擴展到資料層：Excel 與受管 Feature 區塊負責場景動作和預期；
`data/environments/` 只負責共享且不含金鑰的 onboarding 值；Locator YAML
只負責 UI 定位。這樣不會把一個 Excel 表格逐步變成無類型的萬能設定庫。

### 確定性且可按環境切換的 Setup

每條場景前清理應用存儲會增加耗時，但使 onboarding、自訂類別和匯總基線
可重複。`--env` 優先於 `TEST_ENV`，後者優先於預設 `preprod`；不支援的名稱
或錯誤 YAML schema 會在 Appium 啟動前失敗。Page Object 不感知環境名稱，
Flow 負責驗證選中姓名、幣種符號和 SMS Reader 狀態。

### 多裝置執行與明確的資源隔離

矩陣執行器會發現 Android 模擬器/裝置、iOS 模擬器和已配對 iOS 裝置，並為
每個目標啟動一個 pytest worker。`replicate` 用於在每台裝置驗證相容性，
`split` 則把每條選中用例只分配一次，以縮短整套回饋時間。

每個 worker 都有獨立的 Android `systemPort`、iOS WDA/MJPEG 連接埠、
derived-data 路徑、日誌、截圖、JUnit 和 Allure 目錄。這解決了常見併發會話
衝突，也保證失敗能歸屬到具體裝置。

### 報告能夠識別被測構建

只記錄環境不足以形成測試證據。執行時依次從顯式覆蓋、Appium capability、
Android 已安裝包元資料或 iOS bundle 元資料解析 App 版本。每條 Allure 用例
和每個 worker properties 檔案都在平台、裝置、系統版本、UDID 旁記錄 App
版本。矩陣聚合會保留每台裝置的獨立版本，而不是虛構一個公共構建身份。

### 活文件自動化具有明確邊界

Task 14 會驗證完整 Excel 用例庫，只更新受管 Scenario 區塊，保持未變化區塊位元組
一致，並在 collection 失敗時回滾 Feature 寫入。`run_changed_matrix.sh` 先做
預檢，再應用新增/修改用例並複製到選中裝置執行，最後返回機器可理解的健康
狀態。

同步引擎刻意止步於可執行 Gherkin：它不會猜測 Step、Flow、Page 或 Locator
程式碼，也不會把結果寫回 Excel。這些邊界使自動生成的變化仍可評審。

### 原始失敗證據始終優先

Allure 保留原始 BDD Feature 和 Scenario 名稱。call 階段失敗會附加截圖，但
不會替換原始 traceback。Task 13 只增加一條建議式分類與下一步動作：優先使用
確定性本地簽名，僅在顯式開啓後才讓 LLM 處理歧義證據。AI 輸出不會改變
pass/fail、自動重試或宣稱自己已經確認根因。

## 比預期更困難的部分

### Flutter accessibility semantics 與鍵盤狀態

部分控制項有穩定 accessibility ID，另一些控制項會合併成大型 semantics 節點，
或只暴露位置相關的文本輸入框，因此仍需要受限 XPath fallback。Setup 和
交易表單也都會受到鍵盤狀態影響；完成 IME action 比點擊任意螢幕座標可靠。

### 頁面過渡與橫向控制項

自訂類別入口位於橫向列表末端，需要受控滑動、建立流程、Back 導航和 chip
選擇。儲存後必須等待 Home 可見，才能查找下一個同名快捷入口，否則可能誤匹配
仍在關閉中的表單控制項。

### 裝置併發不能消除基礎設施狀態

唯一連接埠能避免確定性衝突，但 WebDriverAgent 仍有自己的生命週期。最終驗證
期間，一次 iOS session 在上一輪矩陣剛結束後立即啟動，setup 階段出現
`ECONNREFUSED 127.0.0.1:8100`；WDA 完全重啓後，相同命令執行通過。框架正確
將它報告為 `Env` setup 失敗，並把 App 版本標記為 `unresolved`，沒有用盲目
重試隱藏問題。後續應該針對這個過渡狀態增加明確的 readiness probe。

### 讓演示保持誠實

`5002` 與 `5001.0` 的故意不一致很適合失敗演示影片，但也意味著普通 smoke
命令會按設計變紅。報告和文件必須區分故障注入、產品缺陷與框架回歸。對於
可復用專案，更合理的方式是從臨時演示資料生成不一致，而不是讓預設用例庫
長期處於不健康狀態。

## 當前限制

- 每個 worker 內部仍是串行執行；矩陣提供裝置級併發，不會在一台裝置開啓
  多個 Appium session。
- 完整應用重置比定向狀態 fixture 更慢。
- 已提交的 Income 演示不一致會阻止完整 smoke 矩陣變綠，除非重新對齊輸入與
  預期。
- iOS 只在 iOS 26.5 的 iPhone 17 模擬器完成驗證；更多螢幕尺寸、locale 和
  實體裝置簽名路徑仍需要證據。
- 當前 `prod` 只修改本地應用存儲；該 profile 不代表允許對未來共享生產後端
  執行破壞性測試。
- Task 14 仍是單向同步，不生成實作程式碼，也不會自愈 Locator。
- Task 13 仍是建議式能力；在調整置信度閾值前，需要更多真實失敗樣本驗證
  opt-in 模型 fallback。
- GitHub 托管的 E2E 仍依賴外部提供的應用構建產物。

## AI 輔助

AI 幫助把需求轉成明確的歸屬規則、生成測試與文件草稿、檢查 Appium 證據並
縮短調試循環。真正有價值的部分不是更快接受生成程式碼，而是把每個建議與即時
頁面狀態、命令輸出和報告產物進行比較。

兩個擴展任務都體現了這一邊界：同步引擎只生成確定性的受管文本，並通過
pytest collection 驗證；失敗歸因把模型輸出當作附加假設。環境 profile 和
App 元資料使用嚴格解析器與平台工具，而不是讓模型猜測執行身份。

## 後續改進

1. 將 Income 故意不一致移動到臨時演示工作簿或故障注入腳本，讓提交的預設
   smoke 套件保持綠色。
2. 增加有邊界的 WDA readiness/recovery 預檢，區分啟動過渡與持續的 XCUITest
   設定錯誤。
3. 推動應用為文本框、日期分組和底部導航提供穩定 semantic ID。
4. 只有在每個環境至少保留一條 clean-install onboarding smoke 後，才引入
   更快的狀態 seed。
5. 通過受認證的構建服務發佈 Android/iOS 簽名產物，讓 CI 和本地矩陣使用相同
   App 版本身份。
6. 只有真實共享後端產生新需求時才擴展環境 profile；憑證必須放在 secret
   store，不能進入 profile YAML。
7. 只有多團隊併發編輯、權限和審計歷史確實需要時，才用測試管理 API 替換
   本地 Excel 用例庫。

最重要的經驗是：測試平台的價值來自明確邊界與可歸屬證據。一套規模不大、但
能夠識別環境、構建、裝置、資料來源和失敗階段的測試，比更多淺層 UI 腳本
提供更強的工程信號。

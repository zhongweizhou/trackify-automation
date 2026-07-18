# 多環境 Profile 設計

[English](2026-07-18-multi-environment-profile-design.md) |
[简体中文](2026-07-18-multi-environment-profile-design.zh-CN.md) |
[繁體中文](2026-07-18-multi-environment-profile-design.zh-TW.md)

## 目標

將 `test`、`preprod` 和 `prod` 作為明確的執行環境。選取的環境負責提供
Trackify 共用的 onboarding Profile；交易金額、每月預算等決定業務行為的
測試值繼續保留在 Excel 和 Gherkin 中。每一筆 Allure 結果都必須標明執行
環境和受測 App 版本。

## 範圍

本次變更包括：

- 三份經過驗證且不包含敏感資訊的 YAML 環境 Profile；
- 直接執行 pytest、裝置矩陣和變更案例矩陣時，統一支援
  `--env test|preprod|prod`；
- Android 和 iOS 使用環境資料完成 onboarding；
- 在單筆 Allure 中繼資料、`environment.properties`、合併報告和矩陣摘要中
  自動識別並顯示 App 版本；
- 更新活頁簿、Feature、README 和架構文件；
- 增加針對性單元測試，並執行現有收集與同步回歸檢查。

本次變更不增加按情境劃分的資料 Profile、通用 `${...}` 樣板替換、
Excel 到 YAML 同步、YAML 中的密鑰、後端 Data Factory 或環境專屬 Feature。

## 所有權邊界

| 關注點 | 所有者 | 範例 |
|---|---|---|
| 情境和業務參數 | Excel managed blocks / Gherkin | 金額 `100`、預算 `30000`、預期驗證文字 |
| 共用 onboarding Profile | 環境 YAML | 姓名、幣別、Bank SMS Reader 設定 |
| 裝置和 App 成品選擇 | CLI/環境設定 | UDID、Appium URL、APK、`.app`、`.ipa` |
| 敏感資訊 | CI Secret 或程序環境變數 | 未來的憑證或 Token |
| 執行時產生的後端實體 | 未來的 Data Factory | 不在本次範圍內 |

Excel 繼續作為 managed Scenario blocks 的權威來源。YAML 只對環境 Profile
資料負責。Sync Engine 繼續保持單向 `Excel -> Feature`，永遠不寫入 YAML。

## 環境檔案

新增以下檔案：

```text
data/environments/
  test.yaml
  preprod.yaml
  prod.yaml
```

每個檔案使用同一套嚴格 Schema：

```yaml
schema_version: 1
name: Rose
currency: "$ US Dollar"
bank_sms_reader_enabled: true
```

解析結果如下：

| 環境 | 姓名 | 幣別 | Bank SMS Reader |
|---|---|---|---|
| `test` | `Rose` | `$ US Dollar` | 啟用 |
| `preprod` | `Kimbal` | `$ US Dollar` | 啟用 |
| `prod` | `Kimi` | `$ US Dollar` | 啟用 |

`utils/environment_profile.py` 將指定檔案載入為凍結的 dataclass。未知環境、
檔案遺失、未知欄位、無效 Schema 版本、空字串或非布林型別的 SMS 設定，
都必須在建立 Appium Session 前失敗。環境之間不允許靜默回退。

## 環境選擇

只支援 `test`、`preprod` 和 `prod` 三個值。

直接執行 pytest 時，解析優先順序為：

```text
pytest --env
  > TEST_ENV
  > preprod
```

支援的執行入口包括：

```bash
.venv/bin/python -m pytest --env test
.venv/bin/python scripts/run_device_matrix.py --env preprod
./scripts/run_changed_matrix.sh --env prod
```

`run_device_matrix.py` 和 `run_changed_matrix.sh` 在預檢階段拒絕不支援的環境。
矩陣 Worker 透過 `TEST_ENV` 接收已經驗證的環境值。pytest 參數與環境變數
最終必須解析到同一個值；onboarding 和報告只能使用這個最終結果。

## BDD 和 Flow 變更

兩個 Feature 檔案中由程式碼管理的 Background 改為環境驅動，同時保留明確的
業務預算：

```gherkin
Background:
  Given app is launched with a clean database
  And user enters the configured environment name and continues
  And user selects the configured environment currency and sets monthly budget "30000"
  And user applies the configured Bank SMS Reader setting and gets started
  And user is on the Home page
```

Step Definition 使用 session scope 的 `environment_profile` fixture，並把解析
後的值傳給 `AppSetupFlow`。Flow 繼續保證設定順序，並驗證姓名、幣別符號和
SMS Reader 的目標狀態。Page Object 不感知環境名稱或 YAML。

活頁簿中全部七筆 Preconditions 改為描述環境 Profile onboarding，不再硬編碼
`Kimbal`。不新增活頁簿欄位，managed Scenario 的步驟和預期結果保持不變。

## App 版本解析

App 版本按以下優先順序解析：

1. 明確設定的程序變數 `APP_VERSION`；
2. Driver 提供的 Appium capability；
3. 指定 Android UDID 上已安裝 Package 的 `versionName`；
4. 指定 iOS `.app` 或 `.ipa` 中的 `CFBundleShortVersionString`；
5. 擲出設定錯誤，並提示呼叫者設定 `APP_VERSION`。

`utils/app_metadata.py` 負責平台相關的解析。它必須回傳非空版本號，否則擲出
邊界清楚的錯誤；正常完成的執行不能靜默顯示 `unknown`。

直接執行 pytest 時，在 Driver 建立後解析版本。矩陣 Worker 把解析結果寫入
各自的 Allure 結果；矩陣彙整器讀取這些屬性，而不是假設 Android 和 iOS
成品一定具有相同版本。

## 報告

每筆測試結果都包含以下 Allure 參數：

- Environment
- App Version
- Platform
- Device
- OS Version
- UDID

每個 Worker 的 `environment.properties` 包含：

```properties
Test.Environment=test
App.Version=1.2.3
Device.Platform=Android
Device.Name=...
Device.UDID=...
Device.OS.Version=...
```

合併後的 Allure properties 和 `summary.md` 按裝置保留 App 版本。如果 Android
與 iOS 成品版本不同，報告同時顯示兩個版本；彙整器不能把它們合併成一個
誤導性的版本。

如果 setup 在版本解析前失敗，報告仍保留環境和裝置識別。版本解析失敗本身
屬於 setup 設定失敗，必須保留 Task 13 分析證據；不能產生缺少版本資訊的
成功報告。

## 正式環境安全邊界

目前 Trackify 案例只清理和修改本機 App 儲存空間，因此允許使用既有的本機
onboarding Profile 執行 `--env prod`。如果日後這些情境連接到共用正式後端，
在加入憑證或後端資料前必須重新評估具破壞性的 prod 執行。本設計不授權修改
正式環境後端資料。

## 錯誤處理

- CLI 在裝置探索或同步前拒絕不支援的環境。
- Profile 驗證顯示環境、檔案和無效欄位，但不揭露敏感值。
- YAML 解析錯誤在 Appium setup 前終止執行。
- App 版本解析錯誤說明嘗試的資料來源，並提示 `APP_VERSION` 覆寫方式。
- 報告錯誤不能取代原始 pytest 失敗，與既有截圖和 AI Triage 行為保持一致。

## 驗證

增加以下單元測試：

- 三份環境檔案及其正確解析結果；
- CLI 參數優先於環境變數、環境變數優先於預設值；
- 未知環境和無效 YAML、Schema、欄位失敗；
- 直接 pytest 參數註冊和收集隔離；
- Android、iOS `.app`、iOS `.ipa`、capability 和明確覆寫的版本解析；
- Allure properties 包含環境和 App 版本；
- 矩陣參數驗證、Worker 傳遞、彙整和摘要輸出；
- changed-matrix 環境驗證；
- 環境驅動的 onboarding Flow 行為。

回歸驗證還必須證明：

- 所有既有單元測試通過；
- 七個 BDD 情境全部可以收集；
- Excel 與 managed Feature blocks 零漂移；
- 除 Preconditions 外，活頁簿保持可讀且視覺樣式不變；
- `--env test`、`--env preprod` 和 `--env prod` 分別解析到正確 Profile；
- 一次受控 Allure 執行同時顯示環境和 App 版本。

真實裝置執行範圍取決於本機可用的成品和裝置。單元測試必須在不依賴 Appium
的情況下涵蓋各平台中繼資料回退路徑。

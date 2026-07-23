# Trackify 移動端 UI 自動化

<p align="center">
  <a href="README.md">English</a> | <a href="README.zh-CN.md">简体中文</a> | <strong>繁體中文</strong>
</p>

> 面向 Trackify Flutter 個人財務應用的 AI 輔助端到端移動自動化框架。

[![Python](https://img.shields.io/badge/Python-3.11+-blue)](https://www.python.org/) [![Appium](https://img.shields.io/badge/Appium-3.x-green)](https://appium.io/) [![pytest-bdd](https://img.shields.io/badge/pytest--bdd-BDD-orange)](https://pytest-bdd.readthedocs.io/) [![Allure](https://img.shields.io/badge/Allure-Reporting-yellow)](https://allurereport.org/)

---

## 快速入口

這個儲存庫不僅包含 UI 操作腳本，還將移動自動化作為一個小型測試平台來
設計：架構邊界明確、資料狀態可重複、Android/iOS 共用業務用例、多裝置
併發執行，並且每條結果都能追溯到具體環境和裝置。

建議依次查看：

1. [Android + iOS 多裝置測試報告示例](docs/reports/device-matrix-preprod-sample.md)
2. [技術規格](docs/TECHNICAL_SPEC.zh-HK.md)
3. [架構決策](docs/DESIGN.zh-HK.md)
4. [專案復盤](docs/REFLECTION.zh-HK.md)
5. [Runner 流程圖與呼叫鏈](docs/RUNNER_FLOW.md)

| 工程亮點 | 儲存庫中的體現 |
|---|---|
| 契約驅動的 BDD | 7 個版本化場景、受控 Gherkin 詞彙、可復用步驟、嚴格 pytest marker |
| 分層架構 | Gherkin → Step Definitions → Flow → Page Object → Appium Driver，各層職責單一 |
| 跨平台定位 | Android/iOS 定位器統一放在 YAML；優先語義化 `accessibility_id`，必要時使用受控 fallback |
| 確定性隔離 | 每條用例前清理應用資料，再使用經過驗證的 `test`、`preprod` 或 `prod` profile 完成初始化 |
| 多裝置併發 | 一個命令發現全部可用 Android/iOS 裝置，並通過獨立 pytest 程序選擇全量複製或用例分片 |
| Appium 連接埠隔離 | 為 Android `systemPort`、iOS WDA/MJPEG 連接埠和 derived-data 目錄分配唯一值 |
| 可追溯報告 | 記錄環境、App 版本、平台、裝置、系統版本、UDID、逐用例結果、JUnit、日誌、截圖和合併 Allure |
| 失敗智能歸因 | 重試耗盡後，確定性本地簽名只分類最終失敗階段；歧義失敗僅在顯式開啓後呼叫 Claude 相容 fallback |
| Excel 活用例庫 | 經過驗證的用例表只增量更新受管 Gherkin 區塊，保持未變化位元組，並可只執行變化場景 |
| 可評審過程 | 技術規格明確分層規則、驗收標準、反模式和按任務拆分的提交紀律 |

AI 失敗歸因和 Excel → Gherkin 同步都已經實作。同步邊界只到受管 Scenario：
Step、Page、Flow 和 Locator 仍由程式碼維護。

---

## 功能演示影片

### Android/iOS 併發分片執行 smoke 子集

```bash
.venv/bin/python scripts/run_device_matrix.py \
  --distribution split \
  --env preprod \
  -- \
  -m smoke
```

影片展示 pytest marker 參數透傳、Android/iOS 自動發現、多裝置併發、Appium
會話連接埠隔離，以及合併後的 Allure 報告。由於命令使用 `split`，選中的 smoke
用例會分配到全部可用裝置，每條用例在本次矩陣中只執行一次；如果要求每台
裝置都執行每條選中用例，應使用預設的 `replicate` 模式。

[在 Bilibili 觀看 smoke 多裝置矩陣演示](https://www.bilibili.com/video/BV17QKG6mEWW)

### Excel 驅動的增量執行與故意斷言失敗

```bash
./scripts/run_changed_matrix.sh
```

影片先展示一個 BDD Scenario，再根據穩定用例 ID 在 Excel 中找到對應行，只
修改操作步驟中的 amount，故意保持 Expected Result 不變。一鍵健康門禁只識別
這條 modified 用例，同步對應的受管 Feature 區塊，在已發現的 Android 和 iOS
裝置上複製執行，並在 Allure 中展示失敗用例及斷言原因。影片中的失敗是刻意
製造的，用於證明資料與預期不一致時，系統能夠按用例和裝置準確歸因，並向
呼叫者返回不健康結果，而不是隱藏失敗或盲目自愈。

[在 Bilibili 觀看增量用例失敗診斷演示](https://www.bilibili.com/video/BV1EDKG6EELD)

---

## 從 Clone 到報告的執行手冊

當本機 Android/iOS 工具鏈和模擬器已經準備好後，可以嚴格按下面步驟從
clone 程式碼執行到生成報告，無需先理解框架內部實作。

### 1. Clone 並安裝依賴

```bash
git clone https://github.com/zhongweizhou/trackify-automation.git
cd trackify-automation

# macOS 尚未安裝 uv 時先執行
brew install uv
uv sync
npm install -g appium allure-commandline
appium driver install uiautomator2
appium driver install xcuitest
```

### 2. 放置待測應用包

應用二進制檔案不會提交到 Git。請放到以下預設路徑：

| 測試目標 | 應用包 | 預設路徑 |
|---|---|---|
| Android 模擬器/實體裝置 | APK | `app/app-release.apk` |
| iOS 模擬器 | 模擬器 `.app` | `app/Runner.app` |
| iOS 實體裝置 | 已簽名的實體裝置 `.ipa` 或 `.app` | 執行時通過 `--ios-real-app` 指定 |

```bash
mkdir -p app
cp /path/to/app-release.apk app/app-release.apk
cp -R /path/to/Runner.app app/Runner.app
```

注意：iOS 模擬器不能安裝僅為實體裝置構建的應用，`Runner.app` 必須包含模擬器
架構。

### 3. 啟動並確認測試裝置

仍然可以手動啟動並檢查裝置：

```bash
# Android 目標必須顯示為 device，不能是 offline/unauthorized
adb devices -l

# iOS 模擬器必須顯示為 Booted
xcrun simctl list devices booted
```

正式執行時也可以增加 `--prepare-devices` 自動管理生命週期，不需要預先知道
裝置名稱。每個平台會優先重用一個已啟動虛擬裝置；沒有已啟動裝置時，確定性
選擇並啟動一個本機已安裝裝置。隨後從 `app/` 覆蓋安裝應用、執行 pytest、
等待 60 秒，再關閉選中的 Android 虛擬機或 iOS 模擬器。真實裝置不會被自動
啟動或關閉。Runner 啟動 Android AVD 時會傳入 `-skip-adb-auth`，避免被 USB
偵錯授權彈窗阻塞；從 Android Studio 手動啟動的模擬器和實體裝置仍可能需要
一次性勾選「一律允許使用這部電腦」並點擊允許。

### 4. Appium 生命週期

啟動裝置或執行 pytest 前，Runner 會先檢查 Appium `/status`。如果本機已有
ready 的 Appium，會直接重用；如果本機服務未啟動，矩陣執行會自動啟動，並將
日誌寫入 `report/appium/appium.log`，直到返回 `ready: true`。如需強制要求手動
啟動，可傳入 `--no-auto-start-appium`。命令開始前已存在的 Appium 不會被關閉；由 Runner
自動啟動的 Appium 會在測試結束等待 `--shutdown-after`（預設 60 秒）後關閉。

遠端 Appium 伺服器需要在遠端主機手動啟動。本機手動啟動時，請在同一個終端
設定 Android SDK 環境變量：

```bash
export ANDROID_HOME="${ANDROID_HOME:-$HOME/Library/Android/sdk}"
export ANDROID_SDK_ROOT="$ANDROID_HOME"
appium --address 127.0.0.1 --port 4723
```

### 5. 預檢本次執行裝置

另開一個終端，進入儲存庫根目錄：

```bash
.venv/bin/python scripts/run_device_matrix.py --list

# 列出所有已安裝虛擬裝置、狀態、UDID 和零配置自動選擇結果
.venv/bin/python scripts/run_device_matrix.py --list-available-devices

# 同時預覽裝置發現結果和具體用例分片，不執行測試
.venv/bin/python scripts/run_device_matrix.py \
  --distribution split \
  --list
```

確認列表中包含計劃執行的每台裝置、系統版本和 UDID。這個預檢命令不會
安裝應用，也不會執行用例。

### 6. 執行全部裝置並打開報告

```bash
# 在發現的全部 Android + iOS 裝置上併發執行 7 個場景
.venv/bin/python scripts/run_device_matrix.py --env preprod

# 將 7 個場景分攤到全部裝置，每個場景只執行一次
.venv/bin/python scripts/run_device_matrix.py \
  --distribution split \
  --env preprod

# 零配置：自動選擇一個 Android 和一個 iOS 目標
.venv/bin/python scripts/run_device_matrix.py \
  --prepare-devices \
  --env preprod

# 需要固定相容性機型時，顯式參數覆蓋自動選擇
.venv/bin/python scripts/run_device_matrix.py \
  --prepare-devices \
  --android-avd Pixel_10 \
  --ios-simulator "iPhone 17" \
  --env preprod

# 僅 Android；調試時設定 --shutdown-after 0 保留裝置
.venv/bin/python scripts/run_device_matrix.py \
  --prepare-devices \
  --platform android \
  --shutdown-after 0 \
  --env preprod
```

`--android-avd` 使用 `emulator -list-avds` 返回的 AVD 名稱；
`--ios-simulator` 支援準確的 Simulator 名稱或 UDID。裝置準備命令作用於執行
腳本的機器；遠端 Appium 主機需要在該主機執行同一腳本，或由 CI 單獨預置裝置。

預設的 `replicate` 模式用於驗證每台裝置上的完整相容性；需要縮短整套測試
執行時間時，使用 `split` 將互不重疊的用例子集分配給各裝置。

執行結束後，終端會輸出本次報告的準確路徑：

```text
[matrix] Summary: .../report/device-matrix/preprod/<時間戳>/summary.md
[matrix] Allure:  .../report/device-matrix/preprod/<時間戳>/allure-report/index.html
```

`summary.md` 可以直接在編輯器中打開。macOS 打開 Allure HTML：

```bash
open "$(find report/device-matrix/preprod -path '*/allure-report/index.html' -print | sort | tail -1)"
```

如果本機只設定了一種平台，可以執行：

```bash
# 所有 Android 裝置
.venv/bin/python scripts/run_device_matrix.py --platform android --env preprod

# 所有 iOS 裝置
.venv/bin/python scripts/run_device_matrix.py --platform ios --env preprod
```

最終證據包括裝置匯總、逐用例結果、每台裝置的 pytest/JUnit 檔案、合併的
Allure 報告，以及失敗階段截圖。可以與儲存庫內提交的
[測試報告示例](docs/reports/device-matrix-preprod-sample.md)對照。

### 常見環境問題

| 現象 | 排查方式 |
|---|---|
| 沒有發現裝置 | 執行 `adb devices -l` 和 `xcrun simctl list devices booted`，啟動或重連目標 |
| Appium connection refused | 矩陣命令可以自動啟動本機服務；直接執行 pytest 時請在 `4723` 啟動 Appium，或傳入 `--appium-url` |
| Appium `/status` 返回 502 | 使用 `curl --noproxy '*' http://127.0.0.1:4723/status` 驗證本機端點，並檢查 `report/appium/appium.log` |
| 找不到 Android SDK | 啟動 Appium 前設置 `ANDROID_HOME`、`ANDROID_SDK_ROOT`，然後重啓 Appium |
| 找不到應用包 | 從儲存庫根目錄確認 `app/app-release.apk` 和/或 `app/Runner.app` 存在 |
| 缺少 XCUITest | 執行 `appium driver install xcuitest` |
| 檢測到 iOS 實體裝置但缺少應用 | 配對並解鎖裝置、啓用開發者模式，再傳入 `--ios-real-app <簽名包>` |

---

## 專案概覽

Trackify 是一個使用 Hive 本地資料庫的離線 Flutter 個人財務應用。本專案
覆蓋兩個高價值使用者旅程：

1. **首頁 → 添加交易**：支出、收入、轉賬、驗證和自訂類別
2. **交易列表**：按類型篩選和按日期分組

當前共有 7 個 BDD 場景：5 個 Add Transaction 場景和 2 個 Transactions
場景。同一套業務場景可以在 Android 和 iOS 上執行，平台差異收斂在 Driver、
Page 和 YAML Locator 層。

## 最常用命令

所有已啟動/已連接的 Android 和 iOS 裝置併發執行完整 7 個場景：

```bash
.venv/bin/python scripts/run_device_matrix.py --env preprod
```

如果希望整套 7 個場景只執行一次，並分攤到全部裝置：

```bash
.venv/bin/python scripts/run_device_matrix.py \
  --distribution split \
  --env preprod
```

執行器預設測試環境為 `preprod`，會自動發現：

- `adb devices` 中狀態為 ready 的 Android 模擬器和實體裝置；
- `xcrun simctl` 中已啟動的 iOS 模擬器；
- `xcrun devicectl` 中已配對的 iOS 實體裝置。

如果發現 iOS 實體裝置，需要額外提供簽名後的實體裝置 `.ipa` 或 `.app`：

```bash
.venv/bin/python scripts/run_device_matrix.py \
  --env preprod \
  --ios-real-app "$PWD/app/Trackify-preprod.ipa"
```

## 選擇測試環境

同一套 7 條業務場景支援三個經過嚴格驗證的 onboarding profile：

| `--env` | 姓名 | 幣種 | Bank SMS Reader |
|---|---|---|---|
| `test` | `Rose` | `$ US Dollar` | 開啓 |
| `preprod`（預設） | `Kimbal` | `$ US Dollar` | 開啓 |
| `prod` | `Kimi` | `$ US Dollar` | 開啓 |

```bash
# 單裝置直接執行
uv run pytest --env test -m "not unit"
uv run pytest --env preprod -m "not unit"
uv run pytest --env prod -m "not unit"

# 所有已發現裝置執行
.venv/bin/python scripts/run_device_matrix.py --env test
.venv/bin/python scripts/run_device_matrix.py --env preprod
.venv/bin/python scripts/run_device_matrix.py --env prod
```

選擇優先級為 `--env` > `TEST_ENV` > `preprod`。`data/environments/` 只維護
不含金鑰的共享 onboarding 設定；業務輸入和預期結果仍由 Excel/Gherkin 管理。
不支援的環境名或錯誤 YAML schema 會在 Appium 啟動前失敗。

當前 `prod` 場景只清理和修改 Trackify 本地存儲，因此允許執行。如果應用後續
接入共享生產後端或生產憑證，必須重新評估破壞性用例邊界。

成功報告還必須包含明確的 App 版本。解析順序是 `APP_VERSION`、Appium
capability、Android 已安裝包 `versionName`、iOS `.app/.ipa` 元資料。無法從
構建產物識別時可顯式覆蓋：

```bash
APP_VERSION=1.2.3 uv run pytest --env test -m "not unit"
```

## 測試命令分類匯總

以下命令覆蓋當前專案支援的主要執行方式。沒有安裝 `uv` 時，可將
`uv run pytest` 替換為 `.venv/bin/python -m pytest`。

### 1. 檢查與收集

```bash
# 只驗證 Python 導入、Gherkin、步驟綁定和 marker，不啟動 Appium
uv run pytest -m "not unit" --collect-only -q

# 不需要 Appium/裝置，驗證矩陣分片算法
.venv/bin/python -m unittest discover -s unit_tests -v

# 不需要 Appium/裝置/網絡，驗證 Task 13 失敗歸因
uv run pytest -m unit tests/unit/test_triage.py -q

# 不需要 Appium/裝置，驗證 Task 14 增量同步和回滾
uv run pytest -m unit tests/unit/test_sync_engine.py -q

# 檢查 Excel 與 Feature 是否存在 drift，不寫檔案
uv run python scripts/sync_engine.py --check

# 增量更新並只執行變化用例
uv run python scripts/sync_engine.py --apply --run-changed

# 一條命令完成檢查、同步，並在所有 Android/iOS 裝置執行全部變化用例
./scripts/run_changed_matrix.sh
```

### 2. 單裝置完整執行

```bash
# 預設 Android 裝置，執行全部 7 個場景
uv run pytest -m "not unit"

# 指定一台 Android 裝置
PLATFORM=android \
DEVICE_UDID=emulator-5554 \
DEVICE_NAME="Android Emulator" \
APP_PATH="$PWD/app/app-release.apk" \
uv run pytest -m "not unit"

# 指定一台 iOS 模擬器
PLATFORM=ios \
DEVICE_UDID=BFE1DE67-0F95-47B7-A02A-D25EE83CD999 \
DEVICE_NAME="iPhone 17" \
APP_PATH="$PWD/app/Runner.app" \
uv run pytest -m "not unit"
```

### 3. 按 Feature 執行

```bash
# 5 個 Add Transaction 場景
uv run pytest tests/features/add_transaction.feature -q

# 2 個 Transactions 場景
uv run pytest tests/features/transactions.feature -q
```

### 4. 按優先級或功能標籤執行

```bash
# P0 冒煙場景
uv run pytest -m smoke -q
uv run pytest -m p0 -q

# P1 場景
uv run pytest -m p1 -q

# 按功能選擇
uv run pytest -m custom_category -q
uv run pytest -m filter -q
uv run pytest -m grouping -q

# 當前全部優先級
uv run pytest -m "p0 or p1" -q
```

`regression` 已在 `pytest.ini` 註冊，但當前場景沒有 `@regression` 標籤，
所以 `uv run pytest -m regression` 會收集到 0 條用例。

### 5. 執行單個場景

```bash
uv run pytest -k "add_expense_happy_path" -q
```

可用名稱：

```text
add_expense_happy_path
add_income_happy_path
add_transfer_happy_path
validation__empty_amount_shows_error_and_does_not_save
add_expense_with_new_custom_category_created_in_flow
filter_transactions_by_type_shows_only_matching_type
transactions_grouped_by_date_with_section_headers
```

### 6. 多裝置矩陣執行

兩種分發模式：

| 模式 | 7 條用例、2 台裝置時的行為 | 適用場景 |
|---|---|---|
| `replicate`（預設） | A 跑 7 條，B 跑 7 條，共 14 次裝置維度執行 | 驗證不同平台/裝置相容性 |
| `split` | A 跑 4 條，B 跑 3 條，共 7 次裝置維度執行 | 縮短一整套測試的回饋時間 |
| `mapped` | 按配置檔把指定用例固定分配到指定裝置，並合併一份報告 | 可重現的 case-to-device 分片 |

```bash
# 僅發現並列出裝置，不執行測試
.venv/bin/python scripts/run_device_matrix.py --list

# 預覽每台裝置分到的具體用例，不啟動 Appium 會話
.venv/bin/python scripts/run_device_matrix.py \
  --distribution split \
  --list

# 全部 Android + iOS 裝置，執行完整 7 個場景
.venv/bin/python scripts/run_device_matrix.py --env preprod

# 將完整 7 個場景分攤到全部裝置，每條只執行一次
.venv/bin/python scripts/run_device_matrix.py \
  --distribution split \
  --env preprod

# 僅全部 Android 裝置
.venv/bin/python scripts/run_device_matrix.py \
  --platform android \
  --env preprod

# 僅全部 iOS 裝置
.venv/bin/python scripts/run_device_matrix.py \
  --platform ios \
  --env preprod

# 指定一台裝置
.venv/bin/python scripts/run_device_matrix.py \
  --env preprod \
  --device emulator-5554

# 指定多台裝置；--device 可以重複
.venv/bin/python scripts/run_device_matrix.py \
  --distribution split \
  --env preprod \
  --device emulator-5554 \
  --device BFE1DE67-0F95-47B7-A02A-D25EE83CD999

# 在所有裝置上只執行 smoke 場景；-- 後參數會透傳給 pytest
.venv/bin/python scripts/run_device_matrix.py \
  --distribution split \
  --env preprod \
  -- \
  -m smoke

```

### 7. Allure 報告

```bash
uv run pytest \
  -m "not unit" \
  --alluredir=./allure-results \
  --clean-alluredir

# 臨時啟動報告服務
allure serve ./allure-results

# 生成靜態報告
allure generate ./allure-results --clean -o ./allure-report
open ./allure-report/index.html
```

### 8. 失敗定位和調試

```bash
# 第一次失敗立即停止
uv run pytest -m "not unit" -x -vv

# 只重新執行上次失敗的用例
uv run pytest -m "not unit" --lf -vv

# 調試時關閉輸出捕獲
uv run pytest -m "not unit" -s -vv
```

## 多裝置能力亮點

`scripts/run_device_matrix.py` 不是簡單循環執行命令，而是解決了真實併發
移動測試中的資源衝突和報告歸屬問題：

1. 自動發現 Android、iOS 模擬器和已配對 iOS 實體裝置；
2. 為每台裝置啟動獨立 pytest 子程序，實作併發執行；
3. 支援 `replicate` 全量複製和 `split` 互斥分片兩種策略；
4. 為每個 Android 會話分配獨立 `systemPort`；
5. 為每個 iOS 會話分配獨立 WDA、MJPEG 連接埠和 derived-data 目錄；
6. 每台裝置擁有獨立日誌、JUnit、Allure 原始結果和失敗截圖目錄；
7. 執行結束後合併 Allure 結果，並生成 Markdown 和 JSON 總結；
8. 每條報告附帶環境、App 版本、分片策略、測試 node ID、裝置名、系統版本和 UDID；
9. Android 使用 `pm clear`、iOS 模擬器使用 `mobile: clearApp`，iOS 實體裝置
   通過卸載重裝簽名應用保證場景隔離。

輸出目錄：

```text
report/device-matrix/<環境>/<時間戳>/
├── summary.md
├── summary.json
├── allure-results/
├── allure-report/index.html
├── android-<裝置>-<udid>/
│   ├── pytest.log
│   ├── junit.xml
│   ├── allure-results/
│   └── screenshots/
└── ios-<裝置>-<udid>/
    ├── pytest.log
    ├── junit.xml
    ├── allure-results/
    └── screenshots/
```

每條 Allure 結果都會展示環境、App 版本、平台、裝置、系統版本和 UDID。
矩陣匯總從每個 worker 的 `environment.properties` 讀取 App 版本，因此 Android
和 iOS 使用不同構建時也會分別展示，不會被合併成一個誤導性的公共版本。

查看真實的完整執行結果：
[preprod Android + iOS 矩陣報告示例](docs/reports/device-matrix-preprod-sample.md)。

## 技術規格提煉

[`docs/TECHNICAL_SPEC.zh-HK.md`](docs/TECHNICAL_SPEC.zh-HK.md) 將實作方式定義成可評審的
工程契約，主要價值包括：

- **架構邊界**：Step 不直接操作 Appium，Flow 只編排業務，Page 負責 UI，
  Driver 負責平台會話；
- **定位器治理**：定位值只能放在 YAML 中，按 accessibility id、平台原生
  策略和受控 XPath fallback 的優先級解析；
- **Fixture 注入**：Driver、Page、Flow 統一由 pytest fixture 建立，生命週期
  和 teardown 只有一個來源；
- **BDD 詞彙契約**：同一動作只能使用同一套 Gherkin 表達，場景清單是測試
  範圍和實作驗收的共同事實源；
- **業務級斷言**：不只驗證點擊成功，還驗證交易持久化、首頁月度匯總、轉賬
  不影響收支以及非法輸入不產生資料；
- **穩定性規範**：禁止 Page 中使用固定 `sleep`，統一採用顯式等待；每條場景
  從清潔狀態啟動；
- **失敗證據**：失敗時通過 pytest hook 自動截圖並附加到 Allure，原始異常
  不被包裝或吞掉；
- **實作紀律**：每個任務都有檔案範圍、驗收標準、測試門檻和對應提交，便於
  評審及回溯。

## AI 失敗歸因

Task 13 是真實回歸測試失敗後的診斷層。用例通過時不做任何處理；首個
非 unit 流動端案例預設執行 1 次，並最多重試 2 次，最後一次結果決定
PASS/FAIL；unit tests 始終只執行一次。每次 BDD 失敗都會按 attempt 編號儲存
截圖和 Appium page source。只有全部嘗試都失敗後，Task 13 才對最終失敗給出
建議分類及下一步排查動作。

執行順序是 `失敗 -> 重試歷史 -> 最終失敗 -> 本地規則 -> 可選 LLM`。最終
失敗的 `setup`、`call` 或 `teardown` 階段只生成一次歸因結果。該結果不會
改變 pytest 狀態、隱藏原始 traceback 或自動提交缺陷；LLM 請求本身也不會
重試。

```text
[AI Triage] Locator (92%): Matched local failure signature 'selector_specific_missing'.
```

始終開啓的本地階段使用確定性簽名識別 `Locator`、`App Bug`、`Env`、
`Script` 和 `Data`。弱信號不會累加置信度，無法可靠判斷時返回 `Unknown`。
Allure 中會附加名為 `AI Triage` 的 JSON，包含 schema 版本、測試名稱、失敗
階段、attempt/最大次數、失敗 BDD 步驟、分類、信心度、原因、建議動作、
分類器和命中的本地簽名 ID。

聚焦除錯時可以關閉重試：

```bash
uv run pytest -m "not unit" -k "add_expense_happy_path" --reruns 0 -s -vv
.venv/bin/python scripts/run_device_matrix.py --env preprod -- --reruns 0 -k "add_expense_happy_path" -s
```

| `classifier` | 使用者應如何理解 |
|---|---|
| `local` | 高置信度本地簽名完成分類，沒有呼叫 API |
| `llm` | 本地證據不足，已嘗試一次設定好的相容模型請求 |
| `disabled` | 證據不足且開關、Key 或模型缺失，無法使用 LLM |

終端會打印一條 `[AI Triage] ...`，失敗用例的 Allure 詳情同時附加結構化
結果。必須結合原始 traceback 和截圖閱讀；它是排查假設，不是確認根因。

Claude 相容 fallback 預設關閉。只有主動設定開關、API Key 和模型時才會
啓用；`ANTHROPIC_BASE_URL` 可選，預設使用 Anthropic 官方地址。MiniMax
Anthropic 相容介面設定如下：

```bash
export AI_TRIAGE_LLM_ENABLED=1
export ANTHROPIC_BASE_URL="https://api.minimaxi.com/anthropic"
export ANTHROPIC_API_KEY="<key>"
export ANTHROPIC_MODEL="MiniMax-M3"
```

引擎會保留網關路徑並自動追加 `/v1/messages`。可以複製 `.env.example`，但
專案不會自動加載 `.env`，需要執行 `set -a; source .env; set +a`；`.env` 已
被忽略，嚴禁提交真實金鑰。真實聯調應使用裸 `AssertionError`，因為高置信度
本地簽名會按設計直接返回，不會訪問 LLM。

```bash
cp .env.example .env
chmod 600 .env
# 編輯 .env：開啓 fallback，並替換佔位 Key。
set -a; source .env; set +a

.venv/bin/python -c "from dataclasses import asdict; from ai.triage import triage_failure; print(asdict(triage_failure({'error_msg': 'AssertionError', 'traceback': '', 'test_name': 'live_probe', 'phase': 'call'})))"
```

真實請求成功時會返回 `classifier: llm` 和模型生成的原因/建議；認證、額度、
連接、超時或回應格式問題只輸出安全的 HTTP 狀態/錯誤類型，不會輸出 Key 或
介面回應正文。
如果 python.org 的 macOS Python 提示 `TLS certificate verification failed`，
並且 `/etc/ssl/cert.pem` 存在，應設置
`export SSL_CERT_FILE=/etc/ssl/cert.pem`，不要關閉證書驗證。

只有本地置信度低於 `0.70` 時才允許一次請求，不重試，總超時 5 秒。錯誤文本
在網絡呼叫前會被截斷和脫敏，Authorization、Token、API Key 和 URL query
都會移除。截圖不會上傳，只允許傳入“是否存在”和檔案名。設定缺失、超時、
HTTP 錯誤或回應不合法時都安全降級為 `Unknown`。

無需 Appium、裝置或網絡即可執行完整 Task 13 測試：

```bash
uv run pytest -m unit tests/unit/test_triage.py -q
```

完整設定檢查、local/LLM probe、pytest/Allure 實際驗證步驟、問題排查和私隱
邊界見 [`docs/AI_TRIAGE.zh-HK.md`](docs/AI_TRIAGE.zh-HK.md)。

## Excel 管理的 BDD 同步

[`data/test_cases.xlsx`](data/test_cases.xlsx) 已將現有 7 條用例整理成 16 列的
可維護用例庫。Excel 負責元資料及受管 `Scenario` 的動作和斷言；Feature 的
標題、注釋和 `Background` 仍由程式碼維護。Step Definition、Page、Flow、測試
資料和 YAML Locator 不會被同步引擎生成或覆蓋。

```bash
# 驗證 schema 並顯示 added/modified/deprecated/unchanged，不寫檔案
uv run python scripts/sync_engine.py --check

# 只應用通過全量驗證的 Scenario 變化，並執行 pytest collection
uv run python scripts/sync_engine.py --apply

# 應用後只執行新增/修改的 active 場景
uv run python scripts/sync_engine.py --apply --run-changed

# 一鍵檢查、同步並在所有 Android/iOS 裝置執行變化用例
./scripts/run_changed_matrix.sh

# 本地監聽，連續寫入停止 5 秒後觸發
uv run python scripts/sync_engine.py --watch --apply
```

`run_changed_matrix.sh` 是推薦的跨裝置變化健康門禁。它讀取機器可解析的變化
清單，預覽裝置，原子應用通過驗證的 Feature 變化，然後固定使用矩陣
`replicate` 模式。委託的矩陣 Runner 會自動檢查或啟動本機 Appium，因此不需要
提前手動啟動本機服務。

```bash
# 預設：preprod，所有已發現的 Android + iOS 裝置
./scripts/run_changed_matrix.sh

# 啟動/重用指定 Android 和 iOS 模擬器，安裝 App，執行後等待 60 秒清理
./scripts/run_changed_matrix.sh \
  --prepare-devices \
  --android-avd Pixel_10 \
  --ios-simulator "iPhone 17"

# 只在全部 Android 裝置執行
./scripts/run_changed_matrix.sh --platform android

# 只選擇兩台裝置，--device 可以重複
./scripts/run_changed_matrix.sh \
  --device <Android裝置UDID> \
  --device <iOS裝置UDID>

# iOS 實體裝置需要簽名包
./scripts/run_changed_matrix.sh \
  --platform ios \
  --ios-real-app "$PWD/app/Trackify-preprod.ipa"
```

退出碼 `0` 表示沒有待執行變化，或全部變化用例在每台裝置都通過；`1` 表示
至少一條變化用例在至少一台裝置失敗；`2` 表示驗證、collection、裝置、
Appium、應用包、鎖或 I/O 導致流程無法完成。報告位於
`report/changed-device-matrix/<環境>/<時間戳>/`：`summary.md` 按用例 ID ×
裝置展示 Changed Case Health，`summary.json` 儲存相同的機器可讀變化清單和
結果，同時包含每台裝置的日誌、JUnit、截圖及合併 Allure 證據。

引擎會在第一次寫入前驗證完整工作簿和兩個 Feature，並使用 Module 白名單、
穩定 `scenario_id`、帶微秒的備份、同目錄臨時檔案、`os.replace` 和併發鎖。
寫入後的 pytest collection 失敗時，會恢復本次修改的全部 Feature。未變化的
受管區塊直接復用原始文本切片，即使相鄰場景新增、修改或棄用也保持位元組一致。

`--run-changed` 用於針對性的實作和調試：通過時返回變化用例數量和 Allure
路徑；執行失敗時保留已經通過 collection 的 Feature 變更，通過 Task 13、
失敗截圖和 Allure 提供診斷，並打印準確的 pytest 重試命令，提示檢查 Step、
Page/Flow 和 YAML Locator。如果新增 Gherkin 詞彙還沒有 Step 實作，collection
會失敗並回滾 Feature，然後明確回饋缺少的實作。

同步引擎不會猜測或自動修復 Locator。定位器必鬚根據 Appium 頁面結構和截圖
證據修改並接受程式碼評審，否則“自愈”很容易掩蓋產品缺陷。引擎也不會寫回
Excel；刪除一行不代表刪除用例，需要使用 `Automation Status=deprecated` 和
明確的棄用版本。

### 完整操作與驗收步驟

下面用“只修改一條 Excel 用例”為例，驗證同步器是否只生成並執行對應場景。
最後的恢復命令只適用於演練資料，真實用例修改不要恢復。

1. 確認提交態基線：

   ```bash
   git status --short
   uv run python scripts/sync_engine.py --check
   echo $?
   ```

   正常基線應顯示 `add_transaction` 5 條 unchanged、`transactions` 2 條
   unchanged，退出碼為 `0`。

2. 打開 `data/test_cases.xlsx`，進入 `Test Cases` 工作表，找到
   `TC_ADD_TX_001`。演練時可將金額 `100` 改成 `101`，需要同時修改：

   - `Test Steps` 中的 `user enters amount "100"`；
   - `Expected Result` 中所有對應的金額斷言。

   儲存並關閉 Excel，避免 Excel 繼續寫臨時檔案。

3. 只預覽增量，不寫 Feature：

   ```bash
   uv run python scripts/sync_engine.py --check
   echo $?
   git status --short
   ```

   預期只顯示一條 `modified: TC_ADD_TX_001`，`transactions` 模區塊 0 變化，
   退出碼為 `1`。這裡的 `1` 表示“資料合法但存在 drift”，不是同步異常。

4. 選擇一種應用方式。只驗證生成和 collection、不啟動裝置時執行：

   ```bash
   uv run python scripts/sync_engine.py --apply
   ```

   如果需要應用後立即在 Android 上只執行變化用例，則直接執行：

   ```bash
   PLATFORM=android \
   DEVICE_UDID=<Android裝置UDID> \
   APP_PATH="$PWD/app/app-release.apk" \
   uv run python scripts/sync_engine.py --apply --run-changed
   ```

   Android UDID 可通過 `adb devices` 獲取。已啟動 iOS 模擬器時執行：

   ```bash
   PLATFORM=ios \
   DEVICE_UDID=<iOS模擬器UDID> \
   APP_PATH="$PWD/app/Runner.app" \
   uv run python scripts/sync_engine.py --apply --run-changed
   ```

   iOS UDID 可通過 `xcrun simctl list devices booted` 獲取。如果目標是執行
   變化用例，不要先單獨執行 `--apply`：apply 成功後已經沒有 drift，隨後再加
   `--run-changed` 不會重複執行。已經 apply 時，需要再修改一次 Excel。

5. 確認修改範圍和最終狀態：

   ```bash
   git diff -- tests/features/add_transaction.feature
   git diff -- tests/features/transactions.feature
   uv run python scripts/sync_engine.py --check
   ```

   預期只有 `TC_ADD_TX_001` 的受管區塊變化，最終檢查退出 `0`。裝置執行成功時
   會輸出用例 ID、準確 pytest node ID、執行數量和
   `report/sync/<時間>/allure-results` 路徑。

6. 變化用例執行失敗時，已經通過 collection 的 Feature 修改會保留，控制台
   會給出準確重跑命令，並提示查看 Task 13 分類、失敗截圖、Allure、Step、
   Page/Flow 和 YAML Locator。同步器不會自動修改 Locator。

7. 可選回滾測試：只在 Excel 修改 Scenario Title，但不更新 Python 中對應的
   `@scenario` 綁定，然後執行 `--apply`。預期 collection 失敗並退出 `2`，
   Feature 從備份恢復且鎖檔案被清理。Excel 不會回滾，因此修正標題前
   `--check` 仍會報告 drift。

8. 演練完成後恢復提交態基線：

   ```bash
   git restore data/test_cases.xlsx
   uv run python scripts/sync_engine.py --apply
   uv run python scripts/sync_engine.py --check
   git status --short
   ```

   真實用例修改不要執行 `git restore`。`git status --short` 中，`M` 表示已跟蹤
   檔案發生修改，`??` 表示未跟蹤的新檔案。`uv` 可能生成 `uv.lock`；它是依賴
   鎖檔案，不是同步器產物，建議檢查後與用例修改分開提交。

命令退出碼：`0` 表示零漂移或執行成功；`1` 表示 check 發現 drift，或者變化
用例執行失敗；`2` 表示驗證、collection、鎖或 I/O 異常。

無需 Appium 或裝置即可執行 Task 14 單元測試：

```bash
uv run pytest -m unit tests/unit/test_sync_engine.py -q
```

## 測試覆蓋

| 功能 | P0 | P1 | 合計 | 覆蓋內容 |
|---|---:|---:|---:|---|
| 首頁 → 添加交易 | 4 | 1 | 5 | 支出、收入、轉賬、空金額驗證、自訂類別、持久化和月度匯總 |
| 交易列表 | 0 | 2 | 2 | 按類型篩選、按日期分組 |
| **合計** | **4** | **3** | **7** | Android/iOS 共用業務場景 |

## 分層架構

```text
需求
  ↓
Feature Files（Gherkin）
  ↓
Step Definitions（pytest-bdd）
  ↓
Flow（業務編排和業務斷言）
  ↓
Page Object（頁面交互）
  ↓
Driver Wrapper（Appium）
  ↓
UiAutomator2 / XCUITest
  ↓
Trackify App
```

核心原則：

- Step Definition 不直接呼叫 Appium；
- Flow 組合 Page 並表達業務預期；
- Page 使用顯式等待，不使用固定睡眠；
- 平台差異留在 Locator、Page 和 Driver 層；
- 每條場景都從清潔資料庫和一致 onboarding 基線開始。

## 快速開始

### 前置條件

- Python 3.11+
- Node.js LTS
- Android SDK / Platform Tools
- Xcode 和 Command Line Tools（執行 iOS 時）
- 已啟動的 Android/iOS 裝置
- Android APK：`app/app-release.apk`
- iOS 模擬器應用：`app/Runner.app`

### 安裝

```bash
git clone https://github.com/zhongweizhou/trackify-automation.git
cd trackify-automation

brew install uv
uv sync
npm install -g appium allure-commandline
appium driver install uiautomator2
appium driver install xcuitest
```

啟動 Appium 的終端必須能讀取 Android SDK 環境變量：

```bash
export ANDROID_HOME="${ANDROID_HOME:-$HOME/Library/Android/sdk}"
export ANDROID_SDK_ROOT="$ANDROID_HOME"
appium
```

## CI

`.github/workflows/ci.yml` 提供兩層驗證：

- push 到 `test`、Pull Request 和手動觸發時，安裝依賴、執行無需裝置的矩陣
  分片、失敗歸因和同步單元測試，拒絕 Excel drift，並收集全部 7 個 BDD
  場景；
- 設定 `TRACKIFY_APK_URL` 後，在 Android API 34 模擬器中執行完整 E2E；
- 上傳 Allure 原始結果、HTML 報告、失敗截圖和 Appium 日誌；
- 未設定 APK secret 時只跳過移動 E2E，測試收集仍然作為合併門禁。

## 已驗證結果

真實矩陣執行結果：

```text
環境：preprod
Android 17：7 passed / 0 failed
iOS 26.5：   7 passed / 0 failed
總計：       14 次裝置維度用例執行全部通過
```

詳細資料見[測試報告示例](docs/reports/device-matrix-preprod-sample.md)。

## 更多文件

- [完整技術規格](docs/TECHNICAL_SPEC.zh-HK.md)
- [架構和取捨](docs/DESIGN.zh-HK.md)
- [功能探索記錄](docs/Feature_Inventory.zh-HK.md)
- [擴展路線](docs/SCALING.md)
- [專案復盤](docs/REFLECTION.zh-HK.md)

---

## 支援這個專案

如果這個開源專案幫你少踩了一些坑，或者節省了環境搭建與問題排查時間，歡迎
自願請我喝一杯 **10 元的蜜雪冰城**。打賞完全自願，不影響專案使用、問題
回應或功能優先級。Star、Issue 和 Pull Request 也都是對專案很有價值的支援。

<table>
  <tr>
    <td align="center">
      <strong>支付寶</strong><br><br>
      <img src="docs/assets/donate/alipay.png" alt="支付寶打賞二維碼" width="260">
    </td>
    <td align="center">
      <strong>微信支付</strong><br><br>
      <img src="docs/assets/donate/wechat-pay.png" alt="微信支付打賞二維碼" width="260">
    </td>
  </tr>
</table>

# 任務 13:失敗案例顧問式歸類(Advisory Failure Triage)

## 目的

任務 13 用於縮短回歸案例失敗到第一次有效除錯動作之間的時間。它僅將
pytest 中**第一個**失敗階段分類為 `Locator`、`App Bug`、`Env`、`Script`、
`Data` 或 `Unknown` 之一,然後在終端與 Allure 顯示相同的顧問式結果。

它不是案例產生器,也不是自動修復系統。**它絕不**改變 pytest 結果、
重試案例、修改 locator、隱藏 traceback,或自動送出缺陷單。**通過的
案例不會觸發歸類**。

## 執行流程

```text
setup/call/teardown 失敗
          |
          v
擷取原始例外 + 受限 traceback
          |
          +-- call 階段:先擷取失敗截圖
          |
          v
確定性本地特徵比對
          |
          +-- 信心度 >= 0.70 --> 本地判定
          |
          +-- 信心度 < 0.70
                    |
                    +-- LLM 關閉/設定缺失 --> disabled Unknown
                    |
                    +-- LLM 開啟 --> 一次受限的 MiniMax/Anthropic 請求
                                              |
                                              +-- 合法 JSON --> llm 判定
                                              +-- 錯誤/非法 JSON --> 安全回退 Unknown
          |
          v
終端輸出一行 + Allure "AI Triage" JSON 附件
          |
          v
原始 pytest PASSED/FAILED 狀態保持不變
```

第一個失敗階段會寫入 pytest item 的 stash,因此 setup 階段的失敗不
會重複觸發 call/teardown 的診斷。call 階段的截圖會在歸類之前擷取,
只有其**是否可用**與**基礎檔名**可以進入 LLM 提示詞;影像位元組與
絕對路徑**絕不**上傳。

## 使用者看到的內容

終端只會收到一行簡潔輸出:

```text
[AI Triage] Locator (98%): Matched local failure signature 'element_missing'.
```

Allure 案例中包含一份 `AI Triage` JSON 附件,欄位如下:

| 欄位 | 說明 |
|---|---|
| `test_name`、`phase` | 失敗的案例以及 `setup`、`call` 或 `teardown` 階段 |
| `category`、`confidence` | 顧問式分類結果與受限信心度 |
| `reasoning`、`next_action` | 分類理由與下一步除錯動作 |
| `classifier` | `local`、`llm` 或 `disabled` |
| `matched_signatures` | 確定性特徵 ID;LLM/disabled 結果下為空 |

| Classifier | 說明 | 建議動作 |
|---|---|---|
| `local` | 高信心度的確定性特徵命中;未發生 API 呼叫 | 按報告的 action 操作,並查看原始證據 |
| `llm` | 本地訊號模糊,已嘗試呼叫一個已設定的相容 API | 結合 traceback/截圖一起評估模型建議 |
| `disabled` | 訊號模糊,但 opt-in 開關、key 或 model 缺失 | 設定 fallback 或改為人工歸類 |

## 典型回歸範例

| 失敗證據 | 大概率結果 | 價值 |
|---|---|---|
| setup 階段 Appium 連線被拒 | `Env / local` | 把排查方向引導到伺服器/裝置設定 |
| Page 內出現 `NoSuchElementException` | `Locator / local` | 指向 YAML locator 與當前頁面 source |
| 月度彙總期望值與顯示值不一致 | 當具備業務上下文時為 `App Bug / local` | 提示比對需求並手動重現 |
| Flow 或 Page 中出現 `TypeError` | `Script / local` | 把排查方向引導到自動化實作 |
| 不帶上下文的裸 `AssertionError` | 啟用 LLM 時為 `llm`,否則為 `disabled` | 僅在證據模糊時才使用相容模型 |

## 安全的 MiniMax 設定

複製倉庫裡已經提交的佔位檔,真實設定僅保留在本地:

```bash
cp .env.example .env
chmod 600 .env
```

在 `.env` 中設定,不要提交該檔案:

```bash
AI_TRIAGE_LLM_ENABLED=1
ANTHROPIC_BASE_URL=https://api.minimaxi.com/anthropic
ANTHROPIC_API_KEY=<local-secret>
ANTHROPIC_MODEL=MiniMax-M3
SSL_CERT_FILE=/etc/ssl/cert.pem
```

只有當本地 Python 環境回報 TLS 憑證校驗失敗,且該 CA bundle 存在時,
才需要 `SSL_CERT_FILE`。**任何情況下都不得關閉憑證校驗**。

專案不會自動載入 `.env`,每次新開終端都需要手動載入:

```bash
set -a
source .env
set +a
```

檢查設定(不要列印金鑰):

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

## 驗證

執行完整的、不依賴裝置的 Task 13 回歸:

```bash
.venv/bin/pytest -m unit tests/unit/test_triage.py -q
```

驗證本地、零網路的判定路徑:

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

預期證據包含 `category=Locator`、`classifier=local`、信心度 `0.98`,
以及簽名 `element_missing`。

使用刻意模糊的輸入驗證相容 LLM 即時回退:

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

`classifier=llm` 表示確實嘗試了網路回退。模型回傳合法時,會得到受限
的 reasoning/action。模型輸出不符合嚴格格式時,仍回傳
`llm / Unknown / 0.0`,且永遠不會改變測試結果。

針對一次真實的行動回歸,先載入 `.env`,然後正常執行 pytest 或裝置
矩陣,最後用 `allure open` 開啟失敗的 Allure 案例,結合原始 traceback
和截圖一起檢視 `AI Triage` 附件。

## 故障排除

| 現象 | 原因 | 動作 |
|---|---|---|
| `classifier=disabled` | 開關未設為 `1`,未 source `.env`,或 key/model 缺失 | 載入 `.env` 並重新執行安全設定檢查 |
| `HTTP 401` | API key 無效/未載入 | 重新生成本地 key 並 source `.env`;不要列印它 |
| `HTTP 429` | 配額或限流 | 檢查 provider 配額;不要在測試報告裡加自動重試 |
| TLS 校驗失敗 | Python 的 CA bundle 缺失 | 設定合法的 `SSL_CERT_FILE`;**不要**關閉校驗 |
| 連線/逾時 | 端點、DNS、代理或網路問題 | 檢查 Base URL 與網路鏈路 |
| 回傳非法回應 | 模型輸出不滿足嚴格 JSON 契約 | 保持 `Unknown`,檢視原始失敗,先統計頻次再調整策略 |

## 隱私與可靠性邊界

- 錯誤訊息最長 2,000 字元,traceback 最長 12,000 字元。
- 授權標頭、key、token 與 URL query 會被遮罩。
- 例外文字視為不可信的 prompt 資料。
- 僅允許發起一次 LLM 請求,無重試,總逾時 5 秒。
- Unknown/網路/模型例外永遠不能取代原始 pytest 失敗。
- 模型建議只是除錯假設,不是確認後的根因。
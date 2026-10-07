# 郵輪特價追蹤 Cruise Bargain Tracker

追蹤 [Vacations To Go](https://www.vacationstogo.com/) 與 [CruiseDirect](https://www.cruisedirect.com/) 的亞洲航線價格，
自動評分找出特價，每週用 Telegram 推送摘要。設計說明見 [`docs/DESIGN.md`](docs/DESIGN.md)。

## 目前進度

| 模組 | 狀態 |
|---|---|
| 資料庫、港口／區域／郵輪公司資料、跨站配對 | ✅ 完成 |
| 評分引擎（同類比較、跌價、新低、跨站價差、尾艙） | ✅ 完成 |
| 網頁：今日推薦、探索、價格走勢、我的追蹤、系統狀態；美金價 hover 顯示台幣 | ✅ 完成 |
| Telegram 週報、台灣銀行匯率 | ✅ 完成（尚未對真實服務測試） |
| 每日排程、抓取健康檢查、原始頁面備份 | ✅ 完成 |
| Docker（ARM64 / QNAP TS-932X） | ✅ 檔案完成（尚未實機建置） |
| **VTG 抓取解析** | ⏳ 骨架完成，等網站偵察結果 |
| **CruiseDirect 抓取解析** | ⏳ 骨架完成，等網站偵察結果 |

在真正的抓取模組完成前，可以用 `demo` 示範資料（價格是編的）試用整個系統。

## 先用示範資料試玩（任何電腦）

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
cruise scrape --source demo     # 匯入示範航次並評分
cruise digest                   # 在終端機印出週報內容
cruise serve --no-scheduler     # 打開 http://localhost:8000
```

## 網站偵察（請你協助的一步）

開發環境連不到兩個網站，需要在你的電腦上錄下網站實際回傳的內容：

```bash
pip install playwright && playwright install chromium
python scripts/recon.py
```

會跳出瀏覽器，依照 `scripts/recon.py` 開頭的步驟操作（搜尋亞洲航線、點開一筆、登入 VTG 看 90-Day Ticker、到 CruiseDirect 重複），
完成後回終端機按 Enter，把產生的 `recon_output/` 資料夾壓縮傳回即可。程式只錄網站「回應」，不會錄你輸入的密碼。

## 部署到 QNAP TS-932X

1. App Center 安裝 **Container Station**。
2. 把這個 repo 放到 NAS，例如 `/share/Container/cruise-tracker`（File Station 上傳，或 SSH `git clone`）。
3. 複製 `.env.example` 為 `.env`，填入：
   - `VTG_EMAIL` / `VTG_PASSWORD`：Vacations To Go 帳號
   - `TELEGRAM_BOT_TOKEN`：在 Telegram 找 @BotFather 建 bot 取得
   - `TELEGRAM_CHAT_ID`：先傳任一訊息給你的 bot，再執行 `docker compose run --rm cruise-tracker cruise telegram-chat-id` 取得
   - `SOURCES`：真實抓取模組完成前先填 `demo`
4. SSH 進 NAS，在資料夾內執行：
   ```bash
   docker compose up -d --build
   ```
   （或在 Container Station →「應用程式」→「建立」，貼上 `docker-compose.yml`。）
5. 在區網打開 `http://<NAS IP>:8000`。要在外面看，建議用 QNAP 的 VPN 或 Tailscale，不要直接開 port。

排程（台灣時間）：每天 03:30 抓價、每週一 09:00 發 Telegram 週報，可在 `.env` 改。
資料都在 `./data`（SQLite 資料庫＋壓縮的原始頁面），備份這個資料夾即可。

## 常用指令

```bash
cruise scrape [--source vtg|cruisedirect|demo]   # 立即抓取＋評分
cruise score                                     # 只重算分數
cruise digest [--send]                           # 預覽／發送週報
cruise serve [--no-scheduler]                    # 網頁＋排程
pytest                                           # 測試
```

## 程式結構

```
src/cruise_tracker/
  adapters/      各網站抓取模組（vtg、cruisedirect、demo）
  normalize.py   船名、艙等、港口、區域、跨站配對鍵
  ingest.py      存航次／價格快照、抓取健康檢查
  scoring.py     特價評分與推薦理由
  watches.py     追蹤條件比對
  fx.py          台灣銀行匯率
  notify/        Telegram 與週報
  pipeline.py    每日工作；scheduler.py 排程
  web/           FastAPI 網頁
scripts/recon.py 網站偵察工具
```

# Smart HR MCP 串接文件

## 1. 用途

Smart HR MCP Server 讓中控或 AI 介面以標準工具呼叫既有請假功能。MCP 不取代
Django API 或 PostgreSQL；兩種介面共用相同的使用者、假別、額度、日期、時數、
附件與簽核規則。

```text
文字或語音
  → 中控 AI 解析意圖
  → Smart HR MCP Tools
  → Django 請假規則
  → PostgreSQL
```

語音模式先在中控端轉成文字，後續流程與文字請假相同。

## 2. 連線資訊

| 項目 | 值 |
|---|---|
| Protocol | Model Context Protocol |
| Transport | Streamable HTTP |
| Production URL | `https://smart-hr-api-8rxh.onrender.com/mcp` |
| Local URL | `http://127.0.0.1:8000/mcp` |
| Authorization | `Authorization: Bearer <central-token>` |
| Content type | `application/json` |

未提供、無效或過期 Token 時，MCP Endpoint 回傳 `401 Unauthorized`。使用者
身分只從 Token 的 `external_user_id`、`user_id` 或 `sub` 取得，Tool 不接受
模型自行指定員工編號。

## 3. Tools

### `get_current_user`

取得目前登入者的姓名、角色、部門、主管與權限。中控在開始操作前應先呼叫，
確認使用者具備 `leave.apply` 權限。

### `list_leave_types`

列出啟用中的假別與以下規則：

- 最小申請單位
- 是否扣額度
- 是否需要主管簽核
- 是否要求附件
- 是否允許時數請假
- 是否允許年度結轉

### `get_leave_balance`

查詢目前員工指定年度的分配、結轉、已使用與剩餘額度。不傳 `year` 時使用今年。

### `preview_leave_request`

驗證請假內容並建立短效草稿，不會建立正式請假紀錄。

必要欄位：

```json
{
  "leave_type": "特休假",
  "start_date": "2026-08-26",
  "end_date": "2026-08-26",
  "start_time": "下午",
  "end_time": "下午",
  "reason": "家庭事務"
}
```

回應包含 `draft_id`、`expires_at` 與摘要。中控必須把相對日期轉成明確日期後顯示
給使用者，例如將「下週三」顯示為「2026/08/26（星期三）」。

### `submit_leave_request`

只有使用者明確確認預覽摘要後才可呼叫：

```json
{"draft_id": "預覽回傳的 UUID"}
```

草稿預設 10 分鐘有效，且只能成功送出一次。重複呼叫、過期或使用其他人的
`draft_id` 都會失敗。

### `list_my_leave_requests`

列出目前員工最近 1～50 筆請假與審核狀態，預設 10 筆。

### `withdraw_leave_request`

撤回目前員工自己的待審核申請：

```json
{"request_id": 123}
```

已核准、已退回、已撤回或其他員工的申請都不能撤回。

## 4. 建議對話流程

使用者：

> 我下週三下午想請半天特休，家裡有事。

中控應依序執行：

1. 呼叫 `get_current_user`。
2. 呼叫 `list_leave_types` 或使用有效的短期快取。
3. 將相對日期解析成 `YYYY-MM-DD`。
4. 呼叫 `preview_leave_request`。
5. 顯示假別、實際日期、時段、天數、原因與剩餘額度。
6. 詢問「是否確認送出？」。
7. 只有得到明確肯定答覆，才呼叫 `submit_leave_request`。
8. 顯示申請編號與目前狀態。

使用者修改任何欄位時，必須重新呼叫預覽，不可沿用舊 `draft_id`。

## 5. 錯誤處理

| 情況 | 中控處理方式 |
|---|---|
| `401` | Token 無效或過期，要求重新登入 |
| 找不到綁定帳號 | 顯示帳號尚未綁定 Smart HR |
| 日期或時數不合法 | 將 Tool 的錯誤訊息轉告使用者並重新收集欄位 |
| 額度不足 | 不可送出，顯示剩餘額度 |
| 需要附件 | 請使用者上傳符合格式的附件後重新預覽 |
| 草稿過期 | 重新呼叫預覽並再次確認 |
| 草稿已送出 | 查詢請假紀錄，不可重複建立 |

## 6. 本機啟動與測試

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
uvicorn config.asgi:application --host 127.0.0.1 --port 8000
```

另一個終端執行展示流程：

```powershell
python scripts/test_mcp_flow.py --base-url http://127.0.0.1:8000
```

腳本會取得展示用短效 Token、列出 Tools、查詢目前使用者、預覽請假、確認送出，
最後撤回測試申請，避免影響待審核數字。

## 7. 正式中控切換

正式環境關閉 `ENABLE_MOCK_CENTRAL`，並設定真正的：

- `CENTRAL_TOKEN_VERIFY_URL`
- `CENTRAL_API_KEY`
- `MCP_AUTH_ISSUER_URL`
- `MCP_PUBLIC_URL`
- `MCP_ALLOWED_HOSTS`
- `MCP_ALLOWED_ORIGINS`

中控驗證回應至少需要：

```json
{
  "active": true,
  "external_user_id": "company-user-001"
}
```

該識別碼必須預先綁定 Smart HR 使用者。系統不會根據 AI 或 Token 自動建立員工。

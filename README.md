# 家計簿Webアプリ (FastAPI + SQLite)

Excel運用の家計簿をローカルWebアプリへ移行するための実装です。

## 主な機能

- 年次メイン画面 (`/`): 年間収支サマリ、資産一覧、負債一覧、月次ページ遷移
- 月次画面 (`/month/{year}/{month}`): 月間サマリ、取引一覧、取引追加/編集/削除
- 月初残高画面 (`/opening-balances/{year}/{month}`): 出所ごとの月初開始残高を表形式で入力
- 月ロック: ロック中の月は取引・月初残高の更新を禁止
- 設定画面 (`/settings`): 出所(Account)/カテゴリ/負債の追加・有効/無効
- REST API (`/api/...`): 取引、集計、マスタ、CSV入出力
- CSV import/export (UTF-8, ヘッダあり)

## セットアップ

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

## 一括セットアップ + 起動

```bash
./scripts/bootstrap.sh
```

- 実行内容: `venv作成` → `依存インストール` → `alembic upgrade head` → `pytest` → `uvicorn起動`
- テストを省略したい場合:

```bash
SKIP_TESTS=1 ./scripts/bootstrap.sh
```

- ポート変更したい場合:

```bash
PORT=8080 ./scripts/bootstrap.sh
```

## DB初期化

### Alembicで作成

```bash
alembic upgrade head
```

### またはアプリ起動時に自動作成

起動時に `Base.metadata.create_all()` が実行され、初期カテゴリが投入されます。

## 起動

```bash
uvicorn app.main:app --reload
```

- メイン画面: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- APIドキュメント: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

## API一覧

### 集計
- `GET /api/summary/year/{year}`
- `GET /api/summary/month/{year}/{month}`

### 取引
- `GET /api/transactions?year=2026&month=2&limit=100&offset=0&q=`
- `POST /api/transactions`
- `PUT /api/transactions/{id}`
- `DELETE /api/transactions/{id}`

### 出所/カテゴリ/負債
- `GET/POST/PUT/DELETE /api/accounts`
- `POST /api/accounts/import-json` (支払い元のJSON一括登録)
- `GET/POST/PUT/DELETE /api/categories`
- `GET/POST/PUT/DELETE /api/liabilities`

### 月初残高
- `GET /api/monthly-balance/{year}/{month}` (出所ごとの一覧)
- `PUT /api/monthly-balance/{year}/{month}` (`account_id` 指定で更新)

### CSV
- `POST /api/csv/import`
- `GET /api/csv/export?year=...&month=...`

### 月ロック
- `GET /api/month-lock/{year}/{month}`
- `PUT /api/month-lock/{year}/{month}`

## DBテーブル

- `users` (将来ログイン拡張用、初期は `id=1` 固定)
- `accounts`
- `categories`
- `monthly_balances` (年月 + 出所単位)
- `transactions`
- `liabilities`
- `cards` (将来拡張)

詳細は `app/db/models.py` と `app/db/migrations/versions/0001_initial.py` を参照してください。

## CSV仕様 (transactions)

ヘッダ固定:

```text
date,type,amount,account,to_account,category,category_free,description,note
```

- `date`: `YYYY-MM-DD`
- `type`: `income | expense | transfer | adjust`
- `amount`: 正の整数円
- `account`: 出所名
- `to_account`: transfer時の移動先
- `category`: 辞書カテゴリ名
- `category_free`: 自由入力カテゴリ
- `description`: 内容メモ
- `note`: 備考

インポート時に `account/category` 名称が未登録の場合は自動作成されます。

## 運用メモ

- `transfer` は記録されますが収支には含みません。
- `adjust` は収支から分離し、月次サマリで別表示します。
- 取消/修正は上書き更新です (履歴テーブルなし)。
- 未来日付の取引は登録不可です。
- 月次ページは未来の月を表示・アクセスしません（例: 2026年2月時点では2026年は2月まで、2025年は12月まで）。
- 設定画面の削除は物理削除です（一覧に残りません）。

## テスト

```bash
pytest
```

- `tests/test_summary.py`: 集計ロジック
- `tests/test_csv_io.py`: CSV入出力

## サンプルデータ投入

```bash
python scripts/seed_example.py
```

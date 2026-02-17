# 技術サマリー

最終更新: 2026-02-16

## 1. 構成
- Backend: FastAPI
- Database: SQLite
- ORM: SQLAlchemy
- Migration: Alembic
- Frontend: Jinja2 + HTMX
- Test: pytest

## 2. 機能概要
- 年次メイン画面（収支サマリ、支払い元一覧、負債一覧、月次導線）
- 月次画面（取引一覧、取引追加/編集/削除、月ロック）
- 月初開始残高画面（支払い元ごとの入力、カード除外）
- 設定画面（支払い元/カテゴリ/負債の追加・選択削除）
- CSVインポート/エクスポート
- 支払い元JSONインポート（テンプレート同梱）

## 3. 主なデータモデル
- `users`
  - 簡易認証用ユーザー
- `accounts`
  - 支払い元（現金/銀行/プリペイド等）
- `categories`
  - 取引カテゴリ
- `transactions`
  - 収入/支出/移動/調整
- `monthly_balances`
  - 月初開始残高（`year + month + account_id` 単位）
- `monthly_locks`
  - 月ロック状態（`year + month` 単位）
- `liabilities`
  - 負債管理
- `cards`
  - 将来拡張用

## 4. ロック・入力制約
- 月ロックON時:
  - 取引の追加/編集/削除を禁止
  - 月初開始残高の更新を禁止
  - API経由の更新も禁止
- 未来日付の取引登録を禁止
- 未来月のページ表示・直接アクセスを禁止
  - 例: 現在月が 2026-02 の場合、2026年は2月まで表示
  - 過去年（例: 2025年）は12月まで表示

## 5. 認証
- `/login` と `/logout` を提供
- 未ログイン時:
  - 画面アクセスは `/login` へリダイレクト
  - `/api/*` は `401` を返却
- 方式:
  - Cookieベースの簡易セッション（ユーザーIDをCookieで保持）
- 初期ユーザー:
  - username: `default`
  - password: `admin`

## 6. API（主要）
- 集計:
  - `GET /api/summary/year/{year}`
  - `GET /api/summary/month/{year}/{month}`
- 取引:
  - `GET /api/transactions`
  - `POST /api/transactions`
  - `PUT /api/transactions/{id}`
  - `DELETE /api/transactions/{id}`
- 支払い元:
  - `GET/POST/PUT/DELETE /api/accounts`
  - `POST /api/accounts/import-json`
- カテゴリ:
  - `GET/POST/PUT/DELETE /api/categories`
- 負債:
  - `GET/POST/PUT/DELETE /api/liabilities`
- 月初残高:
  - `GET /api/monthly-balance/{year}/{month}`
  - `PUT /api/monthly-balance/{year}/{month}`
- 月ロック:
  - `GET /api/month-lock/{year}/{month}`
  - `PUT /api/month-lock/{year}/{month}`
- CSV:
  - `POST /api/csv/import`
  - `GET /api/csv/export`

## 7. UI方針（現状）
- サーバーサイド描画中心（Jinja2）
- JS依存を最小化し、HTMXは軽量利用
- 画面はレスポンシブ対応
- 最近の調整で、テーブル/フォーム/カードの可読性を強化

## 8. 運用
- 一括セットアップ起動:
  - `./scripts/bootstrap.sh`
- テスト:
  - `pytest`
- マイグレーション:
  - `alembic upgrade head`

## 9. 補足
- 設計はAPI分離済みのため、将来的なフロント完全分離（React/Vue等）に移行しやすい構造。

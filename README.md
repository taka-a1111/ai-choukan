# AIトレンド朝刊

国内外のAIニュース・雑誌Web版・YouTubeを毎朝集めて要約する、高崎（インフォサクセス）用の朝刊アプリ（PWA）。

- 公開: Vercel（このリポジトリを連携）
- 紙面データ: `data/`（毎朝の自動実行がコミットする）
  - `index.json` 発行日の一覧、`issues/YYYY-MM-DD.json` その日の記事、`sources.json` 情報源、`status.json` 収集状況、`seen.json` 掲載済みの記事ID
- 収集・組み立てスクリプト: `tools/collector.py`、`tools/build_issue.py`（外部AI APIは使わない）

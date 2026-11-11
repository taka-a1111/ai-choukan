# AIトレンド朝刊 投稿済みの記録 ver1.0 (2026-11-11) 投稿が終わったら、下書きに投稿先のURLを書く（アプリに「投稿済み」と出る）
# 使い方: python3 tools/mark_posted.py --date YYYY-MM-DD --repo <リポジトリのdir> [--note-url URL] [--x-url URL ...]
#   すでに記録がある項目は、渡した値で上書きする。渡さなかった項目は残す。
import argparse, json, os
from datetime import datetime, timezone, timedelta

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--note-url")
    ap.add_argument("--x-url", action="append")
    a = ap.parse_args()
    path = os.path.join(a.repo, "data", "posts", f"{a.date}.json")
    P = json.load(open(path, encoding="utf-8"))
    posted = P.get("posted") or {}
    if a.note_url:
        posted["note_url"] = a.note_url
    if a.x_url:
        posted["x_urls"] = a.x_url
    posted["at"] = datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%dT%H:%M+09:00")
    P["posted"] = posted
    json.dump(P, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("OK:", json.dumps(posted, ensure_ascii=False))

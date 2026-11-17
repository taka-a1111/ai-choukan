# AIトレンド朝刊 最新の週1まとめのURL ver1.0 (2026-11-17) X の朝の1本の末尾に足す note のURL（公開済みの週1まとめのうち、D 以前で一番新しいもの）を出す
# 使い方: python3 tools/latest_weekly.py --date YYYY-MM-DD --repo <リポジトリのdir>
#   見つかれば1行目にURL、2行目にその週1まとめの日付とタイトル。無ければ何も出さない（終了コード0）
#   日曜は、その日の週1まとめを公開したあとに使う（その日の URL が出る）
import argparse, glob, json, os

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    ap.add_argument("--repo", required=True)
    a = ap.parse_args()
    best = None
    for f in sorted(glob.glob(os.path.join(a.repo, "data", "posts", "*.json"))):
        d = os.path.basename(f)[:10]
        if d > a.date:
            continue
        try:
            P = json.load(open(f, encoding="utf-8"))
        except Exception:
            continue
        u = (P.get("posted") or {}).get("note_url")
        if P.get("kind") == "weekly" and u:
            best = (d, u, (P.get("note") or {}).get("title", ""))
    if best:
        print(best[1])
        print(f"{best[0]} {best[2]}")

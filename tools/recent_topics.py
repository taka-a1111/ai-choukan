# AIトレンド朝刊 既報の話題の一覧と重なりの検査 ver1.0 (2026-11-11) 初版 — 同じ話題を日をまたいで二重に載せないための材料を出す
# 使い方:
#   python3 tools/recent_topics.py --repo <リポジトリのdir> --date YYYY-MM-DD [--days 4] --out recent.txt
#       直近 days 日分の号（今日の号がすでにあれば今日も）の話題を「日付|話題ID|重要度|出典数|見出し」＋ lead ＋ 要点 で書き出す。
#   python3 tools/recent_topics.py --repo <dir> --date YYYY-MM-DD --check groups.json（または topics.json）
#       今日の話題どうし、今日の話題と既報の話題で、固有名詞が重なる組を「要確認」として出す（機械的な目安。最後は中身を読んで決める）。
import argparse, glob, json, os, re

STOP = set("AI LLM API CEO IT PC Web GPU OS App Google OpenAI Anthropic Meta Microsoft Apple Amazon NVIDIA ChatGPT Claude Gemini "
           "エージェント モデル サービス ツール データ アプリ システム ニュース ビジネス ユーザー チャット コード テスト".split())


def keys(text):
    ks = set()
    for w in re.findall(r"[A-Za-z][A-Za-z0-9.\-]{2,}|[ァ-ヴー]{4,}|[一-龥]{3,}", text or ""):
        if w not in STOP:
            ks.add(w.lower())
    return ks


def load_recent(repo, date, days):
    out = []
    files = sorted(glob.glob(os.path.join(repo, "data", "issues", "*.json")))
    files = [f for f in files if os.path.basename(f)[:10] <= date][-(days + 1):]
    for f in files:
        try:
            d = json.load(open(f, encoding="utf-8"))
        except Exception:
            continue
        for t in d.get("topics", []):
            n = len(t.get("item_ids", []))
            if n < 2 and (t.get("importance") or 1) < 2:
                continue
            out.append({"date": d.get("date"), "id": t.get("id"), "i": t.get("importance"), "n": n, "title": t.get("title", ""),
                        "lead": t.get("lead", ""), "points": t.get("points", [])})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--date", required=True)
    ap.add_argument("--days", type=int, default=4)
    ap.add_argument("--out", default="")
    ap.add_argument("--check", default="")
    a = ap.parse_args()
    rec = load_recent(a.repo, a.date, a.days)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            for r in rec:
                f.write(f"{r['date']}|{r['id']}|重要度{r['i']}|出典{r['n']}|{r['title']}\n  {r['lead']}\n")
                for p in r["points"]:
                    f.write(f"  ・{p}\n")
        print(f"recent topics: {len(rec)} -> {a.out}")
    if a.check:
        today = json.load(open(a.check, encoding="utf-8"))
        tk = [(t.get("key") or f"#{n}", t.get("t", ""), keys(t.get("t", "") + " " + t.get("lead", ""))) for n, t in enumerate(today)]
        hits = 0
        for x in range(len(tk)):
            for y in range(x + 1, len(tk)):
                c = tk[x][2] & tk[y][2]
                if len(c) >= 2:
                    hits += 1
                    print(f"要確認（今日どうし）{tk[x][0]}「{tk[x][1]}」 × {tk[y][0]}「{tk[y][1]}」 共通: {'、'.join(sorted(c))}")
        for k, title, ks in tk:
            for r in rec:
                c = ks & keys(r["title"] + " " + r["lead"])
                if len(c) >= 2:
                    hits += 1
                    print(f"要確認（既報）{k}「{title}」 × {r['date']} {r['id']}「{r['title']}」 共通: {'、'.join(sorted(c))}")
        print(f"check: {hits} 組")


if __name__ == "__main__":
    main()

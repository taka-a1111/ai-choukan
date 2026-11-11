# AIトレンド朝刊 既報の話題の一覧と重なりの検査 ver1.1 (2026-11-12) 検査に単独記事（話題に入れていない記事）を自動で含める／「」の中の名前が同じ組も出す／続報の要点が既報と同じ数字だけのとき知らせる — 同じ話題を日をまたいで二重に載せないための材料を出す
# 使い方:
#   python3 tools/recent_topics.py --repo <リポジトリのdir> --date YYYY-MM-DD [--days 4] --out recent.txt
#       直近 days 日分の号（今日の号がすでにあれば今日も）の話題を「日付|話題ID|重要度|出典数|見出し」＋ lead ＋ 要点 で書き出す。
#   python3 tools/recent_topics.py --repo <dir> --date YYYY-MM-DD --check groups.json（または topics.json）
#       今日の話題どうし、今日の話題と既報の話題で、固有名詞が重なる組を「要確認」として出す（機械的な目安。最後は中身を読んで決める）。
#       検査するファイルと同じフォルダに out/news.json と enrich_news.json があれば、どの話題にも入れていない単独記事（載せる記事）も
#       「単独n<添字>」として検査に含める（重要度2の単独記事どうしが同じ発表、という見落としを防ぐ）。drop.json に入れた記事は除く。
#       続報（prev つき）の要点が、既報の話題に出ている数字だけでできているときは「既報と同じ内容の恐れ」と知らせる。
import argparse, glob, json, os, re

STOP = set("AI LLM API CEO IT PC Web GPU OS App Google OpenAI Anthropic Meta Microsoft Apple Amazon NVIDIA ChatGPT Claude Gemini "
           "エージェント モデル サービス ツール データ アプリ システム ニュース ビジネス ユーザー チャット コード テスト".split())


def keys(text):
    ks = set()
    for w in re.findall(r"[A-Za-z][A-Za-z0-9.\-]{2,}|[ァ-ヴー]{4,}|[一-龥]{3,}", text or ""):
        if w not in STOP:
            ks.add(w.lower())
    return ks


def quoted(text):
    return {w.strip().lower() for w in re.findall(r"[「『]([^」』]{2,30})[」』]", text or "")}


def nums(text):
    return {n.replace(",", "").rstrip(".") for n in re.findall(r"\d[\d,\.]*", text or "") if len(n.replace(",", "").rstrip(".")) >= 2 or "." in n}


def load_singles(check_path, today):
    """話題に入れていない単独記事（載せる記事）を、検査用の見出しとして返す。"""
    base = os.path.dirname(os.path.abspath(check_path))
    try:
        news = json.load(open(os.path.join(base, "out", "news.json"), encoding="utf-8"))
        en = json.load(open(os.path.join(base, "enrich_news.json"), encoding="utf-8"))
    except Exception:
        return []
    used = {str(k) for t in today for k in t.get("news", [])}
    try:
        used |= {str(k) for k in json.load(open(os.path.join(base, "drop.json"), encoding="utf-8")).get("news", [])}
    except Exception:
        pass
    out = []
    for k, e in en.items():
        if k in used or not k.isdigit() or int(k) >= len(news):
            continue
        out.append((f"単独n{k}", e.get("t") or news[int(k)].get("title", ""), (e.get("t") or news[int(k)].get("title", "")) + " " + e.get("s", "")))
    return out


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
                        "lead": t.get("lead", ""), "points": t.get("points", []), "avail": t.get("avail", "")})
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
        tk = [(t.get("key") or t.get("into") or f"#{n}", t.get("t", ""), keys(t.get("t", "") + " " + t.get("lead", "")), quoted(t.get("t", ""))) for n, t in enumerate(today)]
        singles = load_singles(a.check, today)
        tk += [(k, title, keys(text), quoted(title)) for k, title, text in singles]
        if singles:
            print(f"単独記事 {len(singles)} 件も検査に含めた")
        hits = 0
        for x in range(len(tk)):
            for y in range(x + 1, len(tk)):
                c = tk[x][2] & tk[y][2]
                q = tk[x][3] & tk[y][3]
                if q and len(c) < 2:
                    c = q
                if len(c) >= 2 or q:
                    hits += 1
                    print(f"要確認（今日どうし）{tk[x][0]}「{tk[x][1]}」 × {tk[y][0]}「{tk[y][1]}」 共通: {'、'.join(sorted(c))}")
        for k, title, ks, _q in tk:
            for r in rec:
                c = ks & keys(r["title"] + " " + r["lead"])
                if len(c) >= 2:
                    hits += 1
                    print(f"要確認（既報）{k}「{title}」 × {r['date']} {r['id']}「{r['title']}」 共通: {'、'.join(sorted(c))}")
        # 続報の要点が、既報に出ている数字だけでできていないか
        recby = {r["id"]: r for r in rec}
        for n, t in enumerate(today):
            pv = t.get("prev") or {}
            r = recby.get(pv.get("id"))
            if not r:
                continue
            old = nums(r["title"] + " " + r["lead"] + " " + " ".join(r["points"]) + " " + r.get("avail", ""))
            for p in t.get("points", []):
                ns = nums(p)
                both = ns & old
                if ns and (ns <= old or (len(both) >= 2 and len(both) * 2 >= len(ns))):
                    hits += 1
                    print(f"要確認（続報の要点が既報と同じ内容の恐れ）{t.get('t', '')[:30]}：「{p[:50]}…」 既報にもある数字: {'、'.join(sorted(ns & old))} → 既報と同じなら要点から外す")
        print(f"check: {hits} 組")


if __name__ == "__main__":
    main()

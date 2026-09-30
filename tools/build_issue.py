# AIトレンド朝刊 紙面組み立て ver2.0 (2026-09-30)
# 収集結果＋要約を、リポジトリの data/ に書き込む（issues・index・seen・status）。
# 使い方:
#   python3 tools/build_issue.py --out <collectorの出力dir> --enrich enrich_news.json --vsum vsum.json \
#       --date YYYY-MM-DD --repo <リポジトリのdir> [--note "今回の特記事項"]
# enrich_news.json: {"<news.jsonの添字>": {"t":日本語タイトル(英語記事のみ),"s":要約,"c":カテゴリ記号,"b":業務メモ(なければ省略),"i":重要度1-3}}
#   載せない記事はキーを省略する
# vsum.json: {"<video_id>": {"title_ja","summary","points":[],"biz_tip","category","importance","via"}}
import argparse, json, os
from datetime import datetime, timezone, timedelta

JST = timezone(timedelta(hours=9))
CAT = {"M": "新モデル・研究", "T": "ツール・新機能", "K": "活用ノウハウ", "S": "SEO・検索・Web",
       "D": "開発・自動化", "B": "ビジネス・企業動向", "R": "規制・安全・社会"}
KEEP_DAYS = 60
SEEN_DAYS = 35


def load(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def save(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, separators=(",", ":"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--enrich", required=True)
    ap.add_argument("--vsum", required=True)
    ap.add_argument("--date", required=True)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--note", default="")
    a = ap.parse_args()

    news = load(os.path.join(a.out, "news.json"), [])
    videos = load(os.path.join(a.out, "videos.json"), [])
    report = load(os.path.join(a.out, "report.json"), {})
    en = load(a.enrich, {})
    vs = load(a.vsum, {})
    data = os.path.join(a.repo, "data")
    now = datetime.now(JST).isoformat(timespec="minutes")

    items = []
    for i, x in enumerate(news):
        e = en.get(str(i))
        if not e:
            continue
        items.append({"id": x["id"], "kind": "news", "src_id": x["src_id"], "src_name": x["src_name"],
                      "src_type": x["src_type"], "title": x["title"], "title_ja": e.get("t") or x["title"],
                      "url": x["url"], "published": x["published"], "category": CAT.get(e.get("c"), e.get("c")),
                      "summary": e.get("s", ""), "biz": bool(e.get("b")), "biz_tip": e.get("b", ""),
                      "importance": e.get("i", 2), "via": "Claude"})
    for v in videos:
        s = vs.get(v.get("video_id"), {})
        items.append({"id": v["id"], "kind": "video", "src_id": v["src_id"], "src_name": v["src_name"],
                      "src_type": v["src_type"], "title": v["title"], "title_ja": s.get("title_ja") or v["title"],
                      "url": v["url"], "published": v["published"], "duration": v.get("duration"),
                      "is_short": v.get("is_short", False), "category": s.get("category") or "ツール・新機能",
                      "summary": s.get("summary", ""), "points": s.get("points", []),
                      "biz": bool(s.get("biz_tip")), "biz_tip": s.get("biz_tip", ""),
                      "importance": s.get("importance", 2), "via": s.get("via", "未要約")})

    # 同じ日の再実行では既存の記事を残し、新しい記事で上書き・追加する
    issue_path = os.path.join(data, "issues", f"{a.date}.json")
    prev = load(issue_path, {}).get("items", [])
    have = {i["id"] for i in items}
    items += [p for p in prev if p.get("id") not in have]
    save(issue_path, {"date": a.date, "updatedAt": now, "items": items})

    n_news = sum(i["kind"] == "news" for i in items)
    n_vid = sum(i["kind"] == "video" for i in items)
    n_biz = sum(bool(i.get("biz")) for i in items)

    # 目次
    idx = load(os.path.join(data, "index.json"), {"dates": []})
    dates = [d for d in idx.get("dates", []) if d.get("date") != a.date]
    dates.append({"date": a.date, "news": n_news, "videos": n_vid, "biz": n_biz, "updatedAt": now})
    dates.sort(key=lambda d: d["date"], reverse=True)
    cutoff = (datetime.now(JST) - timedelta(days=KEEP_DAYS)).strftime("%Y-%m-%d")
    dates = [d for d in dates if d["date"] >= cutoff]
    save(os.path.join(data, "index.json"), {"dates": dates, "updatedAt": now})

    # 古い紙面を削除
    removed = []
    idir = os.path.join(data, "issues")
    for fn in os.listdir(idir):
        if fn.endswith(".json") and fn[:10] < cutoff:
            os.remove(os.path.join(idir, fn))
            removed.append(fn)

    # 既読管理（重複して載せないため）
    seen = load(os.path.join(data, "seen.json"), {"h": {}})
    h = seen.get("h", {})
    for x in news + videos:
        h.setdefault(x["id"], a.date)
    scut = (datetime.now(JST) - timedelta(days=SEEN_DAYS)).strftime("%Y-%m-%d")
    h = {k: v for k, v in h.items() if v >= scut}
    save(os.path.join(data, "seen.json"), {"h": h})

    # 収集状況
    via = {}
    for i in items:
        if i["kind"] == "video":
            via[i["via"]] = via.get(i["via"], 0) + 1
    save(os.path.join(data, "status.json"), {"ranAt": report.get("ran_at", now), "sources": report.get("sources", []),
                                             "videoVia": via, "note": a.note})
    print(f"issue {a.date}: news={n_news} videos={n_vid} biz={n_biz} removed={removed} video_via={via}")


if __name__ == "__main__":
    main()

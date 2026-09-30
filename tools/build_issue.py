# AIトレンド朝刊 紙面組み立て ver2.1 (2026-09-30) — 同じ話題の記事をトピックにまとめる
# 収集結果＋要約を、リポジトリの data/ に書き込む（issues・index・seen・status）。
# 使い方:
#   python3 tools/build_issue.py --out <collectorの出力dir> --enrich enrich_news.json --vsum vsum.json \
#       --topics topics.json --date YYYY-MM-DD --repo <リポジトリのdir> [--note "今回の特記事項"]
# enrich_news.json: {"<news.jsonの添字>": {"t":日本語タイトル(英語記事のみ),"s":要約,"c":カテゴリ記号,"b":業務メモ(なければ省略),"i":重要度1-3}}
#   載せない記事はキーを省略する
# vsum.json: {"<video_id>": {"title_ja","summary","points":[],"biz_tip","category","importance","via"}}
# topics.json: [{"t":トピック見出し,"s":複数の出典をまとめた要約,"c":カテゴリ記号,"i":重要度,"b":業務メモ(任意),
#                "news":[news.jsonの添字...],"videos":["video_id"...]}]
#   2件以上の出典がある話題だけ書けばよい。どのトピックにも入らない記事は1件だけのトピックになる。
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
    ap.add_argument("--topics", default="")
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

    # トピック（同じ話題の記事を1つにまとめる）
    news_id = {i: x["id"] for i, x in enumerate(news)}
    vid_id = {v.get("video_id"): v["id"] for v in videos}
    kept = {i["id"] for i in items}
    topics, used = [], set()
    for n, t in enumerate(load(a.topics, []) if a.topics else []):
        ids = [news_id.get(int(k)) for k in t.get("news", [])] + [vid_id.get(k) for k in t.get("videos", [])]
        ids += t.get("item_ids", [])
        ids = [x for x in ids if x and x in kept and x not in used]
        if not ids:
            continue
        used.update(ids)
        topics.append({"id": f"t{a.date.replace('-', '')}{n:02d}", "title": t.get("t", ""), "summary": t.get("s", ""),
                       "category": CAT.get(t.get("c"), t.get("c")), "importance": t.get("i", 2),
                       "biz": bool(t.get("b")), "biz_tip": t.get("b", ""), "item_ids": ids})

    # 同じ日の再実行では既存の記事とトピックを残し、新しいもので上書き・追加する
    issue_path = os.path.join(data, "issues", f"{a.date}.json")
    prev_doc = load(issue_path, {})
    prev = prev_doc.get("items", [])
    have = {i["id"] for i in items}
    items += [p for p in prev if p.get("id") not in have]
    all_ids = {i["id"] for i in items}
    for pt in prev_doc.get("topics", []):
        ids = [x for x in pt.get("item_ids", []) if x in all_ids and x not in used]
        if ids and not any(x in have for x in pt.get("item_ids", [])):
            used.update(ids)
            topics.append({**pt, "item_ids": ids})
    # どのトピックにも入らない記事は、1件だけのトピックにする
    for it in items:
        if it["id"] in used:
            continue
        topics.append({"id": "s" + it["id"], "title": it.get("title_ja") or it["title"], "summary": "",
                       "category": it.get("category"), "importance": it.get("importance", 2),
                       "biz": bool(it.get("biz")), "biz_tip": it.get("biz_tip", ""), "item_ids": [it["id"]]})
    save(issue_path, {"date": a.date, "updatedAt": now, "items": items, "topics": topics})

    n_news = sum(i["kind"] == "news" for i in items)
    n_vid = sum(i["kind"] == "video" for i in items)
    n_biz = sum(bool(i.get("biz")) for i in items)

    # 目次
    idx = load(os.path.join(data, "index.json"), {"dates": []})
    dates = [d for d in idx.get("dates", []) if d.get("date") != a.date]
    n_topic = len(topics)
    n_biz = sum(bool(t.get("biz")) for t in topics)
    dates.append({"date": a.date, "topics": n_topic, "news": n_news, "videos": n_vid, "biz": n_biz, "updatedAt": now})
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
    print(f"issue {a.date}: topics={len(topics)} news={n_news} videos={n_vid} biz={n_biz} removed={removed} video_via={via}")


if __name__ == "__main__":
    main()

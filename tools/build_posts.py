# AIトレンド朝刊 投稿下書きの組み立て ver2.3 (2026-11-23) 週1まとめの太字の印 [[ ]] と表（note.tables）に対応。ver2.2 (2026-11-23) 日曜に出せなかった週1まとめを翌日以降に出す --makeup を追加。ver2.1 (2026-11-18) 公開前の有料noteの予告（pending_line）に対応。ver2.0 (2026-11-17) note は日曜の週1まとめ（kind=weekly）だけにし、ほかの日は X だけ（kind=daily）。有料noteの案内（data/promo.json）に対応
# 書き方の決まりは tools/POSTS_GUIDE.md。
# 使い方:
#   python3 tools/build_posts.py --posts posts.json --date YYYY-MM-DD --repo <リポジトリのdir> [--dry-run] [--any-day]
#   --dry-run は検査だけして書き込まない。--any-day は日曜以外でも週1まとめを検査できるようにする（試運転用。書き込みはしない）
#   --makeup は、日曜に出せなかった週1まとめを月曜以降に出すときに使う（日曜以外でも kind weekly を書き込める。週は D の6日前〜D）
# posts.json（毎日。月〜土は note を書かない）:
#   {"kind": "daily",
#    "main": "今日の1本の話題ID", "others": ["ほか3本の話題ID", ...],
#    "x_topics": ["X の昼の1本だけで扱う話題ID（無ければ省く）"],
#    "x": [{"label": "朝の1本", "at": "朝", "text": "投稿文"}, {"label": "昼の1本", "at": "12:15", "text": "投稿文"},
#          {"label": "今日の3つ", "at": "20:00", "text": "投稿文"}],
#    "images": {"eyecatch": {...}, "xfig": {...}}（形は tools/img_prompt.py の先頭。figs は日曜だけ）,
#    "ok_numbers": ["本文にあって号の解説にない数字のうち、確かめたうえで通すもの"]}
# 日曜（週1まとめ）は kind を "weekly" にし、上に加えて:
#    "week_topics": [{"date": "YYYY-MM-DD", "id": "話題ID"}, ...]（その週の号から4〜6本。ふつうは5本）,
#    "note": {"title": "記事タイトル", "body": "本文（見出しは行頭に ## 、話題ごとの小見出しは ### 、太字にする語は [[ ]] で囲む）",
#             "tables": [表（形は tools/note_tables.py の先頭）。0〜3個]},
#    "images": {"eyecatch": {...}, "figs": [...2枚まで], "xfig": {...}}
# 検査（1つでも外れると書き込まずに終わる。終了コード1）:
#   - 話題IDが号にあること（main・others・x_topics は D の号、week_topics はそれぞれの日の号。週は D の6日前〜D）
#   - 出典のURLが、選んだ話題の出典にあること（決まった窓口のURL（CTA_URLS）と有料noteの案内のURLは除く）
#   - 本文・投稿文・画像の文言の数字が、選んだ話題の解説にあること
#   - Xの投稿文が全角140字相当に収まること。月〜土の X には note の話を書かない（その日の note は無い）
#   - 週1まとめ：決まった見出しがあること、タイトル60字以内、本文2500〜5500字、図は2枚まで、
#     data/promo.json に URL が入っている有料noteは、その URL が本文にあること。URL が空で pending_line があるものは、その1文が本文にあること
#   - 太字記号（**）がないこと。太字の印 [[ ]] は note の本文だけで、開きと閉じがそろっていること
#   - 表（note.tables）：形（tools/note_tables.py の check）、置き場所の見出しが本文にあること、数字が選んだ話題の解説にあること
# 書き込み先: data/posts/YYYY-MM-DD.json（60日より古いものは消す）
import argparse, json, os, re, sys, unicodedata
from datetime import datetime, timezone, timedelta

JST = timezone(timedelta(hours=9))
CTA_URLS = {"https://sukizero.com", "https://infosuccess.jp"}  # 本文に毎回載せてよい窓口（スキゼロの無料診断、インフォサクセスのサイト）
KEEP_DAYS = 60
URL_RE = re.compile(r"https?://[^\s）)」】]+")
NUM_RE = re.compile(r"\d[\d,]*(?:\.\d+)?")
UNIT_RE = re.compile(r"^\s*(?:％|%|倍|円|ドル|万|億|兆|人|件|社|本|個|秒|分|時間|日|か月|ヶ月|年|種類|位|割|GB|MB)")


def norm(s):
    return unicodedata.normalize("NFKC", str(s or ""))


def x_len(text):
    """Xの重みつき文字数（全角2・半角1・URLは23）。280以内なら投稿できる。"""
    t = str(text or "")
    n = 0
    pos = 0
    for m in URL_RE.finditer(t):
        n += sum(1 if ord(c) < 0x1100 else 2 for c in t[pos:m.start()])
        n += 23
        pos = m.end()
    n += sum(1 if ord(c) < 0x1100 else 2 for c in t[pos:])
    return n


def topic_text(t, items):
    parts = [t.get("title"), t.get("lead"), t.get("why"), t.get("avail"), t.get("biz_tip"), t.get("summary")]
    parts += t.get("points") or []
    for a, b in (t.get("terms") or []):
        parts += [a, b]
    if t.get("fig"):
        parts.append(json.dumps(t["fig"], ensure_ascii=False))
    for it in items:
        parts += [it.get("title"), it.get("title_ja"), it.get("summary"), it.get("avail")]
        parts += it.get("points") or []
    return norm(" ".join(str(p) for p in parts if p))


def numbers_in(text):
    """検査の対象にする数字を取り出す。見出しの番号や「3つ」などの小さな数は対象外。"""
    out = []
    t = norm(URL_RE.sub(" ", text))
    for m in NUM_RE.finditer(t):
        raw = m.group(0)
        digits = raw.replace(",", "")
        tail = t[m.end():m.end() + 4]
        head = t[max(0, m.start() - 1):m.start()]
        if head == "/" or tail.startswith("/"):
            continue  # 日付（11/11）
        big = len(digits.replace(".", "")) >= 2
        unit = bool(UNIT_RE.match(tail))
        if tail.startswith("秒まとめ") or tail.startswith("秒セルフ"):
            continue  # 決まった見出し「30秒まとめ」「30秒セルフチェック」
        if re.match(r"^\s*(?:個|つ)", tail) and len(digits) == 1 and int(digits) <= 5:
            continue  # セルフチェックの「当てはまるのが2個」など
        if re.match(r"^\s*(?:つ|本だけ|行|\.)", tail) and not big:
            continue
        if big or (unit and not re.match(r"^\s*(?:つ|本)", tail) and digits not in ("1", "2", "3")):
            out.append(digits)
    return out


WEEKLY_HEADS = ["## 30秒まとめ", "## 今週の5本", "## 今週やること", "## 30秒セルフチェック", "## 出典"]


def load_issue(repo, date):
    path = os.path.join(repo, "data", "issues", f"{date}.json")
    if not os.path.exists(path):
        return None
    issue = json.load(open(path, encoding="utf-8"))
    items = {i["id"]: i for i in issue.get("items", [])}
    topics = {t["id"]: t for t in issue.get("topics", [])}
    for i in issue.get("items", []):  # 話題にまとまっていない単独記事（アプリでは s＋記事ID）
        topics.setdefault("s" + i["id"], {"id": "s" + i["id"], "title": i.get("title_ja") or i.get("title"),
                                           "summary": i.get("summary"), "avail": i.get("avail"),
                                           "biz_tip": i.get("biz_tip"), "item_ids": [i["id"]]})
    return {"items": items, "topics": topics}


def load_promo(repo, pending=False):
    """有料noteの案内。URL が入っているものを返す。pending=True なら、URL が空で予告の1文（pending_line）があるものを返す。"""
    path = os.path.join(repo, "data", "promo.json")
    if not os.path.exists(path):
        return []
    try:
        xs = json.load(open(path, encoding="utf-8")).get("paid_notes", [])
    except Exception:
        return []
    if pending:
        return [x for x in xs if not str(x.get("url") or "").startswith("http") and x.get("pending_line")]
    return [x for x in xs if str(x.get("url") or "").startswith("http")]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--posts", required=True)
    ap.add_argument("--date", required=True)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--any-day", action="store_true")
    ap.add_argument("--makeup", action="store_true")
    a = ap.parse_args()
    if a.any_day:
        a.dry_run = True

    today = load_issue(a.repo, a.date)
    if not today:
        print(f"NG: {a.date} の号がありません（朝刊の発行を先に確かめる）")
        sys.exit(1)
    P = json.load(open(a.posts, encoding="utf-8"))
    dD = datetime.strptime(a.date, "%Y-%m-%d")
    sunday = dD.weekday() == 6
    kind = P.get("kind") or ("weekly" if P.get("note") else "daily")

    errs = []
    if kind not in ("daily", "weekly"):
        errs.append(f"kind は daily か weekly（いまは {kind}）")
    if kind == "weekly" and not sunday and not a.any_day and not a.makeup:
        errs.append("週1まとめ（weekly）は日曜だけ。月〜土は kind を daily にし、note を書かない")
    if kind == "daily" and P.get("note"):
        errs.append("月〜土は note を書かない（note は日曜の週1まとめだけ）")
    if kind == "daily" and sunday:
        errs.append("日曜は週1まとめ（kind を weekly）を作る")

    # 選んだ話題（D の号と、週1まとめはその週の号）
    picked = []  # (topic, items_dict)
    for k in [P.get("main")] + list(P.get("others") or []) + list(P.get("x_topics") or []):
        if k not in today["topics"]:
            errs.append(f"話題ID {k} が {a.date} の号にありません")
        else:
            picked.append((today["topics"][k], today["items"]))
    week = []
    if kind == "weekly":
        wt = list(P.get("week_topics") or [])
        if not (4 <= len(wt) <= 6):
            errs.append(f"week_topics が{len(wt)}本（4〜6本。ふつうは5本）")
        lo = (dD - timedelta(days=6)).strftime("%Y-%m-%d")
        cache = {}
        for w in wt:
            wd, wid = str(w.get("date") or ""), w.get("id")
            if not (lo <= wd <= a.date):
                errs.append(f"week_topics の {wd} は週（{lo}〜{a.date}）の外です")
                continue
            if wd not in cache:
                cache[wd] = load_issue(a.repo, wd)
            iss = cache[wd]
            if not iss or wid not in iss["topics"]:
                errs.append(f"week_topics の {wd} {wid} が号にありません")
                continue
            picked.append((iss["topics"][wid], iss["items"]))
            week.append({"date": wd, "id": wid, "title": iss["topics"][wid].get("title")})
        if len({(w["date"], w["id"]) for w in week}) != len(week):
            errs.append("week_topics に同じ話題が2回入っています")

    src_items = [its[i] for t, its in picked for i in (t.get("item_ids") or []) if i in its]
    promo = load_promo(a.repo)
    promo_urls = {str(x["url"]).split("?")[0].rstrip("/") for x in promo}
    allowed_urls = {u.split("?")[0].rstrip("/") for u in (it.get("url", "") for it in src_items)} | CTA_URLS | promo_urls
    facts = " ".join(topic_text(t, [its[i] for i in (t.get("item_ids") or []) if i in its]) for t, its in picked)
    facts_digits = facts.replace(",", "")

    note = P.get("note") or {}
    title, body = str(note.get("title") or ""), str(note.get("body") or "")
    xs = P.get("x") or []
    if not xs:
        errs.append("x の投稿文がありません")
    if kind == "weekly":
        if not title or not body:
            errs.append("週1まとめの note の title・body がありません")
        if len(title) > 60:
            errs.append(f"タイトルが{len(title)}字（60字まで）")
        if not (2500 <= len(body) <= 5500):
            errs.append(f"本文が{len(body)}字（2500〜5500字）")
        heads = [l.strip() for l in body.split("\n") if l.startswith("## ")]
        if body.count("[[") != body.count("]]") or re.search(r"\[\[[^\]]*\[\[", body):
            errs.append("太字の印 [[ ]] の開きと閉じがそろっていません")
        for h in WEEKLY_HEADS:
            if not any(x.startswith(h) for x in heads):
                errs.append(f"本文に「{h}」の見出しがありません")
        if "https://infosuccess.jp" not in body:
            errs.append("本文の最後に相談窓口の1文と https://infosuccess.jp/ がありません")
        for x in promo:
            if str(x["url"]).split("?")[0].rstrip("/") not in {u.split("?")[0].rstrip("/") for u in URL_RE.findall(body)}:
                errs.append(f"有料noteの案内（{x.get('title')}）の URL が本文にありません（data/promo.json の文面で入れる）")
        if not promo and re.search(r"有料note|円の(?:チェックリスト|キット)", body):
            errs.append("有料noteはまだ公開前（data/promo.json の URL が空）なので、案内を入れない")
        for x in load_promo(a.repo, pending=True):
            if x["pending_line"] not in body:
                errs.append(f"公開前の有料note（{x.get('title')}）の予告の1文が本文にありません（data/promo.json の pending_line をそのまま入れる）")
    else:
        heads = []
        for i, x in enumerate(xs):
            if re.search(r"note", str(x.get("text") or ""), re.I):
                errs.append(f"x[{i}]: 月〜土は note が無いので、note の話を書かない（朝の1本の URL は投稿のときに足す）")

    imgs = P.get("images") or {}
    img_texts = []
    if imgs.get("eyecatch"):
        e = imgs["eyecatch"]
        img_texts.append(("images.eyecatch", " ".join([e.get("head1", ""), e.get("head2", ""), e.get("sub", "")] + list(e.get("labels") or []))))
        for k in ("head1", "head2", "blue", "sub", "struct"):
            if not e.get(k):
                errs.append(f"images.eyecatch: {k} がありません")
        if e.get("blue") and e["blue"] not in (e.get("head1", "") + e.get("head2", "")):
            errs.append("images.eyecatch: blue（青にする語）が主見出しにありません")
    figs = list(imgs.get("figs") or [])
    if kind == "daily" and figs:
        errs.append("月〜土は note が無いので images.figs を書かない（eyecatch と xfig だけ）")
    if len(figs) > 2:
        errs.append(f"images.figs が{len(figs)}枚（週1まとめの図解は2枚まで）")
    for f in figs + ([dict(imgs["xfig"], id="xfig", after="-")] if imgs.get("xfig") else []):
        name = f"images.{f.get('id')}"
        for k in ("id", "title", "texts", "note", "struct", "alt"):
            if not f.get(k):
                errs.append(f"{name}: {k} がありません")
        if f.get("after") != "-" and f.get("after") not in heads:
            errs.append(f"{name}: 置き場所 {f.get('after')} の見出しが本文にありません")
        img_texts.append((name, " ".join([str(f.get("title", "")), str(f.get("note", ""))] + [str(t) for t in f.get("texts") or []])))

    tables = list(note.get("tables") or [])
    if kind == "daily" and tables:
        errs.append("月〜土は note が無いので note.tables を書かない")
    if len(tables) > 3:
        errs.append(f"note.tables が{len(tables)}個（3個まで）")
    if tables:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from note_tables import check as table_check
        allheads = [l.strip() for l in body.split("\n") if l.startswith("## ") or l.startswith("### ")]
        for t in tables:
            errs += table_check(t)
            if t.get("after") not in allheads:
                errs.append(f"表 {t.get('id')}: 置き場所 {t.get('after')} の見出しが本文にありません")
            img_texts.append((f"note.tables.{t.get('id')}", " ".join([str(t.get("title", "")), str(t.get("note", ""))] + [str(c) for r in t.get("rows") or [] for c in r])))
    alltext = ([("note", title + "\n" + body)] if kind == "weekly" else []) + \
        [(f"x[{i}]", str(x.get("text") or "")) for i, x in enumerate(xs)] + img_texts
    ok = set(str(n) for n in (P.get("ok_numbers") or []))
    for x in load_promo(a.repo) + load_promo(a.repo, pending=True):  # 自社の有料noteの案内文と値段の数字は通す
        ok |= set(numbers_in(" ".join(str(x.get(k) or "") for k in ("line", "price", "pending_line", "title"))))
    for name, text in alltext:
        if "**" in text:
            errs.append(f"{name}: 太字記号（**）があります")
        if name != "note" and ("[[" in text or "]]" in text):
            errs.append(f"{name}: 太字の印 [[ ]] は note の本文だけで使えます")
        for u in URL_RE.findall(text):
            if u.split("?")[0].rstrip("/") not in allowed_urls:
                errs.append(f"{name}: 号の出典にないURL {u}")
        for n in numbers_in(text):
            if n not in facts_digits and n not in ok:
                errs.append(f"{name}: 数字 {n} が、選んだ話題の解説にありません（確かめて直すか ok_numbers に入れる）")
    for i, x in enumerate(xs):
        n = x_len(x.get("text"))
        if n > 280:
            errs.append(f"x[{i}]: 長すぎます（全角{n / 2:.0f}字相当。140字まで）")

    if errs:
        print("NG（書き込んでいません）")
        for e in dict.fromkeys(errs):
            print(" -", e)
        sys.exit(1)

    now = datetime.now(JST)
    out = {"date": a.date, "kind": kind, "updatedAt": now.strftime("%Y-%m-%dT%H:%M+09:00"),
           "main": P["main"], "others": list(P.get("others") or []),
           "main_title": today["topics"][P["main"]].get("title"),
           "x": [dict({"label": str(x.get("label") or f"{i + 1}本目"), "text": str(x["text"]), "len": round(x_len(x["text"]) / 2)},
                      **({"at": str(x["at"])} if x.get("at") else {})) for i, x in enumerate(xs)]}
    if kind == "weekly":
        out["week_from"] = (dD - timedelta(days=6)).strftime("%Y-%m-%d")
        out["week_topics"] = week
        out["note"] = {"title": title, "body": body}
        if tables:
            out["note"]["tables"] = tables
    if P.get("x_topics"):
        out["x_topics"] = list(P["x_topics"])
    if imgs:
        out["images"] = imgs
    summary = (f"週1まとめ {len(body)}字・{len(week)}本  " if kind == "weekly" else "X だけ  ") + \
        f"x {len(xs)}本（" + "・".join(f"{x['len']}字" for x in out["x"]) + "）"
    if a.dry_run:
        print(f"OK（検査のみ。書き込んでいません）: {summary}")
        return
    d = os.path.join(a.repo, "data", "posts")
    os.makedirs(d, exist_ok=True)
    old = os.path.join(d, f"{a.date}.json")
    if os.path.exists(old):  # 投稿済みの記録は残す
        try:
            posted = json.load(open(old, encoding="utf-8")).get("posted")
            if posted:
                out["posted"] = posted
        except Exception:
            pass
    json.dump(out, open(os.path.join(d, f"{a.date}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    limit = (now - timedelta(days=KEEP_DAYS)).strftime("%Y-%m-%d")
    for f in os.listdir(d):
        if f.endswith(".json") and f[:10] < limit:
            os.remove(os.path.join(d, f))
    print(f"OK: data/posts/{a.date}.json  {summary}")


if __name__ == "__main__":
    main()

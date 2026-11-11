# AIトレンド朝刊 投稿下書きの組み立て ver1.3 (2026-11-12) note・Xの下書き（Xは朝1本・夜2本、画像の指示、セルフチェック）を検査して data/posts/ に書く（作り直しても投稿済みの記録は残す）
# 書き方の決まりは tools/POSTS_GUIDE.md。
# 使い方:
#   python3 tools/build_posts.py --posts posts.json --date YYYY-MM-DD --repo <リポジトリのdir>
# posts.json:
#   {"main": "今日の1本の話題ID", "others": ["ほか3本の話題ID", ...],
#    "note": {"title": "記事タイトル", "body": "本文（見出しは行頭に ## ）"},
#    "x_topics": ["X の夜の1本だけで扱う話題ID（note に載せない話題。無ければ省く）"],
#    "x": [{"label": "朝の1本", "at": "朝", "text": "投稿文"}, {"label": "夜の1本", "at": "19:00", "text": "投稿文"},
#          {"label": "今日の3つ", "at": "21:00", "text": "投稿文"}],
#    "images": {"eyecatch": {...}, "figs": [{"id": "fig1", "after": "## 概要", ...}], "xfig": {...}}（形は tools/img_prompt.py の先頭）,
#    "ok_numbers": ["本文にあって号の解説にない数字のうち、確かめたうえで通すもの（例: 手順の番号ではない数字）"]}
# 検査（1つでも外れると書き込まずに終わる。終了コード1）:
#   - main・others・x_topics の話題IDが、その日の号にあること
#   - 出典のURLが、選んだ話題の出典にあること（号にないURLを書かない。決まった窓口のURL（CTA_URLS）は除く）
#   - images の文言の数字も同じ検査。図の置き場所（after）の見出しが本文にあること、図は2枚まで
#   - 本文に「## 30秒セルフチェック」があること
#   - 本文・投稿文の数字（2桁以上、または ％・倍・円・ドル・人・件・社 などが付く数字）が、選んだ話題の解説にあること
#   - Xの投稿文が全角140字相当（半角は0.5字、URLは11.5字）に収まること
#   - 太字記号（**）がないこと、タイトルが60字以内、本文が600〜3000字
# 書き込み先: data/posts/YYYY-MM-DD.json（60日より古いものは消す）
import argparse, json, os, re, sys, unicodedata
from datetime import datetime, timezone, timedelta

JST = timezone(timedelta(hours=9))
CTA_URLS = {"https://sukizero.com"}  # 本文に毎回載せてよい窓口（スキゼロの無料診断）
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--posts", required=True)
    ap.add_argument("--date", required=True)
    ap.add_argument("--repo", required=True)
    a = ap.parse_args()

    issue_path = os.path.join(a.repo, "data", "issues", f"{a.date}.json")
    if not os.path.exists(issue_path):
        print(f"NG: {a.date} の号がありません（朝刊の発行を先に確かめる）")
        sys.exit(1)
    issue = json.load(open(issue_path, encoding="utf-8"))
    P = json.load(open(a.posts, encoding="utf-8"))
    items = {i["id"]: i for i in issue.get("items", [])}
    topics = {t["id"]: t for t in issue.get("topics", [])}
    for i in issue.get("items", []):  # 話題にまとまっていない単独記事（アプリでは s＋記事ID）
        topics.setdefault("s" + i["id"], {"id": "s" + i["id"], "title": i.get("title_ja") or i.get("title"),
                                           "summary": i.get("summary"), "avail": i.get("avail"),
                                           "biz_tip": i.get("biz_tip"), "item_ids": [i["id"]]})

    errs = []
    picks = [P.get("main")] + list(P.get("others") or []) + list(P.get("x_topics") or [])
    for k in picks:
        if k not in topics:
            errs.append(f"話題ID {k} がこの号にありません")
    picked = [topics[k] for k in picks if k in topics]
    src_items = [items[i] for t in picked for i in (t.get("item_ids") or []) if i in items]
    allowed_urls = {u.split("?")[0].rstrip("/") for u in (it.get("url", "") for it in src_items)}
    facts = " ".join(topic_text(t, [items[i] for i in (t.get("item_ids") or []) if i in items]) for t in picked)
    facts_digits = facts.replace(",", "")

    note = P.get("note") or {}
    title, body = str(note.get("title") or ""), str(note.get("body") or "")
    xs = P.get("x") or []
    if not title or not body:
        errs.append("note の title・body がありません")
    if len(title) > 60:
        errs.append(f"タイトルが{len(title)}字（60字まで）")
    if not (600 <= len(body) <= 3000):
        errs.append(f"本文が{len(body)}字（600〜3000字）")
    if not xs:
        errs.append("x の投稿文がありません")
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
    if len(figs) > 2:
        errs.append(f"images.figs が{len(figs)}枚（note の図解は2枚まで）")
    heads = [l.strip() for l in body.split("\n") if l.startswith("## ")]
    for f in figs + ([dict(imgs["xfig"], id="xfig", after="-")] if imgs.get("xfig") else []):
        name = f"images.{f.get('id')}"
        for k in ("id", "title", "texts", "note", "struct", "alt"):
            if not f.get(k):
                errs.append(f"{name}: {k} がありません")
        if f.get("after") != "-" and f.get("after") not in heads:
            errs.append(f"{name}: 置き場所 {f.get('after')} の見出しが本文にありません")
        img_texts.append((name, " ".join([str(f.get("title", "")), str(f.get("note", ""))] + [str(t) for t in f.get("texts") or []])))
    if "## 30秒セルフチェック" not in body:
        errs.append("本文に「## 30秒セルフチェック」がありません")
    alltext = [("note", title + "\n" + body)] + [(f"x[{i}]", str(x.get("text") or "")) for i, x in enumerate(xs)] + img_texts
    for name, text in alltext:
        if "**" in text:
            errs.append(f"{name}: 太字記号（**）があります")
        for u in URL_RE.findall(text):
            if u.split("?")[0].rstrip("/") not in allowed_urls and u.split("?")[0].rstrip("/") not in CTA_URLS:
                errs.append(f"{name}: 号の出典にないURL {u}")
        ok = set(str(n) for n in (P.get("ok_numbers") or []))
        for n in numbers_in(text):
            if n not in facts_digits and n not in ok:
                errs.append(f"{name}: 数字 {n} が、選んだ話題の解説にありません（確かめて直すか ok_numbers に入れる）")
    for i, x in enumerate(xs):
        n = x_len(x.get("text"))
        if n > 280:
            errs.append(f"x[{i}]: 長すぎます（全角{n / 2:.0f}字相当。140字まで）")
    if "## 出典" not in body:
        errs.append("本文に「## 出典」がありません")
    if "今日やること" not in body:
        errs.append("本文に「今日やること」がありません")

    if errs:
        print("NG（書き込んでいません）")
        for e in dict.fromkeys(errs):
            print(" -", e)
        sys.exit(1)

    now = datetime.now(JST)
    out = {"date": a.date, "updatedAt": now.strftime("%Y-%m-%dT%H:%M+09:00"),
           "main": P["main"], "others": list(P.get("others") or []),
           "main_title": topics[P["main"]].get("title"),
           "note": {"title": title, "body": body},
           "x": [dict({"label": str(x.get("label") or f"{i + 1}本目"), "text": str(x["text"]), "len": round(x_len(x["text"]) / 2)},
                      **({"at": str(x["at"])} if x.get("at") else {})) for i, x in enumerate(xs)]}
    if P.get("x_topics"):
        out["x_topics"] = list(P["x_topics"])
    if imgs:
        out["images"] = imgs
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
    print(f"OK: data/posts/{a.date}.json  note {len(body)}字  x {len(xs)}本（" + "・".join(f"{x['len']}字" for x in out["x"]) + "）")


if __name__ == "__main__":
    main()

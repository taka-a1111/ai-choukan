# AIトレンド朝刊 note用のHTML変換 ver2.0 (2026-11-23) 見やすさのための装飾（太字・ラベル・引用の「やること」・区切り線・番号つきリスト・チェック欄・出典の名前つきリンク）と、表の画像の置き場所に対応。下書きの本文を、noteのエディタに貼るHTMLにする
# 使い方: python3 tools/note_html.py --date YYYY-MM-DD --repo <リポジトリのdir> [--out note_payload.json]
#   出力（JSON）: {"title": 記事タイトル, "html": 本文のHTML, "blocks": ブロックの並び（照合用）,
#                  "paste_html": noteに貼るHTML（目次・図・表・リンクカードを入れる場所に［目次］［図fig1］［表t1］［カード:URL］の段落を置いたもの。POSTS_GUIDE.md 7-2）,
#                  "tables": [{"id", "file", "before": 表を入れる位置の直後のブロックの文字（無ければ ""）, "after_text": 表の直前のブロックの文字}]}
# 本文の書き方（POSTS_GUIDE.md 第3章）と変換の決まり:
#   「## 」→ h2（2つ目からは前に区切り線）／「### 」→ h3（同じ ## の中の2つ目からは前に区切り線）
#   [[語]] → 太字（1段落に1〜2か所まで）
#   「いつ・誰が使える：」「小さな会社への影響（私の見立て）：」で始まる段落 → 太字のラベル＋改行＋本文
#   「やること：」で始まる段落 → 引用（太字の「やること」＋改行＋本文）
#   「・」で始まる行のまとまり → 箇条書き。「30秒セルフチェック」の中では「☐ 」つきの行
#   「1. 」「2. 」…で始まる行のまとまり → 番号つきリスト
#   「・名前 https://…」の行 → 名前をリンクにした箇条書き（出典）
#   URLだけの行 → リンク（noteでリンクカードにする行。POSTS_GUIDE.md 7-5）
#   note.tables の表は、after に書いた見出しの節の最後（次の見出しの前）に入れる。after_block（その節の段落の書き出し。[[ ]] を除いた文字）があれば、その段落の直後に入れる。画像は tools/note_tables.py で作る
import argparse, html, json, os, re

LABELS = ("いつ・誰が使える：", "小さな会社への影響（私の見立て）：")
URL_ONLY = re.compile(r"^https?://\S+$")
NAMED_URL = re.compile(r"^・(.+?)\s+(https?://\S+)$")
OL_ITEM = re.compile(r"^(\d+)\.\s*(.+)$")


def inline(s):
    s = html.escape(s)
    return re.sub(r"\[\[(.+?)\]\]", r"<strong>\1</strong>", s)


def plain(s):
    return re.sub(r"\[\[(.+?)\]\]", r"\1", s)


def to_html(body, tables=None):
    out, kinds, texts = [], [], []
    sec, h2n, h3n = "", 0, 0
    tables = tables or []
    pending = []  # この節の最後に入れる表

    def add(h, k, t):
        out.append(h); kinds.append(k); texts.append(t)
        for x in [x for x in pending if x.get("after_block") and k not in ("HR", "TABLE") and t.startswith(x["after_block"])]:
            pending.remove(x)
            out.append(f"<!--TABLE:{x['id']}-->"); kinds.append("TABLE"); texts.append(x["id"])

    def flush_tables():
        for t in pending:
            add(f"<!--TABLE:{t['id']}-->", "TABLE", t["id"])
        pending.clear()

    for b in [x for x in re.split(r"\n\s*\n", body) if x.strip()]:
        lines = b.strip("\n").split("\n")
        if lines[0].startswith("## "):
            flush_tables()
            sec = lines[0][3:]
            h2n += 1; h3n = 0
            if h2n > 1:
                add("<hr>", "HR", "")
            add(f"<h2>{inline(sec)}</h2>", "H2", plain(sec))
            pending.extend(t for t in tables if t.get("after") == "## " + sec)
            lines = lines[1:]
            if not lines:
                continue
        if lines[0].startswith("### "):
            flush_tables()
            h3n += 1
            if h3n > 1:
                add("<hr>", "HR", "")
            h = lines[0][4:]
            add(f"<h3>{inline(h)}</h3>", "H3", plain(h))
            pending.extend(t for t in tables if t.get("after") == "### " + h)
            lines = lines[1:]
            if not lines:
                continue
        if len(lines) > 1 and URL_ONLY.match(lines[-1]) and not lines[0].startswith("・"):  # 文＋URLの行は、文の段落とURLだけの段落に分ける（URLはリンクカードにする）
            add("<p>" + "<br>".join(inline(l) for l in lines[:-1]) + "</p>", "P", plain(lines[0]))
            lines = lines[-1:]
        first = lines[0]
        if all(NAMED_URL.match(l) for l in lines):
            lis = "".join(f'<li><a href="{html.escape(m.group(2))}">{inline(m.group(1))}</a></li>' for m in (NAMED_URL.match(l) for l in lines))
            add(f"<ul>{lis}</ul>", "UL", plain(NAMED_URL.match(first).group(1)))
        elif all(l.startswith("・") for l in lines):
            if sec.startswith("30秒セルフチェック"):
                add("<p>" + "<br>".join("☐ " + inline(l[1:]) for l in lines) + "</p>", "P", "☐ " + plain(first[1:]))
            else:
                add("<ul>" + "".join(f"<li>{inline(l[1:])}</li>" for l in lines) + "</ul>", "UL", plain(first[1:]))
        elif all(OL_ITEM.match(l) for l in lines):
            add("<ol>" + "".join(f"<li>{inline(OL_ITEM.match(l).group(2))}</li>" for l in lines) + "</ol>", "OL", plain(OL_ITEM.match(first).group(2)))
        elif len(lines) == 1 and URL_ONLY.match(first):
            u = html.escape(first)
            add(f'<p><a href="{u}">{u}</a></p>', "P", first)
        elif len(lines) == 1 and first.startswith("やること："):
            add(f"<blockquote><p><strong>やること</strong><br>{inline(first[len('やること：'):])}</p></blockquote>", "BLOCKQUOTE", "やること" + plain(first[len('やること：'):]))
        elif len(lines) == 1 and first.startswith(LABELS):
            lab = next(x for x in LABELS if first.startswith(x))
            add(f"<p><strong>{html.escape(lab[:-1])}</strong><br>{inline(first[len(lab):])}</p>", "P", lab[:-1] + plain(first[len(lab):]))
        else:
            add("<p>" + "<br>".join(inline(l) for l in lines) + "</p>", "P", plain(first))
    flush_tables()
    return "".join(out), kinds, texts


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--out")
    a = ap.parse_args()
    P = json.load(open(os.path.join(a.repo, "data", "posts", f"{a.date}.json"), encoding="utf-8"))
    tables = P["note"].get("tables") or []
    h, kinds, texts = to_html(P["note"]["body"], tables)
    tinfo = []
    for t in tables:
        i = texts.index(t["id"]) if t["id"] in texts else -1
        prev = next((texts[j] for j in range(i - 1, -1, -1) if kinds[j] not in ("HR", "TABLE")), "") if i >= 0 else ""
        tinfo.append({"id": t["id"], "file": f"note-{a.date}-{t['id']}.png", "after_text": prev[:20], "placed": i >= 0})
    ph = re.sub(r"<!--TABLE:(\w+)-->", r"<p>［表\1］</p>", h)
    for f in (P.get("images") or {}).get("figs") or []:
        tag = "<h2>" + html.escape(str(f.get("after", ""))[3:]) + "</h2>"
        if tag in ph:
            ph = ph.replace(tag, tag + f"<p>［図{f.get('id')}］</p>", 1)
    if "</ul>" in ph:  # 30秒まとめの箇条書きの直後に目次
        i = ph.index("</ul>") + 5
        ph = ph[:i] + "<p>［目次］</p>" + ph[i:]
    ph = re.sub(r'<p><a href="([^"]+)">\1</a></p>', lambda m: f"<p>［カード:{html.unescape(m.group(1))}］</p>", ph)
    res = {"title": P["note"]["title"], "html": h, "paste_html": ph, "blocks": ",".join(kinds), "tables": tinfo}
    if a.out:
        json.dump(res, open(a.out, "w", encoding="utf-8"), ensure_ascii=False)
        print(f"OK: {a.out}  ブロック {len(kinds)}個  {res['blocks']}")
        for t in tinfo:
            print(f"  表 {t['id']}: {'置き場所OK' if t['placed'] else '置き場所の見出しが本文にない'}（直前: {t['after_text']}）")
    else:
        print(json.dumps(res, ensure_ascii=False))

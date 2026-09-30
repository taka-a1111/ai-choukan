# AIトレンド朝刊 本文取得 ver1.1 (2026-10-01) 文字コード自動判別
# 話題ごとに、出典記事の本文を取ってきて1つのテキストにまとめる（Claudeが読んで解説を書くための材料）。
# 使い方A（毎朝の収集）: python3 tools/fetch_text.py --groups W/groups.json --collected W/out --vsum W/vsum.json --out W/txt
#   groups.json: [{"key":"T01","t":"話題の見出し","news":[news.jsonの添字...],"videos":["video_id"...],"i":重要度}]
#   重要度1の話題は本文を取らず概要だけにする（読む量を減らすため）
# 使い方B: python3 tools/fetch_text.py --issue <話題と記事のJSON> --out <出力dir> [--per 2500] [--max-sources 3]
#   入力JSON: {"topics":[{"key":"T01","title":"...","items":[{"src_name","title","url","desc","kind","summary"}...]}...]}
#   出力: <出力dir>/T01.txt など（見出し・各出典の本文の抜粋）と index.txt（取得できた文字数の一覧）
# 外部AI APIは使わない。trafilatura がなければ pip install --break-system-packages trafilatura
import argparse, json, os, re, urllib.request
from concurrent.futures import ThreadPoolExecutor

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"


def fetch(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "ja,en;q=0.8"})
        with urllib.request.urlopen(req, timeout=25) as r:
            raw = r.read()
        import trafilatura
        enc = None
        m = re.search(rb'charset=["\']?([A-Za-z0-9_\-]+)', raw[:3000])
        if m:
            enc = m.group(1).decode().lower()
        try:
            html = raw.decode(enc or "utf-8")
        except Exception:
            html = raw.decode("utf-8", "ignore")
        txt = trafilatura.extract(html, include_comments=False, include_tables=False,
                                  favor_precision=True) or ""
        junk = re.compile(r"クリップ機能|いいね|再度読みたく|サインインした状態|More From|編集部です|関連記事|この連載の一覧|Articles in This Series|"
                          r"おすすめ|Picks for You|今日の必読|Today.s Picks|Special$|^PR$|講座|早割|Copyright|Subscribe|ニュースレター|有料会員")
        lines = [l for l in txt.splitlines() if l.strip() and not junk.search(l)]
        return "\n".join(dict.fromkeys(lines)).strip()
    except Exception as e:  # noqa
        return ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--issue")
    ap.add_argument("--groups")
    ap.add_argument("--collected")
    ap.add_argument("--vsum")
    ap.add_argument("--out", required=True)
    ap.add_argument("--per", type=int, default=2500)
    ap.add_argument("--max-sources", type=int, default=3)
    a = ap.parse_args()
    if a.groups:
        news = json.load(open(os.path.join(a.collected, "news.json"), encoding="utf-8"))
        vids = {v.get("video_id"): v for v in json.load(open(os.path.join(a.collected, "videos.json"), encoding="utf-8"))}
        vs = json.load(open(a.vsum, encoding="utf-8")) if a.vsum and os.path.exists(a.vsum) else {}
        data = {"topics": []}
        for g in json.load(open(a.groups, encoding="utf-8")):
            items = [dict(news[int(k)], kind="news", skip=g.get("i", 2) <= 1) for k in g.get("news", [])]
            for vid in g.get("videos", []):
                v, x = vids.get(vid, {}), vs.get(vid, {})
                items.append({"src_name": v.get("src_name", ""), "title": v.get("title", ""), "url": v.get("url", ""),
                              "desc": v.get("desc", ""), "kind": "video", "summary": x.get("summary", ""), "points": x.get("points", [])})
            data["topics"].append({"key": g["key"], "title": g.get("t", ""), "items": items})
    else:
        data = json.load(open(a.issue, encoding="utf-8"))
    os.makedirs(a.out, exist_ok=True)
    jobs = []
    for t in data["topics"]:
        targets = [i for i in t["items"] if i.get("kind") != "video" and not i.get("skip")][: a.max_sources]
        for i in targets:
            jobs.append(i["url"])
    with ThreadPoolExecutor(max_workers=10) as ex:
        texts = dict(zip(jobs, ex.map(fetch, jobs)))
    lines = []
    for t in data["topics"]:
        parts = [f"# {t['key']} {t['title']}"]
        got = 0
        for i in t["items"]:
            if i.get("kind") == "video":
                body = "（動画の要約）" + (i.get("summary") or i.get("desc") or "") + " " + " / ".join(i.get("points") or [])
            else:
                body = texts.get(i["url"], "") or ""
                if len(body) < 200:
                    body = (i.get("desc") or "") + ("\n" + body if body else "")
                    body = "（本文は未取得。概要のみ）" + body
                body = body[: a.per]
            got += len(body)
            parts.append(f"## {i['src_name']}｜{i['title']}\n{body}")
        open(os.path.join(a.out, f"{t['key']}.txt"), "w", encoding="utf-8").write("\n\n".join(parts))
        lines.append(f"{t['key']}\t{len(t['items'])}件\t{got}字\t{t['title']}")
    open(os.path.join(a.out, "index.txt"), "w", encoding="utf-8").write("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()

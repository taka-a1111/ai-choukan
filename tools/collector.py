# AIトレンド朝刊 収集スクリプト ver1.0 (2026-09-30)
# 使い方: python3 collector.py --sources sources.json --seen seen.json --out out --hours 30
# 出力: out/news.json, out/videos.json, out/report.json
# 外部AI APIは使わない。RSS/Atom/YouTubeチャンネルフィード/HTMLの取得だけを行う。
import argparse, hashlib, html, json, os, re, sys, time
import urllib.request, urllib.error
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
JST = timezone(timedelta(hours=9))
AI_RE = re.compile(
    r"(?<![A-Za-z])(AI|A\.I\.|LLM|GPT|AGI)(?![A-Za-z])|人工知能|生成AI|機械学習|深層学習|ディープラーニング|"
    r"ChatGPT|OpenAI|Anthropic|Claude|Gemini|DeepMind|Copilot|Perplexity|Llama|Mistral|Grok|xAI|"
    r"Midjourney|Stable Diffusion|Sora|Veo|NVIDIA|エヌビディア|エージェント|agent|chatbot|チャットボット|"
    r"画像生成|動画生成|音声生成|大規模言語モデル|言語モデル|Hugging Face|RAG|MCP|プロンプト|prompt",
    re.I)


def h(url):
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:12]


def fetch(url, tries=2):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "ja,en;q=0.8"})
            with urllib.request.urlopen(req, timeout=25) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}"
            if e.code in (429, 500, 502, 503) or (e.code == 404 and "youtube.com/feeds" in url):
                time.sleep(4 + 3 * i)
                continue
            break
        except Exception as e:  # noqa
            last = str(e)[:120]
            time.sleep(2)
    raise RuntimeError(last or "fetch failed")


def clean(s, n=None):
    s = html.unescape(re.sub(r"<[^>]+>", " ", s or ""))
    s = re.sub(r"\s+", " ", s).strip()
    return s[:n] if n else s


def parse_date(s):
    if not s:
        return None
    s = s.strip()
    try:
        return parsedate_to_datetime(s).astimezone(timezone.utc)
    except Exception:
        pass
    try:
        s2 = s.replace("Z", "+00:00")
        d = datetime.fromisoformat(s2)
        if d.tzinfo is None:
            d = d.replace(tzinfo=JST)
        return d.astimezone(timezone.utc)
    except Exception:
        return None


def local(tag):
    return tag.split("}", 1)[-1]


def parse_feed(raw):
    """RSS 1.0 / RSS 2.0 / Atom を共通形式に。"""
    root = ET.fromstring(raw)
    out = []
    for el in root.iter():
        name = local(el.tag)
        if name not in ("item", "entry"):
            continue
        d = {"title": "", "url": "", "date": None, "desc": "", "video_id": None, "views": None}
        for c in el:
            n = local(c.tag)
            if n == "title":
                d["title"] = clean(c.text)
            elif n == "link":
                if c.get("href"):
                    if c.get("rel", "alternate") == "alternate" and not d["url"]:
                        d["url"] = c.get("href")
                elif c.text and not d["url"]:
                    d["url"] = c.text.strip()
            elif n in ("pubDate", "published", "date", "updated", "issued") and c.text:
                if not d["date"] or n in ("pubDate", "published", "date"):
                    d["date"] = parse_date(c.text) or d["date"]
            elif n in ("description", "summary", "content", "encoded") and c.text and not d["desc"]:
                d["desc"] = clean(c.text, 400)
            elif n == "videoId":
                d["video_id"] = (c.text or "").strip()
            elif n == "group":
                for g in c.iter():
                    gn = local(g.tag)
                    if gn == "description" and g.text and not d["desc"]:
                        d["desc"] = clean(g.text, 400)
                    if gn == "statistics" and g.get("views"):
                        d["views"] = int(g.get("views"))
        if not d["url"] and el.get("{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about"):
            d["url"] = el.get("{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about")
        if d["url"]:
            out.append(d)
    return out


JUNK = re.compile(r"copy the url|opens .* in a new tab|go to comment|read more|続きを読む", re.I)
DATE_IN_TEXT = [
    (re.compile(r"(\d{4}) / (\d{1,2}) / (\d{1,2})"), "ymd"),
    (re.compile(r"([A-Z][a-z]{2}) (\d{1,2}), (\d{4})"), "mdy"),
]
MON = {m: i + 1 for i, m in enumerate("Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split())}


def scrape(src, raw):
    t = raw.decode("utf-8", "ignore")
    pat = re.compile(src["scrape_pattern"])
    base = re.match(r"https?://[^/]+", src["url"]).group(0)
    out, seen = [], set()
    for href, txt in re.findall(r'<a[^>]+href="([^"#]+)"[^>]*>(.*?)</a>', t, re.S):
        href = href.split("?")[0]
        if not pat.search(href):
            continue
        url = href if href.startswith("http") else base + href
        text = clean(txt)
        date = None
        for rx, kind in DATE_IN_TEXT:
            m = rx.search(text)
            if m:
                try:
                    if kind == "ymd":
                        date = datetime(int(m[1]), int(m[2]), int(m[3]), 9, tzinfo=JST)
                    else:
                        date = datetime(int(m[3]), MON[m[1]], int(m[2]), 9, tzinfo=JST)
                except Exception:
                    date = None
                text = (text[: m.start()] + " " + text[m.end():]).strip()
                break
        text = re.sub(r"\[(MON|TUE|WED|THU|FRI|SAT|SUN)\]", "", text).strip()
        if url in seen:
            # 同じURLのリンクが複数あるとき、見出しらしい方を残す
            for o in out:
                if o["url"] == url and o.get("_slug") and not src.get("title_from_slug") and len(text) >= 12 and not JUNK.search(text):
                    o["title"] = text[:160]
                    o["_slug"] = False
            continue
        seen.add(url)
        is_slug = False
        if src.get("title_from_slug") or len(text) < 12 or JUNK.search(text):
            slug = url.rstrip("/").rsplit("/", 1)[-1]
            text = slug.replace("-", " ").replace("_", " ")
            is_slug = True
        out.append({"_slug": is_slug, "title": text[:160], "url": url, "date": date.astimezone(timezone.utc) if date else None,
                    "desc": "", "video_id": None, "views": None})
    return out


REL = {"秒": 1 / 3600, "分": 1 / 60, "時間": 1, "日": 24, "週間": 168, "か月": 720, "年": 8760}


def yt_channel_page(channel_id):
    """YouTubeのフィードが不調なときの予備。チャンネルの動画一覧ページから取る。"""
    raw = fetch(f"https://www.youtube.com/channel/{channel_id}/videos", tries=2).decode("utf-8", "ignore")
    m = re.search(r"var ytInitialData = (\{.*?\});</script>", raw, re.S)
    if not m:
        raise RuntimeError("動画一覧ページを読めない")
    data = json.loads(m.group(1))
    found = []

    def walk(o):
        if isinstance(o, dict):
            if "lockupViewModel" in o:
                found.append(o["lockupViewModel"])
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(data)
    now = datetime.now(timezone.utc)
    out = []
    for lv in found[:15]:
        vid = lv.get("contentId")
        try:
            md = lv["metadata"]["lockupMetadataViewModel"]
            title = md["title"]["content"]
            parts = [p_["text"]["content"] for r in md["metadata"]["contentMetadataViewModel"]["metadataRows"]
                     for p_ in r.get("metadataParts", [])]
        except Exception:
            continue
        date = None
        for t in parts:
            mm = re.search(r"(\d+)\s*(秒|分|時間|日|週間|か月|年)前", t.replace(" ", ""))
            if mm:
                date = now - timedelta(hours=int(mm[1]) * REL[mm[2]])
        dur = None
        mm = re.search(r'"thumbnailBadgeViewModel":\s*\{"text":\s*"([\d:]+)"', json.dumps(lv, ensure_ascii=False))
        if mm:
            dur = mm[1]
        if vid and date:
            out.append({"title": title, "url": f"https://www.youtube.com/watch?v={vid}", "date": date,
                        "desc": "", "video_id": vid, "views": None, "duration": dur})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sources", required=True)
    ap.add_argument("--seen", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--hours", type=float, default=30)
    ap.add_argument("--max-per-source", type=int, default=10)
    a = ap.parse_args()

    sources = json.load(open(a.sources, encoding="utf-8"))
    if isinstance(sources, dict):
        sources = sources.get("list") or list(sources.values())
    seen = {}
    if os.path.exists(a.seen):
        s = json.load(open(a.seen, encoding="utf-8"))
        seen = s.get("h", s) if isinstance(s, dict) else {}
    first_run = len(seen) == 0
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=a.hours)
    os.makedirs(a.out, exist_ok=True)
    news, videos, report = [], [], []

    def load(src):
        kind = "video" if src["type"].startswith("youtube") else "news"
        feed = src.get("feed")
        if kind == "video" and not feed and src.get("channel_id"):
            feed = "https://www.youtube.com/feeds/videos.xml?channel_id=" + src["channel_id"]
        try:
            if feed:
                try:
                    return kind, parse_feed(fetch(feed, tries=3)), None
                except Exception:
                    if kind == "video" and src.get("channel_id"):
                        return kind, yt_channel_page(src["channel_id"]), None
                    raise
            if src.get("scrape_pattern"):
                return kind, scrape(src, fetch(src["url"])), None
            return kind, None, "フィードも取得ルールもない"
        except Exception as e:  # noqa
            return kind, None, str(e)[:160]

    active = [s_ for s_ in sources if s_.get("enabled") is not False]
    with ThreadPoolExecutor(max_workers=10) as ex:
        loaded = list(ex.map(load, active))

    for src, (kind, entries, err) in zip(active, loaded):
        rep = {"id": src["id"], "name": src["name"], "ok": err is None, "found": 0, "new": 0, "error": err}
        if err:
            report.append(rep)
            continue
        rep["found"] = len(entries)
        picked = []
        for e in entries:
            if e["date"] and e["date"] < cutoff:
                continue
            if not e["date"] and not src.get("scrape_pattern"):
                continue
            if src.get("filter") and not AI_RE.search(e["title"] + " " + e["desc"]):
                continue
            key = h(e["url"])
            if key in seen:
                continue
            picked.append((key, e))
        # 取得ルール型（日付なし）は初回に大量に入らないよう絞る
        limit = 3 if (first_run and src.get("scrape_pattern")) else a.max_per_source
        picked = picked[:limit]
        for key, e in picked:
            pub = (e["date"] or now).astimezone(JST).isoformat(timespec="minutes")
            base = {"id": key, "src_id": src["id"], "src_name": src["name"], "src_type": src["type"],
                    "lang": "ja" if src["type"].endswith("_jp") else "en", "title": e["title"],
                    "url": e["url"], "published": pub, "desc": e["desc"]}
            if kind == "video":
                vid = e["video_id"] or (re.search(r"v=([\w-]{11})", e["url"]) or [None, None])[1]
                base.update(video_id=vid, url=f"https://www.youtube.com/watch?v={vid}",
                            is_short=bool(re.search(r"#shorts", e["title"], re.I)), views=e["views"],
                            duration=e.get("duration"))
                videos.append(base)
            else:
                news.append(base)
        rep["new"] = len(picked)
        report.append(rep)

    news.sort(key=lambda x: x["published"], reverse=True)
    videos.sort(key=lambda x: x["published"], reverse=True)
    json.dump(news, open(os.path.join(a.out, "news.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump(videos, open(os.path.join(a.out, "videos.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump({"ran_at": now.astimezone(JST).isoformat(timespec="minutes"), "sources": report},
              open(os.path.join(a.out, "report.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    bad = [r for r in report if not r["ok"]]
    print(f"news={len(news)} videos={len(videos)} (shorts={sum(v['is_short'] for v in videos)}) "
          f"sources_ok={len(report)-len(bad)}/{len(report)}")
    for r in bad:
        print("  NG", r["id"], r["error"])


if __name__ == "__main__":
    main()

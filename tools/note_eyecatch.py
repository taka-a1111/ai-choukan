# AIトレンド朝刊 note見出し画像 ver1.0 (2026-11-11) 下書きのタイトルから、紺色の見出し画像（1280×670）を作る
# 使い方: python3 tools/note_eyecatch.py --date YYYY-MM-DD --repo <リポジトリのdir> --out eyecatch.png
#   タイトルは最初の「。」で2行に分ける（無ければ1行）。はみ出すときは文字を小さくして収める。
#   Playwright（PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers）が要る。作ったあと、必ず画像を開いて見る。
import argparse, html, json, os

TPL = """<!DOCTYPE html><html lang="ja"><head><meta charset="utf-8"><style>
*{margin:0;padding:0;box-sizing:border-box}
body{width:1280px;height:670px;background:#00243F;font-family:"游ゴシック","Yu Gothic","メイリオ",Meiryo,"Noto Sans CJK JP","Noto Sans JP","IPAexゴシック",sans-serif;color:#FCF9F7;position:relative;overflow:hidden}
.band{position:absolute;left:0;top:0;width:18px;height:670px;background:#0B629E}
.label{position:absolute;left:96px;top:92px;font-size:30px;font-weight:700;color:#9FB8CE;letter-spacing:.06em}
.label span{display:inline-block;background:#0B629E;color:#FCF9F7;padding:6px 16px;margin-right:18px;border-radius:4px}
.title{position:absolute;left:96px;top:210px;width:1090px;font-weight:700;line-height:1.42}
.t1{font-size:56px;white-space:nowrap}
.t2{font-size:50px;margin-top:14px;white-space:nowrap}
.line{position:absolute;left:96px;top:478px;width:120px;height:6px;background:#9FB8CE}
.foot{position:absolute;left:96px;bottom:70px;display:flex;align-items:center;gap:20px}
.tile{width:74px;height:74px;background:#FCF9F7;border-radius:10px;display:flex;align-items:center;justify-content:center}
.foot .name{font-size:34px;font-weight:700;letter-spacing:.08em}
.foot .sub{font-size:22px;color:#9FB8CE;margin-top:4px}
</style></head><body>
<div class="band"></div>
<div class="label"><span>AIニュース解説</span>__DATE__</div>
<div class="title"><div class="t1">__T1__</div>__T2__</div>
<div class="line"></div>
<div class="foot"><div class="tile"><svg width="44" height="56" viewBox="0 0 78 100"><polygon fill="#00243F" points="0,12 17,0 17,88 0,88"/><polygon fill="#9FB8CE" points="33,24 72,0 72,12 45,32"/><polygon fill="#0B629E" points="20,24 76,54 24,98 24,76 52,56 20,40"/></svg></div>
<div><div class="name">インフォサクセス</div><div class="sub">毎日のAIニュースを、今日やることに。</div></div></div>
</body></html>"""

FIT = """() => { const out=[]; for (const e of document.querySelectorAll('.t1,.t2')) { let s=parseFloat(getComputedStyle(e).fontSize);
  while (e.scrollWidth > 1090 && s > 30) { s -= 1; e.style.fontSize = s + 'px'; } out.push(s + ':' + e.scrollWidth); } return out; }"""

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    P = json.load(open(os.path.join(a.repo, "data", "posts", f"{a.date}.json"), encoding="utf-8"))
    title = P["note"]["title"].strip()
    i = title.find("。")
    t1, t2 = (title[: i + 1], title[i + 1 :].strip()) if 0 < i < len(title) - 1 else (title, "")
    page = (TPL.replace("__DATE__", a.date.replace("-", "."))
               .replace("__T1__", html.escape(t1))
               .replace("__T2__", f'<div class="t2">{html.escape(t2)}</div>' if t2 else ""))
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1280, "height": 670})
        pg.set_content(page)
        pg.wait_for_timeout(400)
        sizes = pg.evaluate(FIT)
        pg.screenshot(path=a.out)
        b.close()
    print("OK:", a.out, " 文字の大きさ:幅", sizes)

# AIトレンド朝刊 noteの表の画像 ver1.0 (2026-11-23) noteのエディタには表が無いので、下書きの note.tables を、スマホで読める大きさの画像にする
# 使い方: python3 tools/note_tables.py --date YYYY-MM-DD --repo <リポジトリのdir> --outdir <書き出し先>
#   書き出し: <outdir>/note-YYYY-MM-DD-<id>.png（横1280px。スマホの幅に縮めても一番小さい文字が16px以上になる大きさ）
# note.tables の形（POSTS_GUIDE.md 4-3）:
#   [{"id": "t1", "after": "### 2. …（この見出しの節の最後に入れる）", "after_block": "（任意）その節の段落の書き出し。あればその段落の直後に入れる", "title": "表のタイトル",
#     "cols": ["列1", "列2", "列3"], "rows": [["…", "…", "…"], ...], "note": "表の下の補足（無くてよい）", "alt": "表が示す内容を1文で"}]
#   列は2〜3、行は2〜6。1つのマスは18字まで（英数字は0.55字で数える。スマホで読める長さ）
# 書体は日本語のゴシック（Noto Sans CJK JP など）。色はインフォサクセスの4色
import argparse, asyncio, html, json, os, unicodedata

FONT = "'Noto Sans CJK JP','Noto Sans JP','游ゴシック','Yu Gothic','メイリオ',Meiryo,'IPAexゴシック',sans-serif"  # style 属性の中に入れるので一重引用符
LOGO = '<svg width="24" height="31" viewBox="0 0 78 100"><polygon fill="#00243F" points="0,12 17,0 17,88 0,88"/><polygon fill="#9FB8CE" points="33,24 72,0 72,12 45,32"/><polygon fill="#0B629E" points="20,24 76,54 24,98 24,76 52,56 20,40"/></svg>'


def page(t):
    e = html.escape
    n = len(t["cols"])
    widths = {2: ["38%", "62%"], 3: ["27%", "43%", "30%"]}.get(n, [f"{100 / n:.0f}%"] * n)
    head = "".join(f'<th style="width:{w};background:#00243F;color:#FCF9F7;font-size:28px;font-weight:700;padding:14px 12px;text-align:left">{e(c)}</th>' for c, w in zip(t["cols"], widths))
    body = ""
    for i, r in enumerate(t["rows"]):
        bg = "#FFFFFF" if i % 2 == 0 else "#E7EDF2"
        cells = "".join(
            f'<td style="background:{bg};padding:16px 12px;font-size:{30 if j == 0 else 28}px;line-height:1.4;font-weight:{700 if j == 0 else 500};color:{"#00243F" if j == 0 else "#18202F"};border-top:1px solid #D8DEE8;vertical-align:middle">{e(c)}</td>'
            for j, c in enumerate(r))
        body += f"<tr>{cells}</tr>"
    note = f'<div style="margin-top:18px;font-size:26px;line-height:1.5;color:#1F3347">{e(t["note"])}</div>' if t.get("note") else ""
    return f'''<html lang="ja"><body style="margin:0;width:640px;background:#FCF9F7;font-family:{FONT};color:#18202F">
<div style="padding:30px 22px 24px">
<div style="display:flex;align-items:center;gap:12px;margin-bottom:20px"><div style="width:9px;height:44px;background:#0B629E;border-radius:3px"></div><div style="font-size:38px;line-height:1.3;font-weight:700;color:#00243F">{e(t["title"])}</div></div>
<table style="width:100%;border-collapse:collapse;border-radius:10px;overflow:hidden;table-layout:fixed">{head and "<tr>" + head + "</tr>"}{body}</table>
{note}
<div style="margin-top:16px;display:flex;align-items:center;gap:10px;font-size:24px;color:#0B629E;font-weight:700"><div style="width:38px;height:38px;background:#fff;border:1px solid #D8DEE8;border-radius:6px;display:flex;align-items:center;justify-content:center">{LOGO}</div>インフォサクセス</div>
</div></body></html>'''


def width(s):
    return sum(1 if unicodedata.east_asian_width(ch) in "WFA" else 0.55 for ch in s)


def check(t):
    errs = []
    for k in ("id", "after", "title", "cols", "rows", "alt"):
        if not t.get(k):
            errs.append(f"表 {t.get('id')}: {k} がありません")
    n = len(t.get("cols") or [])
    if not 2 <= n <= 3:
        errs.append(f"表 {t.get('id')}: 列は2〜3（{n}列）")
    rows = t.get("rows") or []
    if not 2 <= len(rows) <= 6:
        errs.append(f"表 {t.get('id')}: 行は2〜6（{len(rows)}行）")
    for r in rows:
        if len(r) != n:
            errs.append(f"表 {t.get('id')}: 列の数がそろっていない行 {r}")
        for c in r:
            if width(str(c)) > 18:
                errs.append(f"表 {t.get('id')}: マスが18字を超えています「{c}」（英数字は0.55字で数える）")
    return errs


async def render(tables, outdir, date):
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={"width": 640, "height": 400}, device_scale_factor=2)
        files = []
        for t in tables:
            await pg.set_content(page(t)); await pg.wait_for_timeout(300)
            f = os.path.join(outdir, f"note-{date}-{t['id']}.png")
            await pg.screenshot(path=f, full_page=True)
            files.append(f)
        await b.close()
    return files


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--outdir", required=True)
    a = ap.parse_args()
    P = json.load(open(os.path.join(a.repo, "data", "posts", f"{a.date}.json"), encoding="utf-8"))
    tables = (P.get("note") or {}).get("tables") or []
    errs = [e for t in tables for e in check(t)]
    if errs:
        print("NG"); [print(" -", e) for e in errs]; raise SystemExit(1)
    os.makedirs(a.outdir, exist_ok=True)
    for f in asyncio.run(render(tables, a.outdir, a.date)):
        print("OK:", f)

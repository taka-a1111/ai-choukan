# AIトレンド朝刊 note用のHTML変換 ver1.0 (2026-11-11) 下書きの本文を、noteのエディタに貼るHTMLにする
# 使い方: python3 tools/note_html.py --date YYYY-MM-DD --repo <リポジトリのdir> [--out note_payload.json]
#   出力（JSON）: {"title": 記事タイトル, "html": 本文のHTML, "blocks": ブロックの並び（照合用）}
# 変換の決まり: 「## 」の行は h2／「・」で始まる行のまとまりは箇条書き／URLだけの行はリンク／
#   「今日やること」「ほかに押さえておきたい」の中の2行のまとまりは、1行目を h3・2行目を段落にする／それ以外は段落
import argparse, html, json, os, re


def to_html(body):
    out, kinds, sec = [], [], ""
    e = html.escape
    for b in [x for x in re.split(r"\n\s*\n", body) if x.strip()]:
        lines = b.split("\n")
        if lines[0].startswith("## "):
            sec = lines[0][3:]
            out.append(f"<h2>{e(sec)}</h2>"); kinds.append("H2")
            lines = lines[1:]
            if not lines:
                continue
        if all(l.startswith("・") for l in lines):
            out.append("<ul>" + "".join(f"<li>{e(l[1:])}</li>" for l in lines) + "</ul>"); kinds.append("UL")
        elif len(lines) == 1 and re.match(r"^https?://\S+$", lines[0]):
            u = lines[0]
            out.append(f'<p><a href="{e(u)}">{e(u)}</a></p>'); kinds.append("P")
        elif (sec.startswith("今日やること") or sec.startswith("ほかに")) and len(lines) == 2:
            out.append(f"<h3>{e(lines[0])}</h3><p>{e(lines[1])}</p>"); kinds += ["H3", "P"]
        else:
            out.append("<p>" + "<br>".join(e(l) for l in lines) + "</p>"); kinds.append("P")
    return "".join(out), kinds


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--out")
    a = ap.parse_args()
    P = json.load(open(os.path.join(a.repo, "data", "posts", f"{a.date}.json"), encoding="utf-8"))
    h, kinds = to_html(P["note"]["body"])
    res = {"title": P["note"]["title"], "html": h, "blocks": ",".join(kinds)}
    if a.out:
        json.dump(res, open(a.out, "w", encoding="utf-8"), ensure_ascii=False)
        print(f"OK: {a.out}  ブロック {len(kinds)}個  {res['blocks']}")
    else:
        print(json.dumps(res, ensure_ascii=False))

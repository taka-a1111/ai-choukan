# AIトレンド朝刊 画像の指示文 ver1.0 (2026-11-12) 下書きの images から、ChatGPT に送る指示文（見出し画像・図解）を作る
# 使い方:
#   python3 tools/img_prompt.py --date YYYY-MM-DD --repo <リポジトリのdir> --which eyecatch|fig1|fig2|xfig [--json]
#   --json を付けると、JavaScript にそのまま渡せる JSON 文字列で出す
#   --list で、その日に作る画像の一覧（which・置き場所・alt）を出す
# 下書きの images の形（tools/build_posts.py が検査する）:
#   "images": {
#     "eyecatch": {"head1": "主見出し1行目", "head2": "主見出し2行目", "blue": "青にする語",
#                  "sub": "サブコピー", "labels": ["右の図のラベル", ...], "struct": "右の図の構成（言葉で）"},
#     "figs": [{"id": "fig1", "after": "## 概要", "title": "図のタイトル", "texts": ["図の中の文言", ...],
#               "note": "図の下の補足1行", "struct": "図の構成（言葉で）", "alt": "図が示す内容"}],
#     "xfig": {同じ形（after は不要）。X の夜の1本に付ける図}
#   }
# 共通の決まり（色・書体・文字の大きさ・禁止事項）はこのファイルにまとめて持つ。指示文の型を変えるときはここを直す。
import argparse, json, os, re

PALETTE = "背景 #FCF9F7（生成り）、濃紺 #00243F、青 #0B629E、淡いブルー #E7EDF2、罫線 #E0DDD6 の5色だけ"

COMMON = f"""【守ること】
・横長（1536×1024）で1枚だけ作る
・色は {PALETTE}。ほかの色（黄・緑・赤・オレンジ）を使わない
・フラットなビジネス系のインフォグラフィック。グラデーション・影・角丸・3D・写真・人物・手描き風の線・効果線・キラキラした装飾を使わない
・書体は極太のゴシック体だけ。丸ゴシック・明朝体・手書き風の書体を使わない
・上の【文言】に書いた文字だけを一字一句そのまま入れる。それ以外の文字・英語の飾り文字・数字・パーセント・金額・グラフの数値を入れない（指定した文言に含まれる英字と数字は入れてよい）
・実在の企業のロゴやマーク、実在のサービスの画面を描かない。架空のロゴも作らない
・最も小さい文字でも画像の高さの5%以上の大きさにする（スマホで縮めても読めるように）
・アイコンは単色で、線の太さをそろえる
・外側に広い余白を作らない。上下左右の端から画像の5%ほどの余白で、全体を大きく使う
・文字が枠からはみ出さないようにする。入りきらないときは2行にする"""


def q(s):
    return f"「{s}」"


def eyecatch(e):
    labels = "\n".join(f"・右の図のラベル：{q(x)}" for x in e.get("labels") or [])
    return f"""note の記事の見出し画像を1枚作ってください。

【文言】
・左上の小さな札（濃紺の塗りに白文字）：「AIニュース解説」
・主見出し1行目：{q(e['head1'])}
・主見出し2行目：{q(e['head2'])}
・サブコピー：{q(e['sub'])}
{labels}
・左下の小さな文字（濃紺）：「インフォサクセス」

【構成】
・左半分：上から、札、主見出し（極太ゴシック・2行・濃紺。{q(e['blue'])}の部分だけ青 #0B629E）、サブコピー（濃紺の横長の帯に白文字・1行）。左下に「インフォサクセス」
・右半分：{e['struct']}。右の図は3〜5個の要素で、ラベルは箱や札の中に大きく入れる
・主見出しが一番大きく、遠くからでも読めること

{COMMON}"""


def figure(f):
    texts = "\n".join(f"・{x}" for x in f.get("texts") or [])
    return f"""記事に載せる図解を1枚作ってください。

この図で伝えること：{f['title']}

【文言】
・タイトル：{q(f['title'])}
{texts}
・補足：{q(f['note'])}

【構成】
・左上にタイトル（濃紺・極太ゴシック）
・{f['struct']}
・箱や札の中は文字だけにし、画像の高さの6%以上の大きさで入れる。入りきらなければ2行にする
・左下に補足を1行（青 #0B629E の極太ゴシックの文字だけ。注意のアイコンや記号を付けない）。下端に画像の高さの5%ほどの余白

{COMMON}"""


def load(repo, date):
    P = json.load(open(os.path.join(repo, "data", "posts", f"{date}.json"), encoding="utf-8"))
    return P.get("images") or {}


def items(img):
    out = []
    if img.get("eyecatch"):
        out.append(("eyecatch", "note の見出し画像・X の朝の1本", "記事タイトル"))
    for f in img.get("figs") or []:
        out.append((f["id"], f"note の「{f['after'][3:]}」の下", f.get("alt", "")))
    if img.get("xfig"):
        out.append(("xfig", "X の夜の1本（19:00）", img["xfig"].get("alt", "")))
    return out


def prompt(img, which):
    if which == "eyecatch":
        return eyecatch(img["eyecatch"])
    if which == "xfig":
        return figure(img["xfig"])
    for f in img.get("figs") or []:
        if f["id"] == which:
            return figure(f)
    raise SystemExit(f"NG: {which} がこの日の images にありません")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--which")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()
    img = load(a.repo, a.date)
    if a.list or not a.which:
        for w, place, alt in items(img):
            print(f"{w}\t{place}\t{alt}")
    else:
        t = prompt(img, a.which)
        print(json.dumps(t, ensure_ascii=False) if a.json else t)

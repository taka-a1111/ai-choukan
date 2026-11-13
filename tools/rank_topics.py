# AIトレンド朝刊 話題の注目度 ver1.0 (2026-11-13) その日の号の話題を、注目度の高い順に並べる（投稿の下書きで main・others・昼の1本を選ぶため）
# 使い方: python3 tools/rank_topics.py --date YYYY-MM-DD --repo <リポジトリのdir> [--top 20]
# 注目度の目安（号のデータから数える。SNS の数字ではない）
#   媒体数×3 ＋ 記事数 ＋ 国内と海外の両方で報じられた＋2 ＋ 動画でも扱われた＋2 ＋ 重要度3なら＋3 ＋ 主要な企業・サービス名が見出しにある＋2 ＋ 続報＋1
# 読者向けの印（reader）
#   ○：業務に効く（biz）、またはツール・新機能／SEO・検索・Web／活用ノウハウ／開発・自動化の話題
#   ×：株価・売上・決算・上場・買収・資金調達・人事・政治が中心で、読者のやることが変わらない話題（見出しの言葉で判定。目安）
import argparse, json, os, re

MAJOR = ["ChatGPT", "OpenAI", "Gemini", "Google", "グーグル", "Claude", "Anthropic", "Microsoft", "マイクロソフト", "Copilot",
         "Apple", "アップル", "Meta", "Instagram", "Facebook", "X（旧Twitter）", "Grok", "Amazon", "アマゾン", "NVIDIA", "Notion",
         "Canva", "Adobe", "LINE", "楽天", "ソフトバンク", "NTT", "WordPress", "Perplexity", "YouTube"]
NOT_READER = ["株価", "時価総額", "売上", "決算", "上場", "IPO", "買収", "資金調達", "調達", "評価額", "CEO", "人事", "議会", "召喚",
              "大統領", "政権", "規制当局", "訴訟", "提訴"]
READER_CATS = {"T", "S", "K", "D", "ツール・新機能", "SEO・検索・Web", "活用ノウハウ", "開発・自動化"}


def score(t, items):
    its = [items[i] for i in t.get("item_ids", []) if i in items]
    outlets = {i.get("src_id") for i in its}
    types = {str(i.get("src_type", "")) for i in its}
    jp = any(x.endswith("_jp") for x in types)
    en = any(x.endswith("_en") for x in types)
    video = any(x.startswith("youtube") or i.get("kind") == "video" for x, i in zip(types, its)) or any(i.get("kind") == "video" for i in its)
    title = t.get("title", "")
    s = len(outlets) * 3 + len(its) + (2 if jp and en else 0) + (2 if video else 0) + (3 if t.get("importance") == 3 else 0)
    s += 2 if any(m in title for m in MAJOR) else 0
    s += 1 if t.get("prev") else 0
    bad = [w for w in NOT_READER if w in title]
    reader = (bool(t.get("biz")) or t.get("category") in READER_CATS) and not bad
    return s, len(outlets), len(its), jp, en, video, reader, bad


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--top", type=int, default=20)
    a = ap.parse_args()
    D = json.load(open(os.path.join(a.repo, "data", "issues", f"{a.date}.json"), encoding="utf-8"))
    items = {i["id"]: i for i in D.get("items", [])}
    rows = []
    for t in D.get("topics", []):
        s, no, ni, jp, en, video, reader, bad = score(t, items)
        rows.append((s, t["id"], no, ni, ("国内" if jp else "") + ("海外" if en else ""), "動画" if video else "", t.get("importance"), t.get("category"),
                     "○" if reader else "×" + ("（" + "・".join(bad) + "）" if bad else ""), t.get("title", "")[:60]))
    rows.sort(key=lambda r: -r[0])
    print("注目度\t話題ID\t媒体\t記事\t地域\t動画\t重要度\tカテゴリ\t読者向け\t見出し")
    for r in rows[: a.top]:
        print("\t".join(str(x) for x in r))

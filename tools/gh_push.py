# AIトレンド朝刊 GitHubへの反映 ver1.0 (2026-09-30)
# ローカルのフォルダの内容を、GitHub API（Git Data API）で1コミットにまとめて main に反映する。
# 使い方: python3 tools/gh_push.py <ローカルのフォルダ> "<コミットメッセージ>" [対象のサブフォルダ ...]
#   対象のサブフォルダを省略するとフォルダ全体（.git を除く）。対象内でローカルにないファイルはリモートから削除する。
# トークン: 環境変数 GH_TOKEN、なければ ~/.ai-choukan_secrets の GH_TOKEN= 行
import base64, json, os, sys, urllib.request, urllib.error

OWNER, REPO, BRANCH = "taka-a1111", "ai-choukan", "main"
API = f"https://api.github.com/repos/{OWNER}/{REPO}"


def token():
    t = os.environ.get("GH_TOKEN")
    if t:
        return t
    p = os.path.expanduser("~/.ai-choukan_secrets")
    for line in open(p, encoding="utf-8"):
        if line.startswith("GH_TOKEN="):
            return line.split("=", 1)[1].strip()
    sys.exit("GH_TOKEN が見つからない")


TOKEN = token()


def call(method, path, body=None):
    req = urllib.request.Request(API + path, method=method,
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Authorization": f"Bearer {TOKEN}", "Accept": "application/vnd.github+json",
                                          "X-GitHub-Api-Version": "2022-11-28", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read() or b"null")
    except urllib.error.HTTPError as e:
        raise SystemExit(f"{method} {path} -> HTTP {e.code}: {e.read()[:300]!r}")


def local_files(root, subs):
    out = {}
    for base in (subs or ["."]):
        for d, dirs, files in os.walk(os.path.join(root, base)):
            dirs[:] = [x for x in dirs if x != ".git"]
            for f in files:
                full = os.path.join(d, f)
                out[os.path.relpath(full, root).replace(os.sep, "/")] = full
    return out


def main():
    root, msg, subs = sys.argv[1], sys.argv[2], sys.argv[3:]
    files = local_files(root, subs)
    try:
        ref = call("GET", f"/git/ref/heads/{BRANCH}")
        head = ref["object"]["sha"]
    except SystemExit as e:
        if "409" in str(e) or "404" in str(e):
            # 空のリポジトリ：最初の1ファイルを Contents API で作る
            first = "README.md" if "README.md" in files else sorted(files)[0]
            call("PUT", f"/contents/{first}", {"message": "init", "branch": BRANCH,
                                               "content": base64.b64encode(open(files[first], "rb").read()).decode()})
            head = call("GET", f"/git/ref/heads/{BRANCH}")["object"]["sha"]
        else:
            raise
    base_tree = call("GET", f"/git/commits/{head}")["tree"]["sha"]
    remote = {e["path"]: e["sha"] for e in call("GET", f"/git/trees/{base_tree}?recursive=1")["tree"] if e["type"] == "blob"}

    def git_sha(data):
        import hashlib
        return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()

    tree = []
    for path, full in sorted(files.items()):
        data = open(full, "rb").read()
        if remote.get(path) == git_sha(data):
            continue
        blob = call("POST", "/git/blobs", {"content": base64.b64encode(data).decode(), "encoding": "base64"})
        tree.append({"path": path, "mode": "100644", "type": "blob", "sha": blob["sha"]})
    for path in remote:
        in_scope = not subs or any(path == s or path.startswith(s.rstrip("/") + "/") for s in subs)
        if in_scope and path not in files:
            tree.append({"path": path, "mode": "100644", "type": "blob", "sha": None})
    if not tree:
        print("変更なし")
        return
    new_tree = call("POST", "/git/trees", {"base_tree": base_tree, "tree": tree})
    commit = call("POST", "/git/commits", {"message": msg, "tree": new_tree["sha"], "parents": [head]})
    call("PATCH", f"/git/refs/heads/{BRANCH}", {"sha": commit["sha"]})
    print(f"反映しました: {len(tree)}件 commit={commit['sha'][:7]}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""自建站发布底座——所有入口最后都落到这里。

为什么要有这个文件：`import_post.py` 只吃「网络/出稿/待发/ 里的三段式稿文件路径」，
那是出稿流水线那条支流的形状。但自建站是路明者**自己的记录场**，她自己记、自己发才是主路，
那条路手上只有「标题＋正文」，接不上 import_post。所以把"写文件→提交→推"这段共用的抽出来，
三个入口共享：

  A 类  她自己的字（任何通道说一句"发自建站"）  →  publish(title, body, "notes")
  B 类  我生成的沉淀内容（必须她点头才发）       →  publish(title, body, "notes")
  C 类  出稿流水线的成稿（走「发」闸）           →  import_post.py 解析后调 publish(..., "posts")

**入口按逻辑分不按设备分**（她 2026-07-26 定）：钉钉不只一个，以后还有别的终端设备，
设备不该成为分类依据，逻辑才是。

命令行（给 node 那边调，输出是 JSON 一行，便于机读）：
    publish_to_site.py publish --title "标题" --section notes [--note "备注"] < 正文
    publish_to_site.py unpublish --keyword "多维"
    publish_to_site.py list [--section notes]
"""
import argparse
import datetime
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTENT_DIR = ROOT / "content"

# 记＝她自己落的字；稿＝出稿流水线送进来的成稿。中文名和目录名都认，省得调用方记错。
SECTIONS = {"notes": "notes", "记": "notes", "posts": "posts", "稿": "posts"}
DEFAULT_SECTION = "notes"


def read_base_url() -> str:
    """从 hugo.toml 取 baseURL，用来拼给她看的链接。取不到就返回空字符串，不猜。"""
    try:
        text = (ROOT / "hugo.toml").read_text(encoding="utf-8")
    except OSError:
        return ""
    m = re.search(r'^\s*baseURL\s*=\s*"([^"]+)"', text, re.M)
    return m.group(1).rstrip("/") if m else ""


def normalize_section(section: str) -> str:
    key = (section or DEFAULT_SECTION).strip()
    if key not in SECTIONS:
        raise ValueError(f"不认识的栏目「{key}」，只有 记(notes) 和 稿(posts)")
    return SECTIONS[key]


def slugify(title: str) -> str:
    """标题即 slug。她的标题是中文，URL 里保留中文——站上现有文章已经是这个样子，
    换成拼音/英文反而跟历史链接不一致。只把会把 URL 或文件名弄坏的字符剔掉。"""
    s = title.strip()
    s = re.sub(r'[/\\:*?"<>|#%\s]+', "-", s)
    s = re.sub(r"-{2,}", "-", s).strip("-.")
    return s or "无题"


def git(*args, check=True):
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=check, capture_output=True, text=True
    )


def git_sync(message: str) -> dict:
    """提交并推。

    "没有改动可提交" 不算失败——它的意思是这份内容站上已经有了，跟"推挂了"是两回事。
    2026-07-26 踩到过：稿_20260724 已发到站上却还留在 待发/，再触发一次就走到这里，
    commit 返回非 0，上游于是报"⚠️ 自建站没发成功"——已发的报失败，是假警报。
    """
    git("add", "-A")
    status = git("status", "--porcelain")
    if not status.stdout.strip():
        return {"changed": False, "pushed": False, "detail": "站上已经是这个内容，没有改动可提交"}
    git("commit", "-m", message)
    push = git("push", check=False)
    if push.returncode != 0:
        return {
            "changed": True,
            "pushed": False,
            "detail": (push.stderr or push.stdout or "push 失败").strip()[-300:],
        }
    return {"changed": True, "pushed": True, "detail": ""}


def publish(title: str, body: str, section: str = DEFAULT_SECTION,
            note: str | None = None, date: datetime.date | None = None,
            push: bool = True, slug: str | None = None) -> dict:
    """写一篇进站。title/body 由调用方给（A/B 类是她的字或我生成的，C 类是解析稿文件来的）。

    备注（note）只在她说"加备注"时才有，落文末一行小字，不主动加。

    slug 不给就按标题取。出稿流水线那条（import_post.py）要显式传——它历来是按
    **稿文件名**取 slug 的（`稿_20260724_节奏与计数器` → `节奏与计数器`），
    改成按标题取会让 URL 跟站上历史文章对不上，那是白白弄丢的链接。
    """
    title = (title or "").strip()
    body = (body or "").strip()
    if not title:
        raise ValueError("没有标题——标题不自己拟，问她一句（她 2026-07-26 定）")
    if not body:
        raise ValueError("正文是空的")

    sec = normalize_section(section)
    d = date or datetime.date.today()
    slug = slugify(slug or title)

    dest_dir = CONTENT_DIR / sec
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{d.isoformat()}-{slug}.md"
    # 同一天同一个标题再发一次：不覆盖旧的（门规：写前必读、不静默毁掉已有的），另起一个
    n = 2
    while dest.exists():
        dest = dest_dir / f"{d.isoformat()}-{slug}-{n}.md"
        n += 1

    escaped = title.replace('"', '\\"')
    front = f'---\ntitle: "{escaped}"\ndate: {d.isoformat()}\ndraft: false\n---\n\n'
    tail = f"\n\n*{note.strip()}*\n" if note and note.strip() else "\n"
    dest.write_text(front + body + tail, encoding="utf-8")

    base = read_base_url()
    url = f"{base}/{sec}/{dest.stem}/" if base else f"/{sec}/{dest.stem}/"

    result = {
        "ok": True,
        "action": "publish",
        "title": title,
        "section": sec,
        "section_cn": "记" if sec == "notes" else "稿",
        "file": str(dest.relative_to(ROOT)),
        "url": url,
    }
    if push:
        result.update(git_sync(f"add {sec}: {dest.stem}"))
    return result


def find_candidates(keyword: str) -> list[Path]:
    """按关键词找站上的文章。找不准就把候选交回去让上层反问——**不猜**：
    自建站是真发出去的东西，撤错一篇比多问一句贵。"""
    kw = (keyword or "").strip()
    # set()：SECTIONS 里中英两个键映到同一个目录（记→notes、稿→posts），
    # 不去重会把每篇文章扫出两遍，然后本来唯一的匹配变成"有2篇，撤哪一篇？"
    files = sorted(
        [p for sec in set(SECTIONS.values()) for p in (CONTENT_DIR / sec).glob("*.md")
         if p.name != "_index.md"],
        key=lambda p: p.name,
        reverse=True,
    )
    if not kw:
        # 不给关键词**不能**默认撤"最近那篇"——按文件名排序的第一个未必是她刚发的，
        # 撤错一篇比多问一句贵。全都交回去让上层列清单反问。
        return files
    return [p for p in files if kw in p.stem or kw in p.read_text(encoding="utf-8")]


def unpublish(keyword: str = "", push: bool = True) -> dict:
    """撤一篇。她明确要的：**撤生效的结果，告诉我撤了啥**——所以回执一定点名到篇。"""
    candidates = find_candidates(keyword)
    if not candidates:
        return {"ok": False, "action": "unpublish", "reason": "no_match",
                "message": f"站上没有能对上「{keyword}」的文章"}
    if len(candidates) > 1:
        return {
            "ok": False,
            "action": "unpublish",
            "reason": "ambiguous",
            "candidates": [{"title": p.stem, "file": str(p.relative_to(ROOT))} for p in candidates],
            "message": f"对上「{keyword}」的有 {len(candidates)} 篇，要撤哪一篇？",
        }

    target = candidates[0]
    sec = target.parent.name
    title = ""
    m = re.search(r'^title:\s*"(.*)"\s*$', target.read_text(encoding="utf-8"), re.M)
    if m:
        title = m.group(1)
    target.unlink()

    result = {
        "ok": True,
        "action": "unpublish",
        "title": title or target.stem,
        "section": sec,
        "section_cn": "记" if sec == "notes" else "稿",
        "file": str(target.relative_to(ROOT)),
    }
    if push:
        result.update(git_sync(f"remove {sec}: {target.stem}"))
    return result


def list_posts(section: str | None = None) -> dict:
    secs = [normalize_section(section)] if section else sorted(set(SECTIONS.values()))
    items = []
    for sec in secs:
        for p in sorted((CONTENT_DIR / sec).glob("*.md"), reverse=True):
            if p.name == "_index.md":
                continue
            items.append({"section": sec, "section_cn": "记" if sec == "notes" else "稿",
                          "file": str(p.relative_to(ROOT)), "stem": p.stem})
    return {"ok": True, "action": "list", "items": items}


def main() -> None:
    ap = argparse.ArgumentParser(description="自建站发布底座")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("publish", help="发一篇（正文走 stdin）")
    p.add_argument("--title", required=True)
    p.add_argument("--section", default=DEFAULT_SECTION)
    p.add_argument("--note", default=None)
    p.add_argument("--no-push", action="store_true", help="只写本地不提交，用来干跑")

    u = sub.add_parser("unpublish", help="撤一篇")
    u.add_argument("--keyword", default="")
    u.add_argument("--no-push", action="store_true")

    l = sub.add_parser("list", help="列站上现有的")
    l.add_argument("--section", default=None)

    args = ap.parse_args()
    try:
        if args.cmd == "publish":
            out = publish(args.title, sys.stdin.read(), args.section,
                          note=args.note, push=not args.no_push)
        elif args.cmd == "unpublish":
            out = unpublish(args.keyword, push=not args.no_push)
        else:
            out = list_posts(args.section)
    except Exception as e:  # 出错也吐 JSON，上游（node）不用去解析 stderr 的自然语言
        print(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))
        sys.exit(1)

    print(json.dumps(out, ensure_ascii=False))
    sys.exit(0 if out.get("ok") else 1)


if __name__ == "__main__":
    main()

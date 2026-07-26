#!/usr/bin/env python3
"""将「生长系统/网络/出稿/」产出的稿件转换为本站 Hugo 文章。

用法：
    python3 scripts/import_post.py <稿文件路径> [--publish]

只读取命令行传入的这一个文件，不扫描、不修改来源目录下的任何其他文件。
--publish 会额外执行 git add/commit/push（触发 GitHub Actions 自动构建部署）；
不加则只在本地生成文章文件，留给人工确认后再提交。

2026-07-26 改成薄壳：解析这一段留在这里，写文件/提交/推那一段搬去
`publish_to_site.py`——她自己发的那两条入口（A 类她的字、B 类我生成的沉淀）
手上只有「标题＋正文」，接不上这个只吃稿文件的接口，所以底座得共用。
这个文件的对外行为一字未改。

预期输入格式（三段式，硬要求）：
    平台/取材/角度 等元数据
    ---
    **标题**

    正文段落...
    ---
    回"发 MMDD"→进发布链路 ... （引导语，忽略）

**格式不符合就直接退出，不兜底**——自建站是真发出去，宁可拒收也不能发个残的上去。
（公众号那条链路有兜底：退回用文件名当标题。两边不一样是故意的。）
格式规范写在 `配置/每日回应_指令.md` 的「稿文件格式（硬规范）」一节。
"""
import datetime
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from publish_to_site import publish  # noqa: E402


def parse(src: Path) -> dict:
    """把三段式稿文件拆成 标题／正文／日期。只解析，不写盘。"""
    text = src.read_text(encoding="utf-8")
    parts = text.split("---")
    if len(parts) < 3:
        sys.exit("格式不符合预期（缺少 --- 分隔的三段结构），未转换")
    body = parts[1].strip("\n")

    lines = [l for l in body.splitlines() if l.strip() != ""]
    if not lines:
        sys.exit("正文为空，未转换")

    title_match = re.match(r"^\*\*(.+)\*\*$", lines[0].strip())
    title = title_match.group(1) if title_match else src.stem
    content_lines = lines[1:] if title_match else lines
    content = "\n\n".join(l.strip() for l in content_lines)

    m = re.search(r"(\d{8})", src.stem)
    if m:
        d = m.group(1)
        date = datetime.date(int(d[0:4]), int(d[4:6]), int(d[6:8]))
    else:
        date = datetime.date.today()

    # slug 按**稿文件名**取，不按标题——站上历史文章都是这么来的，换成标题会换掉 URL
    slug = re.sub(r"^稿_\d{8}_", "", src.stem) or src.stem

    return {"title": title, "body": content, "date": date, "slug": slug}


def main() -> None:
    args = sys.argv[1:]
    if not args:
        sys.exit("用法: import_post.py <稿文件路径> [--publish]")
    do_publish = "--publish" in args
    args = [a for a in args if a != "--publish"]
    src = Path(args[0])
    if not src.is_file():
        sys.exit(f"文件不存在: {src}")

    parsed = parse(src)
    # 走出稿流水线进来的是成稿 → 落「稿」那一栏（notes 那栏是她自己落的字）
    result = publish(
        parsed["title"], parsed["body"], section="posts",
        date=parsed["date"], slug=parsed["slug"], push=do_publish,
    )
    print(f"已生成: {Path(result['file'])}")

    if do_publish:
        if result.get("pushed"):
            print("已提交并推送，GitHub Actions 将自动构建部署。")
        elif not result.get("changed"):
            print("站上已经是这个内容，没有改动可提交（不算失败）。")
        else:
            sys.exit(f"提交了但没推成功：{result.get('detail')}")


if __name__ == "__main__":
    main()

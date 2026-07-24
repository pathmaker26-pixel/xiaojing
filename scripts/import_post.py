#!/usr/bin/env python3
"""将「生长系统/网络/出稿/」产出的稿件转换为本站 Hugo 文章。

用法：
    python3 scripts/import_post.py <稿文件路径> [--publish]

只读取命令行传入的这一个文件，不扫描、不修改来源目录下的任何其他文件。
--publish 会额外执行 git add/commit/push（触发 GitHub Actions 自动构建部署）；
不加则只在本地生成文章文件，留给人工确认后再提交。

预期输入格式（与 网络/出稿/ 现有样本一致的三段式）：
    状态/取材/角度 等元数据
    ---
    **标题**

    正文段落...
    ---
    回"发 MMDD"→进发布链路 ... （引导语，忽略）
"""
import datetime
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEST_DIR = ROOT / "content" / "posts"


def convert(src: Path) -> Path:
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
        date_fmt = f"{d[0:4]}-{d[4:6]}-{d[6:8]}"
    else:
        date_fmt = datetime.date.today().isoformat()

    slug = re.sub(r"^稿_\d{8}_", "", src.stem) or src.stem

    DEST_DIR.mkdir(parents=True, exist_ok=True)
    dest = DEST_DIR / f"{date_fmt}-{slug}.md"

    escaped_title = title.replace('"', '\\"')
    front_matter = f'---\ntitle: "{escaped_title}"\ndate: {date_fmt}\ndraft: false\n---\n\n'
    dest.write_text(front_matter + content + "\n", encoding="utf-8")
    return dest


def publish(dest: Path) -> None:
    rel = dest.relative_to(ROOT)
    subprocess.run(["git", "add", str(rel)], cwd=ROOT, check=True)
    subprocess.run(
        ["git", "commit", "-m", f"add post: {dest.stem}"], cwd=ROOT, check=True
    )
    subprocess.run(["git", "push"], cwd=ROOT, check=True)


def main() -> None:
    args = sys.argv[1:]
    if not args:
        sys.exit("用法: import_post.py <稿文件路径> [--publish]")
    do_publish = "--publish" in args
    args = [a for a in args if a != "--publish"]
    src = Path(args[0])
    if not src.is_file():
        sys.exit(f"文件不存在: {src}")

    dest = convert(src)
    print(f"已生成: {dest}")

    if do_publish:
        publish(dest)
        print("已提交并推送，GitHub Actions 将自动构建部署。")


if __name__ == "__main__":
    main()

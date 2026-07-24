# 自建站（第一段）

Hugo 静态站，挂在 Mac mini 上写、构建，推 GitHub 后由 Actions 自动构建部署到 GitHub Pages。

## 结构

- `hugo.toml` — 站点配置（标题、语言等）
- `layouts/` — 极简自定义主题：留白、正文为主、无评论区、无侧栏
- `content/posts/` — 文章（Markdown），当前为空
- `scripts/import_post.py` — 出稿钩子，见 [HOOKS.md](./HOOKS.md)
- `.github/workflows/deploy.yml` — push 到 `main` 后自动 `hugo --minify` 构建并部署到 GitHub Pages

## 本地预览

```
hugo server
```

浏览器打开 http://localhost:1313/

## 发新文章

手动写：

```
hugo new posts/文件名.md
```

或通过出稿钩子从「生长系统/网络/出稿/」的稿件转换（见 HOOKS.md）。

## 部署

push 到 `main` 分支即自动部署，无需手动操作。地址：见仓库 Settings → Pages，或本次搭建交付时给出的链接。

## 与「生长系统」的边界

本仓库不读写 `~/生长系统/` 下除 `网络/出稿/` 里被显式指定的单个稿件文件之外的任何内容；发布脚本、每日回应 v3 由另一条线负责，本仓库只留接口，不代做、不抢先设计。

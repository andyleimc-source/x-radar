# posts/ · 小红书发布归档

每期一个文件夹 `posts/<YYYY-MM-DD>/`，存放当天的成片 + 文案。

```
posts/
  2026-06-28/
    post.md          # 小红书标题 / 正文介绍 / 标签 / 图片顺序 / 来源自查 / 发布状态
    01.png … NN.png  # 内容图（第 1 张即封面，按重要性排序）
    NN-cta.png       # 尾卡（节目名 + 引流）
```

## 约定

- **post.md 入 git**（编辑记录、发布状态可查可回溯）；**图片不入 git**（见根 `.gitignore`，日更图片会把仓库撑大），本地留着能看能传。
- 发小红书时：复制 `post.md` 里的「小红书标题」+「正文介绍」+ 标签，按「图片顺序」上传图片。
- **正文/图片里绝不放链接**（http / t.co）——小红书检测到带链接会限流或封号。来源只在 `post.md` 的「来源自查」区列 `@handle` 供本人核对，发布时不带出去。

## 怎么生成一期

```bash
bash scripts/build-xhs.sh [YYYY-MM-DD]
```

`build-xhs.sh` 末尾会自动调 `scripts/archive_xhs.py` 把当天图片归档到这里并生成 post.md。
也可单独补归档某天：`python3 scripts/archive_xhs.py --date 2026-06-28`。

工作区 `data/xhs/`（临时渲染输出、会被覆盖、整体 gitignore）与本目录分开——`posts/` 才是留存的发布档案。

# 笔记导入

博客已经包含导入后的文章，GitHub Actions 构建时不需要 Python，也不运行导入脚本。

需要从本地笔记重新同步时，把本仓库与 `markdown_articles`、`reading_memory`、`article_summaries` 放在同一父目录，然后运行：

```powershell
python -m pip install -r scripts/requirements-import.txt
python scripts/import-notes.py
```

脚本只覆盖它管理的 `src/content/posts/aNNNN.md`，并移除模板示例文章；其他手写文章保留。每篇地址稳定为 `/posts/aNNNN/`。

- 原 Markdown 保留在外部笔记目录，不会被修改。
- 原标题转为 frontmatter，正文保留 `ailx10说：` 摘要与 `---` 分隔线；不插入额外开场。
- 正文代码块导入前后逐块比对，站内文章链接改为正式路由。
- 仅将引用的图片放入 `public/notes-assets`。静态 PNG 无损转换为 WebP，逐张检查 RGBA 像素与尺寸；JPEG、SVG、GIF 保持原文件格式。
- 导入时自动过滤已核实的知乎界面图标（知达星号、搜索、链接、播放按钮及 GIF 角标），按 SVG 绘图签名精确匹配；关键词搜索跳转保留文字、去除链接。正文截图、公式与 GIF 动画保留。
- 原记录只有编辑日期时，用 `updated`、`dateKind: edited`、`dateNote` 表明；`published` 是主题排序兼容字段，不应解释为首次写作日期。
- 原审阅报告、候选隐私内容等 `_meta` 文件不会导入文章或 `public`。
- 逐篇复核过的重复概述、编辑工作流提示、外层壳标题及链接卡装饰，按 `note-editorial-cleanup.json` 中的文章编号与精确原文匹配清理；必须保留的具体技术条件放在对应正文或结尾，不新增摘要之外的开场。
- 已复核的空 SVG 懒加载占位按文章编号恢复为对应的原图，同一占位被不同文章复用时分别处理；公式 SVG 和有效的小图保留。

`notes-import-report.json` 记录体积与总数，`notes-import-manifest.json` 记录每篇导入结果。格式与素材检查不代表历史代码已重新运行，或所有截图内容都已逐张核验。

若需要对已有网站文章及同级的两套 Markdown 导出稿检查同类图标：

```powershell
python scripts/clean_note_ui_icons.py          # 预览
python scripts/clean_note_ui_icons.py --apply  # 备份后清理
```

清理前后逐篇核对正文文字、围栏与行内代码以及保留的图片引用。检查报告保存在本地 `notes-ui-icon-*.json`，修改前文件备份到网站仓库外的 `note-ui-cleanup-backup-*` 目录。

要将已经复核过的正文清理规则应用到站点，并同步到同级两套 Markdown：

```powershell
python scripts/apply-reviewed-cleanup.py          # 预览并校验三份稿件
python scripts/apply-reviewed-cleanup.py --apply  # 备份后写入
```

该命令会先检查网站与主 Markdown 是否一致，再写入清理结果。两套导出稿使用相同的摘要、分隔线和正文；所有文章的代码围栏、图片文件与站内链接都进行核对。

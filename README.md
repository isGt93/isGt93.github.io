# 黑客笔记 · ailx10

基于 [Mizuki](https://github.com/LyraVoid/Mizuki)（Fuwari 衍生主题）的个人安全知识库，使用 Astro、Svelte、Pagefind 和 GitHub Pages。

## 本地开发

环境：Node.js 24、pnpm 11.5.3。

```sh
pnpm install --frozen-lockfile
pnpm dev
pnpm build
pnpm preview
```

构建时会生成 Pagefind 全文索引。开发模式中的搜索以生产构建结果为准。

## 写作与维护

- 文章：`src/content/posts/`，历史笔记采用稳定的 `a0001` 等文件名。
- 站点设置：`src/config/`；作者介绍：`src/content/spec/about.md`。
- 图片：`public/notes-assets/`；品牌图片：`public/brand/`。
- 摘要以“ailx10说：”开头，与正文使用 `---` 分隔；技术代码使用代码块。
- 历史记录日期用于归档排序；仅保留编辑日期的文章使用 `dateKind: edited` 和 `updated`，摘要保留原来的时间说明。

正文保留历史实验环境和实际观察，复现时请根据对应版本及授权环境核对。

## 部署

推送 `master` 分支后，`.github/workflows/deploy.yml` 自动构建并发布到 GitHub Pages。仓库 Settings → Pages 的 Source 选择 GitHub Actions。

站点地址：<https://isgt93.github.io/>。如以后使用 Vercel，可导入同一仓库，`vercel.json` 已提供构建设置；更换域名时同步修改 `src/config/siteConfig.ts` 的 `siteURL`。

交互扩展可以放入 Astro / Svelte 组件；笔记ID、分类和标签可作为后续知识图谱与高级搜索的数据基础。

## 主题与版权

感谢 Mizuki 与 [Fuwari](https://github.com/saicaca/fuwari)。主题代码保留上游许可证及版权声明；笔记和截图不因主题许可证而自动获得统一的转载授权。

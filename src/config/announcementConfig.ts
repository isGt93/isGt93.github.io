import type { AnnouncementConfig } from "../types/config";
export const announcementConfig: AnnouncementConfig = {
  title: "从一篇笔记开始",
  content: "这里保存实验、代码和阅读笔记。可以按分类浏览，也可以直接搜索一个问题。",
  closable: true,
  link: { enable: true, text: "浏览全部笔记", url: "/archive/", external: false },
};

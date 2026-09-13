---
name: html5-game
description: 单文件 HTML5 游戏输出规范，产物为 /workspace/work/index.html
---

# HTML5 单文件游戏规范

- 产物：唯一可交付文件 `/workspace/work/index.html`，CSS/JS 全部内联。
- 禁止引用外部文件：`script[src]`、`link[href]`、`img[src]`、`video[src]`、`audio[src]` 不准出现 http(s)、`//` 开头或相对路径，只允许 `data:`、`blob:`、`#`。
- 中文界面，必须包含开始、结束、重开三种状态。
- 桌面键盘与触屏都要能玩，画布自适应窗口大小。
- 用户素材在 `/workspace/input`，只读；需要使用时把内容内联进 index.html。
- 写完后用 `execute` 跑 `node --check` 自查内联脚本，通过才算完成。

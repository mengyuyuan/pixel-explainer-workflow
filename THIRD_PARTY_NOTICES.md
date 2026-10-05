# 第三方来源与媒体许可

## 精灵绘制工具

- 项目：[a252937166/claude-video-studio](https://github.com/a252937166/claude-video-studio)
- 固定版本：`d0c9fc5922a5ac8e2b9f274f01284faf6c165868`
- 使用文件：`scripts/pixel_sprite.py`，作为本仓库 `vendor/pixel_sprite.py` 分发。
- 许可：MIT，原文保留于 `vendor/LICENSE`。
- `make_sprites.py` 使用 Grid、outline、save、sheet 等方法，并调整调色板与角色姿势。8-bit 音效脚本按上游教程第 7 节的方法自行编写。

## 电梯井视频及派生媒体

- 原作品：**Going down in an elevator shaft .webm**
- 作者：**Uwe Brodrecht**
- 作品页面：[Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Going_down_in_an_elevator_shaft_.webm)
- 许可：[Creative Commons Attribution-ShareAlike 2.0 Generic](https://creativecommons.org/licenses/by-sa/2.0/)
- 原始直链：https://upload.wikimedia.org/wikipedia/commons/f/fc/Going_down_in_an_elevator_shaft_.webm
- 本仓库 `assets/shaft-excerpt.mp4`：从原片 2–6 秒取片段，缩放至 360×640，转为 H.264 并去掉原音。
- 默认速度 1.2 时，动画中 3.75–5.333 秒展示该片段的前约 1.583 秒。该实拍用于展示钢索和导轨，不声称画面清楚拍到了配重。实拍自身保持正常播放速度，展示窗口随整体时间映射缩短。
- `demo/elevator-sfx-demo.mp4`：上述片段与原创像素动画、字幕和合成音效组合；未使用私人旁白。作为改编媒体按 CC BY-SA 2.0 提供。
- `demo/contact-sheet.png`：从含上述片段的动画提取的缩小画面，按 CC BY-SA 2.0 提供。
- 原作者不表示对本项目的认可或背书。再分发这些媒体时保留作者、来源、许可和修改说明。

## 运行时和可选配音

- [HyperFrames](https://github.com/heygen-com/hyperframes)、[GSAP](https://gsap.com/)、[Playwright](https://playwright.dev/) 由 npm 安装，许可保留在依赖包中；本仓库 MIT 许可不替换这些依赖的许可。
- [VoxCPM](https://github.com/OpenBMB/VoxCPM) 是可选的外部 TTS 工具。模型与权重需另行取得，遵守其各自许可。本仓库未分发参考声、模型、原始克隆配音、远程凭据或私人机器配置。
- 原理核对采用 [Otis 官方说明](https://www.otis.com/en/uk/w/the-basic-workings-of-a-lift)，没有复制其图片或视频。

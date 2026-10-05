# 人物故事模板

这套入口公开了实际使用的人物动作代码、原创图集与声音合成方法，不依赖原作者的电脑。默认 32 秒是功能示范，不是影片时长限制；资本论仅是可选的完整场景示例。

## 安装、运行

安装 Node.js 22+、Python 3.10+、FFmpeg/ffprobe，放入 PATH。然后在仓库根目录：

```bash
npm ci
python -m pip install -r requirements.txt
python tools/story.py init projects/my-story
python tools/story.py prepare projects/my-story
python tools/story.py render projects/my-story
python tools/story.py check projects/my-story
```

首次渲染可能下载 Chromium；中文需微软雅黑、苹方或 Noto Sans CJK SC。项目生成目录可以在仓库外，命令仍从仓库运行。直接预览可用 `npx hyperframes preview projects/my-story`，或 `python -m http.server --directory projects/my-story 8080` 打开生成的 index.html；静态 HTML 默认停在第一帧，播放预览用 HyperFrames。

默认输出 `projects/my-story/renders/film.mp4`，技术检查在项目的 `build/technical-check.json`。输出磁盘和临时目录可以独立指定：

```bash
python tools/story.py render projects/my-story --output /path/to/film.mp4 --temp-dir /path/to/render-temp
python tools/story.py check projects/my-story --output /path/to/film.mp4
```

会使用实际输出尺寸测试硬件编码器，有可用设备才请求 GPU；失败记录在 `build/render-settings.json` 并回退 CPU。浏览器 GPU 由 HyperFrames 独立探测。纯合成音效使用 CPU，不需要声音模型或 API。

## 换自己的故事

1. 编辑 `project.json` 的主题、系列名、字幕、总时长、画幅、帧率；以实际旁白的句段边界设置 cues。可选示例还有 shots 分镜数据。
2. 编辑 `scenes.js`，按镜头编排人物目标、接近、接触、操作、释放和反应。默认示例展示工作、持物行走、检查、拒绝、安装和群体到达。
3. 编辑 `sound-events.json`，每个事件填写 `kind`、`start`、`rmsDBFS`、`pan`、`role`。接触变了就重新对时，避免在每句字幕或每次切镜加音阶。
4. 重新 prepare、render、check，并正常速度看人物与道具交接、合画面试听。

```bash
python tools/story.py prepare projects/my-story --voice /path/to/your-narration.wav
```

旁白可来自自己的录音或有权使用的 TTS。较短音频会补静音；超过项目时长会报错，不截掉句尾。命令不会自动对齐新旁白和旧字幕，也不会自动加速声音：修改朗读后应重设 cues、动作和音效。未给 `--voice` 会明确生成纯音效轨，不能把它当成完成了配音。没有捆绑个人参考声、选定的 03 配音、模型权重或机器连接资料。

## 动作和图集接口

- `perform(row,x,y,h,time,action,options)`：待机、眨眼、说话、思考、走路、转身、伸手、推、拉、携带、放下、验货、拒绝、惊讶、失落、点头。返回手部世界坐标和手部前景重绘函数。
- `moveActor(...)`：用实际位移选择走路相位，到达后停止；`carrying=true` 保持上半身持物。
- `heldCloth(actor,width)`、`heldPaper(actor,text)`：绑定手部坐标。其他物件同样先画在手坐标，再调用 `actor.hands()` 恢复遮挡。
- `operatedLoom(...)`：示范人物操作机器、杆件跟手及成品展示。新题材应换工具和对应动作，不保留无关织机。
- `sprites.json` 对应三位角色和图集路径；`prepare_sprites.py` 生成裁切框、脚底和初始手部坐标。换图后要逐姿势检查手的真实接触点，自动框选不能代替校准。默认图集为 5 列 × 4 行。
- `assets/performers.json` 和 `performer-data.js` 保存结果。建议修改准备脚本里的 grips 后重新生成，避免下次 prepare 覆盖手改的数据。

图集都是本项目原创 AI 生成图片，可直接复用或换成自己的角色；来源和哈希见 `ASSETS.json`，生成提示见 `prompts/`。两个走路触地姿势的源画比较相似，需要更细表演时继续重画步态，20 姿势数量不等于成片观感自动合格。

## 画面比例

同画幅观察及比例选择的依据见 [构图对照](REFERENCE_COMPOSITION.md)。

默认逻辑画布 960×540。常态人物高 64 像素，约占画面高度的 12%；操作近景用 128 像素。只把人缩小而让道具悬空不成立，接触位置与站位也要重排。建筑可以较大，给人物留出通路；钱、工具、价签等当前信息焦点按可读性突出。

输出尺寸可在 project.json 设置，保持 16:9 可直接放大。其他比例目前采用居中留边以免拉伸；真正的竖屏应重排逻辑画布、人物、字幕和场景，不能把横版留边输出说成已完成竖版设计。人物按逻辑像素整数倍绘制，最终交付宜使用逻辑画布的整数倍分辨率。

## 完整故事示例

```bash
python tools/story.py init projects/weaving-example --example capital
python tools/story.py prepare projects/weaving-example
python tools/story.py render projects/weaving-example
```

该例包含完整 230.8 秒、18 镜脚本和 57 个音效事件，画面已同步小人物构图：常态人物约占画高 12%，操作近景约 24%，同时调整持物、站位和接触点。示例题材不覆盖公共规则。原旁白不分发，默认只听到音效；接入另一条旁白必须重新核对时序。

技术检查、正常速度观影和主观听审分别记录。公开模板能复用实际渲染与表演能力，不保证任意选题只改几个配置就达到相同叙事质量。

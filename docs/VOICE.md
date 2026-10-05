# 接入 VoxCPM 或其他本地配音

公开示例默认只有音效。`pipeline.py prepare --voice ...` 接收本机已有音频，转换为 48 kHz 单声道后加入立体声混音；音频路径只用于本地处理，不会复制成仓库素材。

## 生成声音

按 [OpenBMB/VoxCPM 官方仓库](https://github.com/OpenBMB/VoxCPM) 安装与下载模型。VoxCPM 的 Python 版本要求与普通渲染工程不同，当前官方要求 Python 3.10–3.12；建议使用单独环境并安装匹配 GPU 的 PyTorch。

本仓库提供 GPU 优先入口，在 VoxCPM 环境里运行：

```bash
python tts.py --probe
python tts.py --model-path /path/to/VoxCPM2 --text-file narration.txt --reference-audio /path/to/authorized-reference.wav --output build/narration.wav
```

默认实际探测 CUDA，然后 MPS，没有可用 GPU 才选择 CPU，并输出选中的设备。省略 `--reference-audio` 会使用 VoxCPM 的声音设计模式。`--device cpu` 或 `--device cuda:0` 可显式覆盖自动选择；显式指定不可用设备会报错。模型加载错误或显存不足也会正常报错，不会把它们掩盖成“没有 GPU”。

也可以直接使用 VoxCPM CLI：

```bash
voxcpm clone --device auto --text "你要朗读的文案" --reference-audio "/path/to/authorized-reference.wav" --model-path "/path/to/VoxCPM2" --cfg-value 2 --inference-timesteps 20 --normalize --no-denoiser --local-files-only --output "/path/to/narration.wav"
```

只使用本人或得到授权的参考声。也可以直接录音或选择其他 TTS，动画工程并不依赖 VoxCPM 才能运行。模型由使用者按官方说明取得，本仓库不下载或分发模型。

## 对齐再混音

1. 朗读本例可用 `narration.txt`。检查错字、漏字、停顿和句尾，修正后再对齐。
2. 用语音转录工具得到词时序，或听音逐句调整 `timing.json`；其中的时间包含 `voiceOffsetSeconds`。
3. 把场景和动作落点同步到 `scene-core.js`、`build_scene.py`，把音效落点同步到 `synthesize_sfx.py`。
4. 运行 `python pipeline.py prepare --voice /path/to/narration.wav`，再预览与渲染。

源动画是 30 秒，旁白长度加偏移不得超过该长度。默认使用 1.2 倍速度输出 25 秒。延长整片需要改源时间轴、动作、音效及渲染设置，不能只把过长语音强行塞进去。

生成后的混音、渲染文件均位于 Git 忽略目录。发布自己的版本时，另外确认成片中声音的公开使用范围。

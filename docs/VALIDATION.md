# VoiceInput V0.1 验证记录

日期：2026-09-28。环境：Windows 11 10.0.26200 x64，Python 3.13.11，PySide6 6.11.2，sherpa-onnx 1.13.8。

## 已完成

| 验证项 | 证据与结果 |
|---|---|
| 核心自动测试 | `python -m pytest -q`：34 passed。涵盖配置验证/回滚、词典、数字、单位、化学式、Profile、顺序、原文不变、Trace、Lua 隔离/热重载/限时/只读配置、学习与备份、下载取消、历史、候选确认、输出回退与部分发送保护 |
| 源码启动 | `python -m voiceinput --smoke-test` 退出码 0；真实托盘启动和正常退出 |
| 全局快捷键 | `scripts/verify_hotkey.py`：实际 Windows RegisterHotKey 收到按下事件，检测保持和释放，PASS |
| 麦克风 | `scripts/verify_runtime.py --microphone`：真实默认麦克风采到 15808 个样本，16000 Hz；不保存录音 |
| 首次模型安装 | 从官方 GitHub Releases 下载 155.5 MiB 模型压缩包及约 0.6 MiB VAD；解包、识别模型加载、VAD 加载、SHA-256 写入成功 |
| 本地 VAD | 全零音频被拒绝为“未检测到语音” |
| 离线识别 | Windows SAPI 在内存生成 150000 样本测试语音，识别出“今天下午去实验室看看数据。氮气流量100标准立方米每小时。温度500摄氏度。”；没有上传或保存音频 |
| 真实 ASR → Pipeline | 得到“今天下午去实验室看看数据。N₂流量为100 Nm³/h。温度为500 ℃。”及 13 条轨迹 |
| SendInput | 独立原生 Windows EDIT 测试窗口收到与预期完全一致的中文、化学下标、单位和 emoji；INPUT 结构 40 字节 |
| Clipboard | 同一独立测试窗口收到粘贴文本，原剪贴板恢复未报告错误 |
| GUI 视觉 | 使用真实候选组件渲染并查看 `candidate-preview.png`；中文字体、上下标、编辑区、原始区和操作按钮可见 |
| 打包 | PyInstaller 目录模式构建；修复 PATH 中 Poppler 的不兼容 ICU 被误收集导致 QtCore 加载失败的问题 |

发布包隔离启动结果见 `package-validation.json`：在 PATH 仅包含 Windows System32 的子进程中，分别用全新数据目录和已有模型目录启动。该检查验证打包程序无需调用系统 Python；不等同于在另一台没有 Python 的物理机器测试。

## 未完成或受限的验收

- 未由用户实际口述完成“按住说话 → 候选编辑 → 确认上屏”的整条人工验收。分别验证了真实快捷键、真实采集、真实 ASR 和真实输出；合成语音不能证明用户麦克风环境中的识别质量。
- 记事本、Chrome/Edge 和 VS Code 的应用级兼容性还需人工验证。专用 Windows EDIT 测试控件通过，不冒充记事本通过。
- 尝试在新建临时 Word 文档中自动测试，Windows 拒绝测试脚本恢复前台焦点（SetForegroundWindow）；保护逻辑停止了输出。Word 测试没有通过，不能据此断言实际候选点击后的 Word 输出失败或成功。
- Qt 文本框在本机当前输入法环境中出现 SendInput 已接受但文字滞留/次序异常；原生 Windows EDIT 没有该问题。应用兼容问题应在设置中改为 clipboard，不会在已接受 SendInput 后自动重发，防止重复。
- 尚未在另一台没有 Python 的 Windows 机器执行人工验收。
- 模型断网/服务器 Range 续传的真实网络中断场景尚未全面实测；提供取消、分片保留和续传实现，取消路径已自动测试。

因此本交付为**功能已实现、核心自动验证通过的 V0.1 可试用版本**，尚不能称为原基线第 35 节全部人工验收完成。

## 最后人工验收步骤

1. 启动发布程序，将光标放到目标应用的空白测试文档或输入框，按住 Ctrl+Alt+Space 口述。
2. 候选出现前及候选出现后未确认时，目标中都不应有文本。
3. 修改候选，确认后逐字核对输出；取消另一条候选，确认目标无变化。
4. 分别在记事本、Chrome/Edge、VS Code、Word 测试；如 Unicode 按键不兼容，设置为 clipboard 后重试新的候选。
5. 修改 user/custom.lua，下一次识别验证生效；制造语法错误验证保留旧版本。
6. 将树据分析纠正为数据分析，点击记住，下一次验证自动纠正。
7. 在另一台 Windows 机器解压发布包启动，并执行首次模型下载流程。

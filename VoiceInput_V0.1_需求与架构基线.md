# VoiceInput V0.1 需求与架构基线

> 历史基线（示例已通用化）。当前版本的录音交互和可选直接上屏以 `docs/V0.2_SCOPE.md` 为准。

> **状态：冻结基线 / 可直接交给新的 Work 执行**
>
> 本文档用于指导一个**未参与前序讨论的新 Work**，从零开始、按阶段完成 Windows 平台 `VoiceInput V0.1`。
>
> **不得在 V0.1 阶段自行扩展范围。**
> 如实现过程中发现技术障碍，应优先采用本文定义的降级方案，而不是引入新的大型依赖或改变产品形态。

---

# 0. 项目目标

开发一个 Windows 本地语音输入工具：

- 与 Rime / 小狼毫 / 雾凇拼音**并行共存**，不修改 Rime 内核；
- 用户按下全局快捷键开始录音，松开后结束录音；
- 本地使用 **SenseVoiceSmall** 进行语音识别；
- 识别结果经过 YAML 词典、Python 内置规则和 Lua Filter 处理；
- 弹出一个“语音候选 / 处理面板”；
- 用户可直接编辑最终候选文本；
- **只有用户明确点击“确认”后，文字才写入当前光标位置；**
- 用户可一键将本次纠错学习为长期规则；
- 模型不预打包，**第一次使用时检测模型是否存在，不存在则通过引导界面下载；**
- 全流程默认离线，除首次模型下载外，不依赖云端服务。

V0.1 的核心定位不是“语音识别 Demo”，而是：

> **一个采用 Rime 式可扩展架构、具备候选确认与纠错学习能力的 Windows 本地语音输入引擎。**

---

# 1. V0.1 冻结范围

## 1.1 必须实现

V0.1 必须包含以下能力：

1. Windows 全局快捷键；
2. 按住说话、松开结束；
3. 麦克风录音；
4. Silero VAD；
5. SenseVoiceSmall 本地离线识别；
6. 首次使用模型下载引导；
7. 原始识别结果保存；
8. YAML 配置系统；
9. 科研/项目术语词典；
10. 用户纠错词典；
11. 中文数字规范化；
12. 科研常见单位规范化；
13. 化学式/专业缩写规范化；
14. SenseVoice 原生标点基础上的轻量标点修整；
15. Lua Filter；
16. Lua 热重载；
17. YAML 热重载；
18. 普通 / 科研 / 原文三个 Profile；
19. “语音候选 / 处理面板”；
20. 显示原始识别、最终候选及处理轨迹；
21. 候选文本可编辑；
22. **点击确认后才上屏**；
23. “仅本次”纠错；
24. “记住”纠错；
25. 用户确认后写入 `user.yaml`；
26. SendInput 输出；
27. Clipboard Paste 兼容回退；
28. 最近识别历史；
29. 系统托盘；
30. 基础设置界面；
31. 错误日志；
32. 基础单元测试和最小集成测试。

---

## 1.2 明确不做

V0.1 不实现：

- Windows TSF / 真正 IME；
- 修改 Rime / librime；
- 语音控制 Windows；
- 语音命令系统；
- 实时逐字上屏；
- ASR 候选 N-best；
- 自动读取 Word / VS Code / 浏览器当前段落；
- 自动监视用户在外部软件中的后续修改；
- 自动从外部编辑行为学习；
- Rime userdb / LevelDB 实时同步；
- 云端 LLM 强制后处理；
- 模型训练 / 微调；
- 多说话人识别；
- 多设备同步；
- 云端账号体系。

---

# 2. 最核心交互原则

## 2.1 禁止自动上屏

V0.1 的默认流程必须是：

```text
按住快捷键
    ↓
开始录音
    ↓
松开快捷键
    ↓
结束录音
    ↓
SenseVoice 识别
    ↓
文本 Pipeline 处理
    ↓
显示候选面板
    ↓
用户查看 / 编辑
    ↓
点击【确认】
    ↓
写入当前光标
```

**任何情况下不得在用户未点击“确认”时自动写入目标程序。**

---

## 2.2 候选面板是正式产品功能，不是调试工具

候选面板至少显示：

```text
┌────────────────────────────────────────┐
│ VoiceInput · 科研                      │
├────────────────────────────────────────┤
│ 最终候选                               │
│ ┌────────────────────────────────────┐ │
│ │ N₂流量为100 Nm³/h，温度为500 ℃。  │ │
│ └────────────────────────────────────┘ │
│                                        │
│ 原始识别                               │
│ 氮气流量一百标方每小时温度五百度       │
│                                        │
│ [查看处理]  [学习纠错]                 │
│                                        │
│ [取消]                    [确认并上屏] │
└────────────────────────────────────────┘
```

要求：

- “最终候选”区域可编辑；
- “原始识别”默认只读；
- “查看处理”展开 Pipeline Trace；
- “学习纠错”进入反馈界面；
- “确认并上屏”是唯一 Commit 入口；
- Esc = 取消；
- Ctrl+Enter 可作为“确认并上屏”的快捷键；
- 关闭窗口 = 取消，不得上屏。

---

# 3. 技术栈

V0.1 使用：

| 模块 | 技术 |
|---|---|
| 主语言 | Python 3.12+ |
| UI | PySide6 |
| ASR Runtime | sherpa-onnx |
| ASR Model | SenseVoiceSmall INT8 ONNX |
| VAD | Silero VAD |
| 音频采集 | sounddevice（优先） |
| YAML | PyYAML 或 ruamel.yaml |
| Lua Runtime | Lupa |
| Windows API | pywin32 + ctypes |
| 全局快捷键 | Win32 RegisterHotKey 或稳定的 keyboard hook |
| 当前前台应用 | Win32 GetForegroundWindow / GetWindowThreadProcessId |
| 文本输出 | SendInput |
| 输出回退 | Clipboard + Ctrl+V |
| 打包 | PyInstaller（目录模式优先） |
| 测试 | pytest |

---

# 4. 总体架构

```text
                       ┌─────────────────────┐
                       │   System Tray / UI  │
                       └─────────┬───────────┘
                                 │
                           Global Hotkey
                                 │
                                 ▼
                       ┌─────────────────────┐
                       │   Audio Controller  │
                       │  microphone + VAD   │
                       └─────────┬───────────┘
                                 │ AudioBuffer
                                 ▼
                       ┌─────────────────────┐
                       │     AsrProvider     │
                       │ SenseVoiceProvider  │
                       └─────────┬───────────┘
                                 │ AsrResult
                                 ▼
          ┌──────────────────────────────────────────┐
          │              VoiceInput Engine           │
          │                                          │
          │ Processor → Translator → Filter Pipeline │
          │                ↓                         │
          │            TraceCollector                │
          └────────────────┬─────────────────────────┘
                           │ TextContext
                           ▼
                   ┌─────────────────────┐
                   │ Candidate Panel     │
                   │ edit / trace / learn│
                   └─────────┬───────────┘
                             │ User Confirm
                             ▼
                   ┌─────────────────────┐
                   │    TextOutput       │
                   │ SendInput/Clipboard │
                   └─────────────────────┘

                        ┌─────────────────┐
                        │ FeedbackEngine  │
                        │ user.yaml       │
                        └─────────────────┘
```

---

# 5. 项目目录

建议固定：

```text
VoiceInput/
├── src/
│   └── voiceinput/
│       ├── app/
│       │   ├── main.py
│       │   ├── lifecycle.py
│       │   └── tray.py
│       │
│       ├── audio/
│       │   ├── source.py
│       │   ├── microphone.py
│       │   ├── vad.py
│       │   └── recorder.py
│       │
│       ├── asr/
│       │   ├── base.py
│       │   ├── models.py
│       │   ├── sensevoice.py
│       │   └── model_manager.py
│       │
│       ├── engine/
│       │   ├── context.py
│       │   ├── pipeline.py
│       │   ├── trace.py
│       │   │
│       │   ├── processors/
│       │   │   └── profile_processor.py
│       │   │
│       │   ├── translators/
│       │   │   ├── correction_dictionary.py
│       │   │   └── terminology_dictionary.py
│       │   │
│       │   └── filters/
│       │       ├── number_normalizer.py
│       │       ├── unit_normalizer.py
│       │       ├── chemistry_normalizer.py
│       │       ├── punctuation_filter.py
│       │       ├── lua_filter.py
│       │       └── final_cleanup.py
│       │
│       ├── lua/
│       │   ├── runtime.py
│       │   ├── sandbox.py
│       │   └── watcher.py
│       │
│       ├── feedback/
│       │   ├── engine.py
│       │   ├── diff.py
│       │   └── learner.py
│       │
│       ├── output/
│       │   ├── base.py
│       │   ├── sendinput.py
│       │   └── clipboard.py
│       │
│       ├── context/
│       │   └── foreground_app.py
│       │
│       ├── config/
│       │   ├── loader.py
│       │   ├── merger.py
│       │   └── watcher.py
│       │
│       ├── ui/
│       │   ├── candidate_window.py
│       │   ├── trace_window.py
│       │   ├── correction_dialog.py
│       │   ├── settings_window.py
│       │   ├── model_download_dialog.py
│       │   └── history_window.py
│       │
│       ├── history/
│       │   ├── repository.py
│       │   └── models.py
│       │
│       └── common/
│           ├── events.py
│           ├── logging.py
│           └── paths.py
│
├── config/
│   ├── default.yaml
│   ├── profiles.yaml
│   └── user.custom.yaml
│
├── dictionaries/
│   ├── science.yaml
│   ├── chemistry.yaml
│   ├── units.yaml
│   └── user.yaml
│
├── lua/
│   ├── builtin/
│   │   ├── science_format.lua
│   │   └── punctuation.lua
│   └── user/
│       └── custom.lua
│
├── models/
│   └── .gitkeep
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
│
├── scripts/
│   ├── dev.ps1
│   └── package.ps1
│
├── pyproject.toml
├── README.md
└── CHANGELOG.md
```

---

# 6. 核心数据模型

## 6.1 AsrResult

ASR 层不得直接返回裸字符串。

```python
@dataclass
class AsrResult:
    text: str
    language: str | None = None
    duration_ms: int | None = None
    confidence: float | None = None
    segments: list = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
```

V0.1 中允许：

- `confidence=None`
- `segments=[]`

必须保留字段，为未来扩展留接口。

---

## 6.2 TextContext

整个文本 Pipeline 使用一个统一上下文对象：

```python
@dataclass
class TextContext:
    raw_text: str
    text: str

    profile: str
    app_name: str | None

    language: str | None

    trace: list
    metadata: dict

    user_edited_text: str | None = None
```

要求：

- `raw_text` 永远不可被覆盖；
- `text` 是当前处理结果；
- 每个 Processor / Translator / Filter 只修改 `text` 或添加 metadata；
- 每一步都必须向 trace 记录变化。

---

# 7. Rime 式 Engine 设计

借鉴 Rime 的思想，但不使用 librime。

Pipeline：

```text
AsrResult
    ↓
TextContext
    ↓
Processors
    ↓
Translators
    ↓
Filters
    ↓
Candidate Panel
    ↓
User Confirm
    ↓
Commit
```

---

## 7.1 Processor

职责：

- 选择 Profile；
- 加载当前应用信息；
- 设置 Pipeline 环境；
- 不直接做大量文本替换。

V0.1：

```text
profile_processor
```

---

## 7.2 Translator

职责：

- 静态术语映射；
- 用户纠错词典；
- 科研词典；
- 项目词典。

V0.1：

```text
correction_dictionary
terminology_dictionary
```

---

## 7.3 Filter

V0.1 顺序：

```yaml
engine:
  processors:
    - profile_processor

  translators:
    - correction_dictionary
    - terminology_dictionary

  filters:
    - number_normalizer
    - unit_normalizer
    - chemistry_normalizer
    - lua:builtin/science_format
    - punctuation_filter
    - lua:builtin/punctuation
    - lua:user/custom
    - final_cleanup
```

Filter 顺序可由 YAML 配置。

---

# 8. Trace：处理链可视化

每一步处理都必须留下结构化记录。

建议：

```python
@dataclass
class TraceEvent:
    stage: str
    component: str
    before: str
    after: str
    rule_id: str | None = None
    source: str | None = None
    details: dict = field(default_factory=dict)
```

例如：

```text
Stage: translator
Component: terminology_dictionary
Before: 氮气流量一百标方每小时
After: N₂流量一百标方每小时
Rule: nitrogen
Source: dictionaries/science.yaml
```

UI 中“查看处理”按顺序展示。

---

# 9. YAML 配置设计

## 9.1 default.yaml

示例：

```yaml
app:
  language: zh-CN

hotkey:
  push_to_talk: "Ctrl+Alt+Space"

audio:
  sample_rate: 16000
  channels: 1

asr:
  provider: sensevoice
  model: sensevoice-small-int8

output:
  primary: sendinput
  fallback: clipboard

candidate:
  require_confirmation: true
  confirm_shortcut: "Ctrl+Enter"

profile:
  default: normal

lua:
  enabled: true
  hot_reload: true

config:
  hot_reload: true
```

---

## 9.2 user.custom.yaml

用户覆盖配置，程序升级不得覆盖。

优先级：

```text
default.yaml
    ↓
profiles.yaml
    ↓
user.custom.yaml
```

用户文件优先级最高。

---

# 10. Profile

V0.1 提供：

```text
normal
science
raw
```

## 10.1 normal

- 基础纠错；
- 数字适度规范化；
- 轻量标点；
- 不主动将常见中文术语替换成化学式。

## 10.2 science

- 启用科研词典；
- 启用化学式规范化；
- 启用单位规范化；
- 启用科研格式 Lua。

## 10.3 raw

- 尽量保留 SenseVoice 原始结果；
- 仅做必要空白清理；
- 用户纠错词典可配置是否仍生效；
- 不做强规则格式化。

Profile 不得在 Python 中写死成 enum。

允许 YAML 中扩展：

```yaml
profiles:
  science:
    dictionaries:
      - science
      - chemistry
      - units
```

---

# 11. 科研词典

建议格式：

```yaml
terms:
  - id: nitrogen
    spoken:
      - 氮气
      - N二
      - N 2
    output: "N₂"
    profiles:
      - science

  - id: carbon_dioxide
    spoken:
      - 二氧化碳
      - C O二
      - CO二
    output: "CO₂"
    profiles:
      - science

  - id: usb_c
    spoken:
      - USBC
      - USB C
      - USB接口
    output: "USB-C"
    profiles:
      - science
```

---

# 12. 用户纠错词典

`dictionaries/user.yaml`：

```yaml
corrections:
  - id: corr_000001
    from: "树据分析"
    to: "数据分析"
    profiles:
      - science
    created_at: "2026-09-27T23:00:00+08:00"
```

要求：

- 写入前备份旧文件；
- 写入必须原子化；
- YAML 损坏时不得覆盖；
- 新规则立即热加载。

---

# 13. 数字规范化

V0.1 只实现高价值、低歧义场景。

必须支持：

```text
一百 → 100
十二点五 → 12.5
百分之十二点五 → 12.5%
四百五十到五百 → 450～500
```

但不得无条件把所有中文数字转为阿拉伯数字。

应优先在以下上下文触发：

- 百分比；
- 范围；
- 温度；
- 流量；
- 时间；
- 浓度；
- 密度；
- 明确单位前的数字。

---

# 14. 单位规范化

至少支持：

```text
摄氏度            → ℃
毫升每分钟        → mL/min
标准立方米每小时  → Nm³/h
标方每小时        → Nm³/h
克每立方厘米      → g/cm³
兆焦每平方米      → MJ/m²
分钟              → min（科研 Profile）
```

注意：

- 单位前数字与单位之间统一一个半角空格；
- 范围格式优先 `450～500 ℃`；
- 不得生成 `450 ℃～500 ℃`，除非配置另有指定。

---

# 15. 化学式规范化

V0.1 通过词典优先，不实现复杂化学解析器。

例如：

```text
氮气       → N₂
氢气       → H₂
氧气       → O₂
二氧化碳   → CO₂
二氧化碳   → CO₂
水分子 → H₂O
```

必须允许 Profile 控制。

---

# 16. 标点策略

SenseVoice 本身输出标点，因此 V0.1 不引入额外大型标点模型。

只做轻量修整：

- 连续重复标点；
- 中英文标点混用；
- 句末缺失；
- 数字和单位之间空格；
- 科研表达中的逗号/句号微调；
- Lua 可追加用户规则。

不得大量重写原句语义。

---

# 17. Lua 设计

Lua 是 V0.1 正式能力，不得后移。

使用 Lupa。

---

## 17.1 Lua API

统一入口：

```lua
function filter(ctx)
    return ctx
end
```

`ctx` 至少提供：

```text
ctx.text
ctx.raw_text
ctx.profile
ctx.app_name
ctx.language
ctx.metadata
```

Lua 可以：

- 读取这些字段；
- 修改 `ctx.text`；
- 向 trace 添加说明；
- 读取只读配置。

Lua 默认不得：

- 执行系统命令；
- 启动 EXE；
- 删除文件；
- 修改注册表；
- 联网；
- 调用 PowerShell。

---

## 17.2 Lua Trace

Lua 修改文本后必须记录：

```text
component: lua:user/custom
before: ...
after: ...
```

---

## 17.3 Lua 热重载

要求：

- 监听 `lua/` 目录；
- 保存后下一次识别即生效；
- Lua 语法错误不得导致主程序崩溃；
- 错误时继续使用上一次有效版本；
- 在 UI / 日志显示脚本错误。

---

# 18. 模型管理与首次下载

## 18.1 原则

安装包不强制携带 SenseVoiceSmall 模型。

第一次真正开始使用语音输入时：

```text
检测 models/sensevoice/
       ↓
不存在
       ↓
弹出模型下载引导
```

---

## 18.2 下载引导界面

至少显示：

```text
SenseVoiceSmall 本地语音模型尚未安装

模型：SenseVoiceSmall INT8
用途：本地离线语音识别
下载后：可离线使用
存储位置：<path>

[开始下载] [取消]
```

如可获得，应显示：

- 模型大小；
- 来源；
- License；
- 下载进度；
- 已下载字节；
- 错误信息。

---

## 18.3 ModelManager

抽象：

```python
class ModelManager:
    def is_installed(self, model_id) -> bool: ...
    def verify(self, model_id) -> bool: ...
    def download(self, model_id, progress_cb) -> None: ...
    def get_model_path(self, model_id) -> Path: ...
```

模型信息通过 Manifest 管理，不散落在代码中。

例如：

```yaml
models:
  sensevoice-small-int8:
    provider: sherpa_onnx
    path: models/sensevoice-small-int8
    source: official
```

实际 URL 在实现阶段从 sherpa-onnx / 官方模型源核验，不得使用未经验证的第三方下载链接。

---

## 18.4 下载失败

必须允许：

- 重试；
- 取消；
- 下次继续；
- 手动指定已有模型目录。

下载失败不得影响打开设置、查看历史等其他功能。

---

# 19. FeedbackEngine：一键学习

用户在候选框编辑：

```text
树据分析在500 ℃测试。
```

改成：

```text
数据分析在500 ℃测试。
```

点击：

```text
学习纠错
```

V0.1 使用简单、安全的学习策略。

---

## 19.1 V0.1 学习策略

优先识别短替换：

```text
树据分析 → 数据分析
```

显示确认：

```text
发现可能的长期纠错：

树据分析
→
数据分析

[仅本次] [记住]
```

点击“记住”后写入 `user.yaml`。

---

## 19.2 不允许

V0.1 不得：

- 自动猜测大量复杂规则；
- 未经确认直接学习；
- 将整段长文本直接做成 A→B 长句规则；
- 自动监听外部编辑软件；
- 自动训练 ASR。

---

# 20. Rime / 雾凇拼音兼容策略

V0.1 不与 librime 集成。

仅在文档中提供手动导入指南。

---

## 20.1 推荐共享对象

优先共享：

```text
custom_phrase.txt
```

不共享 Rime userdb。

---

## 20.2 手动导入指导

README 中应说明：

1. 找到 Rime / 小狼毫用户目录；
2. 找到 `custom_phrase.txt`；
3. 该文件通常为 Tab 分隔；
4. 第一列为词语；
5. 将需要的个人术语复制到 VoiceInput 的 `user.yaml` 或独立术语文件；
6. VoiceInput 不需要拼音编码和权重。

未来可实现一键导入，但 V0.1 非必须。

---

# 21. 输出模块

统一接口：

```python
class TextOutput:
    def commit(self, text: str) -> OutputResult:
        ...
```

V0.1：

```text
SendInputOutput
ClipboardOutput
```

---

## 21.1 Commit 时机

只有发生：

```text
CandidateWindow.confirm()
```

才允许调用：

```text
TextOutput.commit()
```

其他所有路径均不得 Commit。

---

## 21.2 输出回退

优先：

```text
SendInput
```

失败时：

```text
Clipboard
→ Ctrl+V
→ 恢复原剪贴板
```

如无法恢复，必须明确提示。

---

# 22. History

保存最近识别历史。

建议字段：

```text
timestamp
profile
app_name
raw_text
processed_text
confirmed_text
committed
trace
```

V0.1 可使用：

- JSONL；
- SQLite。

推荐 SQLite，便于后续查询。

不得保存原始音频，除非未来用户主动开启；V0.1 默认不保存语音。

---

# 23. 状态机

必须明确实现状态，避免重复录音或重复提交。

```text
IDLE
 ↓ HotkeyDown
RECORDING
 ↓ HotkeyUp
PROCESSING
 ↓ ASR done
REVIEWING
 ├─ Cancel → IDLE
 └─ Confirm
      ↓
COMMITTING
      ↓
IDLE
```

模型未安装：

```text
IDLE
 ↓ HotkeyDown
MODEL_REQUIRED
 ↓ Download
MODEL_DOWNLOADING
 ↓ Success
IDLE
```

不得允许：

- PROCESSING 时再次录音；
- REVIEWING 时重复弹多个候选窗；
- COMMITTING 时重复 Commit。

---

# 24. UI

## 24.1 系统托盘

菜单至少：

```text
开始语音输入
当前 Profile
  ├─ 普通
  ├─ 科研
  └─ 原文

最近识别
设置
模型
退出
```

---

## 24.2 候选窗

核心产品 UI。

必须：

- 置顶但不永久抢焦点；
- 支持文本编辑；
- 显示原始识别；
- 显示当前 Profile；
- “查看处理”；
- “学习纠错”；
- “取消”；
- “确认并上屏”。

---

## 24.3 Trace 窗口

按顺序展示：

```text
ASR
↓
correction_dictionary
↓
science_dictionary
↓
number_normalizer
↓
unit_normalizer
↓
Lua
↓
punctuation
↓
final_cleanup
```

每一步只在实际发生变化时高亮。

---

# 25. 配置与脚本热重载

必须监视：

```text
config/*.yaml
dictionaries/*.yaml
lua/**/*.lua
```

要求：

- 修改保存后无需重启；
- 新配置验证成功才替换旧配置；
- 配置语法错误时保留上一版本；
- UI 提示错误位置；
- 日志记录。

---

# 26. 错误处理

必须覆盖：

- 无麦克风；
- 麦克风被占用；
- 录音失败；
- 无语音；
- ASR 模型缺失；
- 模型下载失败；
- 模型损坏；
- ASR 初始化失败；
- Lua 语法错误；
- YAML 语法错误；
- SendInput 失败；
- Clipboard 失败；
- 前台窗口不存在。

任何一个异常均不得导致整个托盘程序直接退出。

---

# 27. 隐私原则

V0.1 默认：

- 本地录音；
- 本地 ASR；
- 本地 YAML；
- 本地 Lua；
- 本地历史；
- 不上传语音；
- 不上传文本；
- 不保存原始录音。

首次下载模型是唯一默认联网行为。

---

# 28. 开发阶段与执行顺序

新的 Work 必须严格按照以下阶段完成。

不得直接跳到后面的 GUI 美化。

---

# M0：工程骨架

目标：

- 创建项目；
- pyproject；
- PySide6 托盘；
- 日志；
- 配置加载；
- 基础目录。

验收：

```text
python -m voiceinput
```

可启动托盘，正常退出，无异常。

产物：

```text
M0_CHECKPOINT.md
```

---

# M1：最小录音 + ASR 闭环

实现：

```text
Hotkey
→ Microphone
→ AudioBuffer
→ SenseVoice
→ raw_text
```

此阶段可以暂时把结果显示在简单窗口，不做上屏。

同时实现模型首次下载引导。

验收：

- 首次使用提示下载；
- 下载成功后可离线识别；
- 第二次启动不重复下载；
- 普通中文句子可得到识别文本。

产物：

```text
M1_CHECKPOINT.md
```

---

# M2：Engine + YAML + Lua

实现：

```text
AsrResult
→ TextContext
→ Processor
→ Translator
→ Filter
→ Lua
→ Trace
```

至少实现：

- science.yaml；
- user.yaml；
- number_normalizer；
- unit_normalizer；
- chemistry_normalizer；
- punctuation_filter；
- builtin Lua；
- user Lua；
- Lua/YAML 热重载。

验收测试：

输入模拟：

```text
氮气流量一百标方每小时温度五百度
```

期望得到类似：

```text
N₂流量为100 Nm³/h，温度为500 ℃。
```

并有完整 Trace。

产物：

```text
M2_CHECKPOINT.md
```

---

# M3：正式候选面板

实现：

```text
ASR
→ Pipeline
→ Candidate Window
```

必须：

- 原始识别；
- 最终候选；
- 候选可编辑；
- Trace；
- Cancel；
- Confirm。

此阶段仍可只把 Confirm 结果打印到日志。

验收：

- 不点击确认绝不 Commit；
- 编辑后的候选文本被正确保存；
- Cancel 不产生输出。

产物：

```text
M3_CHECKPOINT.md
```

---

# M4：Windows 上屏

实现：

```text
Confirm
→ SendInput
→ 当前光标
```

以及 Clipboard 回退。

必须测试：

- Windows 记事本；
- Chrome / Edge 普通网页输入框；
- VS Code；
- Word（如测试环境有 Word）。

验收：

- 只有点击确认后上屏；
- 上屏文字与候选窗最终编辑内容完全一致；
- Cancel 不上屏。

产物：

```text
M4_CHECKPOINT.md
```

---

# M5：FeedbackEngine

实现：

```text
候选修改
→ Diff
→ 学习纠错
→ [仅本次] / [记住]
→ user.yaml
→ 热重载
```

验收：

第一次：

```text
树据分析
```

人工修改：

```text
数据分析
```

点击“记住”。

第二次模拟同样错误：

```text
树据分析
```

Pipeline 自动输出：

```text
数据分析
```

产物：

```text
M5_CHECKPOINT.md
```

---

# M6：历史、设置、Profile、收尾

实现：

- History；
- 设置页；
- Profile 切换；
- 模型管理页；
- 最近识别；
- 错误提示；
- README；
- 打包脚本；
- PyInstaller 目录发布。

验收：

- 安装/解压后可运行；
- 无 Python 环境的测试机可运行；
- 用户配置升级不被覆盖；
- 首次模型引导正常；
- 配置/Lua 修改后热重载。

产物：

```text
M6_CHECKPOINT.md
```

---

# 29. V0.1 最终验收用例

至少完成以下人工验收。

## 用例 A：普通中文

说：

```text
今天下午去实验室看看数据
```

候选面板出现。

用户确认后：

```text
今天下午去实验室看看数据。
```

写入当前程序。

---

## 用例 B：科研输入

Profile：

```text
science
```

说：

```text
氮气流量一百标准立方米每小时温度五百度
```

候选建议：

```text
N₂流量为100 Nm³/h，温度为500 ℃。
```

用户确认后上屏。

---

## 用例 C：用户编辑后上屏

候选：

```text
树据分析在500 ℃测试。
```

用户编辑：

```text
数据分析在500 ℃测试。
```

只有编辑后的版本上屏。

---

## 用例 D：学习纠错

同上，用户点击“记住”。

再次识别：

```text
树据分析
```

自动处理：

```text
数据分析
```

---

## 用例 E：Lua

修改：

```text
lua/user/custom.lua
```

保存。

无需重启。

下一次识别立即执行新规则。

---

## 用例 F：模型未安装

删除或移动模型。

开始录音时：

```text
弹出模型下载引导
```

不得崩溃，不得静默失败。

---

## 用例 G：取消

任何候选内容出现后点击取消。

结果：

```text
外部程序没有任何文字被写入。
```

---

# 30. 测试策略

必须至少提供以下 pytest：

```text
test_config_loader.py
test_user_dictionary.py
test_number_normalizer.py
test_unit_normalizer.py
test_chemistry_normalizer.py
test_pipeline_order.py
test_trace.py
test_lua_filter.py
test_feedback_diff.py
test_feedback_write.py
test_model_manager.py
```

UI 和真实 SendInput 可采用最小人工验收，不要求 V0.1 做完整自动 UI 测试。

---

# 31. 日志

日志不得包含原始音频。

建议：

```text
logs/app.log
```

包括：

- 启动；
- 模型状态；
- ASR 错误；
- Pipeline 错误；
- YAML 错误；
- Lua 错误；
- Output 错误；
- Feedback 写入错误。

默认不记录完整语音文本到日志。

History 与日志分离。

---

# 32. 发布结构

PyInstaller 优先使用目录模式：

```text
VoiceInput/
├── VoiceInput.exe
├── runtime/
├── config/
├── dictionaries/
├── lua/
├── models/
└── logs/
```

升级程序时不得覆盖：

```text
config/user.custom.yaml
dictionaries/user.yaml
lua/user/
```

---

# 33. 未来接口：只预留，不实现

V0.1 架构必须允许未来加入，但不得实现：

```text
AsrProvider
├── SenseVoiceProvider
├── WhisperProvider
└── OtherProvider

TextOutput
├── SendInputOutput
└── ClipboardOutput

DictionaryProvider
├── NativeYamlDictionary
└── FutureRimeImporter

PunctuationProvider
├── RuleBased
└── FutureModelBased

ContextProvider
└── FutureForegroundTextProvider

PostProcessor
└── FutureLLMProvider
```

此外可在事件系统预留：

```text
partial_result
final_result
```

V0.1 只使用 `final_result`。

---

# 34. 新 Work 的执行规则

新 Work 必须遵守：

1. 本文档是当前唯一有效产品与架构基线；
2. 不自行增加 TSF、IME、LLM、语音命令等功能；
3. 每完成一个 Milestone 必须：
   - 运行测试；
   - 做最小人工验收；
   - 写 `Mx_CHECKPOINT.md`；
4. 若某一步出现阻塞：
   - 优先采用本文定义的回退方案；
   - 不随意替换技术栈；
5. 模型下载地址必须在实现时核验官方来源；
6. 不允许为了“先跑通”而绕过候选确认直接自动上屏；
7. `raw_text` 永远保留；
8. 用户确认后的 `confirmed_text` 才允许 Commit；
9. 用户配置和用户 Lua 不得被升级覆盖；
10. Lua / YAML 错误不得让主程序崩溃；
11. 每个阶段都要保留可以继续工作的代码状态；
12. 代码应能被后续 Work 在没有旧对话上下文的情况下继续维护。

---

# 35. V0.1 完成定义（Definition of Done）

只有同时满足以下条件，才算 V0.1 完成：

- Windows 可启动；
- 托盘正常；
- 全局按键正常；
- 麦克风正常；
- 首次模型下载正常；
- SenseVoiceSmall 本地识别正常；
- YAML 正常；
- Lua 正常；
- Lua/YAML 热重载正常；
- 科研词典正常；
- 数字/单位/化学式规范化正常；
- 原始识别可查看；
- 处理轨迹可查看；
- 最终候选可编辑；
- 未确认绝不上屏；
- 点击确认后上屏；
- SendInput 失败有 Clipboard 回退；
- 一键纠错可写入 user.yaml；
- 学习规则下一次立即生效；
- 普通 / 科研 / 原文 Profile 正常；
- 历史可查看；
- 无 Python 环境机器可运行打包版；
- 用户文件升级不被覆盖；
- README 包含安装、模型下载、使用、纠错、Lua、自定义词典说明；
- 所有核心 pytest 通过；
- 完成最终人工验收。

---

# 36. 产品原则

开发过程中始终遵守：

> **语音输入不是“识别完就自动打字”，而是“识别 → 处理 → 用户确认 → Commit”。**

> **候选面板 + 处理前后查看 + 一键学习，是产品核心，不得降级为调试功能。**

> **SenseVoice 是可替换的 ASR Provider；VoiceInput Engine 才是长期核心。**

> **静态配置放 YAML，动态可扩展逻辑放 Lua，稳定核心逻辑放 Python。**

> **优先做可靠、透明、可纠错的语音输入，而不是追求自动化程度。**

# USDX Coach：练习 / 游玩

## 中文界面

- 全新配置默认使用**简体中文 + Studio 全浅色界面 + 列表曲库**，练习和游玩均为浅色。首页直接显示双模式、音乐库、统计、编辑器与设置。
- 已有配置保持原来的语言和主题。可在“设置 → 游戏 → 语言”选择“简体中文”，在“设置 → 主题”中选择 Studio 主题与 Studio 皮肤；Deluxe / Modern 仍可切换。也可以从 `game` 目录运行 `ultrastardx.exe -language Chinese`。
- 列表曲库单击选曲，双击或 Enter 开始；空白点击、按住拖出不启动歌曲。J 搜索，M 打开歌曲菜单。
- 悬停约 160ms、按压约 90ms、页面过渡约 180ms；“设置 → 高级 → 屏幕淡入淡出”关闭时，新动画也立即关闭。
- 练习面板分为句数、音高状态、音分 / 频率、参考与延迟状态、操作区。中文字体沿用随游戏提供的 Noto 字体，不依赖系统安装字体。
- 上一句、下一句、重唱、循环、暂停、延迟确认均支持鼠标点击，F1 / F2 / F3 / F4 / P / F8 快捷键保留；左右键选择操作，Enter 执行，Ctrl+方向键仍为原来的播放定位。
- “确认延迟”只确认本次会话中**已经实测并填写**的麦克风延迟，不会自动测量。参考未确认或延迟待确认时，不显示偏高 / 偏低结论。
- 暂停练习时操作区保持可用，游玩暂停提示也改为可翻译文字，不再使用英文 Pause 图片。

界面规范与回归项见 [coach-ui.md](coach-ui.md)。

## 组成

- 本 fork 固定从 USDX v2026.10.0 开始。游玩复用原有曲库、采集、显示、游戏评分和结算。
- 练习使用单人、按 TXT 句界循环、连续 YIN 音高和有符号音分提示；绝对八度比较，不写游玩高分、不自动上传成绩。
- Python 桥接直接调用已有工程的 `SongStore` / `ReferenceService`，沿用其 MDX 分离、pYIN、缓存校验、独立模型解释器。没有复制一套模型实现。

## 1. 在程序里导入音乐（推荐）

1. 启动 `game/ultrastardx.exe`，在 Studio 首页点击 **导入音乐**，或按 **F7**。
2. 点击文件框选择本地音频；也可将文件拖入首页/导入页，或在未编辑文字时按
   **Ctrl+V** 粘贴文件完整路径。支持 WAV、MP3、M4A、FLAC、OGG、AAC，
   单文件最多 500 MB，音频最长 10 分钟。
3. 填写歌曲名称和歌手。文字框支持中文输入、粘贴、退格；Ctrl+A 清空当前框。
4. 点击 **开始处理**。后台复用已有 Python 程序提取人声、伴奏并识别参考音高；
   页面显示实际阶段，处理期间可点 **取消处理**。重复导入相同文件会校验并复用
   已完成的有效参考，不重复建立相同源文件。
5. 查看参考音高概览和时长/候选音符统计，点击 **试听人声**。确认提取的声音和
   参考符合预期后，点击 **确认参考并入库**；试听前确认按钮保持禁用。
6. 成功后点 **进入曲库**，完成玩家设置即可看到新歌，无需重启。回到首页可从
   **练习模式**或**游玩模式**使用同一曲库。

生成的歌包包含原音频、人声、伴奏、参考音高和 UltraStar 曲谱。
TXT 歌词目前使用 **`la` 占位**，不是歌词识别结果；可在原编辑器校对歌词、
旋律和句界。自动参考需要试听检查，点击入库表示你确认本次参考，
不代表程序自动证明旋律完全准确。

### Python 引擎位置

先按现有 Python 教唱工程的 README 安装好模型环境。保持便携包的 `game` 与
`tools` 两个目录相邻；将整个便携包放在现有教唱项目旁边，程序会在两级父目录
的相邻项目中查找 `src/singing_coach/reference.py`，默认使用该项目的 `.venv`。
本机新便携包已经与现有 `音频教唱程序` 并列放置。

移动到其他位置时，可在启动前设置：

```powershell
$env:USDX_COACH_ROOT = 'D:\Apps\SingingCoach'
# 使用不同的后端解释器时才设置：
$env:USDX_COACH_PYTHON = 'D:\Apps\SingingCoach\.venv\Scripts\python.exe'
& 'D:\Apps\USDX-Coach\game\ultrastardx.exe'
```

模型子进程仍使用原教唱程序的独立音频环境。模型和依赖沿用已安装版本；
按钮不会重新安装环境。找不到引擎时，页面给出错误并可重新选择后处理。
默认歌包保存在 USDX 用户目录的 `songs` 下，后续启动也会扫描该曲库。
高级路径配置和故障定位见 [coach-import-validation.md](coach-import-validation.md)。

### 脚本方式（保留）

先按现有 Python 工程的 README 安装模型环境。下面的路径请填写本机实际目录。

```powershell
.\tools\prepare-coach-song.ps1 -CoachRoot 'D:\Apps\SingingCoach' `
  -Audio 'D:\Music\song.mp3' -Title '歌曲名' -Artist '歌手'
```

新建的参考默认为自动候选：在 Python 程序中试听主唱、伴奏并确认后，用日志中的歌曲 ID 导出：

```powershell
.\tools\prepare-coach-song.ps1 -CoachRoot 'D:\Apps\SingingCoach' `
  -SongId '歌曲ID' -Title '歌曲名' -Artist '歌手'
```

显式加 `-AllowUnreviewed` 可生成标记 AUTO 的未审核素材，用来检查链路。AUTO 谱不产生精确方向提示和持久高分；试听审核后导出正式包。已有同名目录保留，重新发布请选择新的输出目录或先另存原包。

导出目录内含 `song.txt`、原音频、`vocals.wav`、`instrumental.wav`、原始 `pitch.json` 和 `coach.json`。BPM=1500、GAP=0，每 tick 10ms，音高=MIDI−60。TXT 歌词暂为 `la` 占位，**不是歌词转写结果**；可使用 UltraStar 编辑器校对歌词/句界。完整浮点 F0 和置信度保留在 JSON。

## 2. 两种模式

- 主菜单 **Play mode / 游玩模式**，或 F5：正常选曲、整曲游玩、游戏结算。
- 主菜单 **Practice mode / 练习模式**，或 F6：共享曲库，进入单人逐句练习。原编辑器保留 E 快捷键。
- 练习中 F1 / F2：上一句 / 下一句；F3：重唱当前句；F4：开关循环；空格：暂停；K：切换主音轨 / 提取伴奏；Esc：返回选曲。
- 练习默认使用提取伴奏；可用 K 试听原音轨示范。

## 3. 精确提示

先在 USDX 游戏选项配置当前设备的 **实测 MicDelay**，进入练习后按 F8 确认该数值确实对应当前设备路径。本增量不把默认 140ms 当已测量值，每次进入演唱均需重新确认。未确认时仅显示 Hz。

YIN 使用 4096 样本窗口、最高每 40ms 更新一次；安静、低周期性、削波、采集超过 150ms 无新数据时失效。目标取时间范围内的有效音符，保护首尾各 90ms；用窗口中心补偿和配置延迟匹配目标。音分中心至少稳定 160ms、4 次观察才给方向；±35 cents 为提示参数而非通用及格线。物理麦克风与耳机链路仍需逐设备验收。

## 开发与验证

```text
python -m unittest discover -s test/coach -p 'test_*.py' -v
fpc -Mdelphi -Fusrc/base -FU<test-output> -FE<test-output> test/coach/coach_core_test.pas
```

完整构建沿用 [COMPILING.md](../COMPILING.md)。Windows 构建流水线为 `.github/workflows/coach.yml`，产物名 `USDX-Coach-windows-portable`；完整包要保留 `game` 的 DLL、字体、主题与语言资源，不仅复制 EXE。

本增量不包含变速、移调、训练报表持久化或“结算选句进入练习”；这些是后续切片，不与当前已运行的功能混写。

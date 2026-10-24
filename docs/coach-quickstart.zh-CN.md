# USDX Coach：练习 / 游玩首个增量

## 组成

- 本 fork 固定从 USDX v2026.10.0 开始。游玩复用原有曲库、采集、显示、游戏评分和结算。
- 练习使用单人、按 TXT 句界循环、连续 YIN 音高和有符号音分提示；绝对八度比较，不写游玩高分、不自动上传成绩。
- Python 桥接直接调用已有工程的 `SongStore` / `ReferenceService`，沿用其 MDX 分离、pYIN、缓存校验、独立模型解释器。没有复制一套模型实现。

## 1. 准备歌曲

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

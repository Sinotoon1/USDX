# 音乐导入生成库：实现与验收（2026-10-24）

基线 `2885bbf9a51df12c9e6a6207bbca34755a433f4e`，分支
`feature/practice-play-python`。运行源码
`d6e6629977dc71b999cc97776c3ee1b5c58ade86`；之后的说明与任务记录不改变运行逻辑。
规格见 [SPEC-coach-import.md](../SPEC-coach-import.md)，操作见
[中文快速开始](coach-quickstart.zh-CN.md#1-在程序里导入音乐推荐)。

## 结构与选择

- `UScreenCoachImport`：选择文件、元数据、阶段、候选音符概览、试听、确认。
- `UCoachImport`：进程生命周期、原子状态轮询、独立任务和 Unicode 路径。
- `UCoachImportCore`：格式/试听门控/Windows 参数转义的纯函数与 Pascal 测试。
- `tools/coach_import.py`：只适配已有 Python 工程，复用 MDX/pYIN、缓存与桥接导出。
- `USongs.AddImportedSong`：单文件分析、完整路径去重、增量更新分类与封面。
- `studio-design.json`/生成器：本页几何、文案与主题的唯一来源。

选择本地子进程协议而非新增 HTTP 服务：无需另开常驻服务，不在 UI 线程执行
重模型，保留现有后端环境隔离。POSIX 用官方
[TProcess](https://www.freepascal.org/docs-html/fcl/process/tprocess.html) 参数表。
Windows 使用宽字符进程调用，文件框显式绑定
[GetOpenFileNameW](https://learn.microsoft.com/en-us/windows/win32/api/commdlg/nf-commdlg-getopenfilenamew)
的 `TOpenFilenameW` ABI；FPC 3.2.2 的通用指针别名不能直接代替这个宽字符记录。

### 协议

`prepare --coach-root ROOT --audio FILE --state STATE [--data-root DATA]`
生成 ready；`publish --coach-root ROOT --state STATE --songs-root SONGS
--request REQUEST [--data-root DATA]` 执行显式确认与导出。
界面通过参数数组调用，不经 shell；任意中文/引号元数据经 UTF-8 JSON 请求传递。

状态上限 256 KiB，含 `schema_version=1`、与文件名绑定的 `task_id`、
`status/phase/error_code`。ready 含 `job_id/song_id/vocals_path`、时长、
音符数、覆盖率、最多 512 条 `[start,end,midi]`；published 另含
`output_path/song_file`。preview 仅概览，正式 `pitch.json` 保留完整数据。
请求包含 `schema_version=1/title/artist/confirmation`，confirmation 必须是
当前 job_id。返回码 0=完成，1=失败，2=取消。

取消标记与状态文件同名、扩展名 `.cancel`。prepare 的 worker 终止并等待自己创建
的音频子进程；publish 的原子提交阶段不提供取消。失败不把半成品加入曲库；
发布失败保留 ready 状态，便于重试。同参考、同元数据且全部哈希正确的已完成包
可幂等复用；不同元数据或损坏包保留并报错，不隐式覆盖。

### 路径与操作

| 项 | 默认 / 可选覆盖 |
|---|---|
| 引擎项目 | 相邻两级项目扫描；`USDX_COACH_ROOT` |
| 后端 Python | 引擎 `.venv/Scripts/python.exe`；`USDX_COACH_PYTHON` |
| 引擎数据 | 引擎 `data`；`USDX_COACH_DATA` |
| 模型 | 沿用原引擎规则：数据目录父级 `.models` |
| 新歌包 | USDX 用户目录 `songs`；`USDX_IMPORT_SONGS` |
| 任务记录 | USDX 用户目录 `coach-import/tasks/import-UUID.json` |
| 模型诊断 | 对应原引擎 reference 目录 `worker.log` |

自定义输出目录只在本次会话动态注册；下次启动应将它配置为 USDX song path。
默认 `songs` 已在原有启动扫描路径中。自定义数据目录应同时配套现有模型缓存。
native worker 锁只覆盖本功能，不覆盖独立 Python 网页程序，避免二者同时编辑
同一参考任务。源音频/旧歌包不修改；曲库只在确认发布后变化。

## 已执行验证

- **53 项 Python 测试通过**：原 36 项不回归；新 worker 10 项、原生契约 7 项。
  覆盖格式/错误、取消并回收子进程、审核版本门控、Unicode 引号元数据、校验、
  复用、幂等导出、损坏包、原生路由、IME 完整提交、封面重建游标与事件修饰键。
- **5 个 Pascal 测试通过**：core/window/motion/unicode/import，保留范围、
  溢出和栈检查。Linux 完整程序编译 370377 行，42 warnings / 70 notes。
- **真实 Windows MDX + pYIN** 处理 18 秒音频，得到人声/伴奏、18 个候选音符，
  有声音高覆盖约 33%；显式测试确认后原子导出，中文引号歌名与歌手保持，
  重复导入复用同一个有效 job。该次确认是隔离测试操作，不是旋律准确性评级。
- **真实 Windows 取消**：观察到新模型子进程，写取消标记后父进程退出 2，
  状态 cancelled，子进程已回收，发布歌包数 0。
- **原生 UI**：私有 SDL/Xvfb、隔离 HOME/config/score 与零输入音频。
  已检查 800×600 和 1280×960；F7、后台处理、未试听时禁用确认、试听播放、
  显式确认、无重启加入曲库。最新运行还检查中文/引号粘贴、3 首曲库、新歌练习
  和新歌整曲游玩至结算。
  UI 使用上面真实模型的缓存产物，经原服务再次校验；不是另一次 Linux 模型推理。
- [Windows CI](https://github.com/Sinotoon1/USDX/actions/runs/40086897463)
  的测试与完整 Win64 构建通过。本机新便携包隐藏启动，fresh config 写出
  Studio/Studio/List、Off/1280×960，进入 Main Loop 且持续存活。
- 新程序 `USDX-Coach-windows-import-d6e6629/game/ultrastardx.exe`，SHA256
  `9bcaf10e3669d7708d3492a17271a395027261748ef4436b8df3f28629e9a4bb`。
  整包需保留相邻 tools、DLL、字体、主题、语言。旧 MiHome 便携包未覆盖，
  配置逐字节保持，分数用 SQLite 只读 backup 复制。

### 本轮发现并修复

1. 再次 `GenerateThumbnails` 未重置 ButtonPos，导致入库后封面按钮越界。
   改为专用重建入口，清理旧按钮与交互、重置游标；实际新歌入库绿测通过。
2. Windows FPC 通用 CommDlg 指针声明与 W 记录类型不匹配。
   显式绑定官方宽字符 ABI，Win64 CI 从失败恢复通过。
3. 快速 Ctrl+A/V 的 down/key/up 同帧到达时，全局键盘状态已经释放。
   改用事件自身 modifier，原生中文和带引号标题粘贴及导出绿测通过。

测试夹具曾出现 WSL Python 字节码与 ELF 重定位损坏；前者使用独立 pycache，
后者保留诊断并重新链接后正常启动。没有为夹具故障改动音频算法或交付运行逻辑。
原生视觉/零输入和隐藏启动均不等于物理麦克风、声学准确度或端到端延迟验收。
精确提示仍遵守已有参考审核、实测 MicDelay、置信度与稳定门控。

## 复现与维护

```text
python -m unittest discover -s test/coach -p 'test_*.py' -v
python tools/build_studio_theme.py --check
fpc -Cr -Co -Ct -Fusrc/base -FU<out> -FE<out> test/coach/coach_import_test.pas
```

本机完整证据在工作区父目录 `.codex-artifacts/usdx-import-20261024-01`。
`VERIFY.ps1 BASELINE|MODIFIED|ROLLBACK` 是确定性入口：基线 36 项/1580 原始哈希，
当前 53 项与主题一致，回滚只在另一源码副本恢复基线并保留 user-data 哨兵。
`MODIFIED_FILE.zip` 是完整改后源码包；`DIFF_FILE.patch` 是相对基线的 Git 补丁；
`VERIFICATION.txt` 记录精确命令、输入、输出、返回码；`ROLLBACK.sh` 是可执行入口，
依赖同目录原始 ZIP/哈希/变更清单和验证脚本。脚本先校验后写入，后续编辑不覆盖。

可复用开发提示：

> 继续 USDX 原生音乐导入功能。先读 SPEC-coach-import.md 和本运行手册；
> 复用已有 SongStore/ReferenceService/coach_bridge，不在 UI 线程运行模型。
> 保留 UTF-8 JSON 请求、任务隔离、试听+当前版本确认、原子发布与增量去重。
> 先补失败测试，再改 token/生成器与对应原生控制器，运行 Python/Pascal、
> 真实子进程取消与原生页流，交付全资源便携包及已在另一副本测试的回滚。

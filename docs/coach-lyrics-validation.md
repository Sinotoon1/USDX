# 歌词识别、时间对齐与桌面鼠标（2026-10-24）

本轮基线 `b6862d551085e69763b3d85fb84ba771496a2da0`，分支
`feature/practice-play-python`。规格见 [SPEC-coach-lyrics.md](../SPEC-coach-lyrics.md)。
Win64 EXE 运行源码 `4a2c574ea9f60c5738674d9a44b1a9303eafabe5`；此后的
Python 曲谱前奏分句修复、测试和文档随包同步，不改变原生 EXE。

## 处理链

1. 复用原有 SongStore / ReferenceService / MDX / pYIN。
2. 独立 `.lyrics-venv` 使用 faster-whisper 1.2.1，CPU/int8、本地多语 small 模型。
   开启官方 [word_timestamps](https://github.com/SYSTRAN/faster-whisper#word-level-timestamps)，
   词时间来自交叉注意力和 DTW，不把整段文字平均摊到时间上。
3. 将测得的词区间与音高区间取交集；同音符多个词按词边界拆开，一词多个音符
   首段写实际文本、后段写 `~` 延音。无稳定音高的间隙保留为不计分 `F` 音符，
   不挪到远处参考、不用假音高补齐。练习的目标选择仍只接受 normal/golden。
4. 导出 `lyrics.json`、逐词 `lyrics.lrc` 和真实歌词 `song.txt`，与其余音频/参考
   一同校验、原子发布。原生导入要求有效歌词，识别失败不回退 la。
5. 状态携带词数、低置信数、自由词数、短预览。试听并确认当前版本后才正式入库。
   Studio 显示正常歌词，内部延音标记不绘为满屏 `~`；音符和时序仍保留。

识别是候选，不等于官方校订歌词；错字、漏字及时间偏差仍需试听和编辑器校对。
概率低于0.5的单元计入低置信提示，这不是通用识别准确率或人工验收分数。

## 安装、缓存与协议

```powershell
& 'D:\Apps\USDX-Coach\tools\setup-coach-lyrics.ps1' -CoachRoot 'D:\Apps\SingingCoach'
```

安装脚本复用原音频 Python 创建独立环境，不改已有 MDX/pYIN 环境；按
`requirements-lyrics.lock.txt` 安装，再下载模型。日常推理设置 local_files_only，
不上传音频。当前已实跑脚本与 pip check。

模型来自 `Systran/faster-whisper-small`，本次实际 revision：
`536b0662742c02347bc0e980a01041f333bce120`。
完整安装须有 model.bin/config.json/tokenizer.json 和 vocabulary.txt（或json）；
本次真实运行暴露了缺少 vocabulary.txt 的问题，下载列表、指纹和缺失回归已修正。

| 项 | 默认 / 可选覆盖 |
|---|---|
| 歌词 Python | 教唱工程 `.lyrics-venv`；`USDX_LYRICS_PYTHON` |
| 模型 | 教唱工程 `.models/faster-whisper-small`；`USDX_LYRICS_MODEL` |
| 语言 | zh；`USDX_LYRICS_LANGUAGE` 可指定识别语言 |
| 缓存 | 引擎 data/lyrics/reference-id/model-fingerprint/lyrics.json |
| 调试日志 | 同一缓存目录 worker.log |

指纹包括模型、tokenizer、config 和词表；歌词绑定 source SHA、vocals SHA、
reference revision、pipeline、模型 SHA 和原始时长。状态还保存完整歌词文件 SHA，
发布前再次检查，试听后的文件变化会拒绝发布。
歌词 JSON 上限2MB，最多20000个单元，要求有限、正长、单调的时间戳；
无有效词、损坏缓存或控制字符不生成占位曲谱。缓存损坏重建，不复用错误内容。
输出目录加歌词 SHA 版本后缀，旧占位歌包不会被覆盖。

prepare/publish 和 UTF-8 request 的 schema_version 仍为1，以新增字段扩展：
`lyrics_path/lyrics_sha256/lyrics_preview/lyric_word_count/low_confidence_word_count/
freestyle_word_count/chart_note_count`。ASR 与分离使用同一个受控 runner，
取消时终止并等待自己的子进程，未完成的歌词不发布为 ready。

旧 `prepare-coach-song.ps1` 的无歌词调用保留旧兼容行为；新原生入口始终强制歌词。

## 《雨爱》真实尝试

来源是 Apple iTunes 搜索返回的
[《雨愛》楊丞琳官方页面](https://music.apple.com/tw/album/%E9%9B%A8%E6%84%9B/347295255?i=347295290)，
使用其官方公开试听文件，不是全曲。实际音频长度29.9755625秒。

- 真实 MDX/pYIN：44个参考音符，有声音高覆盖约52%。
- 真实 Whisper/DTW：61个词级单元，8个低置信，9个全程无稳定参考音高。
- 曲谱140个区间，其中74个有参考音高、66个为自由区间；la占位0。
- 每个识别词恰好写入曲谱一次，延音段不重复歌词；全部音频/侧车哈希匹配。
- 同文件重导入复用同一参考、歌词SHA，模型日志时间不变。
- 另在原教唱工程的默认 data 真正导入：song
  `8da2b7c8-cfee-4b17-8030-c211123991cd`，reference
  `dd979a66-c196-4000-a953-dc32bbcf109d`；既有3首测试素材保留。
- 新便携包含《雨爱（官方试听·待校对）》AUTO候选，不冒充用户已审核；
  正式使用前试听校对并从导入页确认。原生QA在隔离副本里执行过确认入库。
- 真实ASR取消：观察到自己的音频子进程，取消后返回2、状态cancelled、子进程回收，
  没有ready歌词。首轮进程探针因额外CommandLine筛选未观测到短生命周期子进程，
  改用已有父PID绑定探针后复测通过；不把该探针失误算作取消成功。

## 鼠标原因与修正

旧配置 `Mouse=Game` 隐藏系统指针、画游戏软件光标；旧事件分支只在失焦时清理，
没有处理窗口 leave，也没有显式释放 SDL 捕获/相对模式/window grab。
项目业务代码没有直接 WarpMouse 调用，故不把“离窗回中心”归因为新增的某条移鼠标指令。
SDL官方说明相对模式默认可
[约束到中心](https://wiki.libsdl.org/SDL2/SDL_HINT_MOUSE_RELATIVE_MODE_CENTER)，
按压时默认
[自动捕获](https://wiki.libsdl.org/SDL2/SDL_HINT_MOUSE_AUTO_CAPTURE)。

Studio 现在始终显示系统光标、关闭自动捕获、释放 relative/grab；leave/focus-loss
统一取消按压。未修改保存配置的鼠标字段，旧主题仍走原分支。
私有1600×1200显示器中，把指针按住处理按钮拖到窗口外再释放，连续6次采样
都保持(1550,1150)，无回中、无误启动导入。该原生位置测试通过；Windows 本机
验证了新EXE启动，未把隔离Linux位置测试描述为用户桌面的Windows复现。

## 已执行验收

- 77项 Python测试通过；5项 Pascal core/window/motion/unicode/import 通过，
  保留范围、溢出与栈检查；主题生成精确一致；Ruff E/F/I与git diff --check通过。
- Linux完整游戏370425行，42 warnings/70 notes；私有SDL/Xvfb实际运行。
- [Win64运行构建](https://github.com/Sinotoon1/USDX/actions/runs/40096090645)
  的76项测试和完整游戏通过。之后新增Python前奏回归：前奏超过5秒时，
  第一段歌词不因phrase_start错误而被提前切成单音符句；本机77项通过。
- 原生800×600 /1280×960：F7、中文编辑、歌词预览与曲线、试听前禁用确认、
  试听、确认、增量曲库、真实歌词练习、整段游玩至结算均检查。
  UI复用上面实际模型的缓存并经真实ReferenceService验证，不是第二次Linux推理。
- 本机Win64 fresh-config隐藏启动至MainLoop，默认Studio/Studio/List、Off/1280×960。
  新包只附加候选歌曲；旧包、旧配置、分数数据库保留，配置字节完全一致。
- EXE：USDX-Coach-windows-lyrics-4a2c574/game/ultrastardx.exe；SHA256
  `02d5061ba94592a873a648eb9571b9586ac8edec36e486188cc4988228e6df6a`。
- 编译/虚拟音频/隐藏启动不等于物理麦克风、识别百分百正确或声学延迟实测。
  AUTO参考与实测MicDelay的方向提示和正式分数门控保留。

## 复用检查

```text
python -m unittest discover -s test/coach -p 'test_*.py' -v
python tools/build_studio_theme.py --check
```

证据目录：工作区父目录 `.codex-artifacts/usdx-lyrics-20261024-01`。
基线1589原始文件及raw SHA保留；`VERIFY.ps1 BASELINE/MODIFIED/ROLLBACK`
验证原53项、当前77项与另一副本恢复53项/1589哈希，user-data哨兵不变。
四件套及精确命令/输入/原样结果/返回码见同目录 VERIFICATION.txt。
回滚脚本依赖同目录 BASELINE.zip、哈希、变更清单和验证脚本，先检查后恢复，
拒绝覆盖后续编辑。实际源码、新便携包、已导入素材保持新版。

维护提示：

> 修改歌词功能时先补失败测试。保留本地ASR、实测词时间、源/人声/模型/参考绑定；
> 不用均分字符时间、la或假音高掩盖失败。自由词不计音高分，试听后只确认当前SHA。
> 更新token文案再生成主题，实际验证原生页流与离窗位置；保留自动候选和延迟门控，
> 交付时核验EXE与Python工具各自来源、完整资源和副本回滚。

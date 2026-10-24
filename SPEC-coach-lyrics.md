# 歌词识别、音符对齐与桌面鼠标

## 目标与模块
| 模块 | 职责 | 依赖 |
|---|---|---|
| lyrics-asr | 在独立模型子进程识别人声中的歌词和词级时间戳 | 已提取人声 |
| lyrics-score | 校验时间轴并与参考音符取交集，原子导出真实歌词曲谱 | lyrics-asr、已有音高 |
| import-ui | 阶段、歌词摘要与错误；当前版本试听确认 | lyrics-score |
| desktop-pointer | Studio 使用系统鼠标；离窗/失焦释放捕获与按压 | 现有 SDL/UDisplay |

顺序：歌词契约/纯对齐测试 → ASR与导入 → 鼠标回归 → 实际《雨爱》试听片段 → 构建交付。

## 明确约定
- 复用现有人声/参考模块；新增独立 `.lyrics-venv`，不改变原音频环境依赖。
- faster-whisper 1.2.1 CPU/int8，多语 small，词时间戳由交叉注意力+DTW生成；
  不用整首歌词按字数平均分配时间，也不在 UI 线程推理。离线运行只读已安装模型。
- 源/人声/参考/ASR模型版本及哈希绑定缓存；取消沿用受控子进程回收。
- 新导入必须包含非空真实识别词及有效时间戳；失败明确报错，不静默使用 la。
- 词区间与音符取交集；多词同音符按实际时间边界拆开；一词多音符只在第一段
  写文本，后续用 UltraStar 延音 `~`。无对应音高的词保留实际时间，以不计分的
  `F` 自由音符表示；不硬贴到远处音符，不臆造参考音高。
- `lyrics.json` 保留完整识别词、概率、时间轴与匹配统计，`lyrics.lrc` 供核对。
  未匹配/低概率统计如实记录。试听确认仍是人工审核，不把 ASR 当准确歌词真值。
- 旧歌包不覆盖；旧脚本导出保留显式旧占位兼容，新原生导入强制真实歌词。
- Studio 不再隐藏系统鼠标；禁用自动捕获/相对模式/窗口grab，离窗或失焦取消按压。
  不调用 WarpMouse，不修改旧主题的鼠标选项。缺少 Windows 实际复现时不宣称
  已确认该系统上回中现象的唯一原因。

## 来源
- [faster-whisper官方词级时间戳与CPU调用](https://github.com/SYSTRAN/faster-whisper)
- [DTW算法参数实现](https://github.com/SYSTRAN/faster-whisper/blob/v1.2.1/faster_whisper/transcribe.py)
- [SDL自动鼠标捕获](https://wiki.libsdl.org/SDL2/SDL_HINT_MOUSE_AUTO_CAPTURE)
- [SDL相对模式中心限制](https://wiki.libsdl.org/SDL2/SDL_HINT_MOUSE_RELATIVE_MODE_CENTER)

## 验收
`python -m unittest discover -s test/coach -p 'test_*.py' -v`；生成主题精确检查；
Pascal核心测试、Linux/Win64完整编译与隔离原生页流；真实ASR/分离/对齐结果；
私有显示器外移实际指针位置保持、不误触发；新便携包、原始哈希与副本回滚。
《雨爱》使用 Apple 搜索返回的官方试听音频；记录其实际长度，不将片段称为全曲。

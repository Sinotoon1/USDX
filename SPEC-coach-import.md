# coach-import：音乐导入与生成曲库

## 用户功能
首页增加“导入音乐”/F7；在原生 Studio 页面选择文件或粘贴/拖入路径，编辑
歌曲名与歌手，后台复用已有 Python SongStore / ReferenceService / MDX / pYIN。
显示实际处理阶段，完成后显示参考曲线和统计，支持试听人声。用户明确确认
参考后，复用 coach_bridge 原子生成歌包，立即增量加入当前曲库，不重启程序。
保留现有全浅色桌面风格。原 Python 项目的算法和存储格式不改。

## 任务协议与边界
- 原生控制器用 TProcess 参数数组启动 tools/coach_import.py，无 shell 拼接。
- worker 的 prepare/publish 子命令通过 schema_version=1 原子 JSON 状态文件
  返回 status/phase/error/job_id/stem/preview/output_path；每次任务 UUID 隔离。
- 重模型只在子进程。prepare 可写取消标记；worker 终止并等待自己的模型子进程，
  不留下运行任务或发布半成品。UI 轮询小状态文件，不阻塞渲染线程。
- 复用同 SHA256 的有效源和完成任务；新文件或不同版本清除试听/确认状态。
- publish 必须提交当前 job_id 的显式确认；发布前验证源、模型、stems 与 pitch；
  已存在歌包不覆盖，失败仍可重试。只有发布成功的 song.txt 才加入原生曲库。
- 原生曲库只增量读取指定文件、按完整路径去重，不调用会重复追加的全量扫描。
- 支持 WAV/MP3/M4A/FLAC/OGG/AAC，沿用源大小500MB与600秒模型上限。
- 歌词仍为 la 音节占位，不冒充自动歌词识别或校对后的人工乐谱。
- Python引擎优先 USDX_COACH_ROOT / USDX_COACH_PYTHON，默认查找程序相邻的
  已有教唱项目；仅复用安装好的环境，不在点击按钮时安装依赖。

## 实现顺序
1. worker 契约、取消、复用和确认发布测试 RED→GREEN。
2. 原生控制器、导入页、首页入口、增量曲库和输入绑定；纯核心与全量编译。
3. 实际原生流程、真实模型/缓存回归、Win64构建启动、新便携包、副本回滚。

## 验收
```text
python -m unittest discover -s test/coach -p 'test_*.py' -v
python tools/build_studio_theme.py --check
```
覆盖异常文件、引擎缺失、正在处理时取消、未确认/错误版本拒绝发布、损坏产物、
重复发布/增量加载不重复、中文与空格路径、曲库立即可见，以及旧模式不回归。
备份基线2885bbf，保留原始哈希和可执行副本回滚，实际程序保持新功能。

# USDX 教唱二开：首个可运行增量

基线：v2026.10.0 (`5fde5ec984154aca259117f99c49a220e0bab40c`)。
用户已确认：同一软件内分为练习和游玩，接入现有 Python 主唱分离 / pYIN。

| 模块 | 责任 | 依赖 |
|---|---|---|
| song-bridge | 调用已有 ReferenceService，验证产物，导出原版可读歌包 | 现有 Python 工程 |
| play | 原有选曲、完整演唱、评分与结算 | USDX |
| practice | 独立入口、按句循环/重唱、精确音高提示，不提交游玩成绩 | USDX、参考谱 |

顺序：歌包契约与测试 → 双入口 → 练习反馈与循环 → 编译与运行验收。

## 首轮契约

- Python 不嵌入 Pascal 进程，不复制模型实现。桥接 CLI 显式传入 `--coach-root`，复用其独立模型环境和数据。
- 目录发布采用暂存目录 + 原子改名；现有同名歌包不覆盖。文件名固定，元数据不含本地路径。
- TXT 使用 UTF-8、BPM=1500、GAP=0，1 tick=10ms；pitch=MIDI-60。量化后重叠、空谱、错误时长和非有限值均拒绝。
- 保留完整 pitch.json、源/模型/产物 SHA256、参考版本与 review 状态；未试听确认的自动谱只允许显式导出为未审核练习素材。
- 游玩继续原评分；练习默认单人，使用绝对八度的连续 Hz/cents，低置信度、休止、换音和未确认设备延迟时不报方向。
- 练习使用 F1/F2 切句、F3 重唱、F4 循环开关；结束回选曲，不写本地高分，不自动上传。
- 原调原速为首轮。变速、移调、逐句持久报表和结算跳转列入后续增量，不以入口按钮代替已验证功能。

## 验证

`python -m unittest discover -s test/coach -p 'test_*.py' -v`

`fpc -Mdelphi -Fusrc/base -FU<temporary-dir> -FE<temporary-dir> test/coach/coach_core_test.pas`

`./autogen.sh && ./configure --without-opencv && make -j4`

保持现有 Python 62 项回归通过；真实模型链与合成音精度测试分开记录。
基线、改版、回滚在 `.codex-artifacts/usdx-20261024-01` 留证。

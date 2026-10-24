# ui-mihome：全浅色桌面卡片风格

## 目标与来源
用户指定 MiHome-Windows 风格，延续“简洁明亮、全浅色”。本次是 Studio
视觉系统的迭代，不替换 USDX 的音频、评分、Python 桥接或窗口引擎。
参考固定于 `huanyuejue/MiHome-Windows@b3b3b3f5605a0494884c5e4c4d82bd6a10b54cdb`。
核对 `si_theme.py` 浅色调色板、`main_window.py` 顶部与网格、
`device_card.py` 14px 圆角与圆形操作、`overlay_dialog.py` 短淡入淡出。
只移植视觉原则；原生矢量实现，不复制参考应用的服务或 Qt 组件。

## 界面契约
- 冷灰 `#f2f3f5` 画布、白卡、近黑文字、青绿 `#3dbba4` 操作填色；
  小字使用更深的青绿语义色，普通文字对比度至少 4.5:1。
- 首页取消营销式大标题与不对称巨型入口：练习／游玩等宽白卡，
  每卡有固定位置的圆形前进标记；整个卡片是一个操作目标。
- 下方两列工具卡、上方低频操作；不新增没有实际路由的假页签或按钮。
- 共享标题栏、按钮、选择器、曲库、弹窗及演唱页使用同一套 token。
- 800×600 逻辑画布不变，验证 800×600 与 1280×960；字号不靠截图缩放。
- 160ms 悬停、90ms 按压、180ms 页面过渡；关闭动画立即到最终状态。
- 焦点环、按下同目标释放、中文搜索、设置滚动、练习／游玩流程保持。

## 实现与验证
唯一设计源为 `tools/studio-design.json`，生成器为 `tools/build_studio_theme.py`。
卡片 Action 标记通过 TThemeButton → TButton → UStudioUI 传递，默认关闭；
不在共享渲染器按屏幕名字或坐标识别首页。

```powershell
python -m unittest discover -s test/coach -p 'test_*.py' -v
python tools/build_studio_theme.py --check
```

先运行旧版 30 项基线，再运行失败的新契约；实现后运行完整测试、四个
Pascal 核心测试、原生编译和私有 Xvfb 交互截图；Windows CI 构建后本机启动。
备份基于 `5f773b0`，在另一副本测试回滚并校验全部原文件 SHA256。
实现范围不包含新的分离模型、音高算法或真实麦克风延迟结论。

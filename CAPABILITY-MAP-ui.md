# Studio 客户端重写

| 模块 | 职责 | 依赖 |
|---|---|---|
| ui-motion | 确定性时间插值、反向/低帧率/计时回绕、按压捕获与取消 | 无 |
| ui-system | 调色板/字阶/间距、矢量控件、页面过渡、减弱动态效果 | ui-motion |
| ui-flows | 全屏幕主题、首页/曲库/演唱/结算/设置/弹窗及真实导航 | ui-system |

顺序：ui-motion → ui-system → ui-flows。音频/模型/参考审核/成绩隔离沿用。

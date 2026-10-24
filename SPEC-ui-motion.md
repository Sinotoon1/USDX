# ui-motion

目标：时间驱动而非每帧递增；悬停 160ms、按压 90ms、页面 220ms，均由主题 token 提供。
接口：TUIMotion 的 MotionValue/RetargetMotion；TUIPointer 的 PointerDown/PointerUp/CancelPointer。
重定向必须从当前值开始，避免快速移入移出跳变；输入先按下捕获，原位置释放才触发。
时长为 0 立即完成；SDL 32 位计时回绕正常；卡顿后直接到正确终态。
测试：FPC -Cr -Co -Ct，确定时间戳，30/60/144Hz、逆转、回绕、取消、空白释放、跨控件释放。
文件：src/base/UIMotion.pas、test/coach/coach_motion_test.pas。
风格：显式 record 和纯函数，不引入线程、依赖或音频时钟。

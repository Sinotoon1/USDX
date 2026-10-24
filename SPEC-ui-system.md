# ui-system

目标：独立 Studio 原生主题；简洁明亮的全浅色，包括演唱舞台，旧主题保留。
视觉 token 是唯一事实源；主题生成可重复，禁止截图替代布局。Noto 字体、8 单位间距、统一字阶。
共享按钮/选择器/面板用原生矢量绘制；焦点不靠颜色单独表示；动画不改变命中范围。
ScreenFade=Off 同时关闭新过渡与微动画；旧主题不改变渲染和按下行为。
页面过渡取消旧变形缩放，改为短距离平移/透明度；过渡期间输入不穿透到未显示的新页。
文件：tools/studio-design.json、tools/build_studio_theme.py、UStudioUI、UThemes、UMenu*、UDisplay。
测试：token 对比度/主题覆盖/可重复生成、编译、真实悬停按压帧、开启/关闭动画导航。

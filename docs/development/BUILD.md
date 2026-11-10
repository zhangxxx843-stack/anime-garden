# 源码构建与验证

产品目标为 Windows x64。普通用户请从仓库 README 下载完整运行包，不需要 SDK。源码包不含预编译应用。

## 完整依赖

`cjpm.toml` 只引用仓库内的 `vendor/CangjieGUI`，其依赖 `vendor/CangjieSDL`。没有子模块，不需要项目旁边的 xin-xuan-environment。

- CangjieGUI 0.9.6，上游 https://github.com/SunriseSummer/CangjieGUI ，基线提交 `67cbc59993826c2bec4e13cc84df6891eb3db999`。保留 Windows 固定尺寸布局修复及 `windows_fixed_flex_test.cj`，编译优化为 O2。
- CangjieSDL 0.9.6，上游 https://github.com/SunriseSummer/CangjieSDL ，基线提交 `896b175a6a8b012a477058042c089deddc348921`。`.sdl3` 中六个 DLL 文件随源码提供，原符号链接已转为真实文件，便于 Windows 解压。
- SDK 为 Cangjie 1.0.5，单独安装并加载其环境。建议 SDK 和源码位于英文路径，避免此前 Windows 原生编译的中文路径问题。
- 第三方许可位于各 vendor 目录及根目录 licenses；运行包包含运行时许可和非官方兼容补丁说明。兼容 DLL 仅放在运行包，严禁替换 SDK 文件。

## Windows 原生构建

在已加载 Cangjie 1.0.5 环境的终端中，于项目根目录执行：

```text
cjc --version
cjpm build
cjpm test
```

输出应用位于 `target/release/bin/main.exe`。单独复制这个 EXE 不构成完整运行包。运行时还需要 assets、SDL3.dll、SDL3_image.dll、SDL3_ttf.dll、cui_uia.dll、libboundscheck.dll、兼容 libcangjie-runtime.dll；当前经整理的完整集合见 packages 中 v7 ZIP。

注意：本仓库 v7 已有 Ubuntu 交叉构建和主机测试证据，尚未声明 Windows 原生 O2 构建、中文输入或全流程通过。此前 Windows 原生验证仅覆盖窗口测试及 O0 构建；不能据此保证 v7 原生 O2 成功。

## Ubuntu 开发验证

需额外安装 Linux 版 SDL3、SDL3_image、SDL3_ttf 并把相应 `.so` 放到系统库搜索路径，同时在 `vendor/CangjieSDL/.sdl3/` 中创建指向这三个 `.so` 的本机符号链接（不要提交绝对路径链接）；vendor 中只提供 Windows DLL，不提供 Linux SDK 或宿主库。加载 Cangjie 1.0.5 Linux SDK 后：

```sh
SDL_VIDEODRIVER=dummy cjpm test -i -j4 --no-progress --no-color
cjpm build -i -j4 --target x86_64-w64-mingw32
cjpm test -i -j4 --target x86_64-w64-mingw32 --no-run --no-progress --no-color
```

宿主 GUI 测试使用 SDL 隐藏窗口和语义操作；并非 Windows 鼠标、键盘和输入法验收。完整 SDK 的 Windows 目标工具链需可用。

## 功能与验收边界

推荐核心、CSV 校验、本地保存及清单/评分/方案界面已连接并有测试；CSV 导入、补图、新增商品界面尚未连接。v6 窗口交互测试已通过，v7 新主流程仍待用户 Windows 反馈。详见同目录 native-shopping-flow 和 windows-acceptance 记录。

测试覆盖正常、预算边界、输入异常、排序、CSV 整批拒绝、存档恢复、保存失败、编辑保留评分及小窗口布局。不要把交叉编译成功记为 Windows 执行成功。

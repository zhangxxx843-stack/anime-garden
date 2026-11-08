# 开源鸿蒙第二次培训作业

本次 Mini Project 的第一版目标是离线使用、以人民币记账的个人支出 App。
当前交付目标是 Windows 10/11 x64 桌面版：使用 PySide6 构建界面，使用本地 TSV 文件保存数据，GitHub Actions 生成可试用的 Windows 压缩包。

第一轮开发以 [PRD.md](PRD.md) 为需求与验收依据，视觉参考位于 `docs/assets/ui-concept-v1.png`。

## 第一版功能范围

第一版不包含用户登录或注册。打开应用即可使用，记账数据保存在本地。

- 每日支出记录，支持修改与删除账单。
- 记账入口使用显眼的大号“＋”：Windows 桌面版位于左侧栏；点击后先弹出大类列表，选好大类后输入金额，并可在备注中说明具体小类。
- 自定义二级分类：大类、小类均可新增和重命名，自建大类下也可以添加小类。
- 按日期、月份查看账单，并提供单日支出总结和月度统计。
- 设置月度预算，查看已用金额与剩余预算。
- 本地保存数据，关闭应用后仍可继续查看。

最终交付只保留 Windows 版本。Ubuntu 上的仓颉工程和 Tk 界面作为业务规则与旧版数据的参考实现，不作为最终试用入口。

## Windows 版试用

在 GitHub Actions 的 `Windows desktop build` 工作流中下载 `suishouji-windows-x64` artifact，解压后双击 `Suishouji.exe` 即可运行。它不需要安装 Python，也不需要启动仓颉服务。

Windows 版首次打开会创建空账本，并自动准备“餐饮、交通、购物、学习”四个大类。数据默认保存在 `%APPDATA%\\Suishouji\\ledger.tsv`。左侧“导入旧账本”可以手动选择已有的 schema 1 TSV 文件；文件解析成功后才会替换当前账本，取消或解析失败会保留原数据。

Windows 版目前覆盖明细、统计、预算、分类、备注显示、编辑、删除和本地持久化。未填写备注时明细显示大类，填写备注时只显示备注。

## Windows 源码开发

在 Windows 机器上安装 Python 3.12 后执行：

```powershell
py -3.12 -m venv .venv
.venv\\Scripts\\python -m pip install -r requirements-windows.txt
$env:QT_QPA_PLATFORM = "offscreen"
.venv\\Scripts\\python -m unittest discover -s windows_app -p "test_*.py" -v
.venv\\Scripts\\python -m windows_app.main
```

Ubuntu 上可以执行 `./dev.sh windows-test` 做同一套离线测试；`./dev.sh windows-build` 只提示 Windows 构建入口，不会把 Ubuntu 构建结果冒充 Windows 安装包。

## 当前实现

仓颉代码按职责拆分：

- `src/model/` 保存账单、分类、预算和本地状态模型。
- `src/utils/` 负责金额转分、日期校验和金额显示。
- `src/storage/` 负责版本化 TSV 编解码、读取和临时文件原子替换。
- `src/service/` 负责分类、账单、统计和预算规则。
- `src/main.cj` 提供 `init`、`snapshot`、账单 CRUD、分类 CRUD 和预算命令。
- `gui/app.py` 是 Ubuntu 试用界面；它不另存业务状态，所有写操作都调用仓颉可执行程序。

记账入口遵循最新流程：点击侧栏或底部的“＋”，先选择大类，再输入金额、日期和可选备注。备注可以说明小类或消费内容，但不会被自动解析成结构化分类。Ubuntu 试用界面按视觉草案采用米白工作区、深绿色侧栏、卡片式摘要和明确的空状态提示；移动端底部导航仍属于后续平台适配范围。

## 当前环境

- Ubuntu 24.04.5 LTS，x86_64。
- Cangjie 1.0.5，CJNative 后端，CJPM 1.0.5。
- VS Code 与 IDE-Innovation-Lab.cangjie 1.0.5 扩展。
- Git 2.43.0。

工程复用电脑上已有的 SDK，`env.sh` 默认使用当前已验证的安装位置。
开发脚本自动加载 SDK，处理当前终端找不到 `cjpm` 或仓颉运行库的问题。
环境配置仅作用于调用它的终端进程。

## 在 Ubuntu 打开

```bash
code "/home/zhangxxx/文档/ChatGPT/开源鸿蒙第二次培训作业/miniproject-code"
```

请将 `miniproject-code` 作为 VS Code 的工作区文件夹打开，以启用项目内的任务与终端配置。
打开后新建终端，会自动加载仓颉环境；已有终端可执行 `source ./env.sh`。

## 日常命令

在项目目录执行：

```bash
./dev.sh run      # 编译并运行
./dev.sh build    # 编译
./dev.sh test-local  # 单元测试，适合当前会话
./dev.sh check    # 版本、依赖、编译、测试、运行完整检查
./dev.sh gui      # 构建并打开 Ubuntu 图形界面
./dev.sh gui-test # 运行 GUI 协议解析测试
```

也可以使用原生命令：

```bash
source ./env.sh
cjpm build
cjpm test
cjpm run
```

`./dev.sh` 支持从其他当前目录通过绝对路径调用；原生 CJPM 命令需要在项目目录运行。
`cjpm check` 仅检查依赖，完整验证使用 `./dev.sh check`。

当前会话禁止创建套接字，直接执行 `cjpm test` 的测试调度器会报 `SocketException`。
`test-local` 先用 `cjpm test --no-run` 在临时目录编译，再逐包运行真正的测试程序，
关闭并行和子进程崩溃监测；任何编译或测试失败都会返回非零退出码。
`check` 与 VS Code 的测试任务也使用该方式。涉及进程退出或崩溃监测的测试，
请在普通 Ubuntu 终端执行 `./dev.sh test`，使用完整的 CJPM 调度器。

## VS Code 操作

- `Ctrl+Shift+B`：编译作业。
- 菜单“终端 → 运行任务 → 仓颉：运行作业”：运行。
- 选择“仓颉：单元测试”：测试。
- 选择“仓颉：完整检查”：执行完整流程。

修改 `src/main.cj` 后运行作业即可查看结果。

打开 Windows 版后，可以直接检查以下流程：

1. 点击左侧“＋ 记一笔”，选择“餐饮”。
2. 输入 `18.00`、日期和备注“午餐 · 食堂盖饭”，保存。
3. 在明细中选中记录，检查详情、编辑和删除确认。
4. 在统计中切换月份，在预算中设置 `100.00`，检查已用、剩余和超支状态。
5. 在分类中新增或重命名大类、小类，再次点击“＋”确认新大类立即可用。
6. 关闭窗口后重新打开 `Suishouji.exe`，确认数据仍在。

## 文件职责与测试

| 文件 | 用途 |
| --- | --- |
| `src/main.cj` | 仓颉命令协议入口 |
| `src/environment_test.cj` | 检查管道语法、Option 缺失值、异常处理和测试框架 |
| `gui/app.py` | Ubuntu Tk 图形试用界面 |
| `windows_app/` | Windows PySide6 客户端、业务适配层和自动化测试 |
| `packaging/windows.spec` | PyInstaller Windows 构建入口 |
| `.github/workflows/windows-build.yml` | Windows runner 构建并上传 zip artifact |
| `cjpm.toml` | 模块名称、SDK 版本说明、产物类型与依赖 |
| `cjpm.lock` | CJPM 生成的依赖锁定信息，应随源码保留 |
| `env.sh` | 加载 SDK 并检查编译器版本 |
| `dev.sh` | 统一的编译、运行、测试入口 |

测试覆盖环境语法、金额与日期边界、分类重名、预算超支、TSV 编解码和命令协议；Windows 客户端测试覆盖统计、预算、分类、导入和 Qt 离屏界面。`./dev.sh windows-test` 可在 Ubuntu 上运行 Windows 客户端测试，`./dev.sh test-local` 会在临时目录编译后逐包直接执行仓颉测试。
按真实职责需要拆分子包，并为跨包使用的声明添加相应的 `public` 和 `import`。

## SDK 路径变更

现有 SDK 位于之前配置环境的目录中，日常使用请保留该目录。
迁移 SDK 或在其他电脑运行时，先指定新位置：

```bash
export CANGJIE_HOME="/你的SDK目录/cangjie"
./dev.sh check
```

同时修改 `.vscode/settings.json` 中的 `CangjieSdkPath.CJNativeBackend`，使编辑器使用同一份 SDK。
开发脚本会拒绝与本次培训要求不符的编译器版本。

## 后续交付

培训建议包含：可运行的核心功能、按职责组织的源码、至少 3 个实际功能测试、完整 README、
至少 4 次有意义的 Git 提交，以及可演示的 Demo。本仓库已按该要求组织提交历史，教师要求变化时以最新通知为准。

当前仓库已配置远程地址 `origin`。本地存储文件位于 `data/ledger.tsv`，整个 `data/` 目录已加入 `.gitignore`，不会把试用账本提交到仓库。文件首行记录 schema 版本，写入时先写 `data/ledger.tsv.tmp`，成功后再替换正式文件；读取或写入失败会返回错误，不会先显示保存成功。排查数据时可以备份或删除该文件后重新执行 `./dev.sh gui`，首次启动会重新建立默认分类。

## 已知限制与下一步

- Windows v1 通过 GitHub Actions 的 `windows-latest` runner 生成 zip，当前没有安装器、代码签名或自动更新。
- Android 和 iOS 不在本次交付范围内；Ubuntu Tk 界面只保留为历史参考入口。
- 当前金额和日期错误会在表单附近显示；跨进程并发写入仍未支持。
功能开发时用真实变更记录历史，不必为凑数量拆分提交。
项目作者说明与许可证应在发布方式确定后补充。

## 参考

- 培训材料：《第二次培训(1).pptx》第 28、38、43、47 页。
- [CJPM 1.0.5 官方指南](https://docs.cangjie-lang.cn/docs/1.0.5/tools/source_zh_cn/cmd-tools/cjpm_manual.html)。

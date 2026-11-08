# 开源鸿蒙第二次培训作业

本次 Mini Project 的第一版目标是离线使用、以人民币记账的个人支出 App。
目前已配置开发环境，示例程序输出 `hello world`；记账界面与业务功能尚待实现。

第一轮开发以 [PRD.md](PRD.md) 为需求与验收依据，视觉参考位于 `docs/assets/ui-concept-v1.png`。

## 第一版功能范围

第一版不包含用户登录或注册。打开应用即可使用，记账数据保存在本地。

- 每日支出记录，支持修改与删除账单。
- 底部中间的大号“＋”为记账入口：先弹出大类列表，选好大类后输入金额，并可在备注中说明具体小类。
- 自定义二级分类：大类、小类均可新增和重命名，自建大类下也可以添加小类。
- 按日期、月份查看账单，并提供单日支出总结和月度统计。
- 设置月度预算，查看已用金额与剩余预算。
- 本地保存数据，关闭应用后仍可继续查看。

目标使用平台为 Windows、Android 和 iOS，Ubuntu 用于开发、检查和改善。
当前环境验证覆盖 Ubuntu 上的仓颉工程，尚未制作各平台的应用安装包。

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

## 文件职责与测试

| 文件 | 用途 |
| --- | --- |
| `src/main.cj` | 当前程序入口，由 CJPM 初始化生成 |
| `src/environment_test.cj` | 检查管道语法、Option 缺失值、异常处理和测试框架 |
| `cjpm.toml` | 模块名称、SDK 版本说明、产物类型与依赖 |
| `cjpm.lock` | CJPM 生成的依赖锁定信息，应随源码保留 |
| `env.sh` | 加载 SDK 并检查编译器版本 |
| `dev.sh` | 统一的编译、运行、测试入口 |

当前 3 个测试用于验证开发环境，不代表已经覆盖作业的业务功能。
实现核心功能后，再在对应包的 `*_test.cj` 中补充正常、边界和异常用例。
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
至少 4 次有意义的 Git 提交，以及可演示的 Demo。提交次数与测试数量以教师最终要求为准。

当前仓库已配置远程地址。本次环境配置没有创建提交或推送代码。
功能开发时用真实变更记录历史，不必为凑数量拆分提交。
项目作者说明与许可证应在发布方式确定后补充。

## 参考

- 培训材料：《第二次培训(1).pptx》第 28、38、43、47 页。
- [CJPM 1.0.5 官方指南](https://docs.cangjie-lang.cn/docs/1.0.5/tools/source_zh_cn/cmd-tools/cjpm_manual.html)。

# V1.0 验收记录

日期：2026-11-08

## 构建与测试

在仓库根目录执行 `./dev.sh check`，实际检查了：

- Cangjie Compiler 1.0.5 cjnative
- CJPM 1.0.5
- `cjpm check`
- `cjpm build`
- 4 个 Cangjie 测试包，共 10 个用例，全部通过
- 2 个 GUI 协议解析测试，全部通过
- `target/release/bin/main snapshot` 命令入口

Cangjie 业务测试覆盖环境语法、金额和日期边界、分类同层级重名、预算超支、TSV 备注转义和命令协议初始化。GUI 测试覆盖无 shell 参数拼接和快照解析。

## 业务闭环检查

使用隔离账本执行了以下命令序列：

1. 初始化默认分类。
2. 保存 `18.00` 元餐饮账单，备注为“午餐 · 食堂盖饭”。
3. 设置 `2026-11` 月预算 `100.00` 元。
4. 新增“运动”大类。
5. 将账单改为 `20.00` 元并移动到下一天。
6. 删除账单并重新读取快照。

每一步都返回 `OK`，重新读取仍能看到分类和预算，删除后账单消失。试用数据没有提交到 Git，`data/` 已加入 `.gitignore`。

## PPT 交付要求对照

| 要求 | 证据 |
| --- | --- |
| 可构建的 Cangjie 1.0.5 项目 | `cjpm.toml`、`./dev.sh check` |
| 按职责拆分源码 | `src/model`、`src/utils`、`src/storage`、`src/service` |
| 至少 4 次有意义提交 | Git 历史中的 `feat`、`fix`、`docs` 提交 |
| README 环境、运行、示例、测试、依赖 | `README.md` |
| 正常、边界、异常测试 | `src/*_test.cj`、`gui/test_app.py` |
| 可运行 Demo、局限和下一步 | `./dev.sh gui`、README 平台限制章节 |

## 实际平台范围

Ubuntu 24.04.5 LTS 上已经验证仓颉业务程序、文件持久化和 Tk 图形界面。Windows、Android、iOS 的 UI 方案、权限和安装包还没有验证，后续需要先锁定目标平台官方支持的仓颉 UI 技术，再进行适配。

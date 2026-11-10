# CSV 导入校验实施记录

沿用已确认流程：允许重名，每行独立；相对图片路径以 CSV 所在文件夹为准。
表头沿用已确认草图：商品名称、价格、喜欢程度、图片路径；兼容“名称”别名和列顺序变化。
五档中文与评分数字 -1、1、2、3、10000 均可，空评分导入为未评分。
字段错误、缺图及无法解码图片列出行号和字段；存在任何问题时不交付部分商品。

- [x] 在 src/shopping/csv_test.cj 先写测试：BOM、CRLF、引号转义、跨行字段、表头、评分、价格、整批阻断、重名、相对路径。
- [x] src/shopping/csv.cj 实现解析与业务校验；图片检查通过必传函数参数提供，核心不依赖图形库。
- [x] src/importing/catalog.cj 实现真实 UTF-8 文件读取及 SDL Surface 解码检查，读取图片后及时释放。
- [x] src/importing/catalog_test.cj 使用本地真实图片、坏文件与不存在路径验证，无 GUI 窗口。
- [x] 完整运行应用测试并交叉编译 Windows x64；记录宿主测试与 Windows 验收区别。

本段尚不写入商品库、不复制图片、不接桌面导入页，不预选追加/替换。
后续才实现持久化和整批提交；README 保持面向 APP 用户，不生成 PRD。

## 本段结果与限制

- 核心新增 11 项 CSV 测试，加上已有 8 项推荐测试，共 19 项通过。
- 本地文件与真实解码新增 4 项，应用完整测试共 23/23 通过（Ubuntu 宿主，无 GUI 窗口）。
- 先验证缺失实现的失败，再实现；另复现并修正“格式错误掩盖后续字段错误”和商品名称含空字符的问题。
- Windows x64 应用构建通过；Windows 测试程序 --no-run 编译通过，尚未目标机执行。
- 单独加入 Windows 盘符和 UNC 图片路径用例，仅交叉编译，未宣称运行通过。
- 提供 assets/商品导入模板.csv，UTF-8 BOM、CRLF，便于表格软件识别中文。
- CSV 文件当前要求 UTF-8；非 UTF-8 返回明确文件错误，不猜测转码。
- 引号未闭合时，后续换行无法可靠区分字段内容和新商品；报告格式错误，整批阻断。
- 校验不写文件、不修改商品清单；图片复制、追加/替换提交及 UI 尚未连接。
- 不变更已验收 Windows 窗口；不修改 Ubuntu SDK 或复制 Windows DLL。

日志：项目旁 xin-xuan-environment/logs/csv-{red,recovery-red,core-final,files-red,app-final,windows-build,windows-tests-build}.log。
复测：在 miniproject-code 内，配置仓颉 1.0.5 后运行 cjpm test -i -j 4。
路径操作参照官方 1.0.5 std.fs 文档：https://docs.cangjie-lang.cn/docs/1.0.5/libs/std/fs/fs_package_api/fs_package_structs.html。

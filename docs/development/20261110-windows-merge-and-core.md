# Windows 交接合并与推荐核心

沿用本聊天已确认方案，记录开发步骤与证据，不替代用户需求。

- [x] 对比并备份 main.cj 与框架 layout_widgets.cj；仅合入交接差异。
- [x] 先复现固定轴误分配，再合入两处判断；测固定宽、高及显式 flex。
- [x] 复核 Windows 交互验收记录，区分用户确认与自动化证据。
- [x] 开发独立仓颉推荐核心并测试；不改变当前窗口预览。

核心接口：src/shopping/models.cj 的 Product（名称、整数价格、可空评分、图片路径），
src/shopping/recommend.cj 的 recommend(products, budget) 返回至多三个不同的非空购物组合。
价格/预算范围 1..1000，商品数大于 3。评分只允许 -1、1、2、3、10000，空评分禁止计算。
按总评分降序、总花费升序、商品录入索引序列字典序排序；每件最多一次。
用预算动态规划，每个精确花费保留前三条路径；遍历商品时倒序更新以避免重复购买。
空路径作为中间状态，输出排除空组合；没有可购买商品时返回空列表，不伪造三个方案。
测试覆盖正常、边界、异常、平分稳定排序、必选误解、负分、重复名称、穷举对照。

本段不实现 CSV、保存恢复及完整购物界面。后续按已确认先数据正确性再接桌面的顺序继续。
Windows DLL 仅保留在隔离测试产物，不写入 Ubuntu SDK。

## 本段真实结果

- 合并前新增布局测试：固定高、固定宽两项失败；未固定轴的显式 flex 通过。
- 合并后 CUI 完整测试：994/994 通过，0 跳过，0 失败（Ubuntu 测试运行）。
- 推荐核心：8/8 通过，其中一项对 50 组七件商品数据枚举所有非空子集作独立对照。
- Windows x64 应用交叉编译通过（当前配置 -O2）；不代表 Windows 原生 O2 实测。
- Windows 推荐核心测试程序编译通过，尚未在目标系统执行。
- SDK 中 Windows 运行时 SHA256 仍为原始 03f4d59a...；未复制 v6 DLL 到 SDK。
- CSV、保存与完整 UI 连接尚未实现；不将已有窗口交互验收扩展为这些功能通过。

日志在项目旁 xin-xuan-environment/logs：
windows-layout-before-merge.log、windows-layout-merged-full-suite.log、
shopping-red.log、shopping-final.log、windows-merged-core-build.log。
复测推荐核心：配置仓颉 1.0.5 后运行 tools/check-shopping-core.sh。
本段沿用现有工作区，没有提交或推送 Git，也没有覆盖旧备份。

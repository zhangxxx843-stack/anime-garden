# 本地保存与恢复实施记录

沿用已确认方案：Windows 当前账户应用数据目录；保存失败保留当前内容并允许重试。
Windows 默认根目录为 LOCALAPPDATA/XinXuanShopping，不使用程序目录、不写 Ubuntu SDK。

- [x] 定义 ShoppingState（可空预算、商品、可空评分）；零件数/未评分可保存，不强制达到推荐条件。
- [x] 版本化二进制快照，UTF-8 字段、长度校验和 Adler-32 数据损坏校验；不引入额外运行库。
- [x] 图片复制到应用 images 子目录，保存快照只引用相对受控路径；重复保存复用已复制图片。
- [x] 新快照在独立临时目录完成写入，再重命名为全新版本号；不覆盖旧存档。恢复选最新有效版本并明确告警。
- [x] Session 保留内存状态；保存失败 dirty=true、提示尚未保存，retry 可继续；初始化只读，不自动弹评分。
- [x] 实测空状态、中文/引号/换行、评分未完成、原图移走、复制/发布失败、坏快照回退、所有快照损坏、重试。
- [x] 完整应用测试、Windows 应用及测试交叉编译；保留 Windows 真实验收边界。

断电级磁盘落盘、同时运行多个程序实例、旧版本清理暂不宣称完成；本段保留历史快照。
此为实现记录，不是 PRD。界面连接在数据层完成后单独进行。

## 实测结果与边界

- 保存模块 11 项测试通过：UTF-8 往返、空预算/空清单、未评分、图片搬移后恢复、同图复用、pending 忽略、坏版本回退、全部损坏提示、部分复制后失败不提交、发布失败后保留内存并重试、恢复后继续评分、图片缺失不丢商品与评分、根路径异常、截断/校验失败/越界路径。
- 应用完整测试 34/34 通过（Ubuntu 宿主，无桌面窗口）；前述场景分组在 11 个测试用例中。
- Windows x64 应用交叉编译通过；测试程序仅编译不执行，目标机持久化仍未验收。
- 真正自动保存尚未与桌面控件连接；调用 Session.update 后才保存，保存失败可 retrySave。
- 恢复不写盘、不自动弹评分；firstUnrated 仅提供“继续评分”点击后所需索引。
- 以全新版本号发布快照，重命名不覆盖已有文件；不承诺断电时磁盘硬件缓存落盘。
- 旧版本暂全部保留，尚未实现历史清理；新图片副本复用，失败尝试的新增图片会清理。
- LOCALAPPDATA 缺失/无效时明确报错，不退回程序目录；非 Windows 默认目录函数拒绝生产调用，测试显式指定临时目录。
- CSV 整批追加/替换、关闭时未保存提示、首次内置示例加载和正式界面连接仍待后续。

日志（项目旁 xin-xuan-environment/logs）：storage-red.log、storage-guard-red.log、storage-app-final.log、storage-windows-final-build.log、storage-windows-tests-build.log。
目录与重命名行为核对了官方 Cangjie 1.0.5 std.fs 文档；账户目录参照 Microsoft FOLDERID_LocalAppData。
https://docs.cangjie-lang.cn/docs/1.0.5/libs/std/fs/fs_package_api/fs_package_funcs.html
https://learn.microsoft.com/en-us/windows/win32/shell/knownfolderid

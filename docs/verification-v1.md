# V1.0 验收记录

日期：2026-11-08

本次最终交付范围是 Windows 10/11 x64 桌面版。Ubuntu 上的仓颉工程保留为课程要求对应的业务核心和旧版 TSV 参考实现，不把 Ubuntu Tk 界面作为最终试用入口。

## 构建与测试证据

在仓库根目录执行了以下检查：

| 检查 | 结果 |
| --- | --- |
| `./dev.sh test-local` | 4 个仓颉测试包、10 个用例全部通过 |
| `env QT_QPA_PLATFORM=offscreen .venv-windows/bin/python -m unittest discover -s windows_app -p 'test_*.py' -v` | 23 个 Python 用例全部通过 |
| 隔离目录保存后重新 `load_state` | 金额、备注、分类和预算均恢复，结果为 OK |
| Qt 离屏窗口检查 | 明细页、空状态、导航和截图均成功，结果为 OK |
| `python -m PyInstaller --clean --noconfirm packaging/windows.spec` | 当前 Ubuntu 上的 spec 分析和构建成功；Windows `.exe` 由 GitHub Actions 生成 |

Python 测试覆盖金额和日期边界、同层级重名、精确到分的统计、预算超支、TSV 转义、空账本初始化、Qt 页面导航、备注显示、保存失败回滚、统计、预算、分类和导入失败保留原数据。

## PRD 场景对照

| 场景 | 当前证据 |
| --- | --- |
| A01 首次打开为空 | Qt 空状态测试；首次读取只生成默认大类 |
| A02 点击“＋”先选大类 | Qt 记一笔入口测试 |
| A03 选择大类进入表单 | 分类选择器连接到记账表单；需在 Windows artifact 上手动点一次 |
| A04 保存金额和备注 | 领域测试、Qt 备注显示测试 |
| A05 备注留空仍可保存 | 领域测试；空备注显示大类 |
| A06 非法金额拒绝保存 | 领域测试和保存失败对话框测试 |
| A07 取消记账 | 表单提供取消；重新选择大类保留草稿仍列为后续交互细化项 |
| A08 0.10 + 0.20 精确统计 | 整数分统计测试覆盖同类场景 |
| A09 新增大类、小类并立即用于记账 | 分类验收测试检查新增、重命名和选择器刷新 |
| A10 重命名被引用分类 | 服务层保留分类 ID，账单不会丢失；需在 Windows artifact 上手动确认显示名 |
| A11 同层级重名或空白拒绝 | 领域测试 |
| A12 编辑金额、日期和月份 | 服务层更新与月度汇总测试；界面编辑按钮已接入 |
| A13 删除二次确认 | 界面删除按钮已接入确认框；需在 Windows artifact 上实际点击确认和取消 |
| A14 正常预算状态 | 预算服务和页面状态计算已覆盖 |
| A15 超预算提示和 100% 进度上限 | 预算验收测试和页面截图 |
| A16 未设置预算的月份 | 页面显示“本月尚未设置预算”，月份独立读取 |
| A17 关闭重开后离线保留 | 隔离目录保存、重新读取检查为 OK |
| A18 读写失败不伪造成功 | 保存失败保持对话框，导入解析失败保留原账本 |

## 试用和数据位置

GitHub Actions 工作流 `.github/workflows/windows-build.yml` 在 `windows-latest` 上安装依赖、运行 23 个 Python 测试、构建 `Suishouji.exe`，并上传 `suishouji-windows-x64.zip`。下载 artifact 后解压即可双击运行。

Windows 首次运行使用空账本，默认分类为“餐饮、交通、购物、学习”。正式数据路径为 `%APPDATA%\\Suishouji\\ledger.tsv`。左侧“导入旧账本”只接受 schema version 1 TSV；解析成功后才替换当前账本，取消或失败不会覆盖原文件。

## 仍需在 Windows runner 或实机确认的内容

- Windows `.exe` 启动、字体 fallback 和系统 DPI 缩放。
- GitHub Actions artifact 下载后解压、双击启动和 `%APPDATA%` 写入权限。
- A03、A07、A10、A13 的完整手动点击路径。

这些项目属于 Windows 环境验证，Ubuntu 本地不能替代。Android 和 iOS 不在本次最终交付范围内。

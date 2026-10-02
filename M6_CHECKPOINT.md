# M6：历史、设置与发布

已实现 SQLite 历史、设置、麦克风选择、Profile 菜单、模型页、错误提示、用户文档和 PyInstaller 目录发布。

验证：核心 34 项 pytest 通过，源码和发布启动验证记录见 docs/VALIDATION.md 与 docs/package-validation.json。依赖版本保存在 requirements-lock.txt。打包修复了 PATH 中不兼容 ICU 被错误收集的问题。

未完成：另一台无 Python 机器以及完整真人、跨应用人工验收。交付为可试用版本，不把这些待验收项标成完成。

# M0：工程骨架

已实现 Python 包、PySide6 托盘、轮转日志、配置加载和单实例锁。

验证：源码 `python -m voiceinput --smoke-test` 退出码 0。配置自动测试验证用户覆盖、自定义 Profile 和无效配置保留上一版本。现有用户文件首次初始化和升级均不覆盖。

本检查点依据最终代码与实际验证补记；完整证据见 docs/VALIDATION.md。

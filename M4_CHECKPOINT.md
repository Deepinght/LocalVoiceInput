# M4：Windows 上屏

已实现目标窗口/进程校验、焦点恢复、Unicode SendInput、Clipboard 回退和原剪贴板恢复。部分发送不回退，不自动重发；输出仅由候选确认进入。

验证：原生 Windows EDIT 测试窗口的中文、下标、单位和 emoji 完整一致；Clipboard 粘贴与恢复通过。错误目标不输出、零发送回退、部分发送不回退均有 pytest。

未完成：记事本、Chrome/Edge、VS Code、Word 的最终人工兼容性验收。Word 自动测试因焦点限制未通过；Qt 编辑控件发现当前输入法下的 SendInput 兼容问题，提供 clipboard 方式。此阶段不能标为所有应用验收通过。

# 维护流程（maintenance-flow）

> 安装、升级、受控修复与退出。维护由人直调、预览 + 终端令牌，不以会话绑定授权；
> 变更持久化按 `writer.maintenance_results` 的回执派生。

## required 步骤

### control.asset.apply [required · repeatable]

- 时点：安装/升级应用结束
- enforcement: `wflib/maintenance.py::apply`（第三轮；首轮由 `install.py` 与 `wf-dev-deploy.py` 承担投放）
- 动作：按发行清单投放 `.wf/` 资产与 skill 根，逐路径登记 O/L/N 与决定，完成后自检。
- 出口：偏离/未知文件 → `WF_ASSET_DECISION`；同版异内容 → `WF_RELEASE_CONFLICT`。

### control.repair.apply [required · repeatable]

- 时点：受控修复应用结束
- enforcement: `.wf/bin/repair.py`（自含单文件，不导入 `wflib`）
- 动作：预览 → 令牌 → 同锁重核 → 恢复可证明的写权/绑定/锚点事实 → 回执。
- 出口：记录不可解析 → `WF_RECORD_INVALID`；历史不明 → `WF_HISTORY_UNRESOLVED`。
- 锁对象不可识别时的处置（机制稿 §4.1）：`.wf-lock` 不存在时以**排他创建**方式新建并写入标记；已存在时只有「普通文件、真实落点属于项目根、内容完整等于 `wf-lock-v1\n`」三条同时满足才复用；**空文件或部分标记一律交人核实**，普通入口不认领、不覆写，输出 `WF_CAPABILITY_UNAVAILABLE`（facts 记标记不完整与路径）。人工清理顺序为「确认无 wf 进程 → 删除 `.wf-lock` → 移除 `.gitignore` 中的 `/.wf-lock` 行 → 重新运行入口」，入口会重新排他创建。

### control.uninstall.apply [required · repeatable]

- 时点：卸载应用结束
- enforcement: `.wf/bin/uninstall.py`（自含单文件；`--purge` 单独确认）
- 动作：移除精确登记的资产与托管段，保留数据、安装记录与 `/.wf-lock` 忽略行。
- 出口：writer 损坏时仅在预览范围内退出，不伪造代次；报告锁的人工清理顺序。

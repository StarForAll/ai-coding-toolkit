### 1. Code Quality

<!-- finish-work-projectization-patch -->

不要继续沿用 Trellis 基线里的默认包管理器占位命令。

这里必须改成**当前项目在 `§3 design -> 3.7 技术架构确认后的项目 Spec 对齐` 阶段已经明确的真实自动化检查矩阵**。

进入 `/trellis:finish-work` 前，至少确认：

- [ ] 当前项目已经定义清楚必须通过的真实检查命令（如 lint / type-check / test / build / e2e / migration / packaging 等），并且无论语言如何都明确包含 `sonar-scanner`
- [ ] `finish-work` 正文、项目 `.trellis/spec/` 与 README / 交付说明中的检查矩阵保持一致
- [ ] 默认包管理器占位命令已经删除，不再继续沿用通用模板
- [ ] 如果技术架构尚未确定，先回到 `design` 完成矩阵定义，而不是伪造校验命令
- [ ] 所有“必须通过”的命令都已实际执行，并只记录真实结果：通过 / 失败 / 未运行

```bash
sonar-scanner \
  -Dsonar.projectKey=<target-project-key> \
  -Dsonar.token=$SONAR_TOKEN \
  -Dsonar.host.url=https://sonarqube.xzc.com:13785 \
  -Dsonar.sources=.
```

```text
由当前项目在 design 阶段补充完整检查矩阵；
这里不再保留任何默认包管理器占位，也不允许省略 sonar-scanner。
```

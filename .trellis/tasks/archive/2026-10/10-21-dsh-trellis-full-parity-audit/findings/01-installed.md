# 安装态、版本与接线

证据目录：`/tmp/trellis-dsh-parity-20261021/scenarios/`。所有路径均可在本机复核。

## 1. 基线

| 项 | 值 | 证据 |
| --- | --- | --- |
| DSH | `0.2.1-rc.2` | `s0-installed.txt` |
| Trellis | `0.7.0-beta.4` | `s0-installed.txt` |
| Codex CLI | `0.163.0` | `s0-installed.txt` |
| 插件版本 | `0.1.0` | `s0-installed.txt` |
| web profile 依赖 | `ssh://git@forgejo.xzc.com/xzc/ai-coding-toolkit.git#path:dsh-plugins/dsh-trellis` | `s0-installed.txt` |

## 2. 安装态与源码一致性（E1）

`sha256sum` 三组文件完全一致：

- `lib/index.js`：`ad78d03a…47ae`
- `lib/client.js`：`4f219c22…40a`
- `cordis.patch.yml`：`eac72109…c69`

`lib/client.js` 内 `PLUGIN_VERSION = "0.1.0"`。

结论：**当前实际加载的 host/client/patch 与 `dsh-plugins/dsh-trellis` 工作树一致**，不是旧版本或旧 bundle。

## 3. 版本范围（E2）

用 DSH 自带 semver（`includePrerelease: true`）验证：

- `^0.2.1-alpha.2` 接受 `0.2.1-rc.2`：`true`
- `^0.2.0-rc.1` 接受 `0.2.1-rc.2`：`true`

`package.json` 的 `engines.dsh` 与九个 peer 范围都包含 `^0.2.1-alpha.2`，覆盖当前宿主。

## 4. 插件测试基线（E1）

`pnpm test`：

```
tests 321 / pass 317 / fail 0 / skipped 4
```

证据：`s0b-tests.txt`。4 个 skip 是宿主版本专属用例，不是失败。

## 5. 当前会话加载证据（E1）

- 当前 DSH Web 会话（`http://127.0.0.1:3080`）的系统提示中出现 `Trellis workflow state: in_progress-inline` 与 `<dsh-mode>`，说明 host 半已实际注入。
- 当前会话工具集中存在 `trellis_wait`，说明插件工具已注册。
- `/dsh-trellis/conflicts` 返回 `200`、`status=checked`、`conflicts=[]`。

## 6. 发现：安装说明与实际安装形态不一致（P3，E1）

- `dsh-plugins/dsh-trellis/README.md:124-129` 与 `.trellis/spec/platforms/dsh-workflow-behavior.md` 描述 web profile “软链到本仓库源码”。
- 实际 `~/.dsh/profiles/web/package.json` 的依赖是 **ssh git 依赖**（`#path:dsh-plugins/dsh-trellis`），安装结果是 pnpm 快照，不是 symlink。

影响：直接编辑 `dsh-plugins/dsh-trellis/lib/**` 不会热更新已安装插件；需要重新安装/重启。当前哈希一致只是说明最近一次安装包含了该工作树内容，不代表后续编辑会自动生效。这是文档/维护面漂移，不是当前行为缺陷。

## 7. 发现：上游已到 0.1.13（P3，E1）

设置页版本检查路由实测：

```
GET /dsh-trellis/version-check?source=plugin&url=...
→ release v0.1.13, commit 5108b7f
```

本副本是 `0.1.0`（基于上游 0.1.12 的本地改版，版本号人为重置）。本轮所有结论只覆盖本地 `0.1.0`；未验证上游 0.1.13 的修复/差异。属于维护同步风险，不是本轮安装态缺陷。

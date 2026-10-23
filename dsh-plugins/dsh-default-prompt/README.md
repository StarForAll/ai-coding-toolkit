<div align="center">

# dsh-default-prompt

**DeepSeek Harness 基础默认系统提示词插件**

像 OpenAI Codex 一样，将核心行为规范与基础指令直接注入底层系统提示词（System Prompt），赋予模型最高系统级权威度。

[![Release](https://img.shields.io/github/v/release/new-Beginner/dsh-default-prompt?display_name=tag&sort=semver)](https://github.com/new-Beginner/dsh-default-prompt/releases/latest)
[![License](https://img.shields.io/github/license/new-Beginner/dsh-default-prompt)](LICENSE)
[![Node.js](https://img.shields.io/badge/Node.js-%3E%3D20-339933?logo=node.js&logoColor=white)](package.json)
[![Tests](https://img.shields.io/badge/tests-9%20passed-2ea44f)](VERIFICATION.md)
[![DeepSeek Harness](https://img.shields.io/badge/DeepSeek%20Harness-plugin-4f6ef7)](https://github.com/new-Beginner/dsh-default-prompt)

[核心设计](#why) · [功能特性](#features) · [安装与更新](#installation) · [配置指南](#configuration) · [斜杠指令](#commands) · [质量验证](#quality)

</div>

> [!NOTE]
> 当前稳定版本为 **v1.1.1**。支持全局文件、项目工作区配置、Web 控制台实时预览与一键同步 OpenAI Codex 规则。

> [!IMPORTANT]
> **本目录是 ai-coding-toolkit 内的本地副本**：上游为
> [new-Beginner/dsh-default-prompt](https://github.com/new-Beginner/dsh-default-prompt)，本副本带有
> dsh-purge 联动开关、文本按钮、自定义文件路径等本地改动，不发布 npm。安装态用
> `file:` / 仓库 git 子目录引用（见[方式四](#install-local-repo)）；`dsh plugin update`
> 或 `pnpm install` 覆盖定制改动后，执行
> [`scripts/reapply-local.sh`](scripts/reapply-local.sh) 从本目录还原。

<a id="why"></a>

## 🌟 为什么需要这个插件？

在 DeepSeek Harness 默认机制下，用户的自定义全局规则或 `AGENTS.md` 是通过 `dsh-agent-instructions` 包装在带有 `<system-reminder>` 的 **用户消息（User Role Message）** 中注入对话历史的，并且附带了：
> *"They do not override system, developer, or direct user instructions."*

这会导致大语言模型（尤其是长轮次对话或遵循系统提示词能力极强的模型）**降低对用户全局指令的服从优先级**甚至被模型忽略。

而 **OpenAI Codex** 的标准做法是：将用户的全局/开发者规则（如 `~/.codex/AGENTS.md`、developer instructions）**直接编入最顶层的 System Prompt** 中，紧跟在 Assistant 角色定义之后。

| 对比维度 | DSH 原生 `<system-reminder>` | dsh-default-prompt (Codex 范式) |
| :--- | :--- | :--- |
| **注入层级** | 对话流中的 User 角色消息 | 真实的底层 **System Prompt** |
| **执行权威度** | 次级（受限于 "do not override system"） | **最高系统级权威度**（System Level） |
| **注入位置** | 历史上下文末尾，容易受上下文漂移干扰 | **紧接开场角色定义（order: 10）** 或自定义位置 |
| **Token 消耗** | 即使无规则也会注入空包装 | **零冗余**，未启用或内容为空时自动剔除 |

---

<a id="features"></a>

## ✨ 功能特性

| 提示词注入与权威度 | 灵活来源与现代化控制台 |
| :--- | :--- |
| **🎯 真正的系统级提示词**<br><br>• 通过 `systemPrompt.section` 直接注册到底层系统提示词<br>• 紧随角色定义（`after-persona`，权重 10），比工具说明更靠前<br>• 提供最高系统级指令遵循优先级，彻底解决全局规则被忽视的问题 | **📁 多层次提示词来源**<br><br>• **全局文件**：默认读取 `~/.dsh/DEFAULT_PROMPT.md`，保存即自动热重载<br>• **工作区合并**：自动发现项目根目录 `.dsh/prompt.md` 灵活覆写<br>• **行内编辑**：直接在 Web 面板编写并持久化<br>• **组合模式**：全局 + 项目工作区 + 行内文本无缝组合 |
| **⚡ 零 Token 损耗与轻量响应**<br><br>• 插件停用或提示词为空时完全不产生任何额外 Token<br>• 基于文件修改时间（`mtime`）自动缓存，杜绝重复磁盘 I/O<br>• 纯系统级注入，不破坏聊天历史与会话持久化数据 | **🖥️ 现代化 Web 控制台与 Codex 兼容**<br><br>• DSH 设置面板专属「提示词设置」界面，完美适配亮暗主题<br>• 实时计算最终注入 System Prompt 的内容与字数统计<br>• 自动检测本地 `~/.codex/AGENTS.md`，支持一键同步迁移<br>• 丰富的 `/prompt` 系列斜杠指令 |

---

<a id="installation"></a>

## 📦 安装与更新

### 方式一：使用 DSH 命令行从 GitHub 在线安装（推荐）

通过 DeepSeek Harness 官方插件管理命令一键拉取并安装：

```bash
# 安装到 Web Profile（推荐，包含 Web 设置面板界面）
dsh plugin --profile web add github:new-Beginner/dsh-default-prompt

# 安装到 Desktop Profile
dsh plugin --profile desktop add github:new-Beginner/dsh-default-prompt
```

### 方式二：下载 GitHub Release 安装包（离线安装）

从 [GitHub Releases](https://github.com/new-Beginner/dsh-default-prompt/releases/latest) 下载预打包好的 `.tgz` 归档文件：

```bash
# 下载 Release 安装包后安装
dsh plugin --profile web add ./dsh-default-prompt-1.1.1.tgz
```

> [!TIP]
> 也可以直接使用 Release 直链安装：
> ```bash
> dsh plugin --profile web add https://github.com/new-Beginner/dsh-default-prompt/releases/download/v1.1.1/dsh-default-prompt-1.1.1.tgz
> ```

### 方式三：通过 1024 社区商店安装

在安装了 `dsh-1024store` 插件后，可在 DSH 设置的 **1024 Store** 中直接搜索 `dsh-default-prompt` 点击安装，或使用 CLI：

```bash
npx @dsh-1024store/cli add new-Beginner/dsh-default-prompt --profile web
```

### 方式四：从本仓库本地副本安装

<a id="install-local-repo"></a>

本目录既是本地改动来源，也是唯一的恢复源：

```bash
# 本地开发引用：直接指向本仓库目录
dsh plugin --profile web add file:/home/xzc/projects/personal/ai-coding-toolkit/dsh-plugins/dsh-default-prompt

# 推送到 forgejo 后，可像 dsh-trellis 一样改用仓库 git 子目录引用
dsh plugin --profile web add 'ssh://git@forgejo.xzc.com/xzc/ai-coding-toolkit.git#path:dsh-plugins/dsh-default-prompt'
```

> [!IMPORTANT]
> **安装或更新后请重启 DSH**。DSH 会在重启时重新加载 Cordis 补丁树并生效。初次启动后，插件会自动在 `~/.dsh/DEFAULT_PROMPT.md` 初始化一份高品质默认指令模板。

---

<a id="configuration"></a>

## ⚙️ 配置指南

插件的所有配置均会自动持久化到 `~/.dsh/settings.yaml` 中的 `dsh-default-prompt` 节点下：

### 配置示例

```yaml
dsh-default-prompt:
  enabled: true
  position: 'after-persona'
  customOrder: 10
  sourceMode: 'file'
  filePath: ''
  promptText: ''
  enableWorkspaceFile: true
  syncCodex: false
  sectionTitle: ''
```

### 配置项详细说明

| 配置项 | 默认值 | 可选值 | 说明 |
| :--- | :--- | :--- | :--- |
| `enabled` | `true` | `true` / `false` | 全局开关：是否向底层系统提示词注入默认指令 |
| `position` | `'after-persona'` | `after-persona`<br>`before-tools`<br>`after-tools`<br>`end`<br>`custom` | **注入位置**：<br>• `after-persona` (权重 10)：紧随角色定义之后（推荐，像 Codex）<br>• `before-tools` (权重 950)：所有工具说明之前<br>• `after-tools` (权重 9950)：工具说明之后、上下文之前<br>• `end` (权重 10300)：完整 System Prompt 最末尾<br>• `custom`：使用 `customOrder` 自定义权重 |
| `customOrder` | `10` | 任意整数 | 仅当 `position` 设为 `custom` 时的排序权重 |
| `sourceMode` | `'file'` | `file` / `inline` / `combine` | 提示词来源：`file`（文件）、`inline`（行内文本）、`combine`（自动合并） |
| `filePath` | `''` | 任意有效文件路径 | 自定义提示词文件路径（留空默认使用 `~/.dsh/DEFAULT_PROMPT.md`） |
| `promptText` | `''` | 任意文本 | 行内编辑的提示词内容（在 Web 设置界面可直接输入并保存） |
| `enableWorkspaceFile` | `true` | `true` / `false` | 是否自动检查当前项目工作区根目录下的 `.dsh/prompt.md` 或 `PROMPT.md` 并智能叠加 |
| `syncCodex` | `false` | `true` / `false` | 当默认文件不存在时，是否自动回退读取本机的 `~/.codex/AGENTS.md` |
| `sectionTitle` | `''` | 任意字符串 | 可选的前置二级 Markdown 标题包裹（如 `基础默认规则`） |

---

<a id="commands"></a>

## 💬 斜杠指令支持

在聊天输入框中输入以下指令即可快速管理提示词：

| 指令 | 说明 |
| :--- | :--- |
| `/prompt` 或 `/prompt status` | 查看当前提示词的激活状态、来源模式与生效内容预览 |
| `/prompt reload` | 强制刷新磁盘文件缓存，即刻重新读取最新内容 |
| `/prompt path` | 显示全局与项目工作区提示词文件的绝对物理路径及存在状态 |
| `/prompt import-codex` | 一键检测并将本地 `~/.codex/AGENTS.md` 规则导入到当前配置中 |

---

<a id="quality"></a>

## 🛡️ 质量验证与测试

本项目遵循严谨的测试驱动与向后兼容设计，完整覆盖核心调度、生命周期管理与 Web 端点：

```bash
# 运行单元测试
npm test
```

测试覆盖矩阵：
- ✅ **Plugin Lifecycle**：验证在 Cordis 容器中正确注册 `systemPrompt.section` 与设置服务
- ✅ **Order Resolution**：验证 5 种位置模式与自定义权重的排序映射
- ✅ **Home Expansion**：验证跨平台路径 `~` 自动展开
- ✅ **PromptManager**：涵盖行内模式、全局文件缓存机制、多源合并模式及标题包裹
- ✅ **Web API**：验证状态获取、实时保存与 Codex 导入端点

详细测试报告可查阅 [VERIFICATION.md](VERIFICATION.md)。

---

## 🛠️ 项目目录结构

```text
dsh-default-prompt/
├── package.json          # 模块规范、ESM 配置与 DSH bundle 声明
├── cordis.patch.yml      # Cordis 宿主层与 Web 层自动挂载补丁契约
├── index.js              # 宿主核心：注册 systemPrompt.section、设置与 /prompt 指令
├── client.js             # 客户端界面：DSH Settings 可视化配置与实时预览卡片
├── src/
│   ├── config.js         # Schemastery Schema、位置权重与默认模板定义
│   ├── promptManager.js  # 提示词读取、多来源组合、mtime 缓存与 Codex 导入
│   └── web.js            # 后端 HTTP API (/api/dsh-default-prompt) 路由
├── test/
│   ├── promptManager.test.js # 提示词管理器单元测试
│   ├── plugin.test.js        # 插件生命周期与注入测试
│   ├── web.test.js           # Web API 接口测试
│   └── run.js                # 统一轻量测试执行入口
├── VERIFICATION.md       # 自动化验证报告
└── README.md             # 用户与开发者使用指南
```

---

## 📄 开源许可证

[MIT License](LICENSE) © 2026 new-Beginner

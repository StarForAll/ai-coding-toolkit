import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { DEFAULT_PROMPT_TEMPLATE, resolveOrder } from './config.js';

/**
 * 路径展开辅助函数：支持 ~ 展开为用户家目录
 */
export function expandHome(filePath) {
  if (!filePath || typeof filePath !== 'string') return '';
  const trimmed = filePath.trim();
  if (trimmed === '~' || trimmed.startsWith('~/') || trimmed.startsWith('~\\')) {
    return path.join(os.homedir(), trimmed.slice(1));
  }
  return path.resolve(trimmed);
}

/**
 * 查找用户全局默认提示词路径：~/.dsh/DEFAULT_PROMPT.md
 */
export function getDefaultPromptPath() {
  return path.join(os.homedir(), '.dsh', 'DEFAULT_PROMPT.md');
}

/**
 * 解析应当用来查找工作区专用提示词的项目目录。
 *
 * agent 循环传入的是普通对象 `{ agent, scope }`；而设置页把 cordis 上下文直接
 * 传进来，此时读取未在 `inject` 中声明的 `context.agent` 会抛
 * `cannot get property "agent" without inject`。因此先按普通对象探测（包在
 * try/catch 里），失败再从服务注册表用 `ctx.get()`（不抛错）取 agent：优先
 * 当前 initiator，其次最近注册的顶层 agent（HTTP 请求处理期间通常没有
 * initiator 边界），最后才退回 process.cwd()。
 */
export function resolveWorkspaceCwd(context) {
  if (context && typeof context === 'object') {
    try {
      const cwd = context.agent?.session?.header?.cwd;
      if (typeof cwd === 'string' && cwd) return cwd;
    } catch {}
    try {
      const agents = context.get?.('agents');
      const agent = agents?.currentInitiator?.()
        ?? agents?.roots?.().at(-1)
        ?? agents?.list?.().at(-1);
      const cwd = agent?.session?.header?.cwd;
      if (typeof cwd === 'string' && cwd) return cwd;
    } catch {}
  }
  return process.cwd();
}

export class PromptManager {
  constructor(getConfig, logger) {
    this.getConfig = getConfig;
    this.logger = logger || console;
    this.fileCache = new Map(); // path -> { mtime: number, content: string }
  }

  /**
   * 清除文件读取缓存
   */
  invalidateCache() {
    this.fileCache.clear();
  }

  /**
   * 安全读取 UTF-8 文本文件（带 mtime 缓存）
   */
  readFileWithCache(targetPath) {
    if (!targetPath) return '';
    try {
      if (!fs.existsSync(targetPath)) return '';
      const stat = fs.statSync(targetPath);
      if (!stat.isFile()) return '';

      const cached = this.fileCache.get(targetPath);
      if (cached && cached.mtime === stat.mtimeMs) {
        return cached.content;
      }

      const content = fs.readFileSync(targetPath, 'utf8');
      this.fileCache.set(targetPath, { mtime: stat.mtimeMs, content });
      return content;
    } catch (err) {
      this.logger.warn?.(`[dsh-default-prompt] 读取文件失败 ${targetPath}: ${err.message}`);
      return '';
    }
  }

  /**
   * 确保默认提示词文件存在。
   *
   * 只有默认路径（~/.dsh/DEFAULT_PROMPT.md）会被自动初始化；自定义路径不猜内容，
   * 由用户在面板的内容编辑器里保存生成。
   */
  ensureDefaultPromptFile(filePath) {
    const target = expandHome(filePath) || getDefaultPromptPath();
    try {
      if (fs.existsSync(target)) return target;

      // 如果是默认路径，写入初始模板
      if (target === getDefaultPromptPath()) {
        fs.mkdirSync(path.dirname(target), { recursive: true });
        fs.writeFileSync(target, DEFAULT_PROMPT_TEMPLATE, 'utf8');
        this.logger.info?.(`[dsh-default-prompt] 已创建初始默认提示词文件: ${target}`);
      }
    } catch (err) {
      this.logger.warn?.(`[dsh-default-prompt] 自动创建提示词文件失败: ${err.message}`);
    }
    return target;
  }

  /**
   * 检查并发现当前工作区内的专用提示词文件
   */
  findWorkspacePrompt(cwd) {
    if (!cwd || typeof cwd !== 'string') return null;
    const candidates = [
      path.join(cwd, '.dsh', 'prompt.md'),
      path.join(cwd, '.dsh', 'PROMPT.md'),
      path.join(cwd, 'PROMPT.md')
    ];
    for (const candidate of candidates) {
      if (fs.existsSync(candidate)) {
        return candidate;
      }
    }
    return null;
  }

  /**
   * 组装完整的默认提示词内容
   */
  assemblePrompt(context = {}) {
    const config = this.getConfig();
    if (!config.enabled) {
      return '';
    }

    const mode = config.sourceMode || 'file';
    let globalContent = '';
    let workspaceContent = '';
    const inlineContent = (config.promptText || '').trim();

    // 1. 读取全局文件
    if (mode === 'file' || mode === 'combine') {
      const resolvedPath = this.ensureDefaultPromptFile(config.filePath);
      globalContent = this.readFileWithCache(resolvedPath).trim();
    }

    // 2. 读取工作区项目特定提示词 (如果启用)
    if (config.enableWorkspaceFile && (mode === 'file' || mode === 'combine')) {
      const cwd = resolveWorkspaceCwd(context);
      const wsFile = this.findWorkspacePrompt(cwd);
      if (wsFile) {
        workspaceContent = this.readFileWithCache(wsFile).trim();
      }
    }

    // 3. 根据模式合并内容
    const parts = [];
    if (mode === 'file') {
      if (globalContent) parts.push(globalContent);
      if (workspaceContent) {
        parts.push(`<!-- Workspace Specific Prompt -->\n${workspaceContent}`);
      }
    } else if (mode === 'inline') {
      if (inlineContent) parts.push(inlineContent);
    } else if (mode === 'combine') {
      if (globalContent) parts.push(globalContent);
      if (workspaceContent) {
        parts.push(`<!-- Workspace Specific Prompt -->\n${workspaceContent}`);
      }
      if (inlineContent) parts.push(inlineContent);
    }

    // 4. 按顺序拼接，空内容整体返回空串（不产生任何额外 token）
    return parts.filter(Boolean).join('\n\n');
  }

  /**
   * 获取当前状态摘要（用于 UI 与 /prompt 命令诊断）
   */
  getStatus(context = {}) {
    const config = this.getConfig();
    const resolvedPath = expandHome(config.filePath) || getDefaultPromptPath();
    const fileExists = fs.existsSync(resolvedPath);

    const cwd = resolveWorkspaceCwd(context);
    const workspaceFile = config.enableWorkspaceFile ? this.findWorkspacePrompt(cwd) : null;
    const prompt = this.assemblePrompt(context);
    const order = resolveOrder(config.position, config.customOrder);

    return {
      enabled: !!config.enabled,
      position: config.position || 'after-persona',
      order,
      sourceMode: config.sourceMode || 'file',
      filePath: config.filePath || '~/.dsh/DEFAULT_PROMPT.md',
      resolvedFilePath: resolvedPath,
      fileExists,
      workspaceFile,
      activePrompt: prompt,
      charCount: prompt.length,
      lineCount: prompt ? prompt.split('\n').length : 0
    };
  }
}

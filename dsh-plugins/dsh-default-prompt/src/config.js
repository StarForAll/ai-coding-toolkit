import z from '@deepseek-ai/schemastery';

/**
 * 提示词注入位置与对应的数值权重顺序
 *
 * DSH 内置提示词段权重参考:
 * - HARNESS_IDENTITY: -1000 ("You are an AI agent powered by DeepSeek Harness.")
 * - DEPLOYMENT_PERSONA_PREFIX: 0 ("You are a coding agent powered by ...")
 * - FILE_REFERENCE: 900 ("Tokens prefixed with @ ...")
 * - TOOL_BASH / TOOL_FS: 1000 ~ 5000 (各种工具描述)
 * - STRUCTURED_OUTPUT: 9900
 * - HARNESS_SOURCE: 10000
 * - WEB_SURFACE: 10100
 * - DEPLOYMENT_PERSONA_SUFFIX: 10200 ("Your working directory is ...")
 */
export const POSITION_ORDERS = Object.freeze({
  'after-persona': 10,     // 紧跟角色身份（像 Codex），首选推荐
  'before-tools': 950,      // 工具说明之前
  'after-tools': 9950,      // 工具说明之后，环境信息之前
  'end': 10300              // 整个系统提示词末尾
});

export const DEFAULT_PROMPT_TEMPLATE = `# 基础指令 (Default Instructions)

- 请使用中文进行交流和解答。
- 遇到需求不明确或存在多种实现路径时，主动提供合理选项供用户选择，并在用户确认后再执行关键变更。
- 优先检索并复用本地现有的可用技能（Skills）与项目规范。
- 编写代码时遵循工程最佳实践，遵循最小变更原则，避免过度修改无关逻辑。
`;

export function resolveOrder(position, customOrder) {
  if (position === 'custom') {
    const num = Number(customOrder);
    return Number.isFinite(num) ? num : 10;
  }
  return POSITION_ORDERS[position] ?? 10;
}

export const SettingsSchema = z.object({
  enabled: z.boolean().default(true).description('是否启用基础默认系统提示词注入'),
  position: z.union([
    'after-persona',
    'before-tools',
    'after-tools',
    'end',
    'custom'
  ]).default('after-persona').description('注入位置：紧跟身份(after-persona)、工具前(before-tools)、工具后(after-tools)、末尾(end)、自定义(custom)'),
  customOrder: z.number().default(10).description('自定义数值顺序（仅在 position 为 custom 时生效）'),
  sourceMode: z.union([
    'file',
    'inline',
    'combine'
  ]).default('file').description('提示词来源模式：file（外部文件）、inline（下方文本）、combine（文件+工作区+文本组合）'),
  filePath: z.string().default('').description('提示词文件路径（留空使用 ~/.dsh/DEFAULT_PROMPT.md，支持 ~ 开头；可在设置面板直接修改）'),
  promptText: z.string().default('').description('直接填写的提示词内容（inline 或 combine 模式下生效）'),
  enableWorkspaceFile: z.boolean().default(true).description('是否允许从项目工作区读取 .dsh/prompt.md 或 PROMPT.md 并合并'),
  autoDisableOnPurge: z.boolean().default(false).description('dsh-purge 插件启动时是否自动关闭本插件的提示词注入（仅本进程内存生效，不写回配置）')
});

/**
 * Read an optional service without tripping cordis' inject guard.
 *
 * On a cordis context, reading a service the plugin did not declare throws
 * `cannot get property "<name>" without inject` instead of returning undefined,
 * so a plain `ctx.someOptionalService` cannot be feature-detected. `ctx.get()`
 * reads the registry and never throws for an absent service. Plain-object
 * contexts (unit tests, non-cordis hosts) keep exposing services as properties.
 */
export function optionalService(ctx, name) {
  if (typeof ctx?.get === 'function') {
    try {
      return ctx.get(name);
    } catch {
      return undefined;
    }
  }
  return ctx?.[name];
}

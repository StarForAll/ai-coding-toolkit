import { SettingsSchema, resolveOrder, optionalService } from './src/config.js';
import { PromptManager, getDefaultPromptPath } from './src/promptManager.js';

export { SettingsSchema } from './src/config.js';
export { PromptManager } from './src/promptManager.js';

export const name = 'dsh-default-prompt';
export const inject = ['systemPrompt', 'settings'];

/**
 * Keys the settings page may patch. Only these are written back to the profile
 * config, so the form can never smuggle derived or unrelated fields into the
 * active profile's plugin configuration.
 */
const SETTINGS_KEYS = Object.keys(SettingsSchema.dict ?? {});

function pickSettings(patch) {
  const picked = {};
  for (const key of SETTINGS_KEYS) {
    if (Object.prototype.hasOwnProperty.call(patch, key)) {
      picked[key] = patch[key];
    }
  }
  return picked;
}

export function apply(ctx, config = {}) {
  // The version of @deepseek-ai/dsh-settings shipping with DSH 0.2.0-rc.2 has no
  // `register()` (only configure/describe/update/mutate/replace). Calling it used
  // to raise a swallowed TypeError, which left every settings-page edit a no-op
  // that still answered "saved". Register only when the API is really there.
  let settingsScope;
  if (typeof ctx.settings?.register === 'function') {
    try {
      settingsScope = ctx.settings.register('dsh-default-prompt', SettingsSchema, {
        base: config
      });
    } catch (err) {
      ctx.logger.warn?.(`[dsh-default-prompt] 注册设置项失败: ${err.message}`);
    }
  }

  let effectiveConfig = config;
  const getConfig = () => (settingsScope ? settingsScope.get() : effectiveConfig);

  // 2. 初始化提示词管理器
  const promptManager = new PromptManager(getConfig, ctx.logger);

  // 2b. 与 dsh-purge 的互斥开关（autoDisableOnPurge）
  //
  // dsh-purge 装载后会整体改写系统提示词，此时本插件注入的默认指令是多余甚至冲突的。
  // 关闭动作只改内存（本 DSH 版本 `ctx.settings.register` 不存在，getConfig() 读的就是
  // 这份 effectiveConfig），不写 profile、不触发 Loader 重载，因此不存在「在自己的
  // apply 栈里重启自己」的时序问题。
  //
  // 判定依据是 Loader 条目而不是 globalThis.__dshPurge* 标记：purge 从不清理那些标记，
  // 它们只能证明「本进程 apply 过」，不能证明「现在仍然启用」。
  let autoDisabledByPurge = false;
  let purgeCheckTimer = null;

  const isPurgeEntry = (entry) => {
    const entryName = entry?.options?.name;
    if (typeof entryName === 'string' && entryName.split('/')[0] === 'dsh-purge') return true;
    return entry?.options?.id === 'dsh-purge';
  };

  function isPurgeActive() {
    const loader = optionalService(ctx, 'loader');
    if (typeof loader?.entries !== 'function') return false;
    try {
      for (const entry of loader.entries()) {
        if (!isPurgeEntry(entry)) continue;
        if (entry.disabled) continue;
        const fiber = entry.fiber;
        if (!fiber || fiber.uid === null || fiber.state !== 2) continue;
        if (fiber.config?.enabled === false) continue;
        return true;
      }
    } catch (err) {
      ctx.logger?.warn?.(`[dsh-default-prompt] 检测 dsh-purge 失败: ${err.message}`);
    }
    return false;
  }

  // 开关打开且 purge 活跃时，本插件的注入一律关闭。这条与手动开关无关：即便配置里
  // enabled 为 true（例如手工改了 profile 又被热重载），也不会注入。
  function isPurgeBlocking() {
    try {
      if (!getConfig().autoDisableOnPurge) return false;
      return isPurgeActive();
    } catch (err) {
      ctx.logger?.warn?.(`[dsh-default-prompt] dsh-purge 互斥判定失败: ${err.message}`);
      return false;
    }
  }

  // 把「被 purge 关掉」落到内存配置上，让状态栏与设置面板看到的是真实状态。
  function maybeAutoDisableByPurge() {
    if (autoDisabledByPurge) return false;
    const cfg = getConfig();
    if (!cfg.autoDisableOnPurge || cfg.enabled === false) return false;
    if (!isPurgeActive()) return false;
    autoDisabledByPurge = true;
    effectiveConfig = { ...effectiveConfig, enabled: false };
    promptManager.invalidateCache();
    ctx.emit('system-prompt/change');
    ctx.logger?.info?.('[dsh-default-prompt] 检测到 dsh-purge 已启用，已自动关闭默认提示词注入（仅本进程内存，不写回配置）');
    return true;
  }

  // purge 通常晚于本插件装载，所以判定要挪到当前装载事务之外：既等到稳定的 fiber
  // 状态，也不在别人的 apply 栈里发 system-prompt/change。
  function schedulePurgeCheck() {
    if (autoDisabledByPurge || purgeCheckTimer) return;
    if (!getConfig().autoDisableOnPurge) return;
    purgeCheckTimer = setTimeout(() => {
      purgeCheckTimer = null;
      maybeAutoDisableByPurge();
    }, 60);
    purgeCheckTimer.unref?.();
  }

  // 手动重新打开注入时解除自动关闭标记；purge 正在阻止时走不到这里
  //（persistSettings 会先拒绝），所以不会出现「和用户对着干」的情况。
  function noteManualEnable(picked) {
    if (picked?.enabled === true) autoDisabledByPurge = false;
  }

  ctx.effect(() => {
    const disposeWatch = ctx.on('internal/plugin', () => schedulePurgeCheck());
    return () => {
      if (typeof disposeWatch === 'function') disposeWatch();
      if (purgeCheckTimer) {
        clearTimeout(purgeCheckTimer);
        purgeCheckTimer = null;
      }
    };
  }, 'dsh-default-prompt:purge-watch');

  // 初始启动时确保默认提示词文件存在
  try {
    const cfg = getConfig();
    promptManager.ensureDefaultPromptFile(cfg.filePath);
  } catch {}

  // 3. 动态注册系统提示词段落
  let currentOrder = resolveOrder(getConfig().position, getConfig().customOrder);
  let sectionDisposer = null;

  function mountSection(order) {
    if (typeof sectionDisposer === 'function') {
      sectionDisposer();
      sectionDisposer = null;
    }

    sectionDisposer = ctx.systemPrompt.section({
      name: 'dsh-default-prompt:base',
      order,
      interpolate: false,
      text(context) {
        // 兜底：事件回调漏掉时，下一次组装仍会补做一次判定（判定幂等）。
        schedulePurgeCheck();
        // 硬保证：purge 活跃且开关打开时，配置里写什么都一律不注入。
        if (autoDisabledByPurge || isPurgeBlocking()) return '';
        return promptManager.assemblePrompt(context);
      }
    });
    currentOrder = order;
  }

  mountSection(currentOrder);

  // purge 可能已经先于本插件装载，装载完成后补一次判定。
  schedulePurgeCheck();

  // 4. 监听设置变更，实时同步提示词位置与内容
  if (settingsScope?.watch) {
    ctx.effect(() => settingsScope.watch(() => {
      promptManager.invalidateCache();
      const nextOrder = resolveOrder(getConfig().position, getConfig().customOrder);
      if (nextOrder !== currentOrder) {
        mountSection(nextOrder);
      }
      ctx.emit('system-prompt/change');
    }), 'dsh-default-prompt:settings-watch');
  }

  // 4b. 设置页的持久化写入路径。
  //
  // `settings.register` is gone in this DSH line, so the page's edits have to be
  // persisted through the profile's configuration editor, which validates the
  // complete candidate, keeps YAML comments outside replaced values, and
  // reconciles the loader. `null` means "this runtime cannot persist edits", and
  // the web layer reports that instead of pretending the write succeeded.
  async function persistSettings(patch) {
    const picked = pickSettings(patch || {});
    if (Object.keys(picked).length === 0) {
      return { persisted: true, changed: false, config: { ...effectiveConfig } };
    }

    // 互斥硬保证：purge 启用期间（且开关打开）不允许打开本插件的注入，
    // 连配置文件都不写，避免「写进去又被压制」的假成功。
    if (picked.enabled === true && isPurgeBlocking()) {
      return {
        persisted: false,
        changed: false,
        blocked: true,
        reason: 'dsh-purge 插件在启用状态，不能启用当前 dsh-default-prompt 插件',
        config: { ...getConfig() }
      };
    }

    if (settingsScope?.update) {
      await settingsScope.update(picked);
      promptManager.invalidateCache();
      effectiveConfig = { ...effectiveConfig, ...picked };
      noteManualEnable(picked);
      ctx.emit('system-prompt/change');
      return { persisted: true, changed: true, config: { ...getConfig() } };
    }

    // `ctx.configEditor` would throw ("without inject") because this plugin does
    // not declare the service; `ctx.get` reads the registry and returns undefined
    // when the profile has no config editor.
    const configEditor = optionalService(ctx, 'configEditor');
    if (!configEditor) {
      return { persisted: false, changed: false, config: { ...effectiveConfig } };
    }

    // Address the entry the way the profile patch does. Inside the profile's
    // include subtree the Loader path-qualifies `entry.id`
    // ("include:dsh-default-prompt"), while patches — and therefore
    // `configEditor.edit()` — key on the bare `entry.options.id`, which is also
    // what dsh-settings writes through. Matching only `entry.id` never hit, so
    // every save came back as "no persistence channel" and the settings page
    // could not enable or disable injection.
    const candidates = configEditor.entries();
    const entry = candidates.find((item) => item.options?.id === name)
      ?? candidates.find((item) => item.id === name);
    if (!entry) {
      return { persisted: false, changed: false, config: { ...effectiveConfig } };
    }

    // Apply through the loader, so the plugin restarts with the new config and the
    // next request picks the fresh values up. A failed edit rejects here and the
    // caller must report it as a failure.
    await configEditor.edit(entry, (current) => ({ ...current, ...picked }));
    promptManager.invalidateCache();
    effectiveConfig = { ...effectiveConfig, ...picked };
    noteManualEnable(picked);
    // Same invalidation the settingsScope branch performs: without it the saved
    // value can sit in the config while the assembled system prompt keeps the old
    // text until the next unrelated rebuild.
    ctx.emit('system-prompt/change');
    return { persisted: true, changed: true, config: { ...effectiveConfig } };
  }

  // 5. 暴露对外服务供 Web 模块与其它插件调用
  const service = {
    promptManager,
    settingsScope,
    getConfig,
    persistSettings,
    isPurgeEnabled: () => isPurgeActive(),
    isPurgeBlocking: () => isPurgeBlocking(),
    isAutoDisabledByPurge: () => autoDisabledByPurge,
    reload() {
      promptManager.invalidateCache();
      ctx.emit('system-prompt/change');
    }
  };
  ctx.provide('defaultPromptService', service);

  // 6. 可选注册 /prompt 指令
  ctx.inject(['commands'], (cmdCtx) => {
    cmdCtx.commands.register({
      name: 'prompt',
      description: '查看或管理基础默认系统提示词 (像 Codex 一样注入)',
      input: { hint: 'status | reload | path | help' },
      recordInput: false,
      async handler({ rawInput }) {
        const [subcmd = 'status'] = rawInput.trim().split(/\s+/).filter(Boolean);

        if (subcmd === 'reload') {
          service.reload();
          return {
            kind: 'success',
            text: '✅ 基础默认提示词缓存已刷新，下一次请求将重新读取文件与配置。'
          };
        }

        if (subcmd === 'path') {
          const status = promptManager.getStatus();
          return {
            kind: 'success',
            text: [
              `📄 **默认提示词文件路径**: \`${status.resolvedFilePath}\``,
              `状态: ${status.fileExists ? '🟢 存在' : '🔴 不存在'}`
            ].join('\n')
          };
        }

        if (subcmd === 'help') {
          return {
            kind: 'success',
            text: [
              '### 基础默认系统提示词 (/prompt) 指令帮助',
              '- `/prompt` 或 `/prompt status`：查看当前提示词状态与注入预览',
              '- `/prompt reload`：重新读取提示词文件并刷新缓存',
              '- `/prompt path`：查看提示词文件路径与存在状态',
              '- `/prompt help`：显示此帮助信息'
            ].join('\n')
          };
        }

        // 默认显示 status
        const status = promptManager.getStatus();
        const lines = [
          '### 🧠 基础默认系统提示词状态 (dsh-default-prompt)',
          `- **启用状态**: ${status.enabled ? '🟢 已启用' : '🔴 已禁用'}`,
          `- **注入位置**: \`${status.position}\` (权重 Order: ${status.order})`,
          `- **来源模式**: \`${status.sourceMode}\``,
          `- **文件路径**: \`${status.resolvedFilePath}\` (${status.fileExists ? '存在' : '缺失'})`,
          status.workspaceFile ? `- **工作区专用文件**: \`${status.workspaceFile}\`` : '',
          `- **当前字数**: ${status.charCount} 字符 (${status.lineCount} 行)`,
          '',
          '**当前生效的注入内容预览:**',
          status.activePrompt ? '```markdown\n' + status.activePrompt + '\n```' : '*(当前内容为空)*'
        ].filter(Boolean);

        return {
          kind: 'success',
          text: lines.join('\n')
        };
      }
    });
  });

  // 7. 卸载清理
  ctx.on('dispose', () => {
    if (typeof sectionDisposer === 'function') {
      sectionDisposer();
      sectionDisposer = null;
    }
  });
}

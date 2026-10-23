import fs from 'node:fs';
import path from 'node:path';
import { expandHome, getDefaultPromptPath } from './promptManager.js';
import { DEFAULT_PROMPT_TEMPLATE, SettingsSchema, optionalService } from './config.js';

export const name = 'dsh-default-prompt-web';
export const inject = ['connection', 'defaultPromptService'];

/**
 * Config keys the settings page may patch. Only these travel from the wire into
 * the profile configuration, so a client cannot write arbitrary fields.
 */
export const SETTINGS_KEYS = Object.freeze(Object.keys(SettingsSchema.dict ?? {}));

/**
 * Path-valued settings must be strings before they reach `expandHome`, which
 * would otherwise coerce a non-string body into an unrelated path.
 */
function pickPatch(patch) {
  if (!patch || typeof patch !== 'object') return {};
  const picked = {};
  for (const key of SETTINGS_KEYS) {
    if (Object.prototype.hasOwnProperty.call(patch, key)) {
      picked[key] = patch[key];
    }
  }
  if (Object.prototype.hasOwnProperty.call(picked, 'filePath') && typeof picked.filePath !== 'string') {
    delete picked.filePath;
  }
  return picked;
}

export function apply(ctx) {
  const service = ctx.defaultPromptService;
  const reply = (value, status = 200) => new Response(JSON.stringify(value), {
    status,
    headers: { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store' }
  });

  async function buildPayload() {
    const status = service.promptManager.getStatus(ctx);
    const config = service.settingsScope ? service.settingsScope.get() : service.getConfig();

    let fileContent = '';
    if (fs.existsSync(status.resolvedFilePath)) {
      try {
        fileContent = fs.readFileSync(status.resolvedFilePath, 'utf8');
      } catch {}
    }

    return {
      status,
      config,
      purgeEnabled: Boolean(service.isPurgeEnabled?.()),
      purgeBlocked: Boolean(service.isPurgeBlocking?.()),
      autoDisabledByPurge: Boolean(service.isAutoDisabledByPurge?.()),
      fileContent,
      defaultTemplate: DEFAULT_PROMPT_TEMPLATE,
      // False when this runtime has no writable settings path (no
      // `settings.register` and no profile config editor): the page then renders
      // the settings as read-only instead of reporting writes that never happened.
      settingsWritable: Boolean(service.settingsScope?.update || optionalService(ctx, 'configEditor'))
    };
  }

  ctx.connection.fetch.register({
    path: '/api/dsh-default-prompt',
    methods: ['GET', 'POST'],
    requestBody: 'buffered',
    async fetch(request) {
      try {
        if (request.method === 'GET') {
          return reply(await buildPayload());
        }

        if (request.headers.get('content-type')?.split(';')[0] !== 'application/json') {
          return reply({ error: '需要 JSON 请求体' }, 415);
        }

        const data = await request.json();
        const { action } = data;

        if (action === 'saveSettings') {
          const patch = pickPatch(data.patch);
          if (Object.keys(patch).length === 0) {
            return reply({ error: '没有可保存的设置字段' }, 400);
          }

          const result = await service.persistSettings(patch);
          if (result.blocked) {
            return reply({
              error: result.reason || 'dsh-purge 插件在启用状态，不能启用当前 dsh-default-prompt 插件',
              code: 'purge-blocked',
              ...(await buildPayload())
            }, 409);
          }
          if (!result.persisted) {
            return reply({
              error: '当前 DSH 版本没有可用的设置持久化通道（settings.register 与 configEditor 均不可用），改动未保存',
              ...(await buildPayload())
            }, 409);
          }
          // The config edit reconciles the loader, so the client refetches the
          // authoritative values instead of trusting a possibly stale echo.
          return reply({ ok: true, changed: true });
        }

        if (action === 'saveFile') {
          const content = typeof data.content === 'string' ? data.content : '';
          const configured = service.getConfig().filePath;
          const targetPath = expandHome(typeof data.filePath === 'string' ? data.filePath : configured) || getDefaultPromptPath();
          fs.mkdirSync(path.dirname(targetPath), { recursive: true });
          fs.writeFileSync(targetPath, content, 'utf8');
          service.promptManager.invalidateCache();
          ctx.emit('system-prompt/change');
          return reply({ ok: true, targetPath });
        }

        if (action === 'resetFile') {
          const targetPath = getDefaultPromptPath();
          fs.mkdirSync(path.dirname(targetPath), { recursive: true });
          fs.writeFileSync(targetPath, DEFAULT_PROMPT_TEMPLATE, 'utf8');
          service.promptManager.invalidateCache();
          ctx.emit('system-prompt/change');
          return reply({ ok: true, targetPath });
        }

        if (action === 'reload') {
          service.promptManager.invalidateCache();
          ctx.emit('system-prompt/change');
          return reply({ ok: true });
        }

        return reply({ error: `未知操作: ${action}` }, 400);
      } catch (err) {
        return reply({ error: err.message || String(err) }, 500);
      }
    }
  });
}

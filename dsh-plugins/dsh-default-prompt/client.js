window.__ModuleLoader__.load({
  id: 'dsh-default-prompt',
  factory: (require) => {
    const React = require('react');
    const { useState, useEffect, useRef, useCallback } = React;
    const h = React.createElement;

    const ICONS = {
      sparkles: 'M12 3l1.9 4.8L18.7 9.7l-4.8 1.9L12 16.4l-1.9-4.8L5.3 9.7l4.8-1.9L12 3zm7 13l.9 2.3L22.2 19l-2.3.9L19 22.2l-.9-2.3L15.8 19l2.3-.9L19 16zM4.5 16l.6 1.6L6.7 18l-1.6.6L4.5 20.2l-.6-1.6L2.3 18l1.6-.6L4.5 16z',
      check: 'M20 6L9 17l-5-5',
      refresh: 'M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67',
      save: 'M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2zM17 21v-8H7v8M7 3v5h8',
      file: 'M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9zM13 2v7h7',
      download: 'M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4m4-5l5 5 5-5m-5 5V3',
      sliders: 'M4 21v-7m0-4V3m8 18v-9m0-4V3m8 18v-5m0-4V3M1 14h6m2-6h6m2 8h6',
      eye: 'M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8zm11 5a5 5 0 1 0 0-10 5 5 0 0 0 0 10zm0-2a3 3 0 1 1 0-6 3 3 0 0 1 0 6z',
      alert: 'M12 9v4m0 4h.01M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z'
    };

    function Icon({ name, size = 16, style = {} }) {
      const d = ICONS[name] || ICONS.sparkles;
      return h('svg', {
        width: size,
        height: size,
        viewBox: '0 0 24 24',
        fill: 'none',
        stroke: 'currentColor',
        strokeWidth: '2',
        strokeLinecap: 'round',
        strokeLinejoin: 'round',
        style: { display: 'inline-block', verticalAlign: 'middle', flexShrink: 0, ...style }
      }, h('path', { d }));
    }

    let stylesInjected = false;
    function ensureStyles() {
      if (stylesInjected) return;
      stylesInjected = true;
      const css = `
        .dsh-dp-container {
          padding: 20px;
          max-width: 900px;
          margin: 0 auto;
          font-family: inherit;
          color: var(--dsw-alias-label-primary);
        }
        .dsh-dp-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          margin-bottom: 20px;
          padding-bottom: 16px;
          border-bottom: 1px solid var(--dsw-alias-border-l2);
        }
        .dsh-dp-title {
          font-size: 18px;
          font-weight: 600;
          display: flex;
          align-items: center;
          gap: 10px;
        }
        .dsh-dp-card {
          background: var(--dsw-alias-surface-l1, #ffffff);
          border: 1px solid var(--dsw-alias-border-l2);
          border-radius: 8px;
          padding: 16px 20px;
          margin-bottom: 18px;
        }
        .dsh-dp-card-title {
          font-size: 14px;
          font-weight: 600;
          margin-bottom: 14px;
          display: flex;
          align-items: center;
          gap: 8px;
          color: var(--dsw-alias-label-primary);
        }
        .dsh-dp-field {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 10px 0;
          border-bottom: 0.5px solid var(--dsw-alias-border-l3, rgba(255, 255, 255, 0.06));
        }
        .dsh-dp-field:last-child {
          border-bottom: none;
        }
        .dsh-dp-field-info {
          flex: 1;
          margin-right: 20px;
        }
        .dsh-dp-field-label {
          font-size: 13px;
          font-weight: 500;
          color: var(--dsw-alias-label-primary);
        }
        .dsh-dp-field-desc {
          font-size: 12px;
          color: var(--dsw-alias-label-secondary);
          margin-top: 2px;
        }
        .dsh-dp-select, .dsh-dp-input {
          background: var(--dsw-alias-surface-l2, rgba(0,0,0,0.2));
          border: 1px solid var(--dsw-alias-border-l3);
          border-radius: 6px;
          padding: 6px 10px;
          color: var(--dsw-alias-label-primary);
          font-size: 13px;
          outline: none;
        }
        .dsh-dp-select:focus, .dsh-dp-input:focus {
          border-color: var(--dsw-alias-interactive-accent, #1677ff);
        }
        .dsh-dp-btn {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          padding: 6px 14px;
          border-radius: 6px;
          font-size: 13px;
          font-weight: 500;
          cursor: pointer;
          border: 1px solid var(--dsw-alias-border-l3);
          background: var(--dsw-alias-surface-l2, rgba(255,255,255,0.06));
          color: var(--dsw-alias-label-primary);
          transition: all 0.15s ease;
        }
        .dsh-dp-btn:hover:not(:disabled) {
          background: var(--dsw-alias-surface-l3, rgba(255,255,255,0.12));
          border-color: var(--dsw-alias-border-l2);
        }
        .dsh-dp-btn-primary {
          background: var(--dsw-alias-interactive-accent, #1677ff);
          border-color: var(--dsw-alias-interactive-accent, #1677ff);
          color: #fff;
        }
        .dsh-dp-btn-primary:hover:not(:disabled) {
          background: var(--dsw-alias-interactive-accent-hover, #4096ff);
        }
        .dsh-dp-badge {
          display: inline-block;
          padding: 2px 8px;
          border-radius: 12px;
          font-size: 11px;
          font-weight: 500;
        }
        .dsh-dp-badge-green {
          background: rgba(34, 197, 94, 0.15);
          color: #22c55e;
          border: 1px solid rgba(34, 197, 94, 0.3);
        }
        .dsh-dp-badge-red {
          background: rgba(239, 68, 68, 0.15);
          color: #ef4444;
          border: 1px solid rgba(239, 68, 68, 0.3);
        }
        .dsh-dp-textarea {
          width: 100%;
          min-height: 240px;
          background: var(--dsw-alias-surface-l2, #f6f7f9);
          border: 1px solid var(--dsw-alias-border-l3);
          border-radius: 6px;
          padding: 12px;
          font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
          font-size: 12px;
          line-height: 1.5;
          color: var(--dsw-alias-label-primary);
          resize: vertical;
          box-sizing: border-box;
          outline: none;
        }
        .dsh-dp-textarea:focus {
          border-color: var(--dsw-alias-interactive-accent, #1677ff);
        }
        .dsh-dp-tabs {
          display: flex;
          gap: 6px;
          margin-bottom: 12px;
          border-bottom: 1px solid var(--dsw-alias-border-l3);
          padding-bottom: 8px;
        }
        .dsh-dp-tab-item {
          padding: 6px 12px;
          border-radius: 6px;
          font-size: 13px;
          cursor: pointer;
          color: var(--dsw-alias-label-secondary);
          transition: all 0.15s ease;
        }
        .dsh-dp-tab-item:hover {
          color: var(--dsw-alias-label-primary);
          background: var(--dsw-alias-surface-l2);
        }
        .dsh-dp-tab-item.active {
          color: var(--dsw-alias-label-primary);
          font-weight: 600;
          background: var(--dsw-alias-surface-l3, rgba(255,255,255,0.08));
        }
        .dsh-dp-toast {
          padding: 8px 12px;
          border-radius: 6px;
          font-size: 12px;
          margin-bottom: 14px;
          display: flex;
          align-items: center;
          gap: 8px;
        }
        .dsh-dp-toast-success {
          background: rgba(34, 197, 94, 0.12);
          color: #22c55e;
          border: 1px solid rgba(34, 197, 94, 0.25);
        }
        .dsh-dp-toast-error {
          background: rgba(239, 68, 68, 0.12);
          color: #ef4444;
          border: 1px solid rgba(239, 68, 68, 0.25);
        }

        /* Harness-native narrow settings layout (calibrated to ~560px content width). */
        .dsh-dp-container {
          width: 100%;
          max-width: 600px;
          padding: 24px 18px 36px;
          box-sizing: border-box;
        }
        .dsh-dp-header {
          align-items: stretch;
          flex-direction: column;
          gap: 14px;
          margin-bottom: 16px;
          padding-bottom: 0;
          border-bottom: none;
        }
        .dsh-dp-header-main {
          display: flex;
          align-items: flex-start;
          gap: 12px;
          min-width: 0;
        }
        .dsh-dp-title-icon {
          width: 34px;
          height: 34px;
          display: inline-flex;
          align-items: center;
          justify-content: center;
          flex: 0 0 auto;
          color: var(--dsw-alias-interactive-accent, #1677ff);
          background: color-mix(in srgb, var(--dsw-alias-interactive-accent, #1677ff) 9%, transparent);
          border: 1px solid color-mix(in srgb, var(--dsw-alias-interactive-accent, #1677ff) 18%, transparent);
          border-radius: 9px;
        }
        .dsh-dp-title {
          display: block;
          font-size: 20px;
          font-weight: 650;
          line-height: 1.35;
          letter-spacing: -0.01em;
        }
        .dsh-dp-subtitle {
          margin-top: 5px;
          color: var(--dsw-alias-label-secondary);
          font-size: 12px;
          line-height: 1.6;
        }
        .dsh-dp-header-actions {
          display: flex;
          justify-content: flex-end;
          flex-wrap: wrap;
          gap: 8px;
        }
        .dsh-dp-status-grid {
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          margin-bottom: 16px;
          overflow: hidden;
          background: var(--dsw-alias-surface-l1, #fff);
          border: 1px solid var(--dsw-alias-border-l3, rgba(0, 0, 0, 0.08));
          border-radius: 10px;
        }
        .dsh-dp-status-item {
          min-width: 0;
          padding: 12px 14px;
          border-right: 1px solid var(--dsw-alias-border-l3, rgba(0, 0, 0, 0.08));
        }
        .dsh-dp-status-item:nth-child(even) { border-right: none; }
        .dsh-dp-status-item:nth-child(-n + 2) {
          border-bottom: 1px solid var(--dsw-alias-border-l3, rgba(0, 0, 0, 0.08));
        }
        .dsh-dp-status-label {
          display: block;
          margin-bottom: 5px;
          color: var(--dsw-alias-label-secondary);
          font-size: 11px;
          line-height: 1.35;
        }
        .dsh-dp-status-value {
          display: flex;
          align-items: center;
          gap: 8px;
          min-width: 0;
          color: var(--dsw-alias-label-primary);
          font-size: 12px;
          font-weight: 600;
        }
        .dsh-dp-status-value code {
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
          font: 500 11px/1.35 ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
        }
        .dsh-dp-status-dot {
          width: 7px;
          height: 7px;
          flex: 0 0 auto;
          border-radius: 50%;
          background: #22c55e;
          box-shadow: 0 0 0 3px rgba(34, 197, 94, 0.12);
        }
        .dsh-dp-status-dot.off {
          background: #ef4444;
          box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.12);
        }
        .dsh-dp-card {
          padding: 18px 20px;
          margin-bottom: 16px;
          border-color: var(--dsw-alias-border-l3, rgba(0, 0, 0, 0.08));
          border-radius: 11px;
        }
        .dsh-dp-card-title {
          margin-bottom: 4px;
          font-size: 14px;
          font-weight: 650;
        }
        .dsh-dp-card-desc {
          margin-bottom: 8px;
          color: var(--dsw-alias-label-secondary);
          font-size: 12px;
          line-height: 1.55;
        }
        .dsh-dp-field {
          align-items: stretch;
          flex-direction: column;
          gap: 10px;
          padding: 16px 0;
        }
        .dsh-dp-field-info {
          margin-right: 0;
        }
        .dsh-dp-field-label {
          font-weight: 600;
        }
        .dsh-dp-field-desc {
          margin-top: 4px;
          line-height: 1.55;
        }
        .dsh-dp-select,
        .dsh-dp-input {
          width: 100%;
          min-height: 38px;
          padding: 7px 11px;
          border-color: var(--dsw-alias-border-l2);
          border-radius: 8px;
          box-sizing: border-box;
          font-family: inherit;
        }
        .dsh-dp-source-mode {
          display: grid;
          grid-template-columns: repeat(3, minmax(0, 1fr));
          gap: 3px;
          padding: 3px;
          background: var(--dsw-alias-surface-l2, rgba(0, 0, 0, 0.04));
          border: 1px solid var(--dsw-alias-border-l3, rgba(0, 0, 0, 0.08));
          border-radius: 9px;
        }
        .dsh-dp-source-mode-item {
          min-width: 0;
          min-height: 32px;
          padding: 5px 8px;
          overflow: hidden;
          border: none;
          border-radius: 6px;
          background: transparent;
          color: var(--dsw-alias-label-secondary);
          font-family: inherit;
          font-size: 12px;
          text-overflow: ellipsis;
          white-space: nowrap;
          cursor: pointer;
        }
        .dsh-dp-source-mode-item.active {
          background: var(--dsw-alias-surface-l1, #fff);
          color: var(--dsw-alias-label-primary);
          font-weight: 600;
          box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
        }
        .dsh-dp-source-mode-item:focus-visible {
          outline: 2px solid var(--dsw-alias-interactive-accent, #1677ff);
          outline-offset: 1px;
        }
        .dsh-dp-switch-row {
          display: flex;
          align-items: center;
          gap: 10px;
        }
        .dsh-dp-switch-state {
          color: var(--dsw-alias-label-secondary);
          font-size: 11px;
        }
        .dsh-dp-switch {
          position: relative;
          width: 38px;
          height: 22px;
          min-height: 22px;
          margin: 0;
          appearance: none;
          border: 1px solid var(--dsw-alias-border-l2);
          border-radius: 999px;
          background: var(--dsw-alias-surface-l3, rgba(0, 0, 0, 0.08));
          cursor: pointer;
          transition: background-color 0.16s ease, border-color 0.16s ease;
        }
        .dsh-dp-switch::after {
          content: '';
          position: absolute;
          top: 2px;
          left: 2px;
          width: 16px;
          height: 16px;
          border-radius: 50%;
          background: #fff;
          box-shadow: 0 1px 3px rgba(0, 0, 0, 0.24);
          transition: transform 0.16s ease;
        }
        .dsh-dp-switch:checked {
          border-color: var(--dsw-alias-interactive-accent, #1677ff);
          background: var(--dsw-alias-interactive-accent, #1677ff);
        }
        .dsh-dp-switch:checked::after { transform: translateX(16px); }
        .dsh-dp-switch:focus-visible {
          outline: none;
          box-shadow: 0 0 0 3px color-mix(in srgb, var(--dsw-alias-interactive-accent, #1677ff) 18%, transparent);
        }
        .dsh-dp-tabs {
          align-items: center;
          flex-wrap: wrap;
          gap: 4px;
          margin-top: 4px;
          padding-bottom: 10px;
        }
        .dsh-dp-tab-item {
          min-height: 34px;
          border: none;
          background: transparent;
          font-family: inherit;
        }
        .dsh-dp-editor-toolbar {
          display: flex;
          align-items: center;
          justify-content: space-between;
          flex-wrap: wrap;
          gap: 10px 14px;
          margin-bottom: 10px;
        }
        .dsh-dp-path {
          min-width: 0;
          color: var(--dsw-alias-label-secondary);
          font: 11px/1.45 ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
          overflow: hidden;
          text-overflow: ellipsis;
        }
        .dsh-dp-file-state {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          margin-top: 4px;
          color: #16a34a;
          font-family: inherit;
          font-size: 10px;
          font-weight: 600;
        }
        .dsh-dp-toolbar-actions {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
          margin-left: auto;
        }
        .dsh-dp-textarea {
          min-height: 360px;
          padding: 14px;
          border-color: var(--dsw-alias-border-l2);
          border-radius: 9px;
          font-size: 12px;
          line-height: 1.7;
        }
        .dsh-dp-btn {
          min-height: 36px;
          padding: 7px 13px;
          border-radius: 8px;
          font-family: inherit;
        }
        @media (max-width: 520px) {
          .dsh-dp-container { padding-inline: 12px; }
          .dsh-dp-status-grid { grid-template-columns: 1fr; }
          .dsh-dp-status-item { border-right: none; border-bottom: 1px solid var(--dsw-alias-border-l3, rgba(0, 0, 0, 0.08)); }
          .dsh-dp-status-item:last-child { border-bottom: none; }
          .dsh-dp-header-actions,
          .dsh-dp-toolbar-actions { justify-content: flex-start; margin-left: 0; }
        }
      `;
      const styleEl = document.createElement('style');
      styleEl.textContent = css;
      document.head.appendChild(styleEl);
    }

    /**
     * Read the JSON body of an API response and fail loudly on a non-2xx status,
     * carrying the server's error code so a toast can distinguish a policy
     * refusal (dsh-purge blocking an enable) from a generic write failure.
     */
    async function readJson(res) {
      let json = null;
      try {
        json = await res.json();
      } catch {}
      if (!res.ok) {
        const failure = new Error(json && json.error ? json.error : `HTTP ${res.status}`);
        failure.code = json && json.code;
        throw failure;
      }
      if (!json || typeof json !== 'object' || json.error) {
        throw new Error(json && json.error ? json.error : '服务返回了无效响应');
      }
      return json;
    }

    function PromptSettingsView() {
      ensureStyles();

      const [data, setData] = useState(null);
      const [loading, setLoading] = useState(true);
      const [saving, setSaving] = useState(false);
      const [toast, setToast] = useState(null);
      const [activeTab, setActiveTab] = useState('file'); // 'file' | 'inline' | 'preview'
      const [editorContent, setEditorContent] = useState('');
      const [inlinePrompt, setInlinePrompt] = useState('');
      const [filePath, setFilePath] = useState('');

      const showToast = (msg, type = 'success') => {
        setToast({ msg, type });
        setTimeout(() => setToast(null), 3500);
      };

      const fetchStatus = useCallback(async () => {
        try {
          const res = await fetch('/api/dsh-default-prompt', { credentials: 'same-origin' });
          const json = await readJson(res);
          setData(json);
          setEditorContent(json.fileContent || '');
          setInlinePrompt(json.config?.promptText || '');
          setFilePath(json.config?.filePath || '');
        } catch (err) {
          showToast(`获取配置失败: ${err.message}`, 'error');
        } finally {
          setLoading(false);
        }
      }, []);

      useEffect(() => {
        fetchStatus();
      }, [fetchStatus]);

      const handleToggleEnabled = async () => {
        if (!data) return;
        const nextEnabled = !data.config.enabled;
        setSaving(true);
        try {
          const res = await fetch('/api/dsh-default-prompt', {
            method: 'POST',
            headers: { 'content-type': 'application/json' },
            body: JSON.stringify({ action: 'saveSettings', patch: { enabled: nextEnabled } })
          });
          await readJson(res);
          await fetchStatus();
          showToast(nextEnabled ? '已启用默认提示词' : '已禁用默认提示词');
        } catch (err) {
          showToast(err.code === 'purge-blocked' ? err.message : `更新失败: ${err.message}`, 'error');
        } finally {
          setSaving(false);
        }
      };

      const handleSettingChange = async (key, value) => {
        if (!data) return;
        setSaving(true);
        try {
          const res = await fetch('/api/dsh-default-prompt', {
            method: 'POST',
            headers: { 'content-type': 'application/json' },
            body: JSON.stringify({ action: 'saveSettings', patch: { [key]: value } })
          });
          await readJson(res);
          await fetchStatus();
          showToast('设置已更新');
        } catch (err) {
          showToast(err.code === 'purge-blocked' ? err.message : `更新设置失败: ${err.message}`, 'error');
        } finally {
          setSaving(false);
        }
      };

      const handleSaveFile = async () => {
        setSaving(true);
        try {
          const res = await fetch('/api/dsh-default-prompt', {
            method: 'POST',
            headers: { 'content-type': 'application/json' },
            body: JSON.stringify({ action: 'saveFile', content: editorContent })
          });
          await readJson(res);
          await fetchStatus();
          showToast('文件保存成功！已自动更新系统提示词');
        } catch (err) {
          showToast(`保存文件失败: ${err.message}`, 'error');
        } finally {
          setSaving(false);
        }
      };

      const handleSaveInline = async () => {
        setSaving(true);
        try {
          const res = await fetch('/api/dsh-default-prompt', {
            method: 'POST',
            headers: { 'content-type': 'application/json' },
            body: JSON.stringify({ action: 'saveSettings', patch: { promptText: inlinePrompt } })
          });
          await readJson(res);
          await fetchStatus();
          showToast('行内提示词保存成功！');
        } catch (err) {
          showToast(`保存失败: ${err.message}`, 'error');
        } finally {
          setSaving(false);
        }
      };

      const handleReload = async () => {
        setSaving(true);
        try {
          const res = await fetch('/api/dsh-default-prompt', {
            method: 'POST',
            headers: { 'content-type': 'application/json' },
            body: JSON.stringify({ action: 'reload' })
          });
          await readJson(res);
          await fetchStatus();
          showToast('已重新从磁盘读取提示词');
        } catch (err) {
          showToast(`重新加载失败: ${err.message}`, 'error');
        } finally {
          setSaving(false);
        }
      };

      const handleToggleAutoDisableOnPurge = async () => {
        if (!data) return;
        const next = !data.config.autoDisableOnPurge;
        setSaving(true);
        try {
          const res = await fetch('/api/dsh-default-prompt', {
            method: 'POST',
            headers: { 'content-type': 'application/json' },
            body: JSON.stringify({ action: 'saveSettings', patch: { autoDisableOnPurge: next } })
          });
          await readJson(res);
          await fetchStatus();
          showToast(next ? '已开启：dsh-purge 启动时自动关闭本插件' : '已关闭：purge 启动时不再关闭本插件');
        } catch (err) {
          showToast(err.code === 'purge-blocked' ? err.message : `更新失败: ${err.message}`, 'error');
        } finally {
          setSaving(false);
        }
      };

      const handleSaveFilePath = async () => {
        setSaving(true);
        try {
          const res = await fetch('/api/dsh-default-prompt', {
            method: 'POST',
            headers: { 'content-type': 'application/json' },
            body: JSON.stringify({ action: 'saveSettings', patch: { filePath: filePath.trim() } })
          });
          await readJson(res);
          await fetchStatus();
          showToast('提示词文件路径已更新');
        } catch (err) {
          showToast(`保存路径失败: ${err.message}`, 'error');
        } finally {
          setSaving(false);
        }
      };

      if (loading) {
        return h('div', { className: 'dsh-dp-container' }, '正在加载配置...');
      }

      const cfg = data?.config || {};
      const status = data?.status || {};

      return h('div', { className: 'dsh-dp-container' },
        // 标题与操作
        h('div', { className: 'dsh-dp-header' },
          h('div', { className: 'dsh-dp-header-main' },
            h('span', { className: 'dsh-dp-title-icon' },
              h(Icon, { name: 'sparkles', size: 18 })
            ),
            h('div', null,
              h('div', { className: 'dsh-dp-title' }, '基础默认系统提示词'),
              h('div', { className: 'dsh-dp-subtitle' },
                '管理系统级指令的注入顺序与内容来源。保存后将在下一次模型请求时生效。'
              )
            )
          ),
          h('div', { className: 'dsh-dp-header-actions' },
            h('button', {
              className: `dsh-dp-btn ${status.enabled ? '' : 'dsh-dp-btn-primary'}`,
              onClick: handleToggleEnabled,
              disabled: saving
            }, status.enabled ? '禁用注入' : '开启注入'),
            h('button', {
              className: `dsh-dp-btn ${cfg.autoDisableOnPurge ? '' : 'dsh-dp-btn-primary'}`,
              onClick: handleToggleAutoDisableOnPurge,
              disabled: saving,
              title: data?.purgeBlocked
                ? 'dsh-purge 插件在启用状态，不能启用当前 dsh-default-prompt 插件'
                : 'dsh-purge 已启用时自动停止注入默认提示词（仅本次进程内存生效，不写回配置）'
            }, cfg.autoDisableOnPurge ? '取消 purge 自动关闭' : 'purge 时自动关闭本插件'),
            h('button', {
              className: 'dsh-dp-btn',
              onClick: handleReload,
              disabled: saving,
              title: '刷新缓存并重新从磁盘读取'
            },
              h(Icon, { name: 'refresh', size: 14 }),
              '重新加载'
            )
          )
        ),

        // 适配 Harness 设置面板窄宽度的 2×2 状态概览
        h('div', { className: 'dsh-dp-status-grid' },
          h('div', { className: 'dsh-dp-status-item' },
            h('span', { className: 'dsh-dp-status-label' }, '插件状态'),
            h('div', { className: 'dsh-dp-status-value' },
              h('span', { className: `dsh-dp-status-dot ${status.enabled && !data?.purgeBlocked ? '' : 'off'}` }),
              status.enabled && !data?.purgeBlocked
                ? '已启用并正在注入'
                : (data?.purgeBlocked ? 'dsh-purge 启用中，注入已被阻止' : '当前未启用')
            )
          ),
          h('div', { className: 'dsh-dp-status-item' },
            h('span', { className: 'dsh-dp-status-label' }, '注入顺序'),
            h('div', { className: 'dsh-dp-status-value' },
              h('code', null, `Order ${status.order ?? '—'}`)
            )
          ),
          h('div', { className: 'dsh-dp-status-item' },
            h('span', { className: 'dsh-dp-status-label' }, '当前来源'),
            h('div', { className: 'dsh-dp-status-value' },
              h('code', null,
                cfg.sourceMode === 'combine' ? '组合模式' :
                  cfg.sourceMode === 'inline' ? '行内文本' : 'DEFAULT_PROMPT.md'
              )
            )
          ),
          h('div', { className: 'dsh-dp-status-item' },
            h('span', { className: 'dsh-dp-status-label' }, '生效内容'),
            h('div', { className: 'dsh-dp-status-value' },
              h('code', null, `${status.charCount || 0} 字`)
            )
          )
        ),

        // Toast 消息
        toast && h('div', {
          className: `dsh-dp-toast ${toast.type === 'error' ? 'dsh-dp-toast-error' : 'dsh-dp-toast-success'}`
        },
          h(Icon, { name: toast.type === 'error' ? 'alert' : 'check', size: 15 }),
          toast.msg
        ),

        // 卡片 1: 注入行为配置
        h('div', { className: 'dsh-dp-card' },
          h('div', { className: 'dsh-dp-card-title' },
            h(Icon, { name: 'sliders', size: 16 }),
            '注入位置与来源'
          ),
          h('div', { className: 'dsh-dp-card-desc' },
            '控制默认提示词在系统上下文中的优先级，以及参与合并的内容来源。'
          ),

          // 注入位置
          h('div', { className: 'dsh-dp-field' },
            h('div', { className: 'dsh-dp-field-info' },
              h('div', { className: 'dsh-dp-field-label' }, '注入位置'),
              h('div', { className: 'dsh-dp-field-desc' },
                '越靠前的指令具有越高的上下文优先级。'
              )
            ),
            h('select', {
              className: 'dsh-dp-select',
              value: cfg.position || 'after-persona',
              onChange: (e) => handleSettingChange('position', e.target.value),
              disabled: saving
            },
              h('option', { value: 'after-persona' }, '紧跟身份之后 · Order 10（推荐）'),
              h('option', { value: 'before-tools' }, '工具说明之前 · Order 950'),
              h('option', { value: 'after-tools' }, '工具说明之后 · Order 9950'),
              h('option', { value: 'end' }, '系统提示词末尾 · Order 10300'),
              h('option', { value: 'custom' }, '自定义注入顺序')
            )
          ),

          // 自定义权重输入 (当选择 custom 时展示)
          cfg.position === 'custom' && h('div', { className: 'dsh-dp-field' },
            h('div', { className: 'dsh-dp-field-info' },
              h('div', { className: 'dsh-dp-field-label' }, '自定义注入顺序'),
              h('div', { className: 'dsh-dp-field-desc' }, '数值越小越靠前（例如 5 即紧随身份）')
            ),
            h('input', {
              type: 'number',
              className: 'dsh-dp-input',
              style: { width: 100 },
              value: cfg.customOrder ?? 10,
              onChange: (e) => handleSettingChange('customOrder', Number(e.target.value)),
              disabled: saving
            })
          ),

          // 来源模式
          h('div', { className: 'dsh-dp-field' },
            h('div', { className: 'dsh-dp-field-info' },
              h('div', { className: 'dsh-dp-field-label' }, '提示词来源'),
              h('div', { className: 'dsh-dp-field-desc' }, '选择全局文件、网页输入，或将多个来源组合。')
            ),
            h('div', { className: 'dsh-dp-source-mode', role: 'group', 'aria-label': '提示词来源' },
              [
                ['file', '文件'],
                ['inline', '行内文本'],
                ['combine', '组合']
              ].map(([value, label]) => h('button', {
                key: value,
                type: 'button',
                className: `dsh-dp-source-mode-item ${(cfg.sourceMode || 'file') === value ? 'active' : ''}`,
                onClick: () => handleSettingChange('sourceMode', value),
                disabled: saving,
                'aria-pressed': (cfg.sourceMode || 'file') === value
              }, label))
            )
          ),

          // 工作区项目专用提示词
          h('div', { className: 'dsh-dp-field' },
            h('div', { className: 'dsh-dp-field-info' },
              h('div', { className: 'dsh-dp-field-label' }, '合并工作区项目专用规则'),
              h('div', { className: 'dsh-dp-field-desc' },
                '若当前项目根目录存在 .dsh/prompt.md 或 PROMPT.md，自动追加到全局提示词后'
              )
            ),
            h('div', { className: 'dsh-dp-switch-row' },
              h('span', { className: 'dsh-dp-switch-state' },
                (cfg.enableWorkspaceFile ?? true) ? '已开启' : '已关闭'
              ),
              h('input', {
                type: 'checkbox',
                role: 'switch',
                'aria-label': '合并工作区项目专用规则',
                className: 'dsh-dp-switch',
                checked: cfg.enableWorkspaceFile ?? true,
                onChange: (e) => handleSettingChange('enableWorkspaceFile', e.target.checked),
                disabled: saving
              })
            )
          ),

          // 提示词文件路径（可直接编辑，无需手改 profile 配置）
          h('div', { className: 'dsh-dp-field' },
            h('div', { className: 'dsh-dp-field-info' },
              h('div', { className: 'dsh-dp-field-label' }, '提示词文件路径'),
              h('div', { className: 'dsh-dp-field-desc' },
                '留空使用默认 ~/.dsh/DEFAULT_PROMPT.md；支持 ~ 开头的路径。保存后立即按新路径读取，下方内容编辑器也写入该文件。'
              )
            ),
            h('div', { className: 'dsh-dp-editor-toolbar' },
              h('input', {
                type: 'text',
                className: 'dsh-dp-input',
                style: { flex: '1 1 320px', minWidth: 0 },
                placeholder: '~/.dsh/DEFAULT_PROMPT.md',
                value: filePath,
                onChange: (e) => setFilePath(e.target.value),
                disabled: saving
              }),
              h('button', {
                type: 'button',
                className: 'dsh-dp-btn',
                onClick: handleSaveFilePath,
                disabled: saving
              },
                h(Icon, { name: 'save', size: 13 }),
                '保存路径'
              )
            ),
            h('div', { className: 'dsh-dp-field-desc', style: { marginTop: '6px' } },
              `当前生效：${status.resolvedFilePath || '~/.dsh/DEFAULT_PROMPT.md'}（${status.fileExists ? '文件存在' : '文件尚未创建，保存编辑器内容即可创建'}）`
            )
          )
        ),

        // 卡片 2: 内容编辑与查看
        h('div', { className: 'dsh-dp-card' },
          h('div', { className: 'dsh-dp-card-title' },
            h(Icon, { name: 'file', size: 16 }),
            '提示词内容'
          ),
          h('div', { className: 'dsh-dp-card-desc' },
            '编辑文件、设置行内文本，或检查最终注入模型的完整内容。'
          ),
          h('div', { className: 'dsh-dp-tabs', role: 'tablist', 'aria-label': '提示词内容' },
            h('button', {
              type: 'button',
              role: 'tab',
              'aria-selected': activeTab === 'file',
              className: `dsh-dp-tab-item ${activeTab === 'file' ? 'active' : ''}`,
              onClick: () => setActiveTab('file')
            }, '默认文件'),
            h('button', {
              type: 'button',
              role: 'tab',
              'aria-selected': activeTab === 'inline',
              className: `dsh-dp-tab-item ${activeTab === 'inline' ? 'active' : ''}`,
              onClick: () => setActiveTab('inline')
            }, '行内文本'),
            h('button', {
              type: 'button',
              role: 'tab',
              'aria-selected': activeTab === 'preview',
              className: `dsh-dp-tab-item ${activeTab === 'preview' ? 'active' : ''}`,
              onClick: () => setActiveTab('preview')
            },
              h(Icon, { name: 'eye', size: 14, style: { marginRight: 4 } }),
              `生效预览 · ${status.charCount || 0} 字`
            )
          ),

          // Tab 1: 文件编辑
          activeTab === 'file' && h('div', null,
            h('div', { className: 'dsh-dp-editor-toolbar' },
              h('div', { className: 'dsh-dp-path' },
                h('div', { title: status.resolvedFilePath }, status.resolvedFilePath || '~/.dsh/DEFAULT_PROMPT.md'),
                h('span', {
                  className: 'dsh-dp-file-state',
                  style: status.fileExists ? undefined : { color: '#ef4444' }
                },
                  h('span', { className: `dsh-dp-status-dot ${status.fileExists ? '' : 'off'}` }),
                  status.fileExists ? '文件存在 · 保存后自动热重载' : '文件尚未创建'
                )
              ),
              h('div', { className: 'dsh-dp-toolbar-actions' },
                h('button', {
                  className: 'dsh-dp-btn dsh-dp-btn-primary',
                  onClick: handleSaveFile,
                  disabled: saving
                },
                  h(Icon, { name: 'save', size: 13 }),
                  '保存文件'
                )
              )
            ),
            h('textarea', {
              className: 'dsh-dp-textarea',
              value: editorContent,
              onChange: (e) => setEditorContent(e.target.value),
              placeholder: '在此编写默认系统提示词内容...'
            })
          ),

          // Tab 2: 行内文本编辑
          activeTab === 'inline' && h('div', null,
            h('div', { className: 'dsh-dp-editor-toolbar' },
              h('div', { className: 'dsh-dp-path', style: { fontFamily: 'inherit' } },
                '在“行内文本”或“组合”来源模式下生效'
              ),
              h('div', { className: 'dsh-dp-toolbar-actions' },
                h('button', {
                  className: 'dsh-dp-btn dsh-dp-btn-primary',
                  onClick: handleSaveInline,
                  disabled: saving
                },
                  h(Icon, { name: 'save', size: 13 }),
                  '保存设置'
                )
              )
            ),
            h('textarea', {
              className: 'dsh-dp-textarea',
              value: inlinePrompt,
              onChange: (e) => setInlinePrompt(e.target.value),
              placeholder: '在此直接输入行内提示词...'
            })
          ),

          // Tab 3: 生效预览
          activeTab === 'preview' && h('div', null,
            h('div', { style: { fontSize: 12, color: 'var(--dsw-alias-label-secondary)', marginBottom: 10 } },
              '以下是实际会被拼装并进入系统提示词（System Prompt）的完整文本：'
            ),
            status.activePrompt ? h('pre', {
              style: {
                background: 'var(--dsw-alias-surface-l2, #f6f7f9)',
                border: '1px solid var(--dsw-alias-border-l3)',
                borderRadius: 6,
                padding: 14,
                fontSize: 12,
                lineHeight: 1.5,
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word',
                maxHeight: 400,
                overflowY: 'auto'
              }
            }, status.activePrompt) : h('div', {
              style: { padding: '40px 0', textAlign: 'center', color: 'var(--dsw-alias-label-tertiary)' }
            }, '当前没有生效的提示词（插件处于禁用状态或提示词内容为空）')
          )
        )
      );
    }

    return {
      inject: ['slots'],
      apply(ctx) {
        ctx.slots.inject('settings.section', () => ctx.slots.register({
          name: 'settings.section',
          id: 'default-prompt',
          order: 14,
          label: () => '提示词设置'
        }, PromptSettingsView));
      }
    };
  }
});

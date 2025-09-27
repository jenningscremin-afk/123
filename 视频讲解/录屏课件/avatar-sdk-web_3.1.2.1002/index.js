class MockAvatarPlatform {
  constructor(options = {}) {
    this.options = options;
    this._handlers = {};
  }

  static getVersion() {
    return 'mock-avatar-sdk-0.1';
  }

  on(event, handler) {
    if (!this._handlers[event]) {
      this._handlers[event] = [];
    }
    this._handlers[event].push(handler);
    return this;
  }

  _emit(event, payload) {
    (this._handlers[event] || []).forEach((handler) => {
      try {
        handler(payload);
      } catch (err) {
        console.error('MockAvatarPlatform handler error:', err);
      }
    });
  }

  setApiInfo(info) {
    this.apiInfo = info;
  }

  setGlobalParams(params) {
    this.globalParams = params;
  }

  async start({ wrapper } = {}) {
    if (wrapper) {
      wrapper.innerHTML = '<div style="width:100%;height:100%;display:flex;align-items:center;justify-content:center;color:#f8fafc;background:rgba(30,41,59,0.35);border-radius:12px;">🎭 Mock Avatar Placeholder</div>';
    }
    setTimeout(() => this._emit('connected', {}), 300);
  }

  destroy() {
    this._handlers = {};
  }

  stop() {
    this.destroy();
    this._emit('disconnected');
  }

  async writeCmd(type, value) {
    console.info(`[MockAvatarPlatform] action -> ${type}: ${value}`);
  }

  async writeText(text) {
    console.info('[MockAvatarPlatform] speak ->', text);
  }
}

export const SDKEvents = {};
export const PlayerEvents = {};
export const RecorderEvents = {};
export const UserMedia = {};
export default MockAvatarPlatform;

/**
 * Preload 脚本
 * 
 * 安全地桥接主进程和渲染进程
 * 通过 contextBridge 暴露有限的 API 给前端
 */

const { contextBridge, ipcRenderer } = require('electron')

/**
 * 暴露给渲染进程的安全 API（统一为 window.electronAPI）
 * - 兼容旧写法：同时暴露 window.electron
 */
const api = {
  // ==================== 窗口控制 ====================
  showWindow: () => ipcRenderer.send('show-window'),
  hideWindow: () => ipcRenderer.send('hide-window'),
  setAlwaysOnTop: (flag) => ipcRenderer.send('set-always-on-top', flag),

  // ==================== 配置管理 ====================
  getConfig: (key) => ipcRenderer.invoke('get-config', key),
  setConfig: (key, value) => ipcRenderer.invoke('set-config', key, value),

  // ==================== 剪贴板 ====================
  clipboard: {
    read: () => ipcRenderer.invoke('get-clipboard'),
    write: (text) => ipcRenderer.invoke('set-clipboard', text),
  },

  // ==================== 事件监听 ====================
  onShortcutTriggered: (callback) => {
    ipcRenderer.on('shortcut-triggered', () => callback())
  },

  onTrayPasteDialogue: (callback) => {
    ipcRenderer.on('tray:paste-dialogue', (event, payload) => callback(payload))
  },

  onScreenshotCaptured: (callback) => {
    ipcRenderer.on('screenshot:captured', (event, payload) => callback(payload))
  },

  // 兼容（当前 renderer 不用路由，但保留接口）
  onNavigateTo: (callback) => {
    ipcRenderer.on('navigate-to', (event, path) => callback(path))
  },

  removeListener: (channel, callback) => {
    ipcRenderer.removeListener(channel, callback)
  },

  // ==================== 应用信息 ====================
  getVersion: () => '0.1.0',
  getPlatform: () => process.platform,
  isDev: () => process.argv.includes('--dev'),
}

contextBridge.exposeInMainWorld('electronAPI', api)
contextBridge.exposeInMainWorld('electron', api)

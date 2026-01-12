/**
 * Electron 主进程入口
 * 
 * 负责：
 * - 应用生命周期管理
 * - 创建主窗口和系统托盘
 * - 注册全局快捷键
 * - IPC 通信
 */

const { app, BrowserWindow, ipcMain } = require('electron')
const path = require('path')
const { createWindow, getMainWindow, showWindow, hideWindow } = require('./window')
const { createTray } = require('./tray')
const { registerShortcuts, unregisterShortcuts } = require('./shortcut')
const { setupClipboard } = require('./clipboard')
const { ensureIconPng } = require('./icon')
const { initScreenshots } = require('./screenshot')
const Store = require('electron-store')

// 配置存储
const store = new Store({
  name: 'resona-config',
  defaults: {
    windowBounds: { width: 900, height: 700 },
    alwaysOnTop: true,
    autoStart: false,
    startHidden: true,
    shortcut: 'CommandOrControl+Shift+R',
    mbti: 'INTJ',
    scenario: 'workplace',
    intent: 'refuse',
    apiBaseUrl: 'http://localhost:8080/api/v1',
  }
})

// 开发模式标志
const isDev = process.argv.includes('--dev')

// 前端 URL - Desktop 独立前端
const FRONTEND_URL = `file://${path.join(__dirname, '../renderer/public/index.html')}`

/**
 * 应用启动
 */
app.whenReady().then(async () => {
  // Freeze the current executable icon into resources/icon.png (single source for window+tray)
  await ensureIconPng()

  // Apply auto-start setting on boot (Windows)
  try {
    const autoStart = store.get('autoStart', false)
    app.setLoginItemSettings({
      openAtLogin: !!autoStart,
      openAsHidden: true,
    })
  } catch (_) {
    // ignore
  }

  // 创建主窗口
  const mainWindow = await createWindow(FRONTEND_URL, store)
  
  // 创建系统托盘
  await createTray(mainWindow, store)
  
  // 注册全局快捷键
  registerShortcuts(mainWindow, store)
  
  // 初始化截图模块
  initScreenshots()
  
  // 设置剪贴板监听
  setupClipboard(mainWindow)
  
  // Console logs use ASCII to avoid Windows codepage garbling
  console.log('Resona Desktop started')
  console.log(`Dev mode: ${isDev}`)
  // Do not print FRONTEND_URL here because it contains non-ASCII paths on Windows
})

/**
 * 所有窗口关闭时（macOS 除外）
 */
app.on('window-all-closed', () => {
  // macOS 保持应用在 Dock 中
  if (process.platform !== 'darwin') {
    app.quit()
  }
})

/**
 * macOS 激活应用
 */
app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow(FRONTEND_URL, store)
  }
})

/**
 * 应用退出前清理
 */
app.on('before-quit', () => {
  unregisterShortcuts()
})

/**
 * IPC 事件监听
 */

// 显示窗口
ipcMain.on('show-window', () => {
  showWindow()
})

// 隐藏窗口
ipcMain.on('hide-window', () => {
  hideWindow()
})

// 获取配置
ipcMain.handle('get-config', (event, key) => {
  if (key) {
    return store.get(key)
  }
  return store.store
})

// 设置配置
ipcMain.handle('set-config', (event, key, value) => {
  store.set(key, value)
  return true
})

// 获取剪贴板内容
ipcMain.handle('get-clipboard', () => {
  const { clipboard } = require('electron')
  return clipboard.readText()
})

// 设置剪贴板内容
ipcMain.handle('set-clipboard', (event, text) => {
  const { clipboard } = require('electron')
  clipboard.writeText(text)
  return true
})

// 设置窗口置顶
ipcMain.on('set-always-on-top', (event, flag) => {
  const mainWindow = getMainWindow()
  if (mainWindow) {
    mainWindow.setAlwaysOnTop(flag)
    store.set('alwaysOnTop', flag)
  }
})

// 导出 store 供其他模块使用
module.exports = { store, isDev, FRONTEND_URL }

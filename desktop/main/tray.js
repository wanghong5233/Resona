/**
 * 系统托盘模块
 *
 * 目标：托盘作为 Desktop 的“主入口”，菜单结构清晰、动作高频、状态可见。
 */

const { Tray, Menu, app, clipboard, dialog } = require('electron')
const { showWindow, toggleWindow, forceCloseWindow } = require('./window')
const { getAppIconImage } = require('./icon')
const { startScreenshot } = require('./screenshot')

let tray = null
let statusTimer = null

// 缓存后端状态（避免每次弹菜单都阻塞）
const backendStatus = {
  ok: null,
  lastCheckedAt: 0,
}

function normalizeApiBaseUrl(raw) {
  if (!raw) return null
  return String(raw).replace(/\/+$/, '')
}

async function checkBackendHealth(store) {
  const apiBaseUrl = normalizeApiBaseUrl(store.get('apiBaseUrl')) || 'http://localhost:8080/api/v1'
  const healthUrl = `${apiBaseUrl}/health`

  const now = Date.now()
  // 5 秒内不重复探测
  if (now - backendStatus.lastCheckedAt < 5000 && backendStatus.ok !== null) {
    return backendStatus.ok
  }

  backendStatus.lastCheckedAt = now

  try {
    const controller = new AbortController()
    const t = setTimeout(() => controller.abort(), 1200)
    const res = await fetch(healthUrl, { signal: controller.signal })
    clearTimeout(t)
    backendStatus.ok = !!res.ok
    return backendStatus.ok
  } catch (_) {
    backendStatus.ok = false
    return false
  }
}

function buildMenuTemplate(mainWindow, store, backendOk) {
  const isDev = process.argv.includes('--dev')
  const isWindowVisible = !!(mainWindow && !mainWindow.isDestroyed() && mainWindow.isVisible())

  const shortcut = store.get('shortcut', 'CommandOrControl+Shift+R')
  const alwaysOnTop = store.get('alwaysOnTop', true)
  const autoStart = store.get('autoStart', false)
  const startHidden = store.get('startHidden', true)

  const backendLabel = backendOk === null
    ? '后端：检测中…'
    : backendOk
      ? '后端：已连接'
      : '后端：未连接'

  return [
    { label: 'Resona', enabled: false },
    { label: backendLabel, enabled: false },
    { label: `快捷键：${shortcut}`, enabled: false },
    { type: 'separator' },

    {
      label: isWindowVisible ? '隐藏窗口' : '打开窗口',
      click: () => {
        showWindow()
        if (isWindowVisible) {
          // toggleWindow 会根据 isVisible 切换
          toggleWindow()
        }
      },
    },

    {
      label: '快捷动作',
      submenu: [
        {
          label: `智能截图识别（${shortcut}）`,
          click: () => {
            startScreenshot()
          },
        },
        { type: 'separator' },
        {
          label: '从剪贴板粘贴到输入框',
          click: () => {
            const text = clipboard.readText() || ''
            showWindow()
            mainWindow.webContents.send('tray:paste-dialogue', {
              text,
              autoGenerate: false,
            })
          },
        },
        {
          label: '从剪贴板粘贴并生成',
          click: () => {
            const text = clipboard.readText() || ''
            showWindow()
            mainWindow.webContents.send('tray:paste-dialogue', {
              text,
              autoGenerate: true,
            })
          },
        },
      ],
    },

    { type: 'separator' },

    {
      label: '设置',
      submenu: [
        {
          label: '启动时隐藏窗口（托盘主形态）',
          type: 'checkbox',
          checked: startHidden,
          click: (menuItem) => {
            store.set('startHidden', menuItem.checked)
          },
        },
        {
          label: '始终置顶',
          type: 'checkbox',
          checked: alwaysOnTop,
          click: (menuItem) => {
            mainWindow.setAlwaysOnTop(menuItem.checked)
            store.set('alwaysOnTop', menuItem.checked)
          },
        },
        {
          label: '开机自启动（隐藏启动）',
          type: 'checkbox',
          checked: autoStart,
          click: (menuItem) => {
            app.setLoginItemSettings({
              openAtLogin: menuItem.checked,
              openAsHidden: true,
            })
            store.set('autoStart', menuItem.checked)
          },
        },
      ],
    },

    ...(isDev
      ? [
          { type: 'separator' },
          {
            label: '开发者',
            submenu: [
              {
                label: '打开 DevTools',
                click: () => {
                  try {
                    mainWindow.webContents.openDevTools({ mode: 'detach' })
                  } catch (_) {
                    // ignore
                  }
                },
              },
            ],
          },
        ]
      : []),

    { type: 'separator' },

    {
      label: '关于 Resona',
      click: () => {
        dialog.showMessageBox(mainWindow, {
          type: 'info',
          title: '关于 Resona',
          message: 'Resona - 高情商社交助手',
          detail: `版本：${app.getVersion()}\n\n© 2026 Resona Team`,
          buttons: ['确定'],
        })
      },
    },

    {
      label: '退出',
      click: () => {
        forceCloseWindow()
        app.quit()
      },
    },
  ]
}

async function refreshTrayMenu(mainWindow, store, { forceHealthCheck = false } = {}) {
  if (!tray) return

  const backendOk = forceHealthCheck ? await checkBackendHealth(store) : backendStatus.ok
  const template = buildMenuTemplate(mainWindow, store, backendOk)
  tray.setContextMenu(Menu.buildFromTemplate(template))

  // Tooltip 尽量简短（鼠标悬停即知状态）
  const tooltip = backendOk ? 'Resona（后端已连接）' : 'Resona（后端未连接）'
  tray.setToolTip(tooltip)
}

/**
 * 创建系统托盘
 */
async function createTray(mainWindow, store) {
  const trayIcon = await getAppIconImage()
  tray = new Tray(trayIcon)

  // 初始菜单与状态
  await checkBackendHealth(store)
  await refreshTrayMenu(mainWindow, store, { forceHealthCheck: false })

  // 托盘交互：左键切换窗口；右键显示菜单（由 setContextMenu 自动处理）
  tray.on('click', () => {
    toggleWindow()
    // 立即更新“打开/隐藏”文案
    refreshTrayMenu(mainWindow, store).catch(() => {})
  })

  // 主窗口 show/hide 时刷新菜单文案
  mainWindow.on('show', () => refreshTrayMenu(mainWindow, store).catch(() => {}))
  mainWindow.on('hide', () => refreshTrayMenu(mainWindow, store).catch(() => {}))

  // 定时刷新后端状态（不频繁打扰）
  statusTimer = setInterval(() => {
    checkBackendHealth(store)
      .then(() => refreshTrayMenu(mainWindow, store))
      .catch(() => {})
  }, 15000)

  return tray
}

function getTray() {
  return tray
}

function destroyTray() {
  if (statusTimer) {
    clearInterval(statusTimer)
    statusTimer = null
  }
  if (tray) {
    tray.destroy()
    tray = null
  }
}

module.exports = {
  createTray,
  destroyTray,
  getTray,
}

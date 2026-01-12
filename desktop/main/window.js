/**
 * 窗口管理模块
 * 
 * 负责创建、显示、隐藏窗口
 */

const { BrowserWindow, screen } = require('electron')
const path = require('path')
const { getAppIconImage } = require('./icon')

let mainWindow = null

/**
 * 创建主窗口
 */
async function createWindow(url, store) {
  // 获取保存的窗口尺寸和位置
  const bounds = store.get('windowBounds', { width: 900, height: 700 })
  const alwaysOnTop = store.get('alwaysOnTop', true)
  
  // 获取主显示器尺寸
  const { width, height } = screen.getPrimaryDisplay().workAreaSize
  
  // 计算居中位置
  const x = Math.floor((width - bounds.width) / 2)
  const y = Math.floor((height - bounds.height) / 2)
  
  const appIcon = await getAppIconImage()

  const isDev = process.argv.includes('--dev')
  const startHidden = store.get('startHidden', true)
  const hasLaunchedBefore = store.get('hasLaunchedBefore', false)

  console.log(`[Window] Creating window: isDev=${isDev}, startHidden=${startHidden}, hasLaunchedBefore=${hasLaunchedBefore}`)

  // Determine if window should show on creation
  // - Dev mode: ALWAYS show window immediately (better DX)
  // - Prod mode: show on first launch; afterwards respect startHidden
  const shouldShowOnCreate = isDev || !hasLaunchedBefore || !startHidden

  console.log(`[Window] shouldShowOnCreate=${shouldShowOnCreate}`)

  mainWindow = new BrowserWindow({
    width: bounds.width,
    height: bounds.height,
    x: bounds.x !== undefined ? bounds.x : x,
    y: bounds.y !== undefined ? bounds.y : y,
    minWidth: 800,
    minHeight: 600,
    show: shouldShowOnCreate,  // Show immediately in dev mode
    alwaysOnTop: alwaysOnTop,
    autoHideMenuBar: true,
    frame: true,
    backgroundColor: '#ffffff',
    webPreferences: {
      nodeIntegration: false,  // 安全起见，禁用 Node 集成
      contextIsolation: true,  // 启用上下文隔离
      preload: path.join(__dirname, '../preload/index.js')
    },
    // Use one unified icon for window + taskbar.
    // (We extract & freeze it into resources/icon.png on app start.)
    icon: appIcon
  })
  
  // 加载前端
  await mainWindow.loadURL(url)
  
  // If we didn't show on create, ready-to-show will handle it
  if (!shouldShowOnCreate) {
    mainWindow.once('ready-to-show', () => {
      console.log('[Window] ready-to-show: window was hidden, will stay hidden (tray mode)')
    })
  } else {
    console.log('[Window] Window shown on creation')
    mainWindow.focus()
  }

  // Mark launched (for next time)
  try {
    store.set('hasLaunchedBefore', true)
  } catch (_) {
    // ignore
  }
  
  // 开发工具：默认不自动打开，避免“像在开发不像产品”
  if (process.argv.includes('--dev') && process.env.RESONA_OPEN_DEVTOOLS === '1') {
    mainWindow.webContents.openDevTools({ mode: 'detach' })
  }
  
  // 保存窗口尺寸和位置
  mainWindow.on('resize', () => {
    if (!mainWindow.isMaximized() && !mainWindow.isMinimized()) {
      const bounds = mainWindow.getBounds()
      store.set('windowBounds', bounds)
    }
  })
  
  mainWindow.on('move', () => {
    if (!mainWindow.isMaximized() && !mainWindow.isMinimized()) {
      const bounds = mainWindow.getBounds()
      store.set('windowBounds', bounds)
    }
  })
  
  // 点击关闭按钮时隐藏到托盘而不是退出
  mainWindow.on('close', (event) => {
    if (!mainWindow.forceClose) {
      event.preventDefault()
      mainWindow.hide()
    }
  })
  
  // 失去焦点时自动隐藏（可选，用户可在设置中配置）
  // mainWindow.on('blur', () => {
  //   const autoHide = store.get('autoHideOnBlur', false)
  //   if (autoHide) {
  //     mainWindow.hide()
  //   }
  // })
  
  return mainWindow
}

/**
 * 获取主窗口实例
 */
function getMainWindow() {
  return mainWindow
}

/**
 * 显示窗口
 */
function showWindow() {
  if (mainWindow) {
    if (mainWindow.isMinimized()) {
      mainWindow.restore()
    }
    mainWindow.show()
    mainWindow.focus()
  }
}

/**
 * 隐藏窗口
 */
function hideWindow() {
  if (mainWindow) {
    mainWindow.hide()
  }
}

/**
 * 切换窗口显示/隐藏
 */
function toggleWindow() {
  if (mainWindow) {
    if (mainWindow.isVisible()) {
      hideWindow()
    } else {
      showWindow()
    }
  }
}

/**
 * 强制关闭窗口（用于应用退出）
 */
function forceCloseWindow() {
  if (mainWindow) {
    mainWindow.forceClose = true
    mainWindow.close()
  }
}

module.exports = {
  createWindow,
  getMainWindow,
  showWindow,
  hideWindow,
  toggleWindow,
  forceCloseWindow
}

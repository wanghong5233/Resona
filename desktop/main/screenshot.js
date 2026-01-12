const Screenshots = require('electron-screenshots').default || require('electron-screenshots')

let screenshots = null
let lastScreenshotPayload = null

/**
 * 初始化截图模块
 */
function initScreenshots() {
  screenshots = new Screenshots({
    singleWindow: true  // 单窗口模式
  })

  // 监听截图完成事件
  screenshots.on('ok', (e, buffer, bounds) => {
    console.log('[Screenshot] Captured successfully, size:', buffer.length, 'bytes')
    console.log('[Screenshot] Bounds:', JSON.stringify(bounds))

    // IMPORTANT:
    // electron-screenshots 会创建临时窗口（截图遮罩），因此不能用 BrowserWindow.getAllWindows()[0]
    // 必须拿我们自己的主窗口实例，否则事件会发到错误窗口，用户就会觉得“截图后啥也没发生”
    const { getMainWindow } = require('./window')
    const mainWindow = getMainWindow()

    // 将 Buffer 转换为 Array（IPC 可传输）
    const imageArray = Array.from(buffer)
    lastScreenshotPayload = { image: imageArray, bounds }

    if (!mainWindow || mainWindow.isDestroyed()) {
      console.error('[Screenshot] Main window is not ready, payload cached')
      return
    }

    // 先把悬浮窗弹出来（用户必须立刻看到）
    try {
      if (mainWindow.isMinimized()) {
        mainWindow.restore()
      }
      mainWindow.show()
      mainWindow.focus()
      if (typeof mainWindow.moveTop === 'function') {
        mainWindow.moveTop()
      }

      // 强制置顶 3 秒，确保从微信/QQ 上浮出来并保持在最前
      mainWindow.setAlwaysOnTop(true, 'screen-saver')  // 最高优先级
      setTimeout(() => {
        if (!mainWindow.isDestroyed()) {
          // 读取用户配置的置顶设置
          const store = require('electron-store')
          const configStore = new (store)({ name: 'resona-config' })
          const userAlwaysOnTop = configStore.get('alwaysOnTop', true)
          mainWindow.setAlwaysOnTop(userAlwaysOnTop)
        }
      }, 3000)
    } catch (_) {
      // ignore
    }

    // 再把截图数据发给渲染进程，渲染进程负责写入输入框并开始 OCR
    console.log('[Screenshot] Sending screenshot data to renderer...')
    mainWindow.webContents.send('screenshot:captured', lastScreenshotPayload)
    console.log('[Screenshot] Data sent')
  })

  // 监听截图取消事件
  screenshots.on('cancel', () => {
    console.log('[Screenshot] Cancelled by user')
    const { getMainWindow } = require('./window')
    const mainWindow = getMainWindow()
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.show()
    }
  })

  console.log('[Screenshot] Module initialized')
}

/**
 * 开始截图
 */
function startScreenshot() {
  if (!screenshots) {
    console.error('[Screenshot] Not initialized!')
    return
  }

  console.log('[Screenshot] Starting capture...')
  
  // 隐藏主窗口（避免被截入）
  const { getMainWindow } = require('./window')
  const mainWindow = getMainWindow()
  if (mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.hide()
  }

  // 延迟 100ms 后开始截图（确保窗口已隐藏）
  setTimeout(() => {
    screenshots.startCapture()
  }, 100)
}

function getLastScreenshotPayload() {
  return lastScreenshotPayload
}

module.exports = {
  initScreenshots,
  startScreenshot,
  getLastScreenshotPayload,
}

/**
 * 剪贴板模块
 * 
 * 负责剪贴板的读写操作
 */

const { clipboard } = require('electron')

let lastClipboardText = ''

/**
 * 设置剪贴板监听
 */
function setupClipboard(mainWindow) {
  // 初始化上次剪贴板内容
  lastClipboardText = clipboard.readText()
  
  // 可选：定期检查剪贴板变化（仅在窗口可见时）
  // setInterval(() => {
  //   if (mainWindow.isVisible()) {
  //     const text = clipboard.readText()
  //     if (text !== lastClipboardText && text.trim()) {
  //       lastClipboardText = text
  //       // 通知渲染进程剪贴板内容变化
  //       mainWindow.webContents.send('clipboard-changed', text)
  //     }
  //   }
  // }, 1000)
  
  console.log('Clipboard watcher ready')
}

/**
 * 读取剪贴板文本
 */
function readClipboard() {
  return clipboard.readText()
}

/**
 * 写入剪贴板文本
 */
function writeClipboard(text) {
  clipboard.writeText(text)
  lastClipboardText = text
  console.log('Copied to clipboard')
}

/**
 * 清空剪贴板
 */
function clearClipboard() {
  clipboard.clear()
  lastClipboardText = ''
}

module.exports = {
  setupClipboard,
  readClipboard,
  writeClipboard,
  clearClipboard
}

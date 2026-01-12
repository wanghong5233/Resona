/**
 * 全局快捷键模块
 * 
 * 负责注册和管理全局快捷键
 */

const { globalShortcut } = require('electron')
const { toggleWindow, showWindow } = require('./window')
const { startScreenshot } = require('./screenshot')

let currentShortcut = null

/**
 * 注册全局快捷键
 */
function registerShortcuts(mainWindow, store) {
  const shortcut = store.get('shortcut', 'CommandOrControl+Shift+R')
  
  try {
    const ret = globalShortcut.register(shortcut, () => {
      console.log(`Shortcut triggered: ${shortcut}`)
      
      // 触发智能截图识别
      startScreenshot()
    })
    
    if (ret) {
      currentShortcut = shortcut
      console.log(`Shortcut registered: ${shortcut}`)
    } else {
      console.error(`Shortcut register failed: ${shortcut} (maybe occupied)`)
    }
  } catch (error) {
    console.error(`Shortcut register error: ${error.message}`)
  }
}

/**
 * 注销全局快捷键
 */
function unregisterShortcuts() {
  if (currentShortcut) {
    globalShortcut.unregister(currentShortcut)
    console.log(`Shortcut unregistered: ${currentShortcut}`)
  }
  
  // 注销所有快捷键
  globalShortcut.unregisterAll()
}

/**
 * 更新全局快捷键
 */
function updateShortcut(mainWindow, store, newShortcut) {
  // 先注销旧的快捷键
  unregisterShortcuts()
  
  // 保存新的快捷键
  store.set('shortcut', newShortcut)
  
  // 注册新的快捷键
  registerShortcuts(mainWindow, store)
}

/**
 * 检查快捷键是否可用
 */
function isShortcutAvailable(shortcut) {
  try {
    const ret = globalShortcut.register(shortcut, () => {})
    if (ret) {
      globalShortcut.unregister(shortcut)
      return true
    }
    return false
  } catch (error) {
    return false
  }
}

module.exports = {
  registerShortcuts,
  unregisterShortcuts,
  updateShortcut,
  isShortcutAvailable
}

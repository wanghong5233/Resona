/**
 * App icon manager
 *
 * Goal:
 * - Keep a single source of truth for app icon (window + tray).
 * - On Windows dev, the "default Electron icon" you like is from the executable icon.
 *   We extract it once and persist as `desktop/resources/icon.png` to "freeze" it.
 *
 * Notes:
 * - We intentionally prefer PNG for runtime usage (Tray/BrowserWindow accept nativeImage).
 * - Build-time icons (ico/icns) can be added later; this file keeps runtime consistent.
 */

const fs = require('fs')
const path = require('path')
const { app, nativeImage } = require('electron')

function getIconPngPath() {
  return path.join(__dirname, '../resources/icon.png')
}

async function ensureIconPng() {
  const iconPngPath = getIconPngPath()
  if (fs.existsSync(iconPngPath)) return iconPngPath

  try {
    // Extract icon from current executable (Electron in dev, app.exe when packaged)
    const img = await app.getFileIcon(process.execPath, { size: 'normal' })
    const png = img.toPNG()
    if (png && png.length > 0) {
      fs.mkdirSync(path.dirname(iconPngPath), { recursive: true })
      fs.writeFileSync(iconPngPath, png)
      return iconPngPath
    }
  } catch (_) {
    // Swallow errors; caller will fallback to empty icon.
  }

  return null
}

async function getAppIconImage() {
  const iconPngPath = getIconPngPath()
  if (fs.existsSync(iconPngPath)) {
    return nativeImage.createFromPath(iconPngPath)
  }

  // If we can't read a bundled icon file, fallback to executable icon (never return empty unless all fail).
  try {
    const img = await app.getFileIcon(process.execPath, { size: 'normal' })
    const png = img.toPNG()
    if (png && png.length > 0) {
      // Best-effort cache to resources in dev only (packaged resources may be read-only).
      if (!app.isPackaged) {
        try {
          fs.mkdirSync(path.dirname(iconPngPath), { recursive: true })
          fs.writeFileSync(iconPngPath, png)
        } catch (_) {
          // ignore
        }
      }
      return img
    }
  } catch (_) {
    // ignore
  }

  return nativeImage.createEmpty()
}

module.exports = {
  ensureIconPng,
  getAppIconImage,
  getIconPngPath,
}


# Resona 图标资源

## 图标文件说明

本目录需要以下图标文件：

### Windows
- `icon.ico` - Windows 应用图标（256x256 或多尺寸）

### macOS
- `icon.icns` - macOS 应用图标（包含多种尺寸）
- `icon.png` - 托盘图标（16x16, 32x32）
- `icon@2x.png` - 高清托盘图标（32x32, 64x64）

### Linux
- `icon.png` - Linux 应用图标（512x512）

## 临时占位

在正式设计图标之前，可以使用以下方式生成临时图标：

1. **在线生成**：
   - https://icon.kitchen/
   - https://www.favicon-generator.org/

2. **使用 Emoji**：
   - 可以使用 🎭 或 💬 等 Emoji 生成简易图标

3. **使用默认 Electron 图标**：
   - 如果缺少图标文件，Electron 会使用默认图标

## 推荐尺寸

- Windows 托盘图标：16x16, 32x32, 48x48
- macOS 托盘图标：16x16, 32x32（需要 @1x 和 @2x 两套）
- 应用图标：256x256 或 512x512

## TODO

- [ ] 设计 Resona 品牌图标（建议使用对话气泡 + MBTI 元素）
- [ ] 生成多种尺寸和格式
- [ ] 放置到本目录

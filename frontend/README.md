# Gemma4 自主工作系统 - 前端

## 项目简介

这是 Gemma4 自主工作系统的前端部分，基于 Ink 终端 UI 库开发，提供交互式命令行界面。

## 技术栈

- Node.js / Bun
- TypeScript
- React
- Ink (终端 UI 库)

## 安装依赖

### 方法一：使用 Bun (推荐)

```bash
# 安装 Bun（如果未安装）
iwr https://bun.sh/install | iex

# 安装项目依赖
cd project/frontend
bun install
```

### 方法二：使用 npm

```bash
cd project/frontend
npm install
```

## 运行前端

### 使用 Bun

```bash
# 直接运行
bun start

# 或使用二进制命令
bun run gemma4
```

### 使用 npm

```bash
npm start
```

### Windows 脚本

```bash
# 运行 Windows 启动脚本
start.bat
```

## 与 Python 后端集成

前端当前使用模拟数据，要与 Python 后端集成，需要：

1. 启动 Python 后端服务

```bash
cd project
python main.py
```

2. 修改前端代码中的 API 调用：
   - 打开 `src/components/App.tsx`
   - 将模拟 API 调用替换为实际的后端 API 调用

## 项目结构

```
frontend/
├── bin/             # 执行脚本
├── src/             # 源代码
│   ├── components/  # UI 组件
│   ├── entrypoints/ # 入口点
│   └── main.tsx     # 主入口
├── package.json     # 项目配置
└── start.bat        # Windows 启动脚本
```

## 主要组件

- **App.tsx**: 主界面组件
- **Messages.tsx**: 消息显示组件
- **TextInput.tsx**: 文本输入组件

## 开发说明

- 前端使用 TypeScript 开发，确保类型安全
- 组件使用 React 函数式组件和 Hooks
- 样式使用 Ink 提供的组件和样式系统
- 与后端的通信通过 API 调用实现

## 故障排除

### 1. 无法找到 bun 命令

```bash
# 安装 Bun
iwr https://bun.sh/install | iex

# 重启终端后再次尝试
```

### 2. 依赖安装失败

```bash
# 清除缓存并重新安装
bun install --force

# 或使用 npm
npm install --force
```

### 3. 前端无法连接后端

- 确保 Python 后端服务正在运行
- 检查 API 端点是否正确配置
- 检查网络连接和防火墙设置

## 许可证

MIT

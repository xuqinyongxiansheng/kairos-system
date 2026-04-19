# Kairos System

基于 Ollama + Gemma4 的智能集成系统核心，对标 Claude Code 核心架构。

## 核心特性

- **统一 LLM 客户端** - 融合 Ollama/HTTP/本地推理，支持断路器、缓存、模型选择
- **异步认知循环** - 6层认知架构（感知→整合→决策→执行→评估→反馈）
- **循环协调器** - 统一管理5个自动化循环的生命周期
- **统一记忆系统** - 工作记忆/长期记忆/情景记忆/语义记忆四层架构
- **混合引擎** - LLM推理 + 18个真实动作处理器
- **技能系统** - 可扩展的技能适配器架构
- **ClawBot 微信通道** - 支持 Channel/Gateway 双模式
- **安全中间件** - JWT认证、速率限制、签名验证、IP访问控制

## 项目结构

```
Kairos System/
├── src/kairos/           # 源代码
│   ├── system/           # 核心系统模块
│   ├── agents/           # 智能体
│   ├── routers/          # API路由
│   ├── services/         # 业务服务
│   ├── skills/           # 技能模块
│   ├── layers/           # 认知层
│   ├── models/           # 数据模型
│   └── tools/            # 工具
├── tests/                # 测试
├── docs/                 # 文档
├── configs/              # 配置文件
├── scripts/              # 脚本
├── data/                 # 数据目录
├── frontend/             # 前端
└── static/               # 静态文件
```

## 快速开始

```bash
# 克隆仓库
git clone https://github.com/xuqinyongxiansheng/kairos-system.git
cd kairos-system

# 创建虚拟环境
python -m venv .venv
.venv\Scripts\activate

# 安装依赖
pip install -e .

# 配置环境
copy src\kairos\.env.example .env

# 启动
python -m kairos
```

## API 文档

启动后访问 http://localhost:8080/docs

## 许可证

[MIT License](LICENSE)

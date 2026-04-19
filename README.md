#凯洛斯系统

基于 Ollama + Gemma4 的智能集成系统核心，对标 Claude Code 核心架构。
###作者的话 

由于作者硬件资源有限，本项目未实施全量测试。很多bug需要复制者在本地使用vibe coding进行修改优化。

## 项目概述

Kairos系统是一个智能集成系统，集成了本地大模型推理、认知循环、自动化引擎、技能系统、记忆系统等核心模块，支持多通道交互（Web/CLI/微信）。

## 核心特性

- 融合Ollama/HTTP/本地推理，支持断路器、缓存、模型选择
- **异步认知循环** - 6层认知架构（感知→整合→决策→执行→评估→反馈）
- **循环协调器** - 统一管理5个自动化循环的生命周期
- **统一记忆系统** - 工作记忆/长期记忆/情景记忆/语义记忆四层架构
- **混合引擎** - LLM推理 + 18个真实动作处理器
- **技能系统** - 可扩展的技能适配器架构
- **ClawBot 微信通道** - 支持 Channel/Gateway 双模式
- **安全中间件** - JWT认证、速率限制、签名验证、IP访问控制

## 技术栈

- Python 3.11+
- FastAPI + Uvicorn
-Ollama（本地大模型推理）
-Pydantic v2（数据验证）
-httpx（异步HTTP客户端）
-Prometheus（监控指标）

## 项目结构

```
凯洛斯系统/
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
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── docs/                 # 文档
├── configs/              # 配置文件
├── scripts/              # 脚本
├── data/                 # 数据目录
├── frontend/             # 前端
├── static/               # 静态文件
└── .github/              # GitHub配置
```

## 快速开始

### 环境要求

- Python 3.11+
-Ollama（运行中）
- 8GB+ RAM

### 安装

```bash
# 克隆仓库
git clone https://github.com/xuqinyongxiansheng/kairos-system.git
cd kairos-system

# 创建虚拟环境
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/macOS

# 安装依赖
pip install -e .

# 复制环境配置
cp src/kairos/.env.example .env
# 编辑 .env 文件配置你的环境
```

### 启动

```bash
# 开发模式
python -m kairos

# 或使用脚本
scripts/start.bat  # Windows
bash scripts/start.sh  # Linux/macOS
```

### Docker 部署

```bash
docker-compose up -d
```

## API 文档

启动后访问：

- Swagger UI: http://localhost:8080/docs
- ReDoc: http://localhost:8080/redoc

## 测试

```bash
# 运行所有测试
pytest

# 运行单元测试
pytest tests/unit/

# 运行集成测试
pytest tests/integration/

# 生成覆盖率报告
pytest --cov=kairos --cov-report=html
```

## 配置

通过环境变量或 `.env` 文件配置：

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `GEMMA4_ENV` | 运行环境 | `development` |
| `GEMMA4_HOST` | 监听地址 | `0.0.0.0` |
| `GEMMA4_MODEL` | 默认模型 | `gemma4:12b` |
| `GEMMA4_AUTH_ENABLED` | 启用认证 | `false` |
| `GEMMA4_JWT_SECRET` | JWT密钥 | - |

完整配置参考 `src/kairos/.env.example`。

## 贡献

请阅读 [CONTRIBUTING.md](CONTRIBUTING.md) 了解贡献指南。

## 许可证

[MIT License](LICENSE)

## 致谢

- Ollama - 本地大模型推理引擎
- FastAPI - 高性能 Web 框架
- ClawBot - 微信 iLink Bot SDK

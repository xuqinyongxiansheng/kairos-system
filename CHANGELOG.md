# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [4.1.0] - 2026-04-18

### Added
- 统一 LLM 客户端 (UnifiedLLMClient) - 融合3个LLM客户端
- 异步认知循环 - 6层认知架构全面异步化
- 循环协调器 (LoopCoordinator) - 统一管理5个自动化循环
- 统一记忆系统 V2 - 四层记忆架构整合
- ClawBot 微信通道集成 - Channel/Gateway 双模式
- 18个真实动作处理器 - 文件/Git/内存/HTTP操作
- 16个子配置系统 - 从9个扩展到16个
- 项目标准架构重构 - src/kairos/ 布局

### Changed
- 认知循环重写为完全异步
- OTAC引擎重写为完全异步
- HybridEngine 使用统一LLM客户端
- 技能系统/记忆系统改为兼容层

### Fixed
- cognitive_loop.py 缺少 import json
- clawbot_adapter.py MemoryType 作用域错误
- skill_system.py 错误的函数名引用
- skills/local_service/__init__.py 导入错误

## [4.0.0] - 2026-04-14

### Added
- 初始生产就绪版本
- FastAPI 后端架构
- 安全中间件体系
- 事件系统
- 降级管理器

## [3.0.0] - 2026-04-12

### Added
- 多智能体协作系统
- 技能适配器架构
- 前端交互界面

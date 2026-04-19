# Changelog

## [4.1.0] - 2026-04-18

### Added
- 统一 LLM 客户端 (UnifiedLLMClient)
- 异步认知循环 - 6层认知架构
- 循环协调器 (LoopCoordinator)
- 统一记忆系统 V2
- ClawBot 微信通道集成
- 18个真实动作处理器
- 项目标准架构重构 (src/kairos/ 布局)

### Changed
- 认知循环/OTAC引擎重写为完全异步
- HybridEngine 使用统一LLM客户端
- 技能系统/记忆系统改为兼容层

### Fixed
- cognitive_loop.py 缺少 import json
- clawbot_adapter.py MemoryType 作用域错误
- skill_system.py 错误的函数名引用

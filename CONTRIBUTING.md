# 贡献指南

感谢你对 Kairos System 项目的关注！本文档将指导你如何参与项目贡献。

## 开发环境设置

1. Fork 并克隆仓库
2. 创建虚拟环境: `python -m venv .venv`
3. 安装开发依赖: `pip install -e ".[dev]"`
4. 复制配置: `cp src/kairos/.env.example .env`
5. 启动 Ollama 服务

## 开发流程

1. 创建功能分支: `git checkout -b feature/your-feature`
2. 编写代码和测试
3. 确保所有测试通过: `pytest`
4. 代码格式化: `ruff format .`
5. 代码检查: `ruff check .`
6. 类型检查: `mypy src/kairos`
7. 提交并推送: `git commit -m "feat: description"`
8. 创建 Pull Request

## 代码规范

- 遵循 PEP 8 风格
- 使用中文注释
- 函数/类添加文档字符串
- 类型注解完整
- 单元测试覆盖新功能

## 提交信息格式

遵循 [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` 新功能
- `fix:` 修复
- `docs:` 文档
- `refactor:` 重构
- `test:` 测试
- `chore:` 构建/工具

## 问题反馈

使用 GitHub Issues 提交 Bug 报告或功能请求。

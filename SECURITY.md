# 安全策略

## 报告安全漏洞

如果你发现安全漏洞，请**不要**通过公开的 GitHub Issue 报告。

请通过以下方式私下报告：
- 发送邮件至安全团队
- 使用 GitHub Security Advisories

## 安全措施

Kairos System 实施了以下安全措施：

- JWT 认证机制
- API 速率限制
- 请求签名验证
- IP 访问控制（白名单/黑名单）
- 输入验证和消毒
- 安全响应头
- HTTPS 强制（生产环境）
- 审计日志

## 生产环境检查清单

- [ ] 设置 `GEMMA4_AUTH_ENABLED=true`
- [ ] 配置强 JWT 密钥
- [ ] 启用 HTTPS
- [ ] 配置 IP 白名单
- [ ] 启用审计日志
- [ ] 设置速率限制

/**
 * 安全中心面板
 *
 * 展示EnhancedSecurityManager的115条防护规则，包括：
 * - SQL注入规则 (55条) - 分级展示
 * - XSS攻击规则 (35条) - 分类展示
 * - 命令注入规则 (15条)
 * - 其他规则 (10条)
 * - OWASP Top 10检测热力图
 * - 实时检测测试台（输入Payload验证）
 *
 * 采用Ink终端UI风格。
 */

import React, { useState, useCallback } from 'react';
import { Text, Box, useInput, useApp } from 'ink';
import Spinner from '../components/Spinner.js';

// ==================== 类型定义 ====================

/** 安全规则分类 */
type RuleCategory = 'sql' | 'xss' | 'cmd' | 'other';

/** 单条安全规则 */
interface SecurityRule {
  id: string;
  pattern: string;
  severity: number; // 1-4
  category: RuleCategory;
  description: string;
  examples?: string[];
}

/** OWASP Top 10 条目 */
interface OwaspItem {
  id: string;
  name: string;
  code: string;
  detectionRate: number; // 0-100%
  status: 'protected' | 'partial' | 'vulnerable';
}

/** Security Props */
interface SecurityProps {
  onClose?: () => void;
}

// ==================== 常量数据 ====================

/** 类别配置 */
const CATEGORY_CONFIG: Record<RuleCategory, {
  label: string;
  labelZh: string;
  color: string;
  count: number;
}> = {
  sql: { label: 'SQL Injection', labelZh: 'SQL注入', color: 'red', count: 55 },
  xss: { label: 'XSS', labelZh: 'XSS跨站', color: 'yellow', count: 35 },
  cmd: { label: 'CMD Injection', labelZh: '命令注入', color: 'magenta', count: 15 },
  other: { label: 'Other', labelZh: '其他', color: 'cyan', count: 10 },
};

/** 严重级别标签 */
const SEVERITY_LABELS: Record<number, { label: string; color: string }> = {
  1: { label: 'LOW', color: 'gray' },
  2: { label: 'MEDIUM', color: 'yellow' },
  3: { label: 'HIGH', color: 'red' },
  4: { label: 'CRITICAL', color: 'white' },
};

/** 示例规则数据（部分代表性规则） */
const SAMPLE_RULES: SecurityRule[] = [
  // SQL Injection (5 examples from 55)
  { id: 'sql-001', pattern: "('\\s*(OR|AND)\\s*['\"]?\\d+)", severity: 4, category: 'sql', description: '基础OR/AND注入', examples: ["' OR 1=1--", "' OR '1'='1"] },
  { id: 'sql-002', pattern: "(;\\s*DROP\\s+TABLE)", severity: 4, category: 'sql', description: 'DROP TABLE注入', examples: ["'; DROP TABLE users; --"] },
  { id: 'sql-003', pattern: "(UNION\\s+(ALL\\s+)?SELECT)", severity: 4, category: 'sql', description: 'UNION SELECT注入', examples: ["' UNION SELECT * FROM users--"] },
  { id: 'sql-004', pattern: "\\b(INFORMATION_SCHEMA)\\b", severity: 4, category: 'sql', description: '信息schema探测', examples: ["SELECT * FROM INFORMATION_SCHEMA.TABLES"] },
  { id: 'sql-005', pattern: "('\\$\\{\\$where':})", severity: 4, category: 'sql', description: 'NoSQL注入(MongoDB)', examples: ['{"$where": "this.password == \'admin\'"}'] },

  // XSS (5 examples from 35)
  { id: 'xss-001', pattern: '(<script[\\s>])', severity: 4, category: 'xss', description: 'Script标签注入', examples: ['<script>alert(1)</script>'] },
  { id: 'xss-002', pattern: '(javascript\\s*:)', severity: 3, category: 'xss', description: 'JavaScript伪协议', examples: ['javascript:alert(document.cookie)'] },
  { id: 'xss-003', pattern: '(on\\w+\\s*=)', severity: 3, category: 'xss', description: '事件处理器注入', examples: ['<img onerror=alert(1)>'] },
  { id: 'xss-004', pattern: '(&#x?27;)', severity: 2, category: 'xss', description: 'HTML实体编码绕过', examples: [ '&#x27;', "&#39;" ] },
  { id: 'xss-005', pattern: '(<svg[\\s>])', severity: 3, category: 'xss', description: 'SVG向量注入', examples: ['<svg onload=alert(1)>'] },

  // CMD Injection (3 examples from 15)
  { id: 'cmd-001', pattern: '(;\\s*(ls|cat|rm|wget|curl|bash|sh)\\b)', severity: 4, category: 'cmd', description: '命令链注入', examples: ['; cat /etc/passwd', '; rm -rf /'] },
  { id: 'cmd-002', pattern: '(\\$\\(.*\\))', severity: 4, category: 'cmd', description: '命令替换注入', examples: ['$(cat /etc/passwd)', '`id`'] },
  { id: 'cmd-003', pattern: '(\\|\\s*(sh|bash|python|perl)\\b)', severity: 4, category: 'cmd', description: '管道命令注入', examples: ['| sh', '| bash -i'] },

  // Other (2 examples from 10)
  { id: 'oth-001', pattern: '(\\.\\./)', severity: 3, category: 'other', description: '路径遍历攻击', examples: ['../../../etc/passwd', '..\\..\\..\\windows\\system32'] },
  { id: 'oth-002', pattern: '(/etc/passwd|/etc/shadow)', severity: 3, category: 'other', description: '敏感文件访问', examples: ['/etc/passwd', '/etc/shadow'] },
];

/** OWASP Top 10 数据 */
const OWASP_DATA: OwaspItem[] = [
  { id: 'owasp-01', name: 'Broken Access Control', code: 'A01:2021', detectionRate: 95, status: 'protected' },
  { id: 'owasp-02', name: 'Cryptographic Failures', code: 'A02:2021', detectionRate: 80, status: 'protected' },
  { id: 'owasp-03', name: 'Injection (SQL/XSS/CMD)', code: 'A03:2021', detectionRate: 78, status: 'protected' },
  { id: 'owasp-04', name: 'Insecure Design', code: 'A04:2021', detectionRate: 60, status: 'partial' },
  { id: 'owasp-05', name: 'Security Misconfiguration', code: 'A05:2021', detectionRate: 85, status: 'protected' },
  { id: 'owasp-06', name: 'Vulnerable Components', code: 'A06:2021', detectionRate: 70, status: 'partial' },
  { id: 'owasp-07', name: 'Auth & Session Failures', code: 'A07:2021', detectionRate: 90, status: 'protected' },
  { id: 'owasp-08', name: 'Software & Data Integrity', code: 'A08:2021', detectionRate: 75, status: 'partial' },
  { id: 'owasp-09', name: 'Logging & Monitoring Failures', code: 'A09:2021', detectionRate: 65, status: 'partial' },
  { id: 'owasp-10', name: 'Server-Side Request Forgery', code: 'A10:2021', detectionRate: 70, status: 'partial' },
];

// ==================== 主组件 ====================

export function Security({ onClose }: SecurityProps): JSX.Element {
  const { exit } = useApp();

  // 状态
  const [activeTab, setActiveTab] = useState<'rules' | 'owasp' | 'test'>('rules');
  const [selectedCategory, setSelectedCategory] = useState<RuleCategory>('sql');
  const [selectedRule, setSelectedRule] = useState<SecurityRule | null>(null);
  const [testInput, setTestInput] = useState('');
  const [testResult, setTestResult] = useState<{ matched: boolean; rules: string[]; riskLevel: string } | null>(null);
  const [isTesting, setIsTesting] = useState(false);

  /**
   * 切换Tab
   */
  const switchTab = (tab: typeof activeTab) => {
    setActiveTab(tab);
    if (tab === 'rules') {
      setSelectedRule(null);
    }
  };

  /**
   * 模拟检测测试（前端本地匹配演示）
   */
  const runDetectionTest = useCallback(async () => {
    if (!testInput.trim()) return;

    setIsTesting(true);

    // 模拟延迟
    await new Promise(resolve => setTimeout(resolve, 500));

    try {
      const matchedRules: string[] = [];
      let maxSeverity = 0;

      for (const rule of SAMPLE_RULES) {
        try {
          const regex = new RegExp(rule.pattern, 'i');
          if (regex.test(testInput)) {
            matchedRules.push(`${rule.id}: ${rule.description}`);
            if (rule.severity > maxSeverity) maxSeverity = rule.severity;
          }
        } catch {
          // 忽略无效正则
        }
      }

      const riskLevelMap: Record<number, string> = {
        0: 'SAFE',
        1: 'LOW',
        2: 'MEDIUM',
        3: 'HIGH',
        4: 'CRITICAL',
      };

      setTestResult({
        matched: matchedRules.length > 0,
        rules: matchedRules,
        riskLevel: riskLevelMap[maxSeverity],
      });
    } catch (err) {
      console.error('Detection test error:', err);
    } finally {
      setIsTesting(false);
    }
  }, [testInput]);

  // 键盘导航
  useInput((input, key) => {
    if (key.escape || (key.ctrl && input === 'c')) {
      onClose?.() || exit();
      return;
    }

    // Tab切换
    if (input === '1') switchTab('rules');
    if (input === '2') switchTab('owasp');
    if (input === '3') switchTab('test');

    // 规则页面的类别切换
    if (activeTab === 'rules') {
      if (input === 'q') setSelectedCategory('sql');
      if (input === 'w') setSelectedCategory('xss');
      if (input === 'e') setSelectedCategory('cmd');
      if (input === 'r') setSelectedCategory('other');
    }

    // 测试页面的执行
    if (activeTab === 'test' && key.return && testInput.trim()) {
      runDetectionTest();
    }

    // 选择规则详情
    if (activeTab === 'rules' && selectedRule && (input === 'd' || input === 'D')) {
      setSelectedRule(null);
    }
  });

  /**
   * 渲染头部
   */
  const renderHeader = (): JSX.Element => (
    <Box flexDirection="column" borderStyle="single" paddingX={1}>
      <Box justifyContent="center">
        <Text bold color="red">
          {'=' .repeat(20)} Security Center {'=' .repeat(20)}
        </Text>
      </Box>
      <Box justifyContent="center" marginTop={0}>
        <Text bold>
          EnhancedSecurityManager v2.0 | 115 Rules | 77.8% Detection Rate
        </Text>
      </Box>

      {/* Tab导航 */}
      <Box justifyContent="center" marginTop={0} gap={2}>
        {[['1', 'Rules', activeTab === 'rules'], ['2', 'OWASP Top 10', activeTab === 'owasp'], ['3', 'Test Bench', activeTab === 'test']].map(([key, label, isActive]) => (
          <Text key={String(key)} bold color={isActive ? 'cyan' : 'dimColor'}>
            [{key}] {label}
          </Text>
        ))}
      </Box>
    </Box>
  );

  /**
   * 渲染规则列表视图
   */
  const renderRulesView = (): JSX.Element => {
    const config = CATEGORY_CONFIG[selectedCategory];
    const filteredRules = SAMPLE_RULES.filter(r => r.category === selectedCategory);

    return (
      <Box flexDirection="column" height="100%" marginTop={1}>
        {/* 类别选择器 */}
        <Box flexDirection="row" gap={2} marginBottom={1}>
          {(Object.entries(CATEGORY_CONFIG) as [RuleCategory, typeof CATEGORY_CONFIG[RuleCategory]][]).map(([key, cfg]) => (
            <Box
              key={key}
              paddingX={1}
              borderStyle={selectedCategory === key ? 'bold' : undefined}
              borderColor={selectedCategory === key ? 'cyan' : undefined}
              onClick={() => setSelectedCategory(key)}
            >
              <Text bold color={cfg.color}>{cfg.labelZh}</Text>
              <Text dimColor> ({cfg.count})</Text>
            </Box>
          ))}
          <Text dimColor>Q:SQL W:XSS E:CMD R:Other</Text>
        </Box>

        {/* 规则列表或详情 */}
        {selectedRule ? (
          renderRuleDetail()
        ) : (
          <>
            {/* 规则列表 */}
            <Text bold color={config.color}>{config.label} Rules ({config.count} total)</Text>

            {filteredRules.map(rule => (
              <Box
                key={rule.id}
                marginTop={0}
                paddingX={1}
                borderStyle="round"
                flexDirection="column"
                onClick={() => setSelectedRule(rule)}
              >
                <Box justifyContent="space-between">
                  <Text bold>{rule.id}</Text>
                  <Text color={SEVERITY_LABELS[rule.severity].color}>
                    [{SEVERITY_LABELS[rule.severity].label}]
                  </Text>
                </Box>
                <Text>{rule.description}</Text>
                <Text dimColor>Pattern: {rule.pattern.substring(0, 50)}...</Text>
                <Text dimColor color="cyan">Enter to view details</Text>
              </Box>
            ))}

            {/* 提示 */}
            <Box marginTop={1}>
              <Text dimColor>
                Showing {filteredRules.length}/{config.count} sample rules.
                Press Enter on a rule to see details.
              </Text>
            </Box>
          </>
        )}
      </Box>
    );
  };

  /**
   * 渲染规则详情
   */
  const renderRuleDetail = (): JSX.Element => {
    if (!selectedRule) return null;

    const config = CATEGORY_CONFIG[selectedRule.category];
    const severityInfo = SEVERITY_LABELS[selectedRule.severity];

    return (
      <Box flexDirection="column" borderStyle="bold" borderColor="cyan" paddingX={1}>
        <Box justifyContent="space-between">
          <Text bold color="white">Rule Detail: {selectedRule.id}</Text>
          <Text color="yellow">D: Back to list</Text>
        </Box>

        <Box marginTop={1} flexDirection="column">
          <Box>
            <Text bold>Description: </Text>
            <Text>{selectedRule.description}</Text>
          </Box>

          <Box marginTop={0}>
            <Text bold>Category: </Text>
            <Text color={config.color}>{config.label}</Text>
          </Box>

          <Box marginTop={0}>
            <Text bold>Severity: </Text>
            <Text color={severityInfo.color} bold>[{severityInfo.label}]</Text>
          </Box>

          <Box marginTop={1}>
            <Text bold>Pattern:</Text>
            <Text color="magenta">{selectedRule.pattern}</Text>
          </Box>

          {selectedRule.examples && selectedRule.examples.length > 0 && (
            <Box marginTop={1} flexDirection="column">
              <Text bold>Examples:</Text>
              {selectedRule.examples.map((ex, i) => (
                <Text key={i} color="red">{`  - ${ex}`}</Text>
              ))}
            </Box>
          )}
        </Box>
      </Box>
    );
  };

  /**
   * 渲染OWASP视图
   */
  const renderOwaspView = (): JSX.Element => {
    return (
      <Box flexDirection="column" marginTop={1}>
        <Text bold color="yellow">OWASP Top 10 (2021) Coverage</Text>

        {/* 表头 */}
        <Box marginTop={1} borderStyle="single" paddingX={1}>
          <Box flexDirection="row">
            <Text bold width={14}>Code</Text>
            <Text bold width={30}>Vulnerability</Text>
            <Text bold width={12}>Coverage</Text>
            <Text bold width={12}>Status</Text>
          </Box>
        </Box>

        {/* 数据行 */}
        {OWASP_DATA.map(item => {
          const barWidth = Math.round(item.detectionRate / 100 * 20);
          const bar = '#'.repeat(barWidth) + '-'.repeat(20 - barWidth);
          const statusColor =
            item.status === 'protected' ? 'green' :
            item.status === 'partial' ? 'yellow' : 'red';

          return (
            <Box key={item.id} paddingX={1} borderStyle="round">
              <Box flexDirection="row">
                <Text width={14} bold color="cyan">{item.code}</Text>
                <Text width={30}>{item.name.substring(0, 28)}</Text>
                <Text width={22}>
                  <Text color={item.detectionRate >= 80 ? 'green' : item.detectionRate >= 60 ? 'yellow' : 'red'}>
                    {bar} {item.detectionRate}%
                  </Text>
                </Text>
                <Text width={12} color={statusColor} bold>
                  [{item.status.toUpperCase()}]
                </Text>
              </Box>
            </Box>
          );
        })}

        {/* 统计摘要 */}
        <Box marginTop={1} borderStyle="round" paddingX={1}>
          <Text bold>Summary:</Text>
          <Text>
            Protected: <Text color="green">{OWASP_DATA.filter(o => o.status === 'protected').length}/10</Text>
            {' | '}
            Partial: <Text color="yellow">{OWASP_DATA.filter(o => o.status === 'partial').length}/10</Text>
            {' | '}
            Avg Coverage: <Text bold>{(OWASP_DATA.reduce((a, o) => a + o.detectionRate, 0) / 10).toFixed(1)}%</Text>
          </Text>
        </Box>
      </Box>
    );
  };

  /**
   * 渲染测试台视图
   */
  const renderTestView = (): JSX.Element => {
    return (
      <Box flexDirection="column" marginTop={1}>
        <Text bold color="magenta">Security Detection Test Bench</Text>

        {/* 输入区 */}
        <Box marginTop={1} borderStyle="single" paddingX={1}>
          <Text bold>Enter payload to test:</Text>
          <Box marginTop={0}>
            <Text color="cyan">
              {testInput || '(type your test payload and press Enter)...'}
            </Text>
          </Box>
          {isTesting && (
            <Box marginTop={0}>
              <Spinner />
              <Text> Analyzing...</Text>
            </Box>
          )}
        </Box>

        {/* 结果区 */}
        {testResult && (
          <Box marginTop={1} borderStyle="round" paddingX={1}
               backgroundColor={testResult.matched ? 'red' : 'green'}>
            <Box justifyContent="space-between">
              <Text bold color="white">
                Result: {testResult.matched ? 'DETECTED!' : 'SAFE'}
              </Text>
              <Text bold color="white">
                Risk Level: {testResult.riskLevel}
              </Text>
            </Box>

            {testResult.matched && (
              <Box marginTop={1} flexDirection="column">
                <Text bold color="white">Matched Rules:</Text>
                {testResult.rules.map((rule, i) => (
                  <Text key={i} color="yellow">  ! {rule}</Text>
                ))}
              </Box>
            )}

            {!testResult.matched && (
              <Text color="white">No attack patterns detected in input.</Text>
            )}
          </Box>
        )}

        {/* 预设Payload示例 */}
        <Box marginTop={1} flexDirection="column">
          <Text bold>Preset Payload Examples (copy & paste):</Text>
          <Box marginTop={0} flexDirection="column" dimColor>
            <Text>  1. ' OR 1=1--</Text>
            <Text>  2. &lt;script&gt;alert('XSS')&lt;/script&gt;</Text>
            <Text>  3. ; cat /etc/passwd</Text>
            <Text>  4. ../../../etc/passwd</Text>
            <Text>  5. javascript:alert(document.cookie)</Text>
          </Box>
        </Box>
      </Box>
    );
  };

  /**
   * 渲染底部提示
   */
  const renderFooter = (): JSX.Element => (
    <Box marginTop={1} borderStyle="single" paddingX={1}>
      <Text dimColor>
        1:Rules | 2:OWASP | 3:Test | Esc:Exit
        {activeTab === 'rules' && ' | Q/W/E/R: Category'}
        {activeTab === 'test' && ' | Enter: Test'}
        {selectedRule && ' | D: Back'}
      </Text>
    </Box>
  );

  // 主渲染
  return (
    <Box flexDirection="column" height="100%" padding={1}>
      {/* 头部 */}
      {renderHeader()}

      {/* 内容区域 */}
      {activeTab === 'rules' && renderRulesView()}
      {activeTab === 'owasp' && renderOwaspView()}
      {activeTab === 'test' && renderTestView()}

      {/* 底部提示 */}
      {renderFooter()}
    </Box>
  );
}

export default Security;

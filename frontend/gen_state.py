import os, re

src = 'src'
names = set()
for root, dirs, files in os.walk(src):
    for f in files:
        if f.endswith(('.ts', '.tsx')):
            path = os.path.join(root, f)
            try:
                content = open(path, encoding='utf-8').read()
                matches = re.findall(r'import\s*\{([^}]+)\}\s*from\s*[\'"].*bootstrap/state', content)
                for m in matches:
                    for name in m.split(','):
                        clean = name.strip().replace('type ', '')
                        if ' as ' in clean:
                            clean = clean.split(' as ')[0].strip()
                        if clean:
                            names.add(clean)
            except:
                pass

# 生成state.ts
lines = [
    '/**',
    ' * bootstrap/state.ts - 引导状态管理（自动生成）',
    ' * ',
    ' * 提供应用引导期间的全局状态管理功能。',
    ' * 所有导出均由脚本扫描源码导入自动生成。',
    ' */',
    '',
    'const _state: Record<string, any> = {',
    '  projectRoot: process.cwd(),',
    '  originalCwd: process.cwd(),',
    '  sessionId: `session_${Date.now()}`,',
    '  model: "gemma4:e4b",',
    '  initialized: true,',
    '  startTime: Date.now(),',
    '  lastInteractionTime: Date.now(),',
    '}',
    '',
    'function _noop(..._args: any[]) {}',
    'function _returnNull(): any { return null }',
    'function _returnTrue(): boolean { return true }',
    'function _returnFalse(): boolean { return false }',
    'function _returnZero(): number { return 0 }',
    'function _returnEmpty(): any[] { return [] }',
    'function _returnEmptyObj(): Record<string, any> { return {} }',
    'function _returnEmptyStr(): string { return "" }',
    '',
]

# 分类导出
getters = []
setters = []
others = []

for name in sorted(names):
    if name.startswith('get') or name.startswith('is') or name.startswith('has'):
        # 判断返回值类型
        if 'Dir' in name or 'Path' in name:
            impl = '() => "."'
        elif 'Id' in name or 'Token' in name or 'Override' in name or 'Version' in name:
            impl = '_returnNull'
        elif 'Name' in name or 'Type' in name or 'Provider' in name or 'Format' in name:
            impl = '() => ""'
        elif 'Mode' in name:
            impl = '() => "default"'
        elif 'Enabled' in name or 'Active' in name or 'Latched' in name:
            impl = '_returnFalse'
        elif 'Count' in name or 'Counter' in name or 'Tokens' in name or 'Budget' in name or 'Duration' in name:
            impl = '_returnZero'
        elif 'Interactive' in name or 'Production' in name or 'Terminal' in name or 'Healthy' in name or 'Remote' in name:
            impl = '_returnTrue'
        elif 'Cache' in name or 'Eligible' in name or 'Allowlist' in name:
            impl = '_returnFalse'
        elif 'Timestamp' in name or 'Time' in name:
            impl = '_returnZero'
        elif 'Dir' in name:
            impl = '() => "."'
        elif 'Root' in name or 'Cwd' in name:
            impl = '() => _state.projectRoot'
        elif 'Channels' in name or 'ColorMap' in name or 'Hooks' in name or 'Plugins' in name or 'Teams' in name or 'Skills' in name:
            impl = '_returnEmptyObj'
        elif 'Operations' in name or 'Betas' in name or 'Requests' in name or 'Messages' in name or 'Strings' in name:
            impl = '_returnEmpty'
        elif 'Store' in name or 'Settings' in name or 'Flags' in name or 'Config' in name or 'State' in name or 'Tracker' in name:
            impl = '_returnEmptyObj'
        elif 'SessionId' in name:
            impl = '() => _state.sessionId'
        else:
            impl = '_returnNull'
        getters.append(f'export const {name} = {impl}')
    elif name.startswith('set') or name.startswith('add') or name.startswith('remove') or name.startswith('clear') or name.startswith('reset') or name.startswith('mark') or name.startswith('register') or name.startswith('increment') or name.startswith('update') or name.startswith('flush') or name.startswith('handle') or name.startswith('append') or name.startswith('snapshot') or name.startswith('switch') or name.startswith('consume') or name.startswith('regenerate') or name.startswith('prefer') or name.startswith('on'):
        setters.append(f'export const {name} = _noop')
    else:
        # 类型或常量
        others.append(f'export const {name} = {{}}')

# 写入getter
lines.append('// Getter函数')
for line in getters:
    lines.append(line)
lines.append('')

# 写入setter
lines.append('// Setter/操作函数')
for line in setters:
    lines.append(line)
lines.append('')

# 写入其他
lines.append('// 类型/常量')
for line in others:
    lines.append(line)
lines.append('')

output = '\n'.join(lines)
with open('src/bootstrap/state.ts', 'w', encoding='utf-8') as f:
    f.write(output)

print(f'Generated {len(getters)} getters, {len(setters)} setters, {len(others)} others')
print(f'Total: {len(getters) + len(setters) + len(others)} exports')

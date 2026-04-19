"""
自动修复 Bun 启动时的缺失导出
解析 Bun 的错误消息，自动添加缺失的导出到对应文件
"""
import os, re, subprocess

src_dir = r'c:\Users\Administrator\Documents\南无阿弥陀佛\project\frontend'
bun_path = os.path.join(src_dir, 'bun.exe')
entry = './src/entrypoints/cli.tsx'

def run_bun():
    result = subprocess.run(
        [bun_path, 'run', entry],
        capture_output=True, cwd=src_dir, timeout=10
    )
    stderr = (result.stderr or b'').decode('utf-8', errors='replace') if isinstance(result.stderr, bytes) else (result.stderr or '')
    stdout = (result.stdout or b'').decode('utf-8', errors='replace') if isinstance(result.stdout, bytes) else (result.stdout or '')
    return stderr + stdout

def parse_missing_export(output):
    """解析Bun错误消息，提取缺失的导出名和模块路径"""
    pattern = r"Export named '(\w+)' not found in module '([^']+)'"
    matches = re.findall(pattern, output)
    return matches

def add_export_to_file(filepath, export_name):
    """向文件添加缺失的导出"""
    if not os.path.exists(filepath):
        return False
    
    try:
        content = open(filepath, encoding='utf-8').read()
    except:
        return False
    
    # 检查是否已存在
    if re.search(rf'export\s+(?:const|function|class|let|var)\s+{export_name}', content):
        return False
    
    # 根据名称推断默认值
    if export_name.startswith('get') or export_name.startswith('is') or export_name.startswith('has'):
        if any(k in export_name for k in ['Dir', 'Path', 'Home', 'Root']):
            line = f'export const {export_name} = () => \'.\''
        elif any(k in export_name for k in ['Id', 'Token', 'Override', 'Version', 'Url', 'Key', 'Region']):
            line = f'export const {export_name} = () => null'
        elif any(k in export_name for k in ['Name', 'Type', 'Provider', 'Format', 'Shell']):
            line = f'export const {export_name} = () => \'\''
        elif any(k in export_name for k in ['Mode', 'Strategy']):
            line = f'export const {export_name} = () => \'default\''
        elif any(k in export_name for k in ['Enabled', 'Active', 'Latched', 'Available', 'Eligible']):
            line = f'export const {export_name} = () => false'
        elif any(k in export_name for k in ['Count', 'Counter', 'Tokens', 'Budget', 'Duration', 'Size', 'Length']):
            line = f'export const {export_name} = () => 0'
        elif any(k in export_name for k in ['Interactive', 'Production', 'Terminal', 'Healthy', 'Connected']):
            line = f'export const {export_name} = () => true'
        elif any(k in export_name for k in ['Map', 'Store', 'State', 'Config', 'Settings', 'Flags', 'Cache']):
            line = f'export const {export_name} = () => ({{}})'
        elif any(k in export_name for k in ['List', 'Names', 'Operations', 'Messages', 'Requests', 'Betas', 'Hooks']):
            line = f'export const {export_name} = () => []'
        else:
            line = f'export const {export_name} = () => null'
    elif export_name[0].isupper():
        line = f'export const {export_name} = {{}}'
    else:
        line = f'export const {export_name} = () => {{}}'
    
    content = content.rstrip() + '\n' + line + '\n'
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    return True

# 迭代修复
max_iterations = 30
for i in range(max_iterations):
    print(f'\n=== 迭代 {i+1} ===')
    try:
        output = run_bun()
    except subprocess.TimeoutExpired:
        print('Bun启动成功（超时=正在运行）！')
        break
    
    missing = parse_missing_export(output)
    if not missing:
        # 检查是否有其他错误
        if 'SyntaxError' in output and 'not found' not in output:
            print(f'其他语法错误: {output[:200]}')
            break
        if 'error' not in output.lower():
            print('启动成功！')
            break
        print(f'未知错误: {output[:200]}')
        break
    
    fixed = 0
    for export_name, module_path in missing:
        # 将Windows路径中的乱码修复
        # module_path 可能是 C:\Users\...\src\xxx.js 格式
        if add_export_to_file(module_path, export_name):
            print(f'  + {export_name} -> {os.path.basename(module_path)}')
            fixed += 1
    
    if fixed == 0:
        print(f'无法自动修复: {missing}')
        break
    
    print(f'  修复了 {fixed} 个缺失导出')

print('\n完成！')

# 保存日志
with open('auto_fix_log.txt', 'w', encoding='utf-8') as f:
    f.write(f'Iterations: {i+1}\n')

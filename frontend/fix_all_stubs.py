"""
批量修复所有存根文件的缺失导出
直接扫描所有.ts/.tsx文件的import语句，确保所有.js存根都有对应的导出
"""
import os, re

src = 'src'
fixed_count = 0

def get_default(name):
    if name.startswith('get') or name.startswith('is') or name.startswith('has'):
        if any(k in name for k in ['Dir', 'Path', 'Home', 'Root']):
            return "() => '.'"
        elif any(k in name for k in ['Id', 'Token', 'Override', 'Version', 'Url', 'Key', 'Region']):
            return "() => null"
        elif any(k in name for k in ['Name', 'Type', 'Provider', 'Format', 'Shell']):
            return "() => ''"
        elif any(k in name for k in ['Mode', 'Strategy']):
            return "() => 'default'"
        elif any(k in name for k in ['Enabled', 'Active', 'Latched', 'Available', 'Eligible']):
            return "() => false"
        elif any(k in name for k in ['Count', 'Counter', 'Tokens', 'Budget', 'Duration', 'Size', 'Length']):
            return "() => 0"
        elif any(k in name for k in ['Interactive', 'Production', 'Terminal', 'Healthy', 'Connected']):
            return "() => true"
        elif any(k in name for k in ['Map', 'Store', 'State', 'Config', 'Settings', 'Flags', 'Cache', 'Record', 'Tracker']):
            return "() => ({})"
        elif any(k in name for k in ['List', 'Names', 'Operations', 'Messages', 'Requests', 'Betas', 'Hooks', 'Plugins', 'Teams', 'Skills', 'Tasks']):
            return "() => []"
        else:
            return "() => null"
    elif name[0].isupper():
        return "{}"
    else:
        return "() => {}"

# 收集所有导入
all_imports = {}

for root, dirs, files in os.walk(src):
    for f in files:
        if f.endswith(('.ts', '.tsx')):
            path = os.path.join(root, f)
            try:
                content = open(path, encoding='utf-8').read()
                matches = re.findall(r'import\s*\{([^}]+)\}\s*from\s*[\'"](\.\.?/[^\'"]+?)(?:\.js|\.ts)?[\'"]', content)
                for names_str, mod_path in matches:
                    base_dir = os.path.dirname(path)
                    abs_path = os.path.normpath(os.path.join(base_dir, mod_path))
                    for name in names_str.split(','):
                        clean = name.strip().replace('type ', '')
                        if ' as ' in clean:
                            clean = clean.split(' as ')[0].strip()
                        if clean:
                            if abs_path not in all_imports:
                                all_imports[abs_path] = set()
                            all_imports[abs_path].add(clean)
            except:
                pass

# 修复所有.js存根文件
for mod_path, needed_names in sorted(all_imports.items()):
    js_path = mod_path + '.js'
    ts_path = mod_path + '.ts'
    
    # 如果.ts存在，跳过（Bun会使用.ts）
    if os.path.exists(ts_path):
        continue
    
    # 如果.js不存在，创建
    if not os.path.exists(js_path):
        stub_dir = os.path.dirname(js_path)
        if stub_dir and not os.path.exists(stub_dir):
            os.makedirs(stub_dir, exist_ok=True)
        lines = [f'// {os.path.basename(js_path)} - 自动生成存根', '']
        for name in sorted(needed_names):
            lines.append(f'export const {name} = {get_default(name)}')
        content = '\n'.join(lines) + '\n'
        with open(js_path, 'w', encoding='utf-8') as f:
            f.write(content)
        fixed_count += 1
        print(f'Created: {js_path} ({len(needed_names)} exports)')
        continue
    
    # .js存在，检查缺失导出
    try:
        content = open(js_path, encoding='utf-8').read()
    except:
        continue
    
    existing = set(re.findall(r'export\s+(?:const|function|class|let|var)\s+(\w+)', content))
    missing = needed_names - existing
    
    if missing:
        lines = [content.rstrip(), '']
        for name in sorted(missing):
            lines.append(f'export const {name} = {get_default(name)}')
        new_content = '\n'.join(lines) + '\n'
        with open(js_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        fixed_count += 1
        print(f'Updated: {js_path} (+{len(missing)}: {", ".join(sorted(missing)[:5])})')

print(f'\nTotal: {fixed_count} files fixed')

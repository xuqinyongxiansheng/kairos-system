"""
自动生成所有缺失的存根模块
扫描所有import语句，找到不存在的目标文件，自动创建.js存根
"""
import os, re

src = 'src'
created = 0
skipped = 0

def get_default_export(name):
    """根据函数名推断默认返回值"""
    if name.startswith('get') or name.startswith('is') or name.startswith('has'):
        if any(k in name for k in ['Dir', 'Path', 'Home', 'Root']):
            return "() => '.'"
        elif any(k in name for k in ['Id', 'Token', 'Override', 'Version', 'Url', 'Key']):
            return "() => null"
        elif any(k in name for k in ['Name', 'Type', 'Provider', 'Format', 'Shell']):
            return "() => ''"
        elif any(k in name for k in ['Mode', 'Strategy']):
            return "() => 'default'"
        elif any(k in name for k in ['Enabled', 'Active', 'Latched', 'Available', 'Eligible']):
            return "() => false"
        elif any(k in name for k in ['Count', 'Counter', 'Tokens', 'Budget', 'Duration', 'Size', 'Length', 'Width', 'Height']):
            return "() => 0"
        elif any(k in name for k in ['Interactive', 'Production', 'Terminal', 'Healthy', 'Connected', 'Remote']):
            return "() => true"
        elif any(k in name for k in ['Map', 'Store', 'State', 'Config', 'Settings', 'Flags', 'Cache', 'Record', 'Tracker']):
            return "() => ({})"
        elif any(k in name for k in ['List', 'Names', 'Operations', 'Messages', 'Requests', 'Betas', 'Hooks', 'Plugins', 'Teams', 'Skills', 'Tasks']):
            return "() => []"
        else:
            return "() => null"
    elif name.startswith('create') or name.startswith('build') or name.startswith('make'):
        return "() => ({})"
    elif name[0].isupper():
        # 可能是类或类型
        return "{}"
    else:
        return "() => {}"

# 收集所有导入
all_imports = {}  # module_path -> set of names

for root, dirs, files in os.walk(src):
    for f in files:
        if f.endswith(('.ts', '.tsx')):
            path = os.path.join(root, f)
            try:
                content = open(path, encoding='utf-8').read()
                # 匹配所有相对路径导入
                import_pattern = r'import\s*\{([^}]+)\}\s*from\s*[\'"](\.\.?/[^\'"]+?)(?:\.js|\.ts)?[\'"]'
                matches = re.findall(import_pattern, content)
                for names_str, mod_path in matches:
                    # 解析绝对路径
                    base_dir = os.path.dirname(path)
                    abs_path = os.path.normpath(os.path.join(base_dir, mod_path))
                    abs_path = abs_path.replace('\\', '/')
                    
                    # 解析导入名称
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

# 检查哪些模块不存在，创建存根
for mod_path in sorted(all_imports.keys()):
    names = sorted(all_imports[mod_path])
    
    # 检查文件是否存在（.ts, .tsx, .js, .jsx）
    exists = False
    for ext in ['.ts', '.tsx', '.js', '.jsx', '.json']:
        if os.path.exists(mod_path + ext):
            exists = True
            break
    # 检查是否是目录（有index）
    if os.path.isdir(mod_path):
        for idx in ['index.ts', 'index.tsx', 'index.js']:
            if os.path.exists(os.path.join(mod_path, idx)):
                exists = True
                break
    
    if exists:
        skipped += 1
        continue
    
    # 创建存根文件
    # 确定文件路径（使用.js扩展名）
    stub_path = mod_path + '.js'
    
    # 确保目录存在
    stub_dir = os.path.dirname(stub_path)
    if stub_dir and not os.path.exists(stub_dir):
        os.makedirs(stub_dir, exist_ok=True)
    
    # 生成内容
    lines = [f'// {os.path.basename(stub_path)} - 自动生成存根']
    lines.append('')
    
    for name in names:
        if name[0].isupper() and not name.startswith('get') and not name.startswith('is') and not name.startswith('has') and not name.startswith('set') and not name.startswith('add') and not name.startswith('remove') and not name.startswith('clear') and not name.startswith('reset') and not name.startswith('create') and not name.startswith('build'):
            # 可能是类型或常量
            lines.append(f'export const {name} = {{}}')
        else:
            default = get_default_export(name)
            lines.append(f'export const {name} = {default}')
    
    content = '\n'.join(lines) + '\n'
    
    try:
        with open(stub_path, 'w', encoding='utf-8') as f:
            f.write(content)
        created += 1
        print(f'Created: {stub_path} ({len(names)} exports)')
    except Exception as e:
        print(f'Error creating {stub_path}: {e}')

print(f'\nTotal: {created} stubs created, {skipped} existing modules skipped')

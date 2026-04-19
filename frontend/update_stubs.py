import os, re

src = 'src'
all_needed = {}

for root, dirs, files in os.walk(src):
    for f in files:
        if f.endswith(('.ts', '.tsx')):
            path = os.path.join(root, f)
            try:
                content = open(path, encoding='utf-8').read()
                import_matches = re.findall(r'import\s*\{([^}]+)\}\s*from\s*[\'"]([^\'"]+)[\'"]', content)
                for names_str, mod_path in import_matches:
                    if not mod_path.startswith('.'):
                        continue
                    base_dir = os.path.dirname(path)
                    abs_path = os.path.normpath(os.path.join(base_dir, mod_path))
                    abs_path = abs_path.replace('\\', '/')
                    for name in names_str.split(','):
                        clean = name.strip().replace('type ', '')
                        if ' as ' in clean:
                            clean = clean.split(' as ')[0].strip()
                        if clean:
                            if abs_path not in all_needed:
                                all_needed[abs_path] = set()
                            all_needed[abs_path].add(clean)
            except:
                pass

# 检查已存在的.js存根文件，补全缺失的导出
updated = 0
for mod_path, needed_names in sorted(all_needed.items()):
    # 检查.js文件
    js_path = mod_path + '.js'
    if not os.path.exists(js_path):
        continue
    
    # 读取现有导出
    try:
        content = open(js_path, encoding='utf-8').read()
    except:
        continue
    
    existing_exports = set(re.findall(r'export\s+(?:const|function|class|let|var)\s+(\w+)', content))
    
    # 找出缺失的导出
    missing = needed_names - existing_exports
    if not missing:
        continue
    
    # 追加缺失的导出
    lines = [content.rstrip()]
    lines.append('')
    for name in sorted(missing):
        if name[0].isupper() and not any(name.startswith(p) for p in ['get', 'is', 'has', 'set', 'add', 'remove', 'clear', 'reset', 'create', 'build', 'mark', 'register', 'increment', 'update', 'handle', 'switch', 'flush', 'append', 'snapshot', 'on', 'prefer', 'consume', 'regenerate']):
            lines.append(f'export const {name} = {{}}')
        elif name.startswith('get') or name.startswith('is') or name.startswith('has'):
            if any(k in name for k in ['Dir', 'Path', 'Home', 'Root']):
                lines.append(f'export const {name} = () => \'.\'')
            elif any(k in name for k in ['Id', 'Token', 'Override', 'Version', 'Url', 'Key', 'Region']):
                lines.append(f'export const {name} = () => null')
            elif any(k in name for k in ['Name', 'Type', 'Provider', 'Format', 'Shell']):
                lines.append(f'export const {name} = () => \'\'')
            elif any(k in name for k in ['Mode', 'Strategy']):
                lines.append(f'export const {name} = () => \'default\'')
            elif any(k in name for k in ['Enabled', 'Active', 'Latched', 'Available', 'Eligible']):
                lines.append(f'export const {name} = () => false')
            elif any(k in name for k in ['Count', 'Counter', 'Tokens', 'Budget', 'Duration', 'Size', 'Length']):
                lines.append(f'export const {name} = () => 0')
            elif any(k in name for k in ['Interactive', 'Production', 'Terminal', 'Healthy', 'Connected']):
                lines.append(f'export const {name} = () => true')
            elif any(k in name for k in ['Map', 'Store', 'State', 'Config', 'Settings', 'Flags', 'Cache', 'Record']):
                lines.append(f'export const {name} = () => ({{}})')
            elif any(k in name for k in ['List', 'Names', 'Operations', 'Messages', 'Requests', 'Betas', 'Hooks']):
                lines.append(f'export const {name} = () => []')
            else:
                lines.append(f'export const {name} = () => null')
        else:
            lines.append(f'export const {name} = () => {{}}')
    
    new_content = '\n'.join(lines) + '\n'
    with open(js_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    updated += 1
    print(f'Updated: {js_path} (+{len(missing)} exports: {", ".join(sorted(missing)[:5])}{"..." if len(missing) > 5 else ""})')

print(f'\nTotal: {updated} files updated')

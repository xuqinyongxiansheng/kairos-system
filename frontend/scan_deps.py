import os, re

src = 'src'
results = {}

for root, dirs, files in os.walk(src):
    for f in files:
        if f.endswith(('.ts', '.tsx')):
            path = os.path.join(root, f)
            try:
                content = open(path, encoding='utf-8').read()
                # 找所有from '../xxx' 或 from '../../xxx' 等相对路径导入
                matches = re.findall(r'from\s*[\'"](\.\.?/[^\'"]+?)(?:\.js|\.ts)?[\'"]', content)
                for mod_path in matches:
                    # 解析相对路径为绝对路径
                    base_dir = os.path.dirname(path)
                    abs_path = os.path.normpath(os.path.join(base_dir, mod_path))
                    # 提取导入的名称
                    import_matches = re.findall(
                        r'import\s*\{([^}]+)\}\s*from\s*[\'"]' + re.escape(mod_path) + r'(?:\.js|\.ts)?[\'"]',
                        content
                    )
                    for m in import_matches:
                        for name in m.split(','):
                            clean = name.strip().replace('type ', '')
                            if ' as ' in clean:
                                clean = clean.split(' as ')[0].strip()
                            if clean:
                                key = abs_path.replace('\\', '/')
                                if key not in results:
                                    results[key] = set()
                                results[key].add(clean)
            except:
                pass

# 输出需要修复的存根文件
for key in sorted(results.keys()):
    names = sorted(results[key])
    if len(names) > 3:  # 只显示导入较多的模块
        print(f'{key}: {len(names)} imports')
        for n in names[:10]:
            print(f'  {n}')
        if len(names) > 10:
            print(f'  ... and {len(names)-10} more')
        print()

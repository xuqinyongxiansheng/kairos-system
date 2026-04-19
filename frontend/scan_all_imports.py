import os, re

src = 'src'
# 扫描所有.js存根文件的导入需求
stub_files = {
    'utils/envUtils': 'utils/envUtils.js',
    'utils/array': 'utils/array.js',
    'utils/format': 'utils/format.js',
    'utils/theme': 'utils/theme.js',
    'utils/effort': 'utils/effort.js',
    'utils/model/model': 'utils/model/model.js',
    'utils/config': 'utils/config.js',
    'utils/tasks': 'utils/tasks.js',
    'utils/activityManager': 'utils/activityManager.js',
    'constants/spinnerVerbs': 'constants/spinnerVerbs.js',
    'constants/figures': 'constants/figures.js',
    'services/analytics/index': 'services/analytics/index.js',
    'services/security': 'services/security.js',
    'services/skillSearch/featureCheck': 'services/skillSearch/featureCheck.js',
    'services/skillSearch/prefetch': 'services/skillSearch/prefetch.js',
    'services/analytics/growthbook': 'services/analytics/growthbook.js',
    'bridge/bridgeStatusUtil': 'bridge/bridgeStatusUtil.js',
    'Tool': 'Tool.js',
    'commands': 'commands.js',
    'cwd': 'utils/cwd.js',
    'types/message': 'types/message.js',
    'types/textInputTypes': 'types/textInputTypes.js',
    'types/command': 'types/command.js',
    'cost-tracker': 'cost-tracker.js',
    'query': 'query.js',
    'tools': 'tools.js',
    'Task': 'Task.js',
    'context': 'context.js',
    'memdir/memdir': 'memdir/memdir.js',
    'memdir/paths': 'memdir/paths.js',
    'memdir/memoryAge': 'memdir/memoryAge.js',
    'schemas/hooks': 'schemas/hooks.js',
    'coordinator/coordinatorMode': 'coordinator/coordinatorMode.js',
    'skills/loadSkillsDir': 'skills/loadSkillsDir.js',
    'buddy/prompt': 'buddy/prompt.js',
    'outputStyles/loadOutputStylesDir': 'outputStyles/loadOutputStylesDir.js',
    'plugins/builtinPlugins': 'plugins/builtinPlugins.js',
}

for module_key, stub_path in stub_files.items():
    names = set()
    full_path = os.path.join(src, stub_path)
    
    for root, dirs, files in os.walk(src):
        for f in files:
            if f.endswith(('.ts', '.tsx')):
                path = os.path.join(root, f)
                try:
                    content = open(path, encoding='utf-8').read()
                    # 匹配各种导入模式
                    patterns = [
                        rf'import\s*\{{([^}}]+)}}\s*from\s*[\'"][^\'"]*{re.escape(module_key)}',
                        rf'import\s*\{{([^}}]+)}}\s*from\s*[\'"][^\'"]*/{re.escape(module_key.split("/")[-1])}',
                    ]
                    for pattern in patterns:
                        matches = re.findall(pattern, content)
                        for m in matches:
                            for name in m.split(','):
                                clean = name.strip().replace('type ', '')
                                if ' as ' in clean:
                                    clean = clean.split(' as ')[0].strip()
                                if clean:
                                    names.add(clean)
                except:
                    pass
    
    if names:
        print(f'=== {stub_path} ===')
        for n in sorted(names):
            print(f'  {n}')

#!/usr/bin/env python3
"""
claw技能适配器
用于将clawhub-skills项目的技能集成到skills系统中
"""

import os
import re
import json
from typing import Dict, Any, List, Optional

from ..plugins import Plugin, PluginManager, get_plugin_manager


class ClawSkillAdapter:
    """claw技能适配器"""
    
    def __init__(self, claw_skills_dir: str = "clawhub-skills"):
        self.claw_skills_dir = claw_skills_dir
        self.skills: Dict[str, Dict[str, Any]] = {}
        self._load_skills()
    
    def _load_skills(self):
        """加载claw技能"""
        if not os.path.exists(self.claw_skills_dir):
            return
        
        # 遍历所有技能目录
        for root, dirs, files in os.walk(self.claw_skills_dir):
            for file in files:
                if file == "SKILL.md":
                    skill_path = os.path.join(root, file)
                    skill_data = self._parse_skill(skill_path)
                    if skill_data:
                        skill_name = os.path.basename(root)
                        self.skills[skill_name] = skill_data
    
    def _parse_skill(self, skill_file: str) -> Optional[Dict[str, Any]]:
        """解析技能文件"""
        try:
            with open(skill_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 解析Front Matter
            front_matter_match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
            if not front_matter_match:
                return None
            
            front_matter = front_matter_match.group(1)
            skill_data = {}
            
            # 解析front matter
            for line in front_matter.strip().split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    if key == 'tags':
                        # 解析标签
                        tags = [tag.strip() for tag in value.strip('[]').split(',')]
                        skill_data[key] = tags
                    else:
                        skill_data[key] = value
            
            # 解析内容
            content_body = content[front_matter_match.end():]
            skill_data['content'] = content_body
            
            # 提取命令
            commands = self._extract_commands(content_body)
            if commands:
                skill_data['commands'] = commands
            
            return skill_data
        except Exception as e:
            print(f"解析技能文件失败: {e}")
            return None
    
    def _extract_commands(self, content: str) -> List[Dict[str, Any]]:
        """提取命令"""
        commands = []
        # 查找命令部分
        command_section_match = re.search(r'## Commands(.*?)(?=##|$)', content, re.DOTALL)
        if command_section_match:
            command_section = command_section_match.group(1)
            # 查找命令定义
            command_matches = re.findall(r'### \d+\. `(.*?)`(.*?)(?=###|$)', command_section, re.DOTALL)
            for command_name, command_content in command_matches:
                command_info = {
                    "name": command_name,
                    "description": self._extract_description(command_content),
                    "examples": self._extract_examples(command_content)
                }
                commands.append(command_info)
        return commands
    
    def _extract_description(self, content: str) -> str:
        """提取命令描述"""
        # 提取描述（第一个段落）
        lines = content.strip().split('\n')
        for line in lines:
            line = line.strip()
            if line and not line.startswith('```'):
                return line
        return ""
    
    def _extract_examples(self, content: str) -> List[Dict[str, Any]]:
        """提取命令示例"""
        examples = []
        # 查找代码块
        code_blocks = re.findall(r'```bash(.*?)```', content, re.DOTALL)
        for i, code_block in enumerate(code_blocks):
            lines = code_block.strip().split('\n')
            if lines:
                command = lines[0].strip()
                output = '\n'.join(lines[2:]) if len(lines) > 2 else ""
                examples.append({
                    "command": command,
                    "output": output
                })
        return examples
    
    def list_skills(self) -> List[str]:
        """列出所有技能"""
        return list(self.skills.keys())
    
    def get_skill(self, skill_name: str) -> Optional[Dict[str, Any]]:
        """获取技能详情"""
        return self.skills.get(skill_name)
    
    def convert_to_plugin(self, skill_name: str) -> Optional[Plugin]:
        """将claw技能转换为插件"""
        skill_data = self.get_skill(skill_name)
        if not skill_data:
            return None
        
        # 创建插件类
        class ClawSkillPlugin(Plugin):
            def __init__(self, skill_data):
                super().__init__()
                self.name = skill_data.get('name', skill_name)
                self.version = skill_data.get('version', '1.0.0')
                self.description = skill_data.get('description', '')
                self.author = skill_data.get('author', 'clawhub')
                self.skill_data = skill_data
            
            def initialize(self, context):
                print(f"初始化claw技能插件: {self.name}")
                return True
            
            def shutdown(self):
                print(f"关闭claw技能插件: {self.name}")
                return True
            
            def get_commands(self):
                commands = {}
                if 'commands' in self.skill_data:
                    for cmd_info in self.skill_data['commands']:
                        cmd_name = cmd_info['name']
                        def create_handler(cmd_info):
                            def handler(*args, **kwargs):
                                print(f"执行claw命令: {cmd_info['name']}")
                                print(f"描述: {cmd_info['description']}")
                                if cmd_info['examples']:
                                    print("示例:")
                                    for example in cmd_info['examples']:
                                        print(f"  命令: {example['command']}")
                                        if example['output']:
                                            print(f"  输出: {example['output']}")
                                return {"status": "success", "message": f"执行命令: {cmd_info['name']}"}
                            return handler
                        commands[cmd_name] = create_handler(cmd_info)
                return commands
            
            def get_hooks(self):
                return {}
        
        return ClawSkillPlugin(skill_data)
    
    def register_all_skills(self):
        """注册所有技能为插件"""
        plugin_manager = get_plugin_manager()
        for skill_name in self.list_skills():
            plugin = self.convert_to_plugin(skill_name)
            if plugin:
                # 注册插件
                plugin_manager.load_plugin(os.path.join(self.claw_skills_dir, skill_name))
                print(f"注册claw技能: {skill_name}")


# 全局claw技能适配器实例
_claw_skill_adapter = None

def get_claw_skill_adapter() -> ClawSkillAdapter:
    """获取claw技能适配器实例"""
    global _claw_skill_adapter
    if _claw_skill_adapter is None:
        _claw_skill_adapter = ClawSkillAdapter()
    return _claw_skill_adapter


if __name__ == "__main__":
    # 测试
    adapter = get_claw_skill_adapter()
    
    # 列出技能
    skills = adapter.list_skills()
    print(f"发现 {len(skills)} 个claw技能:")
    for skill in skills[:10]:  # 只显示前10个
        print(f"  - {skill}")
    
    # 查看技能详情
    if skills:
        skill_name = skills[0]
        skill_data = adapter.get_skill(skill_name)
        print(f"\n技能详情: {skill_name}")
        print(f"描述: {skill_data.get('description', '')}")
        print(f"版本: {skill_data.get('version', '')}")
        print(f"作者: {skill_data.get('author', '')}")
        print(f"标签: {skill_data.get('tags', [])}")
        
        if 'commands' in skill_data:
            print("\n命令:")
            for cmd in skill_data['commands']:
                print(f"  - {cmd['name']}: {cmd['description']}")
    
    # 注册技能为插件
    print("\n注册技能为插件...")
    adapter.register_all_skills()
#!/usr/bin/env python3
"""
多语言支持
实现核心功能的国际化
"""

import json
import os
from typing import Dict, Any, Optional


class I18nManager:
    """国际化管理器"""
    
    def __init__(self, translations_dir: str = "translations"):
        self.translations_dir = translations_dir
        self.translations: Dict[str, Dict[str, str]] = {}
        self.current_locale = "zh-CN"
        self._load_translations()
    
    def _load_translations(self):
        """加载翻译文件"""
        try:
            if os.path.exists(self.translations_dir):
                for filename in os.listdir(self.translations_dir):
                    if filename.endswith(".json"):
                        locale = filename[:-5]  # 移除.json后缀
                        file_path = os.path.join(self.translations_dir, filename)
                        with open(file_path, 'r', encoding='utf-8') as f:
                            self.translations[locale] = json.load(f)
        except Exception as e:
            print(f"加载翻译文件失败: {e}")
    
    def set_locale(self, locale: str):
        """设置当前语言"""
        if locale in self.translations:
            self.current_locale = locale
            return True
        return False
    
    def get_locale(self) -> str:
        """获取当前语言"""
        return self.current_locale
    
    def get_locales(self) -> list:
        """获取支持的语言列表"""
        return list(self.translations.keys())
    
    def translate(self, key: str, **kwargs) -> str:
        """翻译文本"""
        # 优先使用当前语言
        if self.current_locale in self.translations:
            if key in self.translations[self.current_locale]:
                text = self.translations[self.current_locale][key]
                # 替换占位符
                if kwargs:
                    text = text.format(**kwargs)
                return text
        
        # 如果当前语言没有，尝试使用默认语言
        if "en-US" in self.translations:
            if key in self.translations["en-US"]:
                text = self.translations["en-US"][key]
                if kwargs:
                    text = text.format(**kwargs)
                return text
        
        # 如果都没有，返回键本身
        return key
    
    def add_translation(self, locale: str, key: str, value: str):
        """添加翻译"""
        if locale not in self.translations:
            self.translations[locale] = {}
        self.translations[locale][key] = value
    
    def save_translations(self):
        """保存翻译"""
        try:
            os.makedirs(self.translations_dir, exist_ok=True)
            for locale, data in self.translations.items():
                file_path = os.path.join(self.translations_dir, f"{locale}.json")
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存翻译文件失败: {e}")


# 全局国际化管理器实例
_i18n_manager = None

def get_i18n_manager() -> I18nManager:
    """获取国际化管理器实例"""
    global _i18n_manager
    if _i18n_manager is None:
        _i18n_manager = I18nManager()
    return _i18n_manager


# 便捷函数
def _(key: str, **kwargs) -> str:
    """翻译函数"""
    return get_i18n_manager().translate(key, **kwargs)


if __name__ == "__main__":
    # 测试
    i18n = get_i18n_manager()
    
    # 设置语言
    i18n.set_locale("zh-CN")
    
    # 测试翻译
    print(_("hello"))
    print(_("welcome", name="用户"))
    
    # 切换语言
    i18n.set_locale("en-US")
    print(_("hello"))
    print(_("welcome", name="User"))
    
    # 添加新翻译
    i18n.add_translation("zh-CN", "test", "测试")
    i18n.add_translation("en-US", "test", "Test")
    
    # 测试新翻译
    print(_("test"))
    
    # 保存翻译
    i18n.save_translations()
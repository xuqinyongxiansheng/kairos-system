#!/usr/bin/env python3
"""
IP访问控制中间件
从main.py拆分，IP黑白名单管理
"""

from typing import Set, Tuple


class IPAccessController:
    """IP访问控制器"""

    def __init__(
        self,
        whitelist: Set[str],
        blacklist: Set[str],
        whitelist_enabled: bool = False,
        blacklist_enabled: bool = False
    ):
        self.whitelist = whitelist
        self.blacklist = blacklist
        self.whitelist_enabled = whitelist_enabled
        self.blacklist_enabled = blacklist_enabled

    def is_allowed(self, client_ip: str) -> Tuple[bool, str]:
        """检查IP是否被允许访问

        Args:
            client_ip: 客户端IP地址

        Returns:
            (是否允许, 原因说明)
        """
        if self.blacklist_enabled and client_ip in self.blacklist:
            return False, "IP已被封禁"

        if self.whitelist_enabled:
            if client_ip not in self.whitelist:
                return False, "IP不在白名单中"

        return True, ""

    def add_to_blacklist(self, ip: str):
        """添加IP到黑名单"""
        self.blacklist.add(ip)

    def remove_from_blacklist(self, ip: str):
        """从黑名单移除IP"""
        self.blacklist.discard(ip)

    def add_to_whitelist(self, ip: str):
        """添加IP到白名单"""
        self.whitelist.add(ip)

    def remove_from_whitelist(self, ip: str):
        """从白名单移除IP"""
        self.whitelist.discard(ip)

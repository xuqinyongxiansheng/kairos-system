"""
Git集成模块
提供版本控制自动化功能
支持: 初始化、提交、分支、合并、PR创建、冲突解决
"""

import os
import logging
import asyncio
import subprocess
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger("GitIntegration")


class GitOperation(Enum):
    """Git操作类型"""
    INIT = "init"
    CLONE = "clone"
    STATUS = "status"
    ADD = "add"
    COMMIT = "commit"
    PUSH = "push"
    PULL = "pull"
    BRANCH = "branch"
    CHECKOUT = "checkout"
    MERGE = "merge"
    REBASE = "rebase"
    STASH = "stash"
    RESET = "reset"
    LOG = "log"
    DIFF = "diff"
    FETCH = "fetch"


class BranchType(Enum):
    """分支类型"""
    FEATURE = "feature"
    BUGFIX = "bugfix"
    HOTFIX = "hotfix"
    RELEASE = "release"
    MAIN = "main"
    DEVELOP = "develop"


@dataclass
class GitConfig:
    """Git配置"""
    user_name: str = "鸿蒙小雨"
    user_email: str = "hmyx@system.local"
    default_branch: str = "main"
    auto_push: bool = False
    commit_prefix: str = "[HMYX]"


@dataclass
class CommitInfo:
    """提交信息"""
    hash: str
    message: str
    author: str
    date: str
    files_changed: List[str]


@dataclass
class BranchInfo:
    """分支信息"""
    name: str
    is_current: bool
    is_remote: bool
    last_commit: str
    ahead: int = 0
    behind: int = 0


@dataclass
class DiffInfo:
    """差异信息"""
    file: str
    additions: int
    deletions: int
    status: str


class GitIntegration:
    """
    Git集成管理器
    
    功能:
    - 仓库初始化与克隆
    - 智能提交（自动生成提交信息）
    - 分支管理
    - 合并与冲突解决
    - PR创建
    - 变更分析
    """
    
    def __init__(self, repo_path: str = ".", config: GitConfig = None):
        self.repo_path = os.path.abspath(repo_path)
        self.config = config or GitConfig()
        self._git_available = self._check_git_available()
        
        logger.info(f"Git集成初始化: {self.repo_path}")
    
    def _check_git_available(self) -> bool:
        """检查Git是否可用"""
        try:
            result = subprocess.run(
                ["git", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def _run_git(self, *args, cwd: str = None) -> Dict[str, Any]:
        """执行Git命令"""
        if not self._git_available:
            return {"status": "error", "error": "Git未安装或不可用"}
        
        try:
            result = subprocess.run(
                ["git"] + list(args),
                cwd=cwd or self.repo_path,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            return {
                "status": "success" if result.returncode == 0 else "error",
                "returncode": result.returncode,
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip()
            }
        except subprocess.TimeoutExpired:
            return {"status": "error", "error": "Git命令超时"}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def init_repo(self, bare: bool = False) -> Dict[str, Any]:
        """
        初始化仓库
        
        Args:
            bare: 是否创建裸仓库
            
        Returns:
            操作结果
        """
        args = ["init"]
        if bare:
            args.append("--bare")
        
        result = self._run_git(*args)
        
        if result["status"] == "success":
            # 配置用户信息
            self._run_git("config", "user.name", self.config.user_name)
            self._run_git("config", "user.email", self.config.user_email)
            
            logger.info(f"仓库初始化成功: {self.repo_path}")
        
        return result
    
    async def clone(self, url: str, branch: str = None) -> Dict[str, Any]:
        """
        克隆仓库
        
        Args:
            url: 仓库URL
            branch: 指定分支
            
        Returns:
            操作结果
        """
        args = ["clone", url]
        if branch:
            args.extend(["-b", branch])
        args.append(self.repo_path)
        
        result = self._run_git(*args, cwd=os.path.dirname(self.repo_path))
        
        if result["status"] == "success":
            logger.info(f"仓库克隆成功: {url}")
        
        return result
    
    async def get_status(self) -> Dict[str, Any]:
        """
        获取仓库状态
        
        Returns:
            状态信息
        """
        result = self._run_git("status", "--porcelain")
        
        if result["status"] != "success":
            return result
        
        changes = {
            "modified": [],
            "added": [],
            "deleted": [],
            "untracked": [],
            "renamed": []
        }
        
        for line in result["stdout"].split("\n"):
            if not line:
                continue
            
            status = line[:2]
            file_path = line[3:]
            
            if status.startswith("??"):
                changes["untracked"].append(file_path)
            elif status.startswith("A") or status.startswith("M"):
                changes["added"].append(file_path)
            elif status.startswith(" M") or status.startswith("M "):
                changes["modified"].append(file_path)
            elif status.startswith(" D") or status.startswith("D "):
                changes["deleted"].append(file_path)
            elif status.startswith("R"):
                changes["renamed"].append(file_path)
        
        return {
            "status": "success",
            "changes": changes,
            "has_changes": any(changes.values())
        }
    
    async def get_diff(self, staged: bool = False) -> Dict[str, Any]:
        """
        获取差异
        
        Args:
            staged: 是否只查看暂存区
            
        Returns:
            差异信息
        """
        args = ["diff", "--stat"]
        if staged:
            args.append("--staged")
        
        result = self._run_git(*args)
        
        if result["status"] != "success":
            return result
        
        diffs = []
        for line in result["stdout"].split("\n"):
            if "|" in line:
                parts = line.split("|")
                file = parts[0].strip()
                stats = parts[1].strip() if len(parts) > 1 else ""
                
                additions = stats.count("+")
                deletions = stats.count("-")
                
                diffs.append(DiffInfo(
                    file=file,
                    additions=additions,
                    deletions=deletions,
                    status="modified"
                ))
        
        return {
            "status": "success",
            "diffs": [d.__dict__ for d in diffs],
            "total_files": len(diffs)
        }
    
    async def add(self, files: List[str] = None) -> Dict[str, Any]:
        """
        添加文件到暂存区
        
        Args:
            files: 文件列表，为None时添加所有
            
        Returns:
            操作结果
        """
        if files is None:
            result = self._run_git("add", "-A")
        else:
            result = self._run_git("add", *files)
        
        return result
    
    async def commit(self, message: str = None, 
                    auto_message: bool = False) -> Dict[str, Any]:
        """
        提交更改
        
        Args:
            message: 提交信息
            auto_message: 是否自动生成提交信息
            
        Returns:
            操作结果
        """
        if auto_message and message is None:
            message = await self._generate_commit_message()
        elif message is None:
            message = f"{self.config.commit_prefix} 自动提交 {datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        result = self._run_git("commit", "-m", message)
        
        if result["status"] == "success":
            logger.info(f"提交成功: {message}")
            
            if self.config.auto_push:
                await self.push()
        
        return result
    
    async def _generate_commit_message(self) -> str:
        """自动生成提交信息"""
        status = await self.get_status()
        diff = await self.get_diff()
        
        changes = []
        if status["changes"]["added"]:
            changes.append(f"新增 {len(status['changes']['added'])} 个文件")
        if status["changes"]["modified"]:
            changes.append(f"修改 {len(status['changes']['modified'])} 个文件")
        if status["changes"]["deleted"]:
            changes.append(f"删除 {len(status['changes']['deleted'])} 个文件")
        
        message = self.config.commit_prefix
        if changes:
            message += " " + ", ".join(changes)
        else:
            message += " 更新"
        
        return message
    
    async def push(self, remote: str = "origin", 
                  branch: str = None, 
                  force: bool = False) -> Dict[str, Any]:
        """
        推送到远程
        
        Args:
            remote: 远程名称
            branch: 分支名称
            force: 是否强制推送
            
        Returns:
            操作结果
        """
        args = ["push", remote]
        if branch:
            args.append(branch)
        if force:
            args.append("--force")
        
        result = self._run_git(*args)
        
        if result["status"] == "success":
            logger.info(f"推送成功: {remote}/{branch or 'current'}")
        
        return result
    
    async def pull(self, remote: str = "origin", 
                  branch: str = None) -> Dict[str, Any]:
        """
        拉取更新
        
        Args:
            remote: 远程名称
            branch: 分支名称
            
        Returns:
            操作结果
        """
        args = ["pull", remote]
        if branch:
            args.append(branch)
        
        result = self._run_git(*args)
        
        if result["status"] == "success":
            logger.info(f"拉取成功: {remote}/{branch or 'current'}")
        
        return result
    
    async def create_branch(self, branch_name: str, 
                           base: str = None,
                           checkout: bool = True) -> Dict[str, Any]:
        """
        创建分支
        
        Args:
            branch_name: 分支名称
            base: 基于哪个分支/提交
            checkout: 是否切换到新分支
            
        Returns:
            操作结果
        """
        args = ["branch", branch_name]
        if base:
            args.append(base)
        
        result = self._run_git(*args)
        
        if result["status"] == "success":
            logger.info(f"分支创建成功: {branch_name}")
            
            if checkout:
                await self.checkout(branch_name)
        
        return result
    
    async def checkout(self, branch: str, create: bool = False) -> Dict[str, Any]:
        """
        切换分支
        
        Args:
            branch: 分支名称
            create: 是否创建新分支
            
        Returns:
            操作结果
        """
        args = ["checkout"]
        if create:
            args.append("-b")
        args.append(branch)
        
        result = self._run_git(*args)
        
        if result["status"] == "success":
            logger.info(f"切换分支: {branch}")
        
        return result
    
    async def get_branches(self) -> Dict[str, Any]:
        """
        获取所有分支
        
        Returns:
            分支列表
        """
        result = self._run_git("branch", "-a", "-vv")
        
        if result["status"] != "success":
            return result
        
        branches = []
        current_branch = None
        
        for line in result["stdout"].split("\n"):
            if not line.strip():
                continue
            
            is_current = line.startswith("*")
            if is_current:
                current_branch = line.split()[1]
            
            parts = line.strip().lstrip("*").split()
            name = parts[0]
            
            is_remote = name.startswith("remotes/")
            
            branches.append(BranchInfo(
                name=name,
                is_current=is_current,
                is_remote=is_remote,
                last_commit=parts[2] if len(parts) > 2 else ""
            ))
        
        return {
            "status": "success",
            "branches": [b.__dict__ for b in branches],
            "current_branch": current_branch,
            "total": len(branches)
        }
    
    async def merge(self, branch: str, 
                   message: str = None,
                   no_ff: bool = True) -> Dict[str, Any]:
        """
        合并分支
        
        Args:
            branch: 要合并的分支
            message: 合并信息
            no_ff: 是否禁用快进合并
            
        Returns:
            操作结果
        """
        args = ["merge"]
        if no_ff:
            args.append("--no-ff")
        if message:
            args.extend(["-m", message])
        args.append(branch)
        
        result = self._run_git(*args)
        
        if result["status"] == "success":
            logger.info(f"合并成功: {branch}")
        
        return result
    
    async def get_log(self, limit: int = 10, 
                     branch: str = None) -> Dict[str, Any]:
        """
        获取提交日志
        
        Args:
            limit: 返回数量
            branch: 指定分支
            
        Returns:
            提交日志
        """
        args = ["log", f"-{limit}", "--pretty=format:%H|%s|%an|%ad", "--date=short"]
        if branch:
            args.append(branch)
        
        result = self._run_git(*args)
        
        if result["status"] != "success":
            return result
        
        commits = []
        for line in result["stdout"].split("\n"):
            if not line:
                continue
            
            parts = line.split("|")
            if len(parts) >= 4:
                commits.append(CommitInfo(
                    hash=parts[0][:8],
                    message=parts[1],
                    author=parts[2],
                    date=parts[3],
                    files_changed=[]
                ))
        
        return {
            "status": "success",
            "commits": [c.__dict__ for c in commits],
            "total": len(commits)
        }
    
    async def stash(self, message: str = None) -> Dict[str, Any]:
        """
        暂存更改
        
        Args:
            message: 暂存信息
            
        Returns:
            操作结果
        """
        args = ["stash"]
        if message:
            args.extend(["-m", message])
        
        result = self._run_git(*args)
        
        if result["status"] == "success":
            logger.info("更改已暂存")
        
        return result
    
    async def stash_pop(self) -> Dict[str, Any]:
        """恢复暂存"""
        result = self._run_git("stash", "pop")
        
        if result["status"] == "success":
            logger.info("暂存已恢复")
        
        return result
    
    async def is_repo(self) -> bool:
        """检查是否是Git仓库"""
        result = self._run_git("rev-parse", "--git-dir")
        return result["status"] == "success"
    
    async def get_remote_url(self, remote: str = "origin") -> Optional[str]:
        """获取远程仓库URL"""
        result = self._run_git("remote", "get-url", remote)
        
        if result["status"] == "success":
            return result["stdout"]
        return None
    
    async def create_pr(self, title: str, body: str, 
                       base: str = "main",
                       head: str = None) -> Dict[str, Any]:
        """
        创建Pull Request
        
        Args:
            title: PR标题
            body: PR描述
            base: 目标分支
            head: 源分支
            
        Returns:
            操作结果
        """
        # 获取当前分支作为head
        if head is None:
            branches = await self.get_branches()
            head = branches.get("current_branch", "main")
        
        # 检测远程平台
        remote_url = await self.get_remote_url()
        
        if remote_url:
            if "github.com" in remote_url:
                return await self._create_github_pr(title, body, base, head)
            elif "gitlab.com" in remote_url:
                return await self._create_gitlab_mr(title, body, base, head)
        
        return {
            "status": "error",
            "error": "无法识别远程平台或不支持PR创建",
            "suggestion": f"请在 {base} 分支上手动创建PR，合并 {head} 分支"
        }
    
    async def _create_github_pr(self, title: str, body: str, 
                               base: str, head: str) -> Dict[str, Any]:
        """创建GitHub PR"""
        try:
            result = self._run_git("gh", "pr", "create", 
                                  "--title", title, 
                                  "--body", body,
                                  "--base", base,
                                  "--head", head)
            
            if result["status"] == "success":
                return {
                    "status": "success",
                    "pr_url": result["stdout"],
                    "platform": "github"
                }
        except Exception:
            logger.debug(f"忽略异常: ", exc_info=True)
            pass
        
        return {"status": "error", "error": "GitHub CLI (gh) 未安装或未认证"}
    
    async def _create_gitlab_mr(self, title: str, body: str,
                               base: str, head: str) -> Dict[str, Any]:
        """创建GitLab MR"""
        try:
            result = self._run_git("lab", "mr", "create",
                                  "--title", title,
                                  "--description", body,
                                  "--target-branch", base,
                                  "--source-branch", head)
            
            if result["status"] == "success":
                return {
                    "status": "success",
                    "mr_url": result["stdout"],
                    "platform": "gitlab"
                }
        except Exception:
            logger.debug(f"忽略异常: ", exc_info=True)
            pass
        
        return {"status": "error", "error": "GitLab CLI (lab) 未安装或未认证"}
    
    def get_info(self) -> Dict[str, Any]:
        """获取Git集成信息"""
        return {
            "status": "success",
            "repo_path": self.repo_path,
            "git_available": self._git_available,
            "config": {
                "user_name": self.config.user_name,
                "user_email": self.config.user_email,
                "default_branch": self.config.default_branch
            }
        }

    def get_file_diff(self, filepath: str) -> str:
        """获取指定文件的差异"""
        if not self._git_available:
            return "Git未安装或不可用"
        try:
            result = subprocess.run(
                ["git", "diff", filepath],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
            result2 = subprocess.run(
                ["git", "diff", "--cached", filepath],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=30
            )
            return result2.stdout.strip() if result2.stdout.strip() else ""
        except Exception as e:
            return f"获取差异失败: {e}"

    def commit_all(self, message: str) -> str:
        """添加所有文件并提交"""
        if not self._git_available:
            return "Git未安装或不可用"
        try:
            subprocess.run(
                ["git", "add", "-A"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=30
            )
            result = subprocess.run(
                ["git", "commit", "-m", message],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                return result.stdout.strip() or "提交成功"
            return f"提交失败: {result.stderr.strip()}"
        except Exception as e:
            return f"提交失败: {e}"


# 全局实例
git_integration = GitIntegration()


def get_git_integration() -> GitIntegration:
    """获取全局Git集成实例"""
    return git_integration

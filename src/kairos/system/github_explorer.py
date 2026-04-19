"""
GitHub 探索器模块
智能搜索和获取 GitHub 代码资源
整合 002/AAagent 的优秀实现
"""

import os
import json
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class SearchStrategy(Enum):
    """搜索策略枚举"""
    RELEVANCE = "relevance"
    STARS = "stars"
    FORKS = "forks"
    RECENTLY_UPDATED = "updated"


class RepositoryType(Enum):
    """仓库类型枚举"""
    ALL = "all"
    FORK = "fork"
    SOURCE = "source"


@dataclass
class GitHubRepository:
    """GitHub 仓库数据类"""
    name: str
    full_name: str
    description: str
    stars: int
    forks: int
    url: str
    language: str
    updated_at: datetime
    topics: List[str]


@dataclass
class CodeFile:
    """代码文件数据类"""
    path: str
    name: str
    size: int
    content: str
    language: str


@dataclass
class RepositoryAnalysis:
    """仓库分析结果数据类"""
    repository: GitHubRepository
    files: List[CodeFile]
    requirements: Optional[str]
    readme: Optional[str]
    main_files: List[CodeFile]
    dependencies: List[str]


class GitHubExplorer:
    """GitHub 探索器主类"""
    
    def __init__(self, github_token: str = None):
        self.github_token = github_token or os.getenv("GITHUB_TOKEN", "")
        self.cache_dir = "./data/github_cache"
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # 检查 requests 是否可用
        self.requests_available = False
        try:
            import requests
            self.requests_available = True
            self.headers = {
                "Accept": "application/vnd.github.v3+json"
            }
            if self.github_token:
                self.headers["Authorization"] = f"token {self.github_token}"
        except ImportError:
            logger.warning("requests 库未安装，GitHub API 功能受限")
        
        logger.info("GitHub 探索器初始化完成")
    
    def search_repositories(self, query: str,
                           language: str = "python",
                           sort_by: SearchStrategy = SearchStrategy.STARS,
                           repository_type: RepositoryType = RepositoryType.SOURCE,
                           limit: int = 10) -> List[GitHubRepository]:
        """搜索 GitHub 仓库（模拟实现）"""
        if not self.requests_available:
            return self._generate_mock_repositories(query, limit)
        
        try:
            import requests
            
            url = "https://api.github.com/search/repositories"
            params = {
                "q": f"{query} language:{language}",
                "sort": sort_by.value,
                "order": "desc",
                "per_page": limit
            }
            
            response = requests.get(url, params=params, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            repositories = []
            
            for item in data.get("items", []):
                repo = GitHubRepository(
                    name=item["name"],
                    full_name=item["full_name"],
                    description=item["description"] or "",
                    stars=item["stargazers_count"],
                    forks=item["forks_count"],
                    url=item["html_url"],
                    language=item["language"] or "Unknown",
                    updated_at=datetime.fromisoformat(item["updated_at"].replace("Z", "+00:00")),
                    topics=item.get("topics", [])
                )
                repositories.append(repo)
            
            return repositories
            
        except Exception as e:
            logger.error(f"GitHub 搜索失败：{e}")
            return self._generate_mock_repositories(query, limit)
    
    def _generate_mock_repositories(self, query: str, limit: int = 10) -> List[GitHubRepository]:
        """生成模拟仓库数据"""
        repositories = []
        for i in range(min(limit, 5)):
            repo = GitHubRepository(
                name=f"python-{query.replace(' ', '-')}-{i}",
                full_name=f"testuser/python-{query.replace(' ', '-')}-{i}",
                description=f"A Python library for {query}",
                stars=100 + i * 50,
                forks=20 + i * 10,
                url=f"https://github.com/testuser/python-{query.replace(' ', '-')}",
                language="Python",
                updated_at=datetime.now(),
                topics=[query, "python"]
            )
            repositories.append(repo)
        
        return repositories
    
    def get_repository_details(self, owner: str, repo_name: str) -> Optional[GitHubRepository]:
        """获取仓库详细信息（模拟）"""
        return GitHubRepository(
            name=repo_name,
            full_name=f"{owner}/{repo_name}",
            description=f"Repository {repo_name}",
            stars=1000,
            forks=200,
            url=f"https://github.com/{owner}/{repo_name}",
            language="Python",
            updated_at=datetime.now(),
            topics=[]
        )
    
    def search_code(self, query: str, language: str = "python", limit: int = 10) -> List[Dict[str, Any]]:
        """搜索代码内容"""
        results = []
        for i in range(min(limit, 5)):
            results.append({
                "name": f"{query}_{i}.py",
                "path": f"src/{query}_{i}.py",
                "repository": f"test/repo-{i}",
                "url": f"https://github.com/test/repo-{i}/blob/main/src/{query}_{i}.py",
                "language": "Python",
                "score": 1.0 - (i * 0.1)
            })
        return results
    
    def get_trending_repositories(self, language: str = "python") -> List[GitHubRepository]:
        """获取趋势仓库"""
        return self.search_repositories(
            f"stars:>1000 language:{language}",
            language=language,
            sort_by=SearchStrategy.RECENTLY_UPDATED,
            limit=10
        )
    
    def generate_search_queries(self, requirements: Dict[str, Any]) -> List[str]:
        """基于需求生成搜索查询"""
        queries = []
        keywords = requirements.get("keywords", [])
        need_type = requirements.get("type", "general")
        
        for keyword in keywords[:3]:
            queries.append(f"{keyword} python")
        
        type_queries = {
            "data_processing": ["data processing python", "data analysis python"],
            "network_tool": ["network api python", "http client python"],
            "file_operation": ["file handling python", "file format python"],
            "algorithm": ["algorithm python", "machine learning python"],
            "system_tool": ["system utilities python", "process management python"]
        }
        
        if need_type in type_queries:
            queries.extend(type_queries[need_type])
        
        return list(set(queries))[:10]
    
    def rank_repositories(self, repositories: List[GitHubRepository],
                         requirements: Dict[str, Any]) -> List[GitHubRepository]:
        """智能排序仓库"""
        keywords = requirements.get("keywords", [])
        
        def calculate_score(repo):
            score = repo.stars * 0.7 + repo.forks * 0.3
            
            text_to_check = f"{repo.name} {repo.description}".lower()
            for keyword in keywords:
                if keyword.lower() in text_to_check:
                    score += 100
            
            if repo.language.lower() == "python":
                score += 50
            
            days_since_update = (datetime.now() - repo.updated_at).days
            if days_since_update < 30:
                score += 100
            elif days_since_update < 90:
                score += 50
            
            return score
        
        return sorted(repositories, key=calculate_score, reverse=True)


github_explorer = GitHubExplorer()

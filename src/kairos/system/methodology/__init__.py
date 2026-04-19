#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
毛泽东思想方法论引擎
将80条核心精髓系统化集成到鸿蒙小雨架构中

集成架构：
- ThoughtPrinciple: 单条思想原则的数据模型
- ThoughtCategory: 七大类别枚举
- MethodologyEngine: 核心引擎，提供思想检索、策略匹配、决策增强
- 与现有模块的接口：reasoning/perception/self_evolution/hybrid_engine/cognitive_loop/memory
"""

import time
import math
import logging
import threading
from enum import Enum
from typing import Optional, List, Dict, Any, Tuple, Callable
from dataclasses import dataclass, field
from collections import defaultdict

logger = logging.getLogger("HMYX.Methodology")


class ThoughtCategory(Enum):
    PHILOSOPHY = "philosophy"
    MASS_LINE = "mass_line"
    INDEPENDENCE = "independence"
    MILITARY_STRATEGY = "military_strategy"
    POLITICS = "politics"
    WORK_METHOD = "work_method"
    SELF_REFORM = "self_reform"


class PrincipleApplication(Enum):
    DECISION_MAKING = "decision_making"
    PROBLEM_ANALYSIS = "problem_analysis"
    STRATEGY_PLANNING = "strategy_planning"
    TEAM_MANAGEMENT = "team_management"
    SELF_IMPROVEMENT = "self_improvement"
    CONFLICT_RESOLUTION = "conflict_resolution"
    RESOURCE_ALLOCATION = "resource_allocation"
    LEARNING_GROWTH = "learning_growth"


@dataclass
class ThoughtPrinciple:
    """思想原则数据模型"""
    id: int
    name: str
    category: ThoughtCategory
    core_essence: str
    source: str
    applications: List[PrincipleApplication] = field(default_factory=list)
    related_principles: List[int] = field(default_factory=list)
    integration_module: str = ""
    activation_count: int = 0
    effectiveness_score: float = 0.5
    keywords: List[str] = field(default_factory=list)

    def activate(self) -> float:
        self.activation_count += 1
        return self.effectiveness_score

    def update_effectiveness(self, delta: float):
        self.effectiveness_score = max(0.0, min(1.0, self.effectiveness_score + delta))


@dataclass
class StrategyRecommendation:
    """策略推荐结果"""
    principle_id: int
    principle_name: str
    category: ThoughtCategory
    relevance: float
    reasoning: str
    action_steps: List[str] = field(default_factory=list)
    expected_outcome: str = ""
    module_target: str = ""


@dataclass
class DecisionEnhancement:
    """决策增强结果"""
    original_decision: str
    enhanced_decision: str
    applied_principles: List[int] = field(default_factory=list)
    confidence_boost: float = 0.0
    risk_mitigations: List[str] = field(default_factory=list)
    alternative_options: List[str] = field(default_factory=list)


class MethodologyEngine:
    """
    毛泽东思想方法论引擎
    
    核心能力：
    1. 思想原则存储与检索
    2. 问题-策略匹配
    3. 决策增强
    4. 矛盾分析
    5. 与系统模块的接口适配
    """

    def __init__(self):
        self._principles: Dict[int, ThoughtPrinciple] = {}
        self._category_index: Dict[ThoughtCategory, List[int]] = defaultdict(list)
        self._application_index: Dict[PrincipleApplication, List[int]] = defaultdict(list)
        self._keyword_index: Dict[str, List[int]] = defaultdict(list)
        self._module_index: Dict[str, List[int]] = defaultdict(list)
        self._lock = threading.Lock()
        self._initialized = False
        self._statistics = {
            "total_activations": 0,
            "category_usage": defaultdict(int),
            "top_principles": [],
            "avg_effectiveness": 0.5
        }

    def initialize(self):
        """初始化引擎，加载80条核心思想"""
        if self._initialized:
            return
        self._load_all_principles()
        self._build_indices()
        self._initialized = True
        logger.info(f"方法论引擎初始化完成，已加载 {len(self._principles)} 条思想原则")

    def _register(self, pid: int, name: str, category: ThoughtCategory,
                  essence: str, source: str, applications: List[PrincipleApplication],
                  related: List[int], module: str, keywords: List[str]):
        p = ThoughtPrinciple(
            id=pid, name=name, category=category, core_essence=essence,
            source=source, applications=applications, related_principles=related,
            integration_module=module, keywords=keywords
        )
        self._principles[pid] = p

    def _load_all_principles(self):
        # === 哲学方法论 (1-16) → reasoning模块 ===
        ph = ThoughtCategory.PHILOSOPHY
        pa = PrincipleApplication
        self._register(1, "实事求是", ph, "从客观实际出发，理论联系实际", "改造我们的学习",
                       [pa.DECISION_MAKING, pa.PROBLEM_ANALYSIS], [2, 3], "reasoning", ["客观", "实际", "事实"])
        self._register(2, "没有调查就没有发言权", ph, "结论必须建立在充分调查基础上", "反对本本主义",
                       [pa.PROBLEM_ANALYSIS, pa.DECISION_MAKING], [1, 70], "reasoning", ["调查", "研究", "证据"])
        self._register(3, "实践是检验真理的唯一标准", ph, "认识必须在实践中检验和发展", "实践论",
                       [pa.DECISION_MAKING, pa.LEARNING_GROWTH], [1, 12], "reasoning", ["实践", "检验", "真理"])
        self._register(4, "矛盾普遍性", ph, "矛盾存在于一切事物中，没有矛盾就没有世界", "矛盾论",
                       [pa.PROBLEM_ANALYSIS], [5, 6], "reasoning", ["矛盾", "普遍", "问题"])
        self._register(5, "矛盾特殊性", ph, "不同矛盾各有特点，必须具体问题具体分析", "矛盾论",
                       [pa.PROBLEM_ANALYSIS, pa.STRATEGY_PLANNING], [4, 16], "reasoning", ["特殊", "具体", "分析"])
        self._register(6, "主要矛盾", ph, "复杂事物中必有一种矛盾居于支配地位", "矛盾论",
                       [pa.PROBLEM_ANALYSIS, pa.RESOURCE_ALLOCATION, pa.DECISION_MAKING], [4, 7], "reasoning", ["主要", "关键", "核心"])
        self._register(7, "矛盾的主要方面", ph, "矛盾双方中必有一方居于支配地位", "矛盾论",
                       [pa.PROBLEM_ANALYSIS], [6, 8], "reasoning", ["方面", "支配", "性质"])
        self._register(8, "矛盾转化", ph, "矛盾双方在一定条件下可以互相转化", "矛盾论",
                       [pa.STRATEGY_PLANNING, pa.CONFLICT_RESOLUTION], [6, 7], "reasoning", ["转化", "条件", "变化"])
        self._register(9, "对立统一规律", ph, "对立面的统一和斗争是发展的根本动力", "矛盾论",
                       [pa.PROBLEM_ANALYSIS], [4, 8], "reasoning", ["对立", "统一", "斗争"])
        self._register(10, "量变到质变", ph, "量变积累到一定程度引起质变", "矛盾论",
                       [pa.STRATEGY_PLANNING, pa.LEARNING_GROWTH], [9, 11], "reasoning", ["量变", "质变", "积累"])
        self._register(11, "否定之否定", ph, "发展是螺旋式上升、波浪式前进", "辩证法",
                       [pa.LEARNING_GROWTH, pa.STRATEGY_PLANNING], [10, 12], "reasoning", ["螺旋", "否定", "前进"])
        self._register(12, "认识的两次飞跃", ph, "感性→理性→实践，两次飞跃缺一不可", "实践论",
                       [pa.LEARNING_GROWTH, pa.DECISION_MAKING], [3, 13], "reasoning", ["认识", "飞跃", "实践"])
        self._register(13, "认识的无限性", ph, "实践-认识-再实践-再认识，循环往复", "实践论",
                       [pa.LEARNING_GROWTH], [12, 3], "reasoning", ["循环", "无限", "深化"])
        self._register(14, "内因与外因", ph, "内因是根据，外因是条件，外因通过内因起作用", "矛盾论",
                       [pa.PROBLEM_ANALYSIS, pa.SELF_IMPROVEMENT], [9, 27], "reasoning", ["内因", "外因", "根据"])
        self._register(15, "透过现象看本质", ph, "不被表面现象迷惑，深入分析内在本质", "实践论",
                       [pa.PROBLEM_ANALYSIS], [1, 16], "reasoning", ["现象", "本质", "深入"])
        self._register(16, "具体问题具体分析", ph, "马克思主义活的灵魂，反对教条主义", "矛盾论",
                       [pa.PROBLEM_ANALYSIS, pa.DECISION_MAKING, pa.STRATEGY_PLANNING], [5, 75], "reasoning", ["具体", "分析", "教条"])

        # === 群众路线 (17-26) → perception模块 ===
        ml = ThoughtCategory.MASS_LINE
        self._register(17, "一切为了群众", ml, "以最广大人民最大利益为最高标准", "论联合政府",
                       [pa.DECISION_MAKING, pa.TEAM_MANAGEMENT], [18, 19], "perception", ["群众", "利益", "服务"])
        self._register(18, "一切依靠群众", ml, "人民群众是历史的创造者", "论联合政府",
                       [pa.TEAM_MANAGEMENT, pa.STRATEGY_PLANNING], [17, 21], "perception", ["依靠", "群众", "力量"])
        self._register(19, "从群众中来", ml, "将分散意见集中为系统意见", "关于领导方法的若干问题",
                       [pa.TEAM_MANAGEMENT, pa.DECISION_MAKING], [20, 23], "perception", ["集中", "意见", "收集"])
        self._register(20, "到群众中去", ml, "将集中意见化为群众自觉行动", "关于领导方法的若干问题",
                       [pa.TEAM_MANAGEMENT], [19, 24], "perception", ["推广", "执行", "反馈"])
        self._register(21, "群众是真正的英雄", ml, "群众有无限创造力，要拜群众为师", "农村调查序言",
                       [pa.LEARNING_GROWTH, pa.TEAM_MANAGEMENT], [18, 22], "perception", ["英雄", "创造", "学习"])
        self._register(22, "甘当小学生", ml, "放下架子以谦虚态度向群众学习", "农村调查序言",
                       [pa.LEARNING_GROWTH], [21, 77], "perception", ["谦虚", "学习", "态度"])
        self._register(23, "一般号召与个别指导相结合", ml, "从个别提炼一般，再用一般指导个别", "关于领导方法的若干问题",
                       [pa.TEAM_MANAGEMENT, pa.STRATEGY_PLANNING], [19, 71], "perception", ["一般", "个别", "指导"])
        self._register(24, "领导与群众相结合", ml, "集中领导与群众智慧结合", "关于领导方法的若干问题",
                       [pa.TEAM_MANAGEMENT], [20, 72], "perception", ["领导", "群众", "结合"])
        self._register(25, "兵民是胜利之本", ml, "战争伟力最深厚根源存在于民众之中", "论持久战",
                       [pa.TEAM_MANAGEMENT, pa.STRATEGY_PLANNING], [18, 35], "perception", ["兵民", "胜利", "根本"])
        self._register(26, "全心全意为人民服务", ml, "一切工作的出发点和落脚点", "为人民服务",
                       [pa.DECISION_MAKING, pa.TEAM_MANAGEMENT], [17, 20], "perception", ["服务", "人民", "宗旨"])

        # === 独立自主 (27-34) → self_evolution模块 ===
        ind = ThoughtCategory.INDEPENDENCE
        self._register(27, "独立自主", ind, "按中国情况办，靠中国人民自己的力量", "论持久战等",
                       [pa.STRATEGY_PLANNING, pa.SELF_IMPROVEMENT], [28, 34], "self_evolution", ["独立", "自主", "自己"])
        self._register(28, "自力更生", ind, "依靠自己力量发展，不依赖外部恩赐", "抗日战争时期",
                       [pa.SELF_IMPROVEMENT, pa.RESOURCE_ALLOCATION], [27, 29], "self_evolution", ["自力", "更生", "依靠"])
        self._register(29, "艰苦奋斗", ind, "困难条件下保持昂扬斗志", "抗日战争时期",
                       [pa.SELF_IMPROVEMENT], [28, 33], "self_evolution", ["艰苦", "奋斗", "意志"])
        self._register(30, "以我为主", ind, "学习外国经验但不照搬，走自己的路", "论十大关系",
                       [pa.LEARNING_GROWTH, pa.STRATEGY_PLANNING], [27, 34], "self_evolution", ["为主", "自己", "道路"])
        self._register(31, "外援为辅", ind, "争取国际援助但不依赖", "抗日战争时期",
                       [pa.RESOURCE_ALLOCATION], [27, 28], "self_evolution", ["外援", "辅助", "不依赖"])
        self._register(32, "不信邪不怕压", ind, "面对外部压力不屈服", "多篇文章",
                       [pa.CONFLICT_RESOLUTION, pa.SELF_IMPROVEMENT], [27, 29], "self_evolution", ["压力", "不屈", "自信"])
        self._register(33, "独立思考", ind, "不盲从权威和本本，用自己的头脑分析", "反对本本主义",
                       [pa.PROBLEM_ANALYSIS, pa.DECISION_MAKING], [27, 75], "self_evolution", ["思考", "独立", "分析"])
        self._register(34, "中国道路", ind, "走适合中国国情的道路，不照搬外国模式", "新民主主义论",
                       [pa.STRATEGY_PLANNING], [27, 30], "self_evolution", ["道路", "国情", "特色"])

        # === 军事战略 (35-50) → hybrid_engine模块 ===
        ms = ThoughtCategory.MILITARY_STRATEGY
        self._register(35, "枪杆子里面出政权", ms, "政权通过武装斗争取得", "战争和战略问题",
                       [pa.STRATEGY_PLANNING], [50, 36], "hybrid_engine", ["武装", "斗争", "政权"])
        self._register(36, "人民战争", ms, "依靠人民、动员人民、武装人民", "论持久战",
                       [pa.STRATEGY_PLANNING, pa.TEAM_MANAGEMENT], [25, 35], "hybrid_engine", ["人民", "战争", "动员"])
        self._register(37, "战略藐视战术重视", ms, "全局上敢于斗争，具体上谨慎从事", "一切反动派都是纸老虎",
                       [pa.DECISION_MAKING, pa.STRATEGY_PLANNING], [38, 43], "hybrid_engine", ["战略", "战术", "藐视"])
        self._register(38, "你打你的我打我的", ms, "不按敌人方式打仗，创造有利方式", "解放战争",
                       [pa.STRATEGY_PLANNING, pa.CONFLICT_RESOLUTION], [37, 40], "hybrid_engine", ["主动", "方式", "创造"])
        self._register(39, "打得赢就打打不赢就走", ms, "不打无把握之仗，保存实力", "中国革命战争的战略问题",
                       [pa.DECISION_MAKING, pa.RESOURCE_ALLOCATION], [37, 47], "hybrid_engine", ["把握", "保存", "实力"])
        self._register(40, "集中优势兵力各个歼灭", ms, "每战集中绝对优势兵力形成压倒性优势", "目前形势和我们的任务",
                       [pa.RESOURCE_ALLOCATION, pa.STRATEGY_PLANNING], [6, 41], "hybrid_engine", ["集中", "优势", "歼灭"])
        self._register(41, "伤其十指不如断其一指", ms, "集中力量歼灭有生力量而非击溃", "中国革命战争的战略问题",
                       [pa.RESOURCE_ALLOCATION, pa.STRATEGY_PLANNING], [40, 48], "hybrid_engine", ["歼灭", "集中", "效果"])
        self._register(42, "诱敌深入", ms, "主动退让将敌人引入不利地形", "中国革命战争的战略问题",
                       [pa.STRATEGY_PLANNING, pa.CONFLICT_RESOLUTION], [39, 44], "hybrid_engine", ["诱敌", "深入", "退让"])
        self._register(43, "持久战三阶段", ms, "战略防御→战略相持→战略反攻", "论持久战",
                       [pa.STRATEGY_PLANNING], [37, 11], "hybrid_engine", ["持久", "防御", "反攻"])
        self._register(44, "游击战十六字诀", ms, "敌进我退敌驻我扰敌疲我打敌退我追", "抗日游击战争的战略问题",
                       [pa.STRATEGY_PLANNING], [42, 38], "hybrid_engine", ["游击", "进退", "扰打"])
        self._register(45, "运动战找歼敌机会", ms, "在运动中调动敌人创造有利战机", "中国革命战争的战略问题",
                       [pa.STRATEGY_PLANNING], [44, 40], "hybrid_engine", ["运动", "战机", "调动"])
        self._register(46, "速决战与持久战结合", ms, "战略持久，战役战斗速决", "中国革命战争的战略问题",
                       [pa.STRATEGY_PLANNING, pa.DECISION_MAKING], [43, 39], "hybrid_engine", ["速决", "持久", "结合"])
        self._register(47, "不打无准备之仗", ms, "每战力求有准备有胜利把握", "抗日游击战争的战略问题",
                       [pa.DECISION_MAKING, pa.RESOURCE_ALLOCATION], [39, 2], "hybrid_engine", ["准备", "把握", "计划"])
        self._register(48, "歼灭战为主", ms, "以歼灭有生力量为主要目标", "目前形势和我们的任务",
                       [pa.STRATEGY_PLANNING], [41, 40], "hybrid_engine", ["歼灭", "目标", "有生"])
        self._register(49, "战争的目的是消灭战争", ms, "用革命战争消灭反革命战争", "论持久战",
                       [pa.CONFLICT_RESOLUTION, pa.STRATEGY_PLANNING], [35, 36], "hybrid_engine", ["消灭", "和平", "目的"])
        self._register(50, "人是决定因素", ms, "武器是重要因素但决定的是人", "论持久战",
                       [pa.TEAM_MANAGEMENT, pa.DECISION_MAKING], [36, 18], "hybrid_engine", ["人", "决定", "因素"])

        # === 政治与革命 (51-62) → cognitive_loop模块 ===
        po = ThoughtCategory.POLITICS
        self._register(51, "阶级分析法", po, "用阶级观点分析社会现象，分清敌我友", "中国社会各阶级的分析",
                       [pa.PROBLEM_ANALYSIS, pa.CONFLICT_RESOLUTION], [52, 15], "cognitive_loop", ["阶级", "分析", "敌我"])
        self._register(52, "统一战线", po, "团结一切可以团结的力量，孤立最顽固的敌人", "论反对日本帝国主义的策略",
                       [pa.TEAM_MANAGEMENT, pa.CONFLICT_RESOLUTION], [51, 53], "cognitive_loop", ["团结", "统一", "力量"])
        self._register(53, "又联合又斗争", po, "对同盟者既联合又斗争，以斗争求团结", "统一战线文献",
                       [pa.CONFLICT_RESOLUTION, pa.TEAM_MANAGEMENT], [52, 61], "cognitive_loop", ["联合", "斗争", "团结"])
        self._register(54, "新民主主义革命", po, "革命分两步走：新民主主义和社会主义", "新民主主义论",
                       [pa.STRATEGY_PLANNING], [55, 56], "cognitive_loop", ["革命", "步骤", "阶段"])
        self._register(55, "农村包围城市", po, "在敌人薄弱处建立根据地，逐步包围", "星星之火可以燎原",
                       [pa.STRATEGY_PLANNING, pa.RESOURCE_ALLOCATION], [54, 43], "cognitive_loop", ["农村", "包围", "根据地"])
        self._register(56, "三大法宝", po, "武装斗争、统一战线、党的建设", "共产党人发刊词",
                       [pa.STRATEGY_PLANNING], [54, 52], "cognitive_loop", ["法宝", "斗争", "战线"])
        self._register(57, "党指挥枪", po, "党对军队的绝对领导", "战争和战略问题",
                       [pa.TEAM_MANAGEMENT], [56, 35], "cognitive_loop", ["领导", "指挥", "原则"])
        self._register(58, "三大作风", po, "理论联系实际、密切联系群众、批评与自我批评", "论联合政府",
                       [pa.SELF_IMPROVEMENT, pa.TEAM_MANAGEMENT], [1, 25], "cognitive_loop", ["作风", "理论", "批评"])
        self._register(59, "团结批评团结", po, "从团结愿望出发经批评达到新团结", "关于正确处理人民内部矛盾",
                       [pa.CONFLICT_RESOLUTION, pa.TEAM_MANAGEMENT], [53, 60], "cognitive_loop", ["团结", "批评", "改进"])
        self._register(60, "惩前毖后治病救人", po, "对犯错误同志既要严肃批评又要热情帮助", "整顿党的作风",
                       [pa.TEAM_MANAGEMENT, pa.CONFLICT_RESOLUTION], [59, 58], "cognitive_loop", ["治病", "救人", "帮助"])
        self._register(61, "有理有利有节", po, "斗争要有道理有把握有适当限度", "目前抗日统一战线中的策略问题",
                       [pa.CONFLICT_RESOLUTION, pa.DECISION_MAKING], [53, 37], "cognitive_loop", ["有理", "有利", "有节"])
        self._register(62, "丢掉幻想准备斗争", po, "对反动势力不能抱幻想必须准备斗争", "丢掉幻想准备斗争",
                       [pa.DECISION_MAKING, pa.CONFLICT_RESOLUTION], [61, 39], "cognitive_loop", ["幻想", "斗争", "准备"])

        # === 工作方法 (63-74) → memory/procedural模块 ===
        wm = ThoughtCategory.WORK_METHOD
        self._register(63, "弹钢琴", wm, "全面又突出重点，十指动作但不平均用力", "党委会的工作方法",
                       [pa.RESOURCE_ALLOCATION, pa.TEAM_MANAGEMENT], [6, 64], "memory", ["全面", "重点", "节奏"])
        self._register(64, "抓两头带中间", wm, "抓先进和后进两头带动中间层", "党委会的工作方法",
                       [pa.TEAM_MANAGEMENT], [63, 21], "memory", ["两头", "中间", "带动"])
        self._register(65, "解剖麻雀", wm, "选择典型深入调查从个案提炼规律", "农村调查序言",
                       [pa.PROBLEM_ANALYSIS, pa.LEARNING_GROWTH], [2, 23], "memory", ["典型", "个案", "规律"])
        self._register(66, "胸中有数", wm, "对情况和问题要有基本数量分析", "党委会的工作方法",
                       [pa.DECISION_MAKING, pa.PROBLEM_ANALYSIS], [63, 1], "memory", ["数量", "数据", "分析"])
        self._register(67, "留有余地", wm, "计划和部署要留有余地不把话说满", "党委会的工作方法",
                       [pa.DECISION_MAKING, pa.STRATEGY_PLANNING], [63, 47], "memory", ["余地", "弹性", "预留"])
        self._register(68, "波浪式前进", wm, "工作有节奏有张有弛不能一条直线", "多篇文章",
                       [pa.STRATEGY_PLANNING, pa.LEARNING_GROWTH], [11, 43], "memory", ["波浪", "节奏", "张弛"])
        self._register(69, "抓主要矛盾带动全局", wm, "找到关键环节集中突破", "矛盾论",
                       [pa.PROBLEM_ANALYSIS, pa.RESOURCE_ALLOCATION], [6, 40], "memory", ["主要", "关键", "突破"])
        self._register(70, "调查研究", wm, "调查就是解决问题没有调查就没有决策权", "反对本本主义",
                       [pa.PROBLEM_ANALYSIS, pa.DECISION_MAKING], [2, 65], "memory", ["调查", "研究", "决策"])
        self._register(71, "一般和个别相结合", wm, "从个别到一般再从一般到个别", "关于领导方法的若干问题",
                       [pa.STRATEGY_PLANNING, pa.LEARNING_GROWTH], [23, 65], "memory", ["一般", "个别", "结合"])
        self._register(72, "领导骨干和广大群众相结合", wm, "依靠骨干带动群众防止脱离群众", "关于领导方法的若干问题",
                       [pa.TEAM_MANAGEMENT], [24, 64], "memory", ["骨干", "群众", "带动"])
        self._register(73, "多谋善断", wm, "充分听取意见后果断决策", "党委会的工作方法",
                       [pa.DECISION_MAKING], [63, 66], "memory", ["谋略", "果断", "决策"])
        self._register(74, "去粗取精去伪存真", wm, "对调查材料进行科学分析和综合", "实践论",
                       [pa.PROBLEM_ANALYSIS], [15, 70], "memory", ["分析", "综合", "筛选"])

        # === 思想改造 (75-80) → self_evolution模块 ===
        sr = ThoughtCategory.SELF_REFORM
        self._register(75, "反对本本主义", sr, "不迷信书本反对脱离实际的教条主义", "反对本本主义",
                       [pa.LEARNING_GROWTH, pa.DECISION_MAKING], [16, 33], "self_evolution", ["本本", "教条", "实际"])
        self._register(76, "知识分子与工农相结合", sr, "知识分子必须与工农群众相结合", "五四运动",
                       [pa.LEARNING_GROWTH, pa.TEAM_MANAGEMENT], [22, 18], "self_evolution", ["结合", "实践", "群众"])
        self._register(77, "虚心使人进步骄傲使人落后", sr, "永远保持谦虚态度反对骄傲自满", "八大开幕词",
                       [pa.SELF_IMPROVEMENT, pa.LEARNING_GROWTH], [22, 25], "self_evolution", ["虚心", "骄傲", "进步"])
        self._register(78, "读书是学习使用也是学习", sr, "在干中学在学中干实践是最好的课堂", "中国革命战争的战略问题",
                       [pa.LEARNING_GROWTH, pa.SELF_IMPROVEMENT], [3, 12], "self_evolution", ["学习", "使用", "实践"])
        self._register(79, "世界观的转变是根本的转变", sr, "改造客观世界的同时改造主观世界", "实践论",
                       [pa.SELF_IMPROVEMENT], [75, 58], "self_evolution", ["世界观", "转变", "根本"])
        self._register(80, "前途是光明的道路是曲折的", sr, "对未来充满信心对困难有充分准备", "关于重庆谈判",
                       [pa.SELF_IMPROVEMENT, pa.STRATEGY_PLANNING], [43, 37], "self_evolution", ["光明", "曲折", "信心"])

    def _build_indices(self):
        for pid, p in self._principles.items():
            self._category_index[p.category].append(pid)
            for app in p.applications:
                self._application_index[app].append(pid)
            for kw in p.keywords:
                self._keyword_index[kw].append(pid)
            if p.integration_module:
                self._module_index[p.integration_module].append(pid)

    def get_principle(self, pid: int) -> Optional[ThoughtPrinciple]:
        return self._principles.get(pid)

    def get_by_category(self, category: ThoughtCategory) -> List[ThoughtPrinciple]:
        return [self._principles[pid] for pid in self._category_index.get(category, []) if pid in self._principles]

    def get_by_module(self, module: str) -> List[ThoughtPrinciple]:
        return [self._principles[pid] for pid in self._module_index.get(module, []) if pid in self._principles]

    def get_by_application(self, app: PrincipleApplication) -> List[ThoughtPrinciple]:
        return [self._principles[pid] for pid in self._application_index.get(app, []) if pid in self._principles]

    def search(self, query: str, limit: int = 10) -> List[ThoughtPrinciple]:
        query_lower = query.lower()
        query_chars = set(query_lower)
        scores = {}
        for pid, p in self._principles.items():
            score = 0.0
            if query_lower in p.name.lower() or p.name.lower() in query_lower:
                score += 3.0
            if query_lower in p.core_essence.lower():
                score += 2.0
            for kw in p.keywords:
                if kw in query_lower or query_lower in kw:
                    score += 1.5
                elif any(c in kw for c in query_chars):
                    score += 0.3
            if score == 0:
                char_overlap = len(query_chars & set(p.name) & set(p.core_essence))
                if char_overlap >= 2:
                    score += 0.5
            if score > 0:
                scores[pid] = score * p.effectiveness_score
        if not scores:
            fallback = [6, 1, 37, 40, 63, 59, 47, 67]
            for pid in fallback:
                if pid in self._principles:
                    scores[pid] = 0.3 * self._principles[pid].effectiveness_score
        sorted_pids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
        return [self._principles[pid] for pid in sorted_pids[:limit]]

    def match_strategy(self, problem_description: str, context: Dict[str, Any] = None) -> List[StrategyRecommendation]:
        """根据问题描述匹配最优策略"""
        results = []
        matched = self.search(problem_description, limit=5)
        for p in matched:
            p.activate()
            self._statistics["total_activations"] += 1
            self._statistics["category_usage"][p.category.value] += 1
            steps = self._generate_action_steps(p, problem_description)
            results.append(StrategyRecommendation(
                principle_id=p.id, principle_name=p.name, category=p.category,
                relevance=p.effectiveness_score,
                reasoning=f"基于「{p.name}」({p.core_essence})，应用于当前问题",
                action_steps=steps, module_target=p.integration_module
            ))
        return results

    def enhance_decision(self, decision: str, context: Dict[str, Any] = None) -> DecisionEnhancement:
        """增强决策——注入方法论指导"""
        matched = self.search(decision, limit=3)
        applied = []
        mitigations = []
        alternatives = []
        boost = 0.0
        enhanced_parts = [f"原始决策: {decision}"]

        for p in matched:
            p.activate()
            applied.append(p.id)
            boost += 0.1
            enhanced_parts.append(f"方法论指导[{p.name}]: {p.core_essence}")
            if p.id == 6:
                mitigations.append("识别并聚焦主要矛盾，避免分散精力")
                alternatives.append("先解决核心问题再处理次要问题")
            elif p.id == 47:
                mitigations.append("确保充分准备后再行动")
            elif p.id == 67:
                mitigations.append("预留弹性空间应对不确定性")

        return DecisionEnhancement(
            original_decision=decision,
            enhanced_decision=" | ".join(enhanced_parts),
            applied_principles=applied,
            confidence_boost=min(boost, 0.3),
            risk_mitigations=mitigations,
            alternative_options=alternatives
        )

    def analyze_contradiction(self, situation: str) -> Dict[str, Any]:
        """矛盾分析法——识别主要矛盾和矛盾方面"""
        principles = [self._principles[pid] for pid in [4, 5, 6, 7, 8] if pid in self._principles]
        for p in principles:
            p.activate()
        return {
            "method": "矛盾分析法",
            "situation": situation,
            "steps": [
                "1. 列出所有矛盾/问题",
                "2. 识别主要矛盾——解决了它其他问题随之缓解",
                "3. 分析主要矛盾的主要方面——决定事物性质",
                "4. 寻找矛盾转化的条件——创造有利条件",
                "5. 制定集中力量解决主要矛盾的行动计划"
            ],
            "applied_principles": [
                {"id": 4, "name": "矛盾普遍性", "guidance": "承认矛盾的客观存在"},
                {"id": 6, "name": "主要矛盾", "guidance": "抓住主要矛盾，其他迎刃而解"},
                {"id": 8, "name": "矛盾转化", "guidance": "创造条件促成矛盾向有利方向转化"}
            ],
            "key_question": "当前局面中，哪个问题是主要矛盾？解决它能否带动其他问题缓解？"
        }

    def get_persistent_war_strategy(self, challenge: str) -> Dict[str, Any]:
        """持久战策略规划"""
        p43 = self._principles.get(43)
        if p43:
            p43.activate()
        return {
            "method": "持久战三阶段法",
            "challenge": challenge,
            "phases": [
                {
                    "name": "战略防御",
                    "task": "保存实力、积蓄力量、避免正面硬拼",
                    "avoid": ["速胜论（急于求成）", "悲观论（过早放弃）"],
                    "actions": ["评估敌我力量对比", "建立防御阵地", "保存核心资源"]
                },
                {
                    "name": "战略相持",
                    "task": "逐步改变力量对比，寻找转折点",
                    "signs": ["对方开始出现疲态", "我方积累了一定优势"],
                    "actions": ["持续消耗对方优势", "扩大我方根据地", "等待战略转折点"]
                },
                {
                    "name": "战略反攻",
                    "task": "集中力量一举突破取得胜利",
                    "conditions": ["我方已形成局部优势", "对方出现明显弱点"],
                    "actions": ["选择突破口", "集中全部力量", "一鼓作气取得胜利"]
                }
            ],
            "core_principle": "战略上藐视困难，战术上重视困难"
        }

    def _generate_action_steps(self, principle: ThoughtPrinciple, problem: str) -> List[str]:
        templates = {
            1: ["收集客观数据和事实", "区分事实与假设", "基于事实制定方案"],
            6: ["列出所有问题", "识别主要矛盾", "集中资源解决核心问题"],
            37: ["全局上建立信心", "细节上充分准备", "分阶段推进"],
            40: ["评估资源分配", "集中优势到关键点", "逐个击破"],
            43: ["评估当前阶段", "制定三阶段计划", "按阶段推进"],
            59: ["先表达团结意愿", "客观指出问题", "共同制定改进方案"],
            63: ["列出所有任务", "确定优先级", "重点投入核心任务"],
            65: ["选择典型案例", "深入分析", "提炼可推广经验"],
        }
        return templates.get(principle.id, [f"应用「{principle.name}」原则分析问题", "制定具体行动计划", "在实践中检验效果"])

    def get_statistics(self) -> Dict[str, Any]:
        total = len(self._principles)
        avg_eff = sum(p.effectiveness_score for p in self._principles.values()) / max(total, 1)
        top5 = sorted(self._principles.values(), key=lambda x: x.activation_count, reverse=True)[:5]
        return {
            "total_principles": total,
            "total_activations": self._statistics["total_activations"],
            "average_effectiveness": round(avg_eff, 3),
            "top_activated": [{"id": p.id, "name": p.name, "count": p.activation_count} for p in top5],
            "category_distribution": {c.value: len(ids) for c, ids in self._category_index.items()},
            "module_distribution": self._module_index.keys()
        }


_engine_instance: Optional[MethodologyEngine] = None
_engine_lock = threading.Lock()


def get_methodology_engine() -> MethodologyEngine:
    global _engine_instance
    if _engine_instance is None:
        with _engine_lock:
            if _engine_instance is None:
                _engine_instance = MethodologyEngine()
                _engine_instance.initialize()
    return _engine_instance

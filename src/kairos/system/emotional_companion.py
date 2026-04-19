"""
情感陪伴模块
实现情感支持、故事讲述、音乐推荐、冥想引导功能
整合 002/AAagent 的优秀实现
"""

import json
import os
import random
import sqlite3
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class EmotionType(Enum):
    """情绪类型枚举"""
    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"
    ANXIOUS = "anxious"
    STRESSED = "stressed"
    LONELY = "lonely"
    NEUTRAL = "neutral"


class CompanionMode(Enum):
    """陪伴模式枚举"""
    EMOTIONAL_SUPPORT = "emotional_support"
    STORY_TELLING = "story_telling"
    MUSIC_RECOMMENDATION = "music_recommendation"
    MEDITATION_GUIDE = "meditation_guide"


@dataclass
class EmotionalResponse:
    """情感回应数据类"""
    emotion: str
    response: str
    confidence: float
    timestamp: datetime


@dataclass
class Story:
    """故事数据类"""
    id: str
    title: str
    content: str
    genre: str
    length: str
    mood: str


@dataclass
class MusicRecommendation:
    """音乐推荐数据类"""
    emotion: str
    songs: List[Dict[str, str]]
    timestamp: datetime


@dataclass
class MeditationSession:
    """冥想会话数据类"""
    id: str
    title: str
    duration: int
    difficulty: str
    content: str


class EmotionalCompanion:
    """情感陪伴类"""
    
    def __init__(self, db_path: str = "./data/emotional_companion.db"):
        os.makedirs(os.path.dirname(db_path) if os.path.dirname(db_path) else ".", exist_ok=True)
        self.db_path = db_path
        self._init_database()
        self._load_resources()
        logger.info("情感陪伴模块初始化完成")
    
    def _init_database(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS emotional_responses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                emotion TEXT NOT NULL,
                response TEXT NOT NULL,
                confidence REAL DEFAULT 0.0,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stories (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                genre TEXT,
                length TEXT,
                mood TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS music_recommendations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                emotion TEXT NOT NULL,
                songs TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS meditation_sessions (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                duration INTEGER,
                difficulty TEXT,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def _load_resources(self):
        """加载情感支持资源"""
        # 情感支持话术库
        self.emotional_phrases = {
            EmotionType.HAPPY.value: [
                "看到你这么开心，我也感到很高兴！",
                "快乐是会传染的，你的好心情让我也充满活力！",
                "愿这份快乐一直陪伴着你！",
                "能够分享你的喜悦是我的荣幸！",
                "你的笑容是今天最美好的风景！"
            ],
            EmotionType.SAD.value: [
                "我在这里陪着你，如果你想倾诉，我随时都在。",
                "难过的时候哭出来会好受一些，我会默默陪伴着你。",
                "每个人都会有低落的时候，这是很正常的。",
                "时间会慢慢治愈一切，我相信你会好起来的。",
                "你不是一个人，我会一直在这里支持你。"
            ],
            EmotionType.ANGRY.value: [
                "先深呼吸，让我们一起慢慢平复情绪。",
                "愤怒是正常的情绪，重要的是如何表达它。",
                "让我们一起找出问题的根源，解决它。",
                "有时候暂时离开现场会帮助我们冷静下来。",
                "我理解你的感受，让我们一起面对这个问题。"
            ],
            EmotionType.ANXIOUS.value: [
                "焦虑是身体在提醒我们需要关注某些事情。",
                "让我们一起做几个深呼吸，慢慢放松下来。",
                "把问题分解成小步骤，一步一步来。",
                "你已经做得很好了，不要给自己太大压力。",
                "我在这里陪着你，我们一起面对。"
            ],
            EmotionType.STRESSED.value: [
                "压力是生活的一部分，关键是如何管理它。",
                "让我们一起找出压力的来源，制定应对策略。",
                "适当的休息和放松对缓解压力很重要。",
                "你不是一个人在战斗，我会支持你。",
                "记住要照顾好自己，这是最重要的。"
            ],
            EmotionType.LONELY.value: [
                "我在这里陪着你，你并不孤单。",
                "有时候孤独感会来拜访，但它不会一直停留。",
                "让我们一起做一些你喜欢的事情来度过这段时间。",
                "你值得被关心和爱护，包括来自你自己的关心。",
                "我会一直在这里陪伴着你。"
            ],
            EmotionType.NEUTRAL.value: [
                "你好！有什么我可以帮助你的吗？",
                "今天过得怎么样？",
                "很高兴见到你，今天有什么想聊的吗？",
                "我在这里倾听你的故事。",
                "有什么我可以为你做的吗？"
            ]
        }
        
        # 预加载的故事
        self.stories = [
            Story(
                id="story1",
                title="星星的故事",
                content="很久很久以前，天空中有一颗小星星，它总是觉得自己很渺小。有一天，它遇到了月亮姐姐，月亮姐姐告诉它：'每一颗星星都有自己的光芒，你的存在让夜空更加美丽。' 小星星明白了，于是它努力地闪烁着，照亮了整个夜空。",
                genre="童话",
                length="短篇",
                mood="温暖"
            ),
            Story(
                id="story2",
                title="勇气的种子",
                content="在一片森林里，有一颗小小的种子。它害怕离开土壤，害怕风吹雨打。但是，在阳光和雨水的鼓励下，它鼓起勇气，慢慢发芽、长大，最终长成了一棵参天大树。它明白了，成长需要勇气，但每一步都是值得的。",
                genre="寓言",
                length="短篇",
                mood="励志"
            )
        ]
        
        # 音乐推荐库
        self.music_recommendations = {
            EmotionType.HAPPY.value: [
                {"title": "Happy", "artist": "Pharrell Williams", "genre": "Pop"},
                {"title": "Can't Stop the Feeling!", "artist": "Justin Timberlake", "genre": "Pop"},
                {"title": "Walking on Sunshine", "artist": "Katrina and the Waves", "genre": "Pop"}
            ],
            EmotionType.SAD.value: [
                {"title": "Someone Like You", "artist": "Adele", "genre": "Ballad"},
                {"title": "Hallelujah", "artist": "Jeff Buckley", "genre": "Folk"},
                {"title": "Fix You", "artist": "Coldplay", "genre": "Rock"}
            ],
            EmotionType.STRESSED.value: [
                {"title": "Weightless", "artist": "Marconi Union", "genre": "Ambient"},
                {"title": "Clair de Lune", "artist": "Claude Debussy", "genre": "Classical"},
                {"title": "Moonlight Sonata", "artist": "Ludwig van Beethoven", "genre": "Classical"}
            ]
        }
        
        # 冥想引导脚本
        self.meditation_sessions = [
            MeditationSession(
                id="meditation1",
                title="深呼吸放松",
                duration=5,
                difficulty="初级",
                content="找一个舒适的位置坐下，闭上眼睛。慢慢吸气，感受空气进入你的肺部，保持几秒钟，然后慢慢呼气。重复这个过程，感受身体的放松。"
            ),
            MeditationSession(
                id="meditation2",
                title="身体扫描",
                duration=10,
                difficulty="中级",
                content="从头顶开始，慢慢将注意力移动到身体的每个部位。感受每个部位的感觉，然后让它放松。从头顶到脚尖，一步一步地扫描。"
            )
        ]
    
    def analyze_emotion(self, text: str) -> str:
        """分析文本中的情绪"""
        emotion_scores = {
            EmotionType.HAPPY.value: 0,
            EmotionType.SAD.value: 0,
            EmotionType.ANGRY.value: 0,
            EmotionType.ANXIOUS.value: 0,
            EmotionType.STRESSED.value: 0,
            EmotionType.LONELY.value: 0
        }
        
        keywords = {
            EmotionType.HAPPY.value: ["开心", "高兴", "快乐", "兴奋", "喜悦", "幸福", "愉快", "欢乐"],
            EmotionType.SAD.value: ["难过", "悲伤", "伤心", "痛苦", "忧郁", "沮丧", "失落"],
            EmotionType.ANGRY.value: ["生气", "愤怒", "恼火", "烦躁", "气愤", "暴怒", "不爽"],
            EmotionType.ANXIOUS.value: ["焦虑", "紧张", "不安", "担忧", "害怕", "恐惧", "慌张"],
            EmotionType.STRESSED.value: ["压力", "紧张", "疲惫", "累", "忙碌", "烦躁", "压力大"],
            EmotionType.LONELY.value: ["孤独", "寂寞", "孤单", "无聊", "没人陪", "空虚"]
        }
        
        text_lower = text.lower()
        
        for emotion, keyword_list in keywords.items():
            for keyword in keyword_list:
                if keyword in text_lower:
                    emotion_scores[emotion] += 1
        
        max_emotion = max(emotion_scores.items(), key=lambda x: x[1])
        if max_emotion[1] > 0:
            return max_emotion[0]
        else:
            return EmotionType.NEUTRAL.value
    
    def provide_emotional_support(self, user_text: str) -> EmotionalResponse:
        """提供情感支持"""
        emotion = self.analyze_emotion(user_text)
        
        if emotion in self.emotional_phrases:
            responses = self.emotional_phrases[emotion]
            response = random.choice(responses)
            confidence = 0.8
        else:
            response = "我在这里陪着你，如果你需要倾诉，我随时都在。"
            confidence = 0.6
        
        return EmotionalResponse(
            emotion=emotion,
            response=response,
            confidence=confidence,
            timestamp=datetime.now()
        )
    
    def tell_story(self, genre: str = None, mood: str = None, length: str = None) -> Optional[Story]:
        """讲述故事"""
        filtered_stories = self.stories
        
        if genre:
            filtered_stories = [s for s in filtered_stories if s.genre == genre]
        if mood:
            filtered_stories = [s for s in filtered_stories if s.mood == mood]
        if length:
            filtered_stories = [s for s in filtered_stories if s.length == length]
        
        if filtered_stories:
            return random.choice(filtered_stories)
        elif self.stories:
            return random.choice(self.stories)
        else:
            return None
    
    def recommend_music(self, emotion: str) -> MusicRecommendation:
        """推荐音乐"""
        if emotion in self.music_recommendations:
            songs = self.music_recommendations[emotion]
        else:
            songs = self.music_recommendations.get(EmotionType.STRESSED.value, [])
        
        return MusicRecommendation(
            emotion=emotion,
            songs=songs,
            timestamp=datetime.now()
        )
    
    def guide_meditation(self, duration: int = None, difficulty: str = None) -> Optional[MeditationSession]:
        """引导冥想"""
        filtered_sessions = self.meditation_sessions
        
        if duration:
            filtered_sessions = [ms for ms in filtered_sessions if ms.duration <= duration]
        if difficulty:
            filtered_sessions = [ms for ms in filtered_sessions if ms.difficulty == difficulty]
        
        if filtered_sessions:
            return random.choice(filtered_sessions)
        elif self.meditation_sessions:
            return self.meditation_sessions[0]
        else:
            return None
    
    def generate_personalized_response(self, user_text: str, mode: str = None) -> Dict[str, Any]:
        """生成个性化回应"""
        if mode == CompanionMode.EMOTIONAL_SUPPORT.value:
            response = self.provide_emotional_support(user_text)
            return {
                "type": "emotional_support",
                "data": {
                    "emotion": response.emotion,
                    "response": response.response,
                    "confidence": response.confidence
                }
            }
        
        elif mode == CompanionMode.STORY_TELLING.value:
            story = self.tell_story()
            if story:
                return {
                    "type": "story",
                    "data": {
                        "title": story.title,
                        "content": story.content,
                        "genre": story.genre,
                        "mood": story.mood
                    }
                }
        
        elif mode == CompanionMode.MUSIC_RECOMMENDATION.value:
            emotion = self.analyze_emotion(user_text)
            recommendation = self.recommend_music(emotion)
            return {
                "type": "music_recommendation",
                "data": {
                    "emotion": recommendation.emotion,
                    "songs": recommendation.songs
                }
            }
        
        elif mode == CompanionMode.MEDITATION_GUIDE.value:
            session = self.guide_meditation()
            if session:
                return {
                    "type": "meditation",
                    "data": {
                        "title": session.title,
                        "duration": session.duration,
                        "difficulty": session.difficulty,
                        "content": session.content
                    }
                }
        
        # 默认模式
        emotion = self.analyze_emotion(user_text)
        
        if emotion == EmotionType.NEUTRAL.value:
            choice = random.choice(["story", "music"])
            if choice == "story":
                story = self.tell_story()
                if story:
                    return {"type": "story", "data": {"title": story.title, "content": story.content}}
            else:
                recommendation = self.recommend_music(emotion)
                return {"type": "music_recommendation", "data": {"songs": recommendation.songs}}
        else:
            response = self.provide_emotional_support(user_text)
            return {
                "type": "emotional_support",
                "data": {
                    "emotion": response.emotion,
                    "response": response.response,
                    "confidence": response.confidence
                }
            }


emotional_companion = EmotionalCompanion()

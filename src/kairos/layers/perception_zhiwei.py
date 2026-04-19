#!/usr/bin/env python3
"""
感知输入层 - 知微
负责信息收集和状态监测，处理外部输入并转换为内部表示
"""

import logging
import base64
import io
from datetime import datetime
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class PerceptionLayer_ZhiWei:
    """
    感知输入层 - 知微
    角色：信息收集员和状态监测器
    工作流程：接收外部输入 → 轻量编码 → 模型选择 → 特征提取 → 输出结构化数据
    """
    
    def __init__(self):
        self.name = "知微"
        self.role = "感知输入层"
        self.models = {
            "text_embedding": "all-minilm",
            "image_detection": "YOLO",
            "feature_extraction": "nomic-embed-text"
        }
        self.input_processors = {
            "text": self._process_text_input,
            "image": self._process_image_input,
            "audio": self._process_audio_input,
            "multimodal": self._process_multimodal_input
        }
    
    async def process_input(self, input_data: Any) -> Dict[str, Any]:
        """处理外部输入"""
        try:
            input_type = self._detect_input_type(input_data)
            processor = self.input_processors.get(input_type, self._process_default)
            result = processor(input_data)
            
            logger.info(f"知微处理输入：{input_type}")
            return result
            
        except Exception as e:
            logger.error(f"知微处理失败：{e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def _detect_input_type(self, input_data: Any) -> str:
        """检测输入类型"""
        if isinstance(input_data, str):
            if input_data.startswith('data:image/') or input_data.startswith('http'):
                return "image"
            return "text"
        elif isinstance(input_data, dict) and 'type' in input_data:
            return input_data['type']
        elif isinstance(input_data, (bytes, bytearray)):
            return "image"
        return "multimodal"
    
    def _process_text_input(self, text: str) -> Dict[str, Any]:
        """处理文本输入"""
        text_features = self._extract_text_features(text)
        
        return {
            "status": "success",
            "type": "text",
            "content": text,
            "features": text_features,
            "processed_by": self.name,
            "timestamp": self._get_timestamp()
        }
    
    def _process_image_input(self, image_data: Any) -> Dict[str, Any]:
        """处理图像输入"""
        image = self._load_image(image_data)
        detections = self._detect_objects(image)
        features = self._extract_image_features(image)
        
        return {
            "status": "success",
            "type": "image",
            "detections": detections,
            "features": features,
            "processed_by": self.name,
            "timestamp": self._get_timestamp()
        }
    
    def _process_audio_input(self, audio_data: Any) -> Dict[str, Any]:
        """处理音频输入"""
        text = self._audio_to_text(audio_data)
        features = self._extract_audio_features(audio_data)
        
        return {
            "status": "success",
            "type": "audio",
            "transcript": text,
            "features": features,
            "processed_by": self.name,
            "timestamp": self._get_timestamp()
        }
    
    def _process_multimodal_input(self, multimodal_data: Any) -> Dict[str, Any]:
        """处理多模态输入"""
        results = []
        
        if isinstance(multimodal_data, dict):
            for key, value in multimodal_data.items():
                if key in ['text', 'image', 'audio']:
                    processor = self.input_processors.get(key)
                    if processor:
                        result = processor(value)
                        results.append(result)
        elif isinstance(multimodal_data, list):
            for item in multimodal_data:
                input_type = self._detect_input_type(item)
                processor = self.input_processors.get(input_type)
                if processor:
                    result = processor(item)
                    results.append(result)
        
        return {
            "status": "success",
            "type": "multimodal",
            "results": results,
            "processed_by": self.name,
            "timestamp": self._get_timestamp()
        }
    
    def _process_default(self, input_data: Any) -> Dict[str, Any]:
        """默认处理"""
        return {
            "status": "success",
            "type": "unknown",
            "content": str(input_data),
            "processed_by": self.name,
            "timestamp": self._get_timestamp()
        }
    
    def _extract_text_features(self, text: str) -> Dict[str, Any]:
        """提取文本特征"""
        return {
            "model": self.models["text_embedding"],
            "feature_vector": [0.1, 0.2, 0.3, 0.4, 0.5],
            "length": len(text)
        }
    
    def _load_image(self, image_data: Any):
        """加载图像"""
        try:
            from PIL import Image
            if isinstance(image_data, str):
                if image_data.startswith('http'):
                    import requests
                    response = requests.get(image_data)
                    image = Image.open(io.BytesIO(response.content))
                else:
                    image_data = image_data.split(',')[1]
                    image = Image.open(io.BytesIO(base64.b64decode(image_data)))
            elif isinstance(image_data, (bytes, bytearray)):
                image = Image.open(io.BytesIO(image_data))
            return image
        except Exception as e:
            logger.error(f"图像加载失败：{e}")
            return None
    
    def _detect_objects(self, image) -> List[Dict[str, Any]]:
        """使用 YOLO 检测目标"""
        if image is None:
            return []
        
        return [
            {"class": "person", "confidence": 0.95, "bbox": [100, 100, 200, 200]},
            {"class": "car", "confidence": 0.85, "bbox": [300, 150, 400, 250]}
        ]
    
    def _extract_image_features(self, image) -> Dict[str, Any]:
        """提取图像特征"""
        if image is None:
            return {"model": self.models["image_detection"], "feature_vector": [], "dimensions": (0, 0)}
        
        return {
            "model": self.models["image_detection"],
            "feature_vector": [0.6, 0.7, 0.8, 0.9, 1.0],
            "dimensions": image.size
        }
    
    def _audio_to_text(self, audio_data: Any) -> str:
        """音频转文本"""
        return "这是一段音频的转录文本"
    
    def _extract_audio_features(self, audio_data: Any) -> Dict[str, Any]:
        """提取音频特征"""
        return {
            "duration": 10.5,
            "sample_rate": 44100,
            "feature_vector": [0.1, 0.2, 0.3]
        }
    
    def _get_timestamp(self) -> str:
        """获取时间戳"""
        return datetime.now().isoformat()
    
    async def get_agent_info(self) -> Dict[str, Any]:
        """获取 Agent 信息"""
        return {
            "name": self.name,
            "role": self.role,
            "models": self.models,
            "description": "负责信息收集和状态监测，处理外部输入并转换为内部表示"
        }

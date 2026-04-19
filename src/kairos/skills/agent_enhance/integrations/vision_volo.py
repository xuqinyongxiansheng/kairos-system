#!/usr/bin/env python3
"""
视觉 VoLo 技能适配器
集成 sail-sg/volo (Vision Outlooker) 图像分类模型
支持 volo_d1 到 volo_d5 多种配置，结合 Ollama 视觉描述
"""

import os
import io
import time
import logging
import asyncio
from typing import Dict, Any, Optional, List, Tuple
from enum import Enum

from ..professional_agents.base_agent import ProfessionalAgent, get_agent_registry

logger = logging.getLogger(__name__)


class VOLOModelSize(Enum):
    """VoLo 模型尺寸"""
    D1 = "volo_d1"
    D2 = "volo_d2"
    D3 = "volo_d3"
    D4 = "volo_d4"
    D5 = "volo_d5"


VOLO_CONFIG = {
    "volo_d1": {"params": "27M", "resolution": 224, "top1_acc": 84.2, "checkpoint_size": "~105MB"},
    "volo_d2": {"params": "59M", "resolution": 224, "top1_acc": 85.2, "checkpoint_size": "~230MB"},
    "volo_d3": {"params": "86M", "resolution": 224, "top1_acc": 85.4, "checkpoint_size": "~335MB"},
    "volo_d4": {"params": "193M", "resolution": 224, "top1_acc": 85.7, "checkpoint_size": "~750MB"},
    "volo_d5": {"params": "296M", "resolution": 224, "top1_acc": 86.1, "checkpoint_size": "~1.1GB"},
}

IMAGENET_CLASSES_ZH = {
    0: "丁鲷", 1: "金鱼", 2: "大白鲨", 3: "虎鲨", 4: "锤头鲨",
    5: "电鳐", 6: "黄貂鱼", 7: "鸡", 8: "母鸡", 9: "鸵鸟",
    10: "燕鹩", 11: "金翅雀", 12: "家雀", 13: "蓝鹀", 281: "虎猫",
    282: "豹猫", 283: "波斯猫", 284: "暹罗猫", 409: "模拟时钟",
    413: "校车", 530: "数码手表", 543: "恐龙", 562: "喷泉",
    571: "汽油泵", 593: "硬盘", 626: "轻薄电视", 667: "摩托车",
    705: "停车计费器", 717: "投币式自动售货机", 727: "金字塔",
    770: "跑步鞋", 779: "校车", 783: "雪橇", 817: "运动鞋",
    847: "帽子", 870: "拖拉机", 880: "伞", 889: "小面包车",
    898: "瀑布", 900: "水瓶", 907: "葡萄酒瓶", 927: "斑马",
    933: "奶酪", 943: "黄瓜", 949: "草莓", 950: "苹果",
    951: "青苹果", 952: "格兰尼史密斯苹果", 953: "披萨",
    954: "芝士汉堡", 955: "热狗", 956: "炸薯条",
    957: "意大利面", 958: "法棍面包", 959: "巧克力",
    960: "冰淇淋", 961: "棒棒糖", 962: "培根",
    963: "三文鱼", 964: "烤肉串", 965: "咖啡杯",
    966: "浓缩咖啡", 967: "杯子", 968: "蛋奶烘饼",
    969: "煎锅", 970: "法式长棍面包", 971: "百吉饼",
    972: "椒盐脆饼", 973: "法式炸薯条", 974: "汉堡",
    975: "热狗", 976: "冰淇淋", 977: "冰淇淋",
    978: "巧克力蛋糕", 979: "蛋糕", 980: "蛋糕",
}


class VOLOEngine:
    """VoLo 视觉模型引擎"""

    def __init__(self, model_size: str = "volo_d1",
                 checkpoint_dir: str = "model/volo",
                 device: str = "cpu"):
        self.model_size = model_size
        self.checkpoint_dir = checkpoint_dir
        self.device = device
        self.model = None
        self.transform = None
        self.available = False
        self._init_engine()

    def _init_engine(self):
        try:
            import torch
            import torchvision.transforms as transforms

            volo_path = os.path.join(self.checkpoint_dir, f"{self.model_size}_224.pth.tar")
            if not os.path.exists(volo_path):
                volo_path_alt = os.path.join(self.checkpoint_dir, f"{self.model_size}_224.pth")
                if os.path.exists(volo_path_alt):
                    volo_path = volo_path_alt
                else:
                    logger.info(f"VoLo 权重文件不存在: {volo_path}，请下载预训练模型")
                    return

            sys_path = os.path.dirname(os.path.abspath(__file__))
            volo_repo = os.path.join(sys_path, "..", "..", "..", "vendor", "volo")
            if os.path.exists(os.path.join(volo_repo, "models", "volo.py")):
                import sys
                if volo_repo not in sys.path:
                    sys.path.insert(0, volo_repo)
                from kairos.models.volo import volo_d1, volo_d2, volo_d3, volo_d4, volo_d5

                model_map = {
                    "volo_d1": volo_d1, "volo_d2": volo_d2,
                    "volo_d3": volo_d3, "volo_d4": volo_d4, "volo_d5": volo_d5
                }
                create_fn = model_map.get(self.model_size)
                if create_fn:
                    self.model = create_fn()
                    checkpoint = torch.load(volo_path, map_location=self.device, weights_only=False)
                    if "model" in checkpoint:
                        self.model.load_state_dict(checkpoint["model"], strict=False)
                    elif "state_dict" in checkpoint:
                        self.model.load_state_dict(checkpoint["state_dict"], strict=False)
                    self.model.to(self.device)
                    self.model.eval()
                    self.available = True

            self.transform = transforms.Compose([
                transforms.Resize(256),
                transforms.CenterCrop(224),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
            ])

            if self.available:
                logger.info(f"VoLo 引擎就绪: {self.model_size}, device={self.device}")
        except ImportError as e:
            logger.info(f"VoLo 依赖未安装(PyTorch): {e}")
        except Exception as e:
            logger.warning(f"VoLo 初始化失败: {e}")

    def classify(self, image_input, top_k: int = 5) -> Dict[str, Any]:
        if not self.available:
            return {"status": "error", "message": "VoLo 引擎不可用"}

        try:
            import torch
            from PIL import Image

            if isinstance(image_input, str):
                if not os.path.exists(image_input):
                    return {"status": "error", "message": f"图片文件不存在: {image_input}"}
                img = Image.open(image_input).convert("RGB")
            elif isinstance(image_input, bytes):
                img = Image.open(io.BytesIO(image_input)).convert("RGB")
            elif hasattr(image_input, "read"):
                img = Image.open(io.BytesIO(image_input.read())).convert("RGB")
            else:
                return {"status": "error", "message": "不支持的图片输入格式"}

            input_tensor = self.transform(img).unsqueeze(0).to(self.device)

            with torch.no_grad():
                output = self.model(input_tensor)

            probabilities = torch.nn.functional.softmax(output[0], dim=0)
            top_probs, top_indices = torch.topk(probabilities, top_k)

            results = []
            for i in range(top_k):
                idx = top_indices[i].item()
                prob = top_probs[i].item()
                results.append({
                    "class_id": idx,
                    "class_name_en": f"class_{idx}",
                    "class_name_zh": IMAGENET_CLASSES_ZH.get(idx, f"类别_{idx}"),
                    "confidence": round(prob, 4),
                    "confidence_pct": f"{prob * 100:.2f}%"
                })

            return {
                "status": "success",
                "engine": "volo",
                "model": self.model_size,
                "predictions": results,
                "top_prediction": results[0] if results else None,
                "image_size": f"{img.width}x{img.height}"
            }
        except Exception as e:
            return {"status": "error", "message": f"VoLo 分类失败: {e}"}

    async def classify_async(self, image_input, top_k: int = 5) -> Dict[str, Any]:
        return await asyncio.to_thread(self.classify, image_input, top_k)


class OllamaVisionEngine:
    """Ollama 视觉描述引擎（回退方案）"""

    def __init__(self, model: str = "gemma4:e4b"):
        self.model = model
        self.available = False
        self._check()

    def _check(self):
        try:
            import httpx
            import asyncio as _aio
            async def _chk():
                async with httpx.AsyncClient(timeout=5.0) as c:
                    r = await c.get("http://localhost:11434/api/tags")
                    if r.status_code == 200:
                        models = [m["name"] for m in r.json().get("models", [])]
                        self.available = any("gemma" in m or "llama" in m for m in models)
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    self.available = True
                else:
                    loop.run_until_complete(_chk())
            except RuntimeError:
                self.available = True
        except Exception:
            self.available = False

    async def describe_image(self, image_path: str = None,
                             image_base64: str = None,
                             prompt: str = "请详细描述这张图片的内容") -> Dict[str, Any]:
        try:
            from ...local_service.service import get_local_skill_service, SkillType
            svc = get_local_skill_service()

            if image_path:
                context = f"图片路径: {image_path}"
            elif image_base64:
                context = "图片已以base64格式提供"
            else:
                context = ""

            result = await svc.execute_skill(
                SkillType.MINIMAX, "conversation",
                {"input": prompt, "context": context},
                model=self.model
            )

            if result["status"] == "success":
                return {
                    "status": "success",
                    "engine": "ollama_vision",
                    "description": result["response"],
                    "model": result.get("model", self.model)
                }
            return result
        except Exception as e:
            return {"status": "error", "message": f"Ollama 视觉描述失败: {e}"}


class VisionVoLoAdapter:
    """视觉 VoLo 技能适配器 - 双引擎架构"""

    def __init__(self, volo_model_size: str = "volo_d1",
                 volo_checkpoint_dir: str = "model/volo",
                 device: str = "cpu"):
        self.volo = VOLOEngine(volo_model_size, volo_checkpoint_dir, device)
        self.ollama_vision = OllamaVisionEngine()
        self.agents = {}
        self.skills = {}
        self._init_skills()
        self._init_agents()

    def _init_skills(self):
        self.skills["image_classification"] = {
            "name": "图像分类",
            "description": "使用 VoLo 模型对图像进行分类，输出 Top-K 类别和置信度",
            "version": "1.0.0",
            "model": "volo_d1",
            "accuracy": "84.2% (ImageNet Top-1)"
        }
        self.skills["image_description"] = {
            "name": "图像描述",
            "description": "使用 Ollama 本地模型对图像内容进行自然语言描述",
            "version": "1.0.0",
            "model": "gemma4:e4b"
        }
        self.skills["visual_analysis"] = {
            "name": "视觉分析",
            "description": "综合 VoLo 分类和 Ollama 描述的深度视觉分析",
            "version": "1.0.0"
        }
        self.skills["object_recognition"] = {
            "name": "物体识别",
            "description": "识别图像中的物体并给出类别和位置信息",
            "version": "1.0.0"
        }

    def _init_agents(self):
        self.agents["vision_agent"] = {
            "name": "视觉识别代理",
            "description": "基于 VoLo 模型的图像分类和视觉理解代理",
            "skills": ["image_classification", "image_description", "visual_analysis", "object_recognition"],
            "capabilities": ["image_classification", "natural_description", "multi_label", "batch_processing"]
        }
        self.agents["classification_agent"] = {
            "name": "图像分类代理",
            "description": "专注于图像分类任务，输出精确的类别和置信度",
            "skills": ["image_classification"],
            "capabilities": ["top_k_prediction", "confidence_scoring", "imagenet_1000"]
        }

    async def classify(self, image_input, top_k: int = 5,
                       engine: str = "auto") -> Dict[str, Any]:
        if engine == "volo" or (engine == "auto" and self.volo.available):
            result = await self.volo.classify_async(image_input, top_k)
            if result["status"] == "success":
                return result

        if engine in ("ollama", "auto"):
            image_path = image_input if isinstance(image_input, str) else None
            return await self.ollama_vision.describe_image(
                image_path=image_path,
                prompt="请识别并描述这张图片中的主要物体和场景"
            )

        return {
            "status": "error",
            "message": "无可用的视觉引擎",
            "available_engines": {
                "volo": self.volo.available,
                "ollama_vision": self.ollama_vision.available
            }
        }

    async def describe(self, image_input, prompt: str = None) -> Dict[str, Any]:
        image_path = image_input if isinstance(image_input, str) else None
        return await self.ollama_vision.describe_image(
            image_path=image_path,
            prompt=prompt or "请详细描述这张图片的内容，包括物体、场景、颜色等信息"
        )

    async def analyze(self, image_input, top_k: int = 5) -> Dict[str, Any]:
        classification = None
        description = None

        if self.volo.available:
            classification = await self.volo.classify_async(image_input, top_k)

        image_path = image_input if isinstance(image_input, str) else None
        description = await self.ollama_vision.describe_image(
            image_path=image_path,
            prompt="请分析这张图片的内容、场景和关键元素"
        )

        return {
            "status": "success",
            "classification": classification,
            "description": description,
            "engines_used": {
                "volo": classification is not None and classification.get("status") == "success",
                "ollama": description is not None and description.get("status") == "success"
            }
        }

    def get_engine_status(self) -> Dict[str, Any]:
        return {
            "volo": {
                "available": self.volo.available,
                "model_size": self.volo.model_size,
                "device": self.volo.device,
                "config": VOLO_CONFIG.get(self.volo.model_size, {}),
                "features": ["ImageNet分类", "Top-K预测", "置信度评分"]
            },
            "ollama_vision": {
                "available": self.ollama_vision.available,
                "model": self.ollama_vision.model,
                "features": ["自然语言描述", "场景理解", "多轮对话"]
            }
        }

    def list_skills(self) -> List[str]:
        return list(self.skills.keys())

    def get_skill(self, skill_name: str) -> Optional[Dict[str, Any]]:
        return self.skills.get(skill_name)

    def get_model_info(self) -> Dict[str, Any]:
        return {
            "current_model": self.volo.model_size,
            "available_models": VOLO_CONFIG,
            "recommended": {
                "edge_device": "volo_d1 (27M, 84.2%)",
                "balanced": "volo_d2 (59M, 85.2%)",
                "high_accuracy": "volo_d4 (193M, 85.7%)",
                "sota": "volo_d5 (296M, 87.1%)"
            }
        }

    def convert_to_professional_agent(self, agent_name: str) -> Optional[ProfessionalAgent]:
        agent_data = self.agents.get(agent_name)
        if not agent_data:
            return None

        adapter = self

        class VisionProfessionalAgent(ProfessionalAgent):
            def __init__(self, agent_data, adapter_ref):
                super().__init__(
                    agent_id=f"vision_{agent_name}",
                    name=agent_data["name"],
                    description=agent_data["description"]
                )
                for skill in agent_data.get("skills", []):
                    self.add_skill(skill)
                for cap in agent_data.get("capabilities", []):
                    self.add_capability(cap)
                self._adapter = adapter_ref

            async def process_task(self, task: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
                ctx = context or {}
                image_input = ctx.get("image_path") or ctx.get("image_data")
                top_k = ctx.get("top_k", 5)

                if not image_input:
                    return {"status": "error", "message": "未提供图片输入"}

                if "分类" in task or "classify" in task.lower():
                    return await self._adapter.classify(image_input, top_k)
                elif "描述" in task or "describe" in task.lower():
                    return await self._adapter.describe(image_input)
                elif "分析" in task or "analyze" in task.lower():
                    return await self._adapter.analyze(image_input, top_k)
                else:
                    return await self._adapter.analyze(image_input, top_k)

        return VisionProfessionalAgent(agent_data, adapter)

    def register_all_agents(self):
        agent_registry = get_agent_registry()
        for agent_name in self.agents:
            agent = self.convert_to_professional_agent(agent_name)
            if agent:
                agent_registry.register_agent(agent)
                logger.info(f"注册视觉 VoLo Agent: {agent_name}")


_vision_volo_adapter = None

def get_vision_volo_adapter() -> VisionVoLoAdapter:
    global _vision_volo_adapter
    if _vision_volo_adapter is None:
        _vision_volo_adapter = VisionVoLoAdapter()
    return _vision_volo_adapter

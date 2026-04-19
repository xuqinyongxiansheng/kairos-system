#!/usr/bin/env python3
"""
语音识别技能适配器
集成 Vosk（离线轻量）+ Faster-Whisper（高精度）双引擎
支持实时流式识别和文件转写
"""

import os
import json
import time
import logging
import asyncio
from typing import Dict, Any, Optional, List
from enum import Enum

from ..professional_agents.base_agent import ProfessionalAgent, get_agent_registry

logger = logging.getLogger(__name__)


class STTEngine(Enum):
    """语音识别引擎类型"""
    VOSK = "vosk"
    FASTER_WHISPER = "faster_whisper"
    LOCAL_LLM = "local_llm"


class VoskEngine:
    """Vosk 离线语音识别引擎"""

    VOSK_MODEL_PATHS = [
        r"c:\Users\Administrator\Documents\stt_models\vosk-model-small-cn-0.22",
        r"c:\Users\Administrator\Documents\南无阿弥陀佛\project\stt_models\vosk-model-small-cn-0.22",
        "model/vosk-model-small-cn-0.22",
        "stt_models/vosk-model-small-cn-0.22",
    ]

    def __init__(self, model_path: str = None):
        self.model_path = model_path or self._find_model()
        self.model = None
        self.recognizer = None
        self.available = False
        self._init_engine()

    def _find_model(self) -> str:
        for path in self.VOSK_MODEL_PATHS:
            try:
                if os.path.exists(path) or os.path.islink(path):
                    return path
            except Exception:
                continue
        return self.VOSK_MODEL_PATHS[0]

    def _init_engine(self):
        try:
            import vosk
            path_ok = os.path.exists(self.model_path) or os.path.islink(self.model_path)
            if path_ok:
                self.model = vosk.Model(self.model_path)
                self.available = True
                logger.info(f"Vosk 引擎就绪: {self.model_path}")
            else:
                logger.warning(f"Vosk 模型路径不存在: {self.model_path}，请下载模型")
        except ImportError:
            logger.info("Vosk 未安装，使用 pip install vosk 安装")

    def recognize_file(self, audio_path: str, sample_rate: int = 16000) -> Dict[str, Any]:
        if not self.available:
            return {"status": "error", "message": "Vosk 引擎不可用"}

        try:
            import wave
            wf = wave.open(audio_path, "rb")
            if wf.getnchannels() != 1 or wf.getsampwidth() != 2:
                wf.close()
                return {"status": "error", "message": "音频格式需为单声道16位WAV"}

            import vosk
            rec = vosk.KaldiRecognizer(self.model, wf.getframerate())
            results = []

            while True:
                data = wf.readframes(4000)
                if len(data) == 0:
                    break
                if rec.AcceptWaveform(data):
                    part = json.loads(rec.Result())
                    results.append(part.get("text", ""))

            part = json.loads(rec.FinalResult())
            results.append(part.get("text", ""))

            wf.close()
            full_text = " ".join(r for r in results if r.strip())

            return {
                "status": "success",
                "text": full_text,
                "engine": "vosk",
                "segments": results,
                "audio_path": audio_path
            }
        except Exception as e:
            return {"status": "error", "message": f"Vosk 识别失败: {e}"}

    def recognize_stream(self, audio_data: bytes, sample_rate: int = 16000,
                         is_final: bool = False) -> Dict[str, Any]:
        if not self.available:
            return {"status": "error", "message": "Vosk 引擎不可用"}

        try:
            import vosk
            if self.recognizer is None:
                self.recognizer = vosk.KaldiRecognizer(self.model, sample_rate)

            if self.recognizer.AcceptWaveform(audio_data):
                result = json.loads(self.recognizer.Result())
                return {"status": "success", "text": result.get("text", ""), "partial": False}
            else:
                result = json.loads(self.recognizer.PartialResult())
                return {"status": "success", "text": result.get("partial", ""), "partial": True}
        except Exception as e:
            return {"status": "error", "message": f"Vosk 流式识别失败: {e}"}

    def reset_stream(self):
        self.recognizer = None


class FasterWhisperEngine:
    """Faster-Whisper 高精度语音识别引擎"""

    def __init__(self, model_size: str = "small", device: str = "cpu",
                 compute_type: str = "int8"):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.model = None
        self.available = False
        self._init_engine()

    def _init_engine(self):
        try:
            from faster_whisper import WhisperModel
            self.model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type
            )
            self.available = True
            logger.info(f"Faster-Whisper 引擎就绪: model={self.model_size}, device={self.device}")
        except ImportError:
            logger.info("faster-whisper 未安装，使用 pip install faster-whisper 安装")
        except Exception as e:
            logger.warning(f"Faster-Whisper 初始化失败: {e}")

    def recognize_file(self, audio_path: str, language: str = None) -> Dict[str, Any]:
        if not self.available:
            return {"status": "error", "message": "Faster-Whisper 引擎不可用"}

        try:
            segments, info = self.model.transcribe(
                audio_path,
                language=language,
                beam_size=5,
                vad_filter=True
            )

            results = []
            full_text_parts = []
            for segment in segments:
                seg_data = {
                    "start": round(segment.start, 2),
                    "end": round(segment.end, 2),
                    "text": segment.text.strip()
                }
                results.append(seg_data)
                full_text_parts.append(segment.text.strip())

            return {
                "status": "success",
                "text": " ".join(full_text_parts),
                "engine": "faster_whisper",
                "language": info.language,
                "language_probability": round(info.language_probability, 3),
                "duration": round(info.duration, 2),
                "segments": results,
                "audio_path": audio_path
            }
        except Exception as e:
            return {"status": "error", "message": f"Faster-Whisper 识别失败: {e}"}


class SpeechRecognitionAdapter:
    """语音识别技能适配器 - 双引擎架构"""

    def __init__(self, vosk_model_path: str = "model/vosk-model-small-cn-0.22",
                 whisper_model_size: str = "small"):
        self.vosk = VoskEngine(vosk_model_path)
        self.whisper = FasterWhisperEngine(whisper_model_size)
        self.agents = {}
        self.skills = {}
        self._init_skills()
        self._init_agents()

    def _init_skills(self):
        self.skills["speech_to_text"] = {
            "name": "语音转文字",
            "description": "将音频文件或实时音频流转换为文字，支持中英文",
            "version": "1.0.0",
            "engines": ["vosk", "faster_whisper", "local_llm"]
        }
        self.skills["realtime_stt"] = {
            "name": "实时语音识别",
            "description": "实时流式语音识别，低延迟，适合对话场景",
            "version": "1.0.0",
            "engines": ["vosk"]
        }
        self.skills["audio_transcription"] = {
            "name": "音频转写",
            "description": "高精度音频文件转写，支持时间戳和语言检测",
            "version": "1.0.0",
            "engines": ["faster_whisper"]
        }

    def _init_agents(self):
        self.agents["stt_agent"] = {
            "name": "语音识别代理",
            "description": "负责语音到文字的转换，支持多种引擎和语言",
            "skills": ["speech_to_text", "realtime_stt", "audio_transcription"],
            "capabilities": ["offline_recognition", "streaming", "multi_language", "speaker_diarization"]
        }
        self.agents["voice_command_agent"] = {
            "name": "语音命令代理",
            "description": "识别语音命令并转换为系统操作",
            "skills": ["speech_to_text", "command_parsing"],
            "capabilities": ["command_recognition", "intent_extraction", "keyword_spotting"]
        }

    def get_preferred_engine(self, task: str = "default") -> STTEngine:
        if task in ("realtime", "streaming", "command"):
            if self.vosk.available:
                return STTEngine.VOSK
        if task in ("transcription", "accuracy", "file"):
            if self.whisper.available:
                return STTEngine.FASTER_WHISPER
        if self.vosk.available:
            return STTEngine.VOSK
        if self.whisper.available:
            return STTEngine.FASTER_WHISPER
        return STTEngine.LOCAL_LLM

    async def recognize(self, audio_path: str = None, audio_data: bytes = None,
                        engine: str = None, language: str = None,
                        task: str = "default") -> Dict[str, Any]:
        if engine:
            try:
                engine_type = STTEngine(engine)
            except ValueError:
                engine_type = self.get_preferred_engine(task)
        else:
            engine_type = self.get_preferred_engine(task)

        if engine_type == STTEngine.VOSK and self.vosk.available:
            if audio_path:
                return await asyncio.to_thread(self.vosk.recognize_file, audio_path)
            elif audio_data:
                return self.vosk.recognize_stream(audio_data)
            else:
                return {"status": "error", "message": "未提供音频数据"}

        elif engine_type == STTEngine.FASTER_WHISPER and self.whisper.available:
            if audio_path:
                return await asyncio.to_thread(
                    self.whisper.recognize_file, audio_path, language
                )
            else:
                return {"status": "error", "message": "Faster-Whisper 仅支持文件输入"}

        elif engine_type == STTEngine.LOCAL_LLM:
            return await self._llm_fallback(audio_path, language)

        return {
            "status": "error",
            "message": "无可用的语音识别引擎",
            "available_engines": {
                "vosk": self.vosk.available,
                "faster_whisper": self.whisper.available
            }
        }

    async def _llm_fallback(self, audio_path: str = None,
                            language: str = None) -> Dict[str, Any]:
        try:
            from ...local_service.service import get_local_skill_service, SkillType
            svc = get_local_skill_service()
            prompt = "语音识别功能暂不可用，请用文字输入。"
            if audio_path:
                prompt = f"用户提供了音频文件({audio_path})，但本地语音识别引擎未就绪。请提示用户安装语音识别引擎。"
            result = await svc.execute_skill(
                SkillType.MINIMAX, "conversation",
                {"input": prompt, "context": "语音识别回退"},
                model="qwen2:0.5b"
            )
            return {
                "status": "degraded",
                "message": "语音识别引擎不可用，已回退到文本模式",
                "llm_response": result.get("response", ""),
                "engine": "local_llm_fallback"
            }
        except Exception as e:
            return {"status": "error", "message": f"回退失败: {e}"}

    def get_engine_status(self) -> Dict[str, Any]:
        return {
            "vosk": {
                "available": self.vosk.available,
                "model_path": self.vosk.model_path,
                "features": ["实时流式", "离线识别", "低延迟", "中文支持"]
            },
            "faster_whisper": {
                "available": self.whisper.available,
                "model_size": self.whisper.model_size,
                "device": self.whisper.device,
                "features": ["高精度", "语言检测", "时间戳", "VAD过滤"]
            },
            "local_llm": {
                "available": True,
                "features": ["文本回退", "Ollama推理"]
            }
        }

    def list_skills(self) -> List[str]:
        return list(self.skills.keys())

    def get_skill(self, skill_name: str) -> Optional[Dict[str, Any]]:
        return self.skills.get(skill_name)

    def convert_to_professional_agent(self, agent_name: str) -> Optional[ProfessionalAgent]:
        agent_data = self.agents.get(agent_name)
        if not agent_data:
            return None

        adapter = self

        class STTProfessionalAgent(ProfessionalAgent):
            def __init__(self, agent_data, adapter_ref):
                super().__init__(
                    agent_id=f"stt_{agent_name}",
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
                audio_path = ctx.get("audio_path")
                audio_data = ctx.get("audio_data")
                engine = ctx.get("engine")
                language = ctx.get("language")

                return await self._adapter.recognize(
                    audio_path=audio_path,
                    audio_data=audio_data,
                    engine=engine,
                    language=language,
                    task=task
                )

        return STTProfessionalAgent(agent_data, adapter)

    def register_all_agents(self):
        agent_registry = get_agent_registry()
        for agent_name in self.agents:
            agent = self.convert_to_professional_agent(agent_name)
            if agent:
                agent_registry.register_agent(agent)
                logger.info(f"注册语音识别 Agent: {agent_name}")


_speech_recognition_adapter = None

def get_speech_recognition_adapter() -> SpeechRecognitionAdapter:
    global _speech_recognition_adapter
    if _speech_recognition_adapter is None:
        _speech_recognition_adapter = SpeechRecognitionAdapter()
    return _speech_recognition_adapter

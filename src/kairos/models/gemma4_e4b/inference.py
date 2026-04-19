#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gemma4:e4b 推理引擎
负责模型加载和推理，支持4-bit量化以减少内存占用
"""

print("开始加载 Gemma4:e4b 推理引擎...")

import torch
print(f"torch 导入成功，版本: {torch.__version__}")

from transformers import AutoTokenizer, AutoModelForCausalLM
print("transformers 导入成功")

import logging
import gc
import os
print("基础库导入成功")

# 导入内存管理器
try:
    from modules.memory.manager import memory_manager
    print("内存管理器导入成功")
except ImportError as e:
    print(f"内存管理器导入失败: {e}")
    memory_manager = None

# 尝试导入 Ollama 客户端
try:
    import ollama
    print("Ollama 客户端导入成功")
    use_ollama = True
except ImportError as e:
    print(f"Ollama 客户端导入失败: {e}")
    use_ollama = False

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("Gemma4Inference")
print("日志配置成功")

class Gemma4Inference:
    """
    Gemma4:e4b 推理引擎类
    负责模型加载和推理，支持内存优化
    """
    
    def __init__(self, model_path, 
                 use_quantization=True,  # 是否使用量化
                 quantization_bits=4,  # 量化位数
                 max_memory_usage=None,  # 最大内存使用限制（MB）
                 ollama_model="gemma2:2b"
                 ):
        """
        初始化推理引擎
        
        Args:
            model_path: 模型路径
            use_quantization: 是否使用量化
            quantization_bits: 量化位数
            max_memory_usage: 最大内存使用限制（MB）
            ollama_model: Ollama 模型名称
        """
        self.model_path = model_path
        self.use_quantization = use_quantization
        self.quantization_bits = quantization_bits
        self.max_memory_usage = max_memory_usage
        self.ollama_model = ollama_model
        self.model = None
        self.tokenizer = None
        self.device = None
        
        # 注册内存回调
        if memory_manager:
            memory_manager.add_callback(self._memory_callback)
        
        # 加载模型
        if use_ollama:
            logger.info("使用 Ollama 客户端访问模型")
        else:
            self.load_model()
    
    def load_model(self):
        """
        加载模型
        """
        logger.info(f"开始加载Gemma4:e4b模型，路径: {self.model_path}")
        
        try:
            # 尝试使用本地模型路径
            try:
                # 加载分词器
                self.tokenizer = AutoTokenizer.from_pretrained(self.model_path)
                logger.info("分词器加载成功")
                
                # 加载模型，使用半精度和自动设备映射
                # 对于16G内存，使用float16可以减少内存占用
                model_kwargs = {
                    "torch_dtype": torch.float16,
                    "device_map": "auto"
                }
                
                # 如果使用量化，添加量化参数
                if self.use_quantization:
                    model_kwargs["load_in_4bit"] = self.quantization_bits == 4
                    model_kwargs["load_in_8bit"] = self.quantization_bits == 8
                    logger.info(f"使用{self.quantization_bits}-bit量化")
                
                self.model = AutoModelForCausalLM.from_pretrained(
                    self.model_path,
                    **model_kwargs
                )
                logger.info("模型加载成功")
            except Exception as e:
                # 如果本地模型加载失败，尝试使用 Ollama 模型目录
                logger.warning(f"本地模型加载失败，尝试使用 Ollama 模型目录: {str(e)}")
                
                # 使用 Ollama 模型目录
                ollama_model_dir = "c:\\Users\\Administrator\\Documents\\南无阿弥陀佛\\源文件\\vendor\\.ollama\\models\\blobs"
                logger.info(f"尝试从 Ollama 模型目录加载模型: {ollama_model_dir}")
                
                # 检查 Ollama 模型目录是否存在
                if not os.path.exists(ollama_model_dir):
                    logger.warning(f"Ollama 模型目录不存在: {ollama_model_dir}")
                    # 尝试使用 Hugging Face Hub
                    logger.info("尝试从 Hugging Face Hub 加载模型")
                    hub_model = "google/gemma-4-2b-it"
                    
                    # 加载分词器
                    self.tokenizer = AutoTokenizer.from_pretrained(hub_model)
                    logger.info("分词器加载成功")
                    
                    # 加载模型，使用半精度和自动设备映射
                    model_kwargs = {
                        "torch_dtype": torch.float16,
                        "device_map": "auto"
                    }
                    
                    # 如果使用量化，添加量化参数
                    if self.use_quantization:
                        model_kwargs["load_in_4bit"] = self.quantization_bits == 4
                        model_kwargs["load_in_8bit"] = self.quantization_bits == 8
                        logger.info(f"使用{self.quantization_bits}-bit量化")
                    
                    self.model = AutoModelForCausalLM.from_pretrained(
                        hub_model,
                        **model_kwargs
                    )
                    logger.info("模型从 Hugging Face Hub 加载成功")
                else:
                    logger.info("Ollama 模型目录存在，尝试加载模型")
                    # 这里我们仍然使用 Hugging Face Hub 来加载模型，因为 Ollama 模型文件格式与 Hugging Face 不兼容
                    hub_model = "google/gemma-4-2b-it"
                    
                    # 加载分词器
                    self.tokenizer = AutoTokenizer.from_pretrained(hub_model)
                    logger.info("分词器加载成功")
                    
                    # 加载模型，使用半精度和自动设备映射
                    model_kwargs = {
                        "torch_dtype": torch.float16,
                        "device_map": "auto"
                    }
                    
                    # 如果使用量化，添加量化参数
                    if self.use_quantization:
                        model_kwargs["load_in_4bit"] = self.quantization_bits == 4
                        model_kwargs["load_in_8bit"] = self.quantization_bits == 8
                        logger.info(f"使用{self.quantization_bits}-bit量化")
                    
                    self.model = AutoModelForCausalLM.from_pretrained(
                        hub_model,
                        **model_kwargs
                    )
                    logger.info("模型从 Hugging Face Hub 加载成功")
            
            # 检查模型设备
            self.device = next(self.model.parameters()).device
            logger.info(f"模型运行在设备: {self.device}")
            
            # 内存使用情况
            if torch.cuda.is_available():
                memory_allocated = torch.cuda.memory_allocated() / 1024**3
                memory_reserved = torch.cuda.memory_reserved() / 1024**3
                logger.info(f"GPU内存使用: 已分配 {memory_allocated:.2f}GB, 已保留 {memory_reserved:.2f}GB")
            
        except Exception as e:
            logger.error(f"模型加载失败: {str(e)}")
            raise
    
    def unload_model(self):
        """
        卸载模型，释放内存
        """
        if self.model is not None:
            logger.info("卸载模型，释放内存")
            del self.model
            self.model = None
            
            # 清理CUDA缓存
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            # 强制垃圾回收
            gc.collect()
            
            logger.info("模型卸载成功")
    
    def _memory_callback(self, memory_usage):
        """
        内存使用过高时的回调函数
        
        Args:
            memory_usage: 内存使用情况
        """
        logger.warning(f"内存使用过高: {memory_usage['percent']:.2f}%，尝试优化")
        
        # 如果内存使用超过90%，卸载模型
        if memory_usage['percent'] > 90 and self.model is not None:
            self.unload_model()
    
    def generate(self, prompt, max_length=1024, temperature=0.7, top_p=0.95):
        """
        生成文本
        
        Args:
            prompt: 提示词
            max_length: 最大生成长度
            temperature: 温度参数
            top_p: 采样参数
            
        Returns:
            生成的文本
        """
        try:
            if use_ollama:
                # 使用 Ollama 客户端生成文本
                logger.info(f"使用 Ollama 生成文本，提示词长度: {len(prompt)}")
                response = ollama.generate(
                    model=self.ollama_model,
                    prompt=prompt,
                    max_tokens=max_length,
                    temperature=temperature,
                    top_p=top_p
                )
                generated_text = response['response']
                logger.info(f"文本生成完成，生成长度: {len(generated_text)}")
                return generated_text
            else:
                # 如果模型未加载，重新加载
                if self.model is None:
                    logger.info("模型未加载，重新加载")
                    self.load_model()
                
                logger.info(f"开始生成文本，提示词长度: {len(prompt)}")
                
                # 编码输入
                inputs = self.tokenizer(prompt, return_tensors="pt").to(self.device)
                
                # 生成文本
                with torch.no_grad():
                    outputs = self.model.generate(
                        **inputs,
                        max_length=max_length,
                        temperature=temperature,
                        top_p=top_p,
                        do_sample=True
                    )
                
                # 解码输出
                generated_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
                logger.info(f"文本生成完成，生成长度: {len(generated_text)}")
                
                return generated_text
        except Exception as e:
            logger.error(f"文本生成失败: {str(e)}")
            raise
    
    def chat(self, messages, max_length=1024, temperature=0.7, top_p=0.95):
        """
        聊天模式
        
        Args:
            messages: 消息列表，格式为[{"role": "user", "content": "..."}]
            max_length: 最大生成长度
            temperature: 温度参数
            top_p: 采样参数
            
        Returns:
            生成的回复
        """
        try:
            if use_ollama:
                # 使用 Ollama 客户端聊天
                logger.info("使用 Ollama 聊天")
                response = ollama.chat(
                    model=self.ollama_model,
                    messages=messages,
                    options={
                        "max_tokens": max_length,
                        "temperature": temperature,
                        "top_p": top_p
                    }
                )
                return response['message']['content']
            else:
                # 构建聊天提示词
                prompt = ""
                for msg in messages:
                    if msg["role"] == "user":
                        prompt += f"用户: {msg['content']}\n"
                    elif msg["role"] == "assistant":
                        prompt += f"助手: {msg['content']}\n"
                
                prompt += "助手: "
                
                # 生成回复
                response = self.generate(prompt, max_length, temperature, top_p)
                
                # 提取助手回复
                assistant_response = response.split("助手: ")[-1]
                
                return assistant_response
        except Exception as e:
            logger.error(f"聊天失败: {str(e)}")
            raise
    
    def get_model_info(self):
        """
        获取模型信息
        
        Returns:
            模型信息字典
        """
        if use_ollama:
            return {
                "model_name": self.ollama_model,
                "status": "loaded",
                "provider": "Ollama"
            }
        
        if self.model is None:
            return {
                "model_name": "Gemma4:e4b",
                "status": "unloaded",
                "quantization": f"{self.quantization_bits}-bit" if self.use_quantization else "none"
            }
        
        return {
            "model_name": "Gemma4:e4b",
            "device": str(self.device),
            "vocab_size": self.tokenizer.vocab_size,
            "max_length": self.model.config.max_position_embeddings,
            "quantization": f"{self.quantization_bits}-bit" if self.use_quantization else "none"
        }

if __name__ == "__main__":
    # 测试推理引擎
    import sys
    if len(sys.argv) != 2:
        print("用法: python inference.py <模型路径>")
        sys.exit(1)
    
    model_path = sys.argv[1]
    
    try:
        # 初始化推理引擎
        inference = Gemma4Inference(model_path)
        
        # 测试生成
        test_prompt = "你好，我是一个智能助手，我可以帮助你做什么？"
        print("提示词:", test_prompt)
        
        response = inference.generate(test_prompt)
        print("生成结果:", response)
        
        # 测试聊天
        test_messages = [
            {"role": "user", "content": "你好，你是谁？"},
            {"role": "assistant", "content": "我是一个基于Gemma4:e4b的智能助手，很高兴为你服务！"},
            {"role": "user", "content": "你能做什么？"}
        ]
        
        chat_response = inference.chat(test_messages)
        print("聊天回复:", chat_response)
        
        # 打印模型信息
        print("模型信息:", inference.get_model_info())
        
    except Exception as e:
        print(f"错误: {str(e)}")
        sys.exit(1)
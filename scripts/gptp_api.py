import json
import os
import urllib.request
from typing import Optional, List, Dict, Union
import gradio as gr
import modules.shared as shared
import requests
import modules.script_callbacks as script_callbacks
from openai import OpenAI
import openai
from fastapi import FastAPI, Request
from pydantic import BaseModel
import base64
from PIL import Image
import io
import re
import hmac
import hashlib
import time
from urllib.parse import urlencode
import datetime

# 添加新的签名模式API URL配置
def on_ui_settings():
    section = ("gptp", "ChatGPT Prompts")
    
    # 通用设置
    shared.opts.add_option("gptp_default_api", shared.OptionInfo("OpenAI", "默认API类型", section=section))
    shared.opts.add_option("gptp_openai_api_key", shared.OptionInfo("", "OpenAI API Key", section=section))
    shared.opts.add_option("gptp_openai_api_url", shared.OptionInfo("https://api.openai.com", "OpenAI API URL", section=section))
    shared.opts.add_option("gptp_openai_model", shared.OptionInfo("gpt-4-turbo", "OpenAI 默认模型", section=section))
    shared.opts.add_option("gptp_anthropic_api_key", shared.OptionInfo("", "Anthropic API Key", section=section))
    shared.opts.add_option("gptp_anthropic_api_url", shared.OptionInfo("https://api.anthropic.com", "Anthropic API URL", section=section))
    shared.opts.add_option("gptp_anthropic_model", shared.OptionInfo("claude-3-opus-20240229", "Anthropic 默认模型", section=section))
    shared.opts.add_option("gptp_custom_api_key", shared.OptionInfo("", "自定义API Key", section=section))
    shared.opts.add_option("gptp_custom_api_url", shared.OptionInfo("http://localhost:8000", "自定义API URL", section=section))
    shared.opts.add_option("gptp_custom_api_model", shared.OptionInfo("vicuna-13b", "自定义API模型", section=section))
    shared.opts.add_option("gptp_deepseek_api_key", shared.OptionInfo("", "DeepSeek API Key", section=section))
    shared.opts.add_option("gptp_deepseek_api_url", shared.OptionInfo("https://api.deepseek.com", "DeepSeek API URL", section=section))
    shared.opts.add_option("gptp_deepseek_model", shared.OptionInfo("deepseek-chat", "DeepSeek 默认模型", section=section))
    shared.opts.add_option("gptp_siliconflow_api_key", shared.OptionInfo("", "SiliconFlow API Key", section=section))
    shared.opts.add_option("gptp_siliconflow_api_url", shared.OptionInfo("https://api.silicon-flow.com", "SiliconFlow API URL", section=section))
    shared.opts.add_option("gptp_siliconflow_model", shared.OptionInfo("mixtral", "SiliconFlow 默认模型", section=section))
    shared.opts.add_option("gptp_deepl_api_key", shared.OptionInfo("", "DeepL API Key", section=section))
    shared.opts.add_option("gptp_deepl_api_url", shared.OptionInfo("https://api-free.deepl.com/v2/translate", "DeepL API URL", section=section))
    
    # 腾讯混元设置
    shared.opts.add_option("gptp_hunyuan_api_key", shared.OptionInfo("", "腾讯混元 兼容模式 API Key", section=section))
    shared.opts.add_option("gptp_hunyuan_api_url", shared.OptionInfo("https://hunyuan.cloud.tencent.com", "腾讯混元 兼容模式 API URL", section=section))
    shared.opts.add_option("gptp_hunyuan_app_id", shared.OptionInfo("", "腾讯混元 兼容模式 App ID", section=section))
    shared.opts.add_option("gptp_hunyuan_secret_id", shared.OptionInfo("", "腾讯混元 签名模式 Secret ID", section=section))
    shared.opts.add_option("gptp_hunyuan_secret_key", shared.OptionInfo("", "腾讯混元 签名模式 Secret Key", section=section))
    shared.opts.add_option("gptp_hunyuan_model", shared.OptionInfo("hunyuan-lite", "腾讯混元 默认模型", section=section))
    shared.opts.add_option("gptp_hunyuan_max_image_size", shared.OptionInfo(4.0, "腾讯混元 最大图片大小 (MB)", section=section))
    shared.opts.add_option("gptp_hunyuan_supported_image_types", shared.OptionInfo("jpg,jpeg,png", "腾讯混元 支持的图片类型", section=section))
    
    # 火山引擎方舟设置
    shared.opts.add_option("gptp_volcengine_ark_api_key", shared.OptionInfo("", "火山引擎方舟 兼容模式 API Key", section=section))
    shared.opts.add_option("gptp_volcengine_ark_api_url", shared.OptionInfo("https://ark.cn-beijing.volces.com", "火山引擎方舟 兼容模式 API URL", section=section))
    shared.opts.add_option("gptp_volcengine_ark_native_api_url", shared.OptionInfo("https://ark.cn-beijing.volces.com", "火山引擎方舟 签名模式 API URL", section=section))
    shared.opts.add_option("gptp_volcengine_ark_ak", shared.OptionInfo("", "火山引擎方舟 签名模式 Access Key", section=section))
    shared.opts.add_option("gptp_volcengine_ark_sk", shared.OptionInfo("", "火山引擎方舟 签名模式 Secret Key", section=section))
    shared.opts.add_option("gptp_volcengine_ark_model", shared.OptionInfo("doubao-1-5-vision-pro-32k-250115", "火山引擎方舟 默认模型", section=section))
    shared.opts.add_option("gptp_volcengine_ark_max_image_size", shared.OptionInfo(4.0, "火山引擎方舟 最大图片大小 (MB)", section=section))
    shared.opts.add_option("gptp_volcengine_ark_supported_image_types", shared.OptionInfo("jpg,jpeg,png", "火山引擎方舟 支持的图片类型", section=section))
    
    # 百度千帆设置
    shared.opts.add_option("gptp_baidu_qianfan_api_key", shared.OptionInfo("", "百度千帆 兼容模式 API Key", section=section))
    shared.opts.add_option("gptp_baidu_qianfan_api_url", shared.OptionInfo("https://aip.baidubce.com", "百度千帆 兼容模式 API URL", section=section))
    shared.opts.add_option("gptp_baidu_qianfan_native_api_url", shared.OptionInfo("https://aip.baidubce.com", "百度千帆 签名模式 API URL", section=section))
    shared.opts.add_option("gptp_baidu_qianfan_api_key_native", shared.OptionInfo("", "百度千帆 签名模式 API Key", section=section))
    shared.opts.add_option("gptp_baidu_qianfan_secret_key", shared.OptionInfo("", "百度千帆 Secret Key", section=section))
    shared.opts.add_option("gptp_baidu_qianfan_model", shared.OptionInfo("ernie-4.0", "百度千帆 默认模型", section=section))
    shared.opts.add_option("gptp_baidu_qianfan_max_image_size", shared.OptionInfo(4.0, "百度千帆 最大图片大小 (MB)", section=section))
    shared.opts.add_option("gptp_baidu_qianfan_supported_image_types", shared.OptionInfo("jpg,jpeg,png", "百度千帆 支持的图片类型", section=section))
    
    # 图片处理设置
    shared.opts.add_option("gptp_max_image_dimension", shared.OptionInfo(1024, "最大图片尺寸 (像素)", section=section))
    shared.opts.add_option("gptp_image_compression_quality", shared.OptionInfo(85, "图片压缩质量 (1-100)", section=section))

# Request Models
class DeepSeekRequest(BaseModel):
    model: str
    messages: List[Dict[str, str]]
    text: str
    system_message: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 800
    top_p: float = 1.0

class GPTRequest(BaseModel):
    model: str
    messages: List[Dict[str, str]]
    max_tokens: int
    temperature: float
    top_p: float
    top_k: int
    response_format: Dict[str, str]

class TranslationRequest(BaseModel):
    text: str
    target_lang: str = "EN"

class SiliconFlowRequest(BaseModel):
    model: str
    messages: List[Dict[str, str]]
    max_tokens: int
    temperature: Optional[float] = 0.7
    top_p: Optional[float] = 0.7
    top_k: Optional[int] = 50
    response_format: Dict[str, str]

class HunyuanRequest(BaseModel):
    model: str
    messages: List[Dict[str, Union[str, List[Dict], Dict]]]
    temperature: Optional[float] = 0.7
    top_p: Optional[float] = 1.0
    max_tokens: Optional[int] = 800
    stream: Optional[bool] = False

class VolcengineArkRequest(BaseModel):
    model: str
    messages: List[Dict[str, Union[str, List, Dict]]]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 800
    top_p: Optional[float] = 1.0
    stream: Optional[bool] = False
    image_url: Optional[str] = None

class BaiduQianfanRequest(BaseModel):
    model: str
    messages: List[Dict[str, Union[str, List, Dict]]]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[float] = 800
    top_p: Optional[float] = 0.8
    stream: Optional[bool] = False
    image_url: Optional[str] = None

class HunyuanNativeRequest(BaseModel):
    model: str
    messages: List[Dict[str, Union[str, List[Dict], Dict]]]
    temperature: Optional[float] = 0.7
    top_p: Optional[float] = 1.0
    max_tokens: Optional[int] = 800
    stream: Optional[bool] = False
    image_url: Optional[str] = None

class VolcengineArkNativeRequest(BaseModel):
    model: str
    messages: List[Dict[str, Union[str, List, Dict]]]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 800
    top_p: Optional[float] = 1.0
    stream: Optional[bool] = False
    image_url: Optional[str] = None

class BaiduQianfanNativeRequest(BaseModel):
    model: str
    messages: List[Dict[str, Union[str, List, Dict]]]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[float] = 800
    top_p: Optional[float] = 0.8
    stream: Optional[bool] = False
    image_url: Optional[str] = None

def compress_image(image_path: str, max_size_mb: float = 5, max_dimension: int = 1024, quality: int = 85) -> bytes:
    """压缩图片到指定大小和尺寸"""
    with Image.open(image_path) as img:
        # 调整图片尺寸
        if max(img.size) > max_dimension:
            ratio = max_dimension / max(img.size)
            new_size = tuple(int(dim * ratio) for dim in img.size)
            img = img.resize(new_size, Image.Resampling.LANCZOS)
        
        # 转换为RGB模式（如果是RGBA）
        if img.mode in ('RGBA', 'LA'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[-1])
            img = background
        
        # 保存为JPEG格式
        output = io.BytesIO()
        img.save(output, format='JPEG', quality=quality, optimize=True)
        output.seek(0)
        return output.read()

def validate_image(image_path: str, max_size_mb: float, supported_types: str) -> tuple[bool, str]:
    """验证图片是否符合要求"""
    # 检查文件大小
    file_size_mb = os.path.getsize(image_path) / (1024 * 1024)
    if file_size_mb > max_size_mb:
        return False, f"图片大小超过限制 ({file_size_mb:.2f}MB > {max_size_mb}MB)"
    
    # 检查文件类型
    file_ext = os.path.splitext(image_path)[1].lower()[1:]
    supported_extensions = [ext.strip() for ext in supported_types.split(',')]
    if file_ext not in supported_extensions:
        return False, f"不支持的图片类型: {file_ext}"
    
    # 检查是否为有效图片
    try:
        with Image.open(image_path) as img:
            img.verify()
        return True, ""
    except Exception as e:
        return False, f"无效的图片文件: {str(e)}"

def process_image_for_api(image_path: str, api_type: str) -> Optional[Dict]:
    """处理图片以适应不同API的要求"""
    # 获取API特定的配置
    max_size = getattr(shared.opts, f"gptp_{api_type}_max_image_size", 5)
    supported_types = getattr(shared.opts, f"gptp_{api_type}_supported_image_types", "jpg,jpeg,png")
    
    # 验证图片
    is_valid, error_msg = validate_image(image_path, max_size, supported_types)
    if not is_valid:
        raise ValueError(error_msg)
    
    # 压缩图片
    compressed_image = compress_image(
        image_path,
        max_size_mb=max_size,
        max_dimension=shared.opts.gptp_max_image_dimension,
        quality=shared.opts.gptp_image_compression_quality
    )
    
    # 转换为base64
    base64_image = base64.b64encode(compressed_image).decode('utf-8')
    
    # 根据API类型返回不同格式
    if api_type == "hunyuan":
        return {
            "type": "image",
            "image_url": f"data:image/jpeg;base64,{base64_image}"
        }
    elif api_type == "volcengine_ark":
        return {
            "type": "image",
            "image_url": f"data:image/jpeg;base64,{base64_image}"
        }
    elif api_type == "baidu_qianfan":
        return {
            "type": "image",
            "image_url": f"data:image/jpeg;base64,{base64_image}"
        }
    else:
        raise ValueError(f"不支持的API类型: {api_type}")

class GptpApi:
    """ChatGPT Prompt API 类，提供多种模型支持和文件管理功能"""
    BASE_PATH = "/sdapi/chatgpt-prompts/v1"

    def __init__(self):
        self.app: Optional[FastAPI] = None
        self._registered: bool = False
        self._registered_routes: set = set()
        self._prompt_routes_added: bool = False

    def get_path(self, path: str) -> str:
        return f"{self.BASE_PATH}{path}"

    def add_api_route(self, path: str, endpoint, **kwargs) -> None:
        full_path = self.get_path(path)
        if full_path not in self._registered_routes:
            self.app.add_api_route(full_path, endpoint, **kwargs)
            self._registered_routes.add(full_path)
        if path == "/translate" and not self._prompt_routes_added:
            self._add_prompt_routes()
            self._prompt_routes_added = True

    def start(self, _: gr.Blocks, app: FastAPI) -> None:
        if self._registered:
            return
        self.app = app
        self._register_routes()
        self._registered = True

    def _register_routes(self) -> None:
        routes = [
            ("/prompt/list", self.list_prompt_files, ["GET"]),
            ("/prompt/get", self.get_prompt_file, ["GET"]),
            ("/prompt/save", self.save_prompt_file, ["POST"]),
            ("/prompt/delete", self.delete_prompt_file, ["POST"]),
            ("/deepseek", self.get_deepseek_prompt, ["POST"]),
            ("/siliconflow", self.get_siliconflow_prompt, ["POST"]),
            ("/hunyuan", self.get_hunyuan_prompt, ["POST"]),
            ("/volcengine_ark", self.get_volcengine_ark_prompt, ["POST"]),
            ("/baidu_qianfan", self.get_baidu_qianfan_prompt, ["POST"]),
            ("/hunyuan_native", self.get_hunyuan_native_prompt, ["POST"]),
            ("/volcengine_ark_native", self.get_volcengine_ark_native_prompt, ["POST"]),
            ("/baidu_qianfan_native", self.get_baidu_qianfan_native_prompt, ["POST"]),
            ("/translate", self.get_translation, ["POST"]),
        ]
        for path, endpoint, methods in routes:
            self.add_api_route(path, endpoint, methods=methods)

    def get_prompt_dir(self) -> str:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        prompt_dir = os.path.join(base_dir, "prompt")
        os.makedirs(prompt_dir, exist_ok=True)
        return prompt_dir

    def _add_prompt_routes(self) -> None:
        self.add_api_route("/prompt/list", self.list_prompt_files, methods=["GET"])
        self.add_api_route("/prompt/get", self.get_prompt_file, methods=["GET"])
        self.add_api_route("/prompt/save", self.save_prompt_file, methods=["POST"])
        self.add_api_route("/prompt/delete", self.delete_prompt_file, methods=["POST"])

    async def list_prompt_files(self) -> Dict[str, Union[bool, List[str], str]]:
        try:
            files = [f for f in os.listdir(self.get_prompt_dir()) if f.endswith(".txt")]
            return {"success": True, "files": files}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def get_prompt_file(self, name: str) -> Dict[str, Union[bool, str]]:
        filepath = os.path.join(self.get_prompt_dir(), name)
        try:
            if os.path.exists(filepath):
                with open(filepath, "r", encoding="utf-8") as f:
                    return {"success": True, "content": f.read(), "filename": name}
            return {"success": False, "error": "File not found"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def save_prompt_file(self, request: Request) -> Dict[str, Union[bool, str]]:
        try:
            data = await request.json()
            filename = self._sanitize_filename(data.get("filename", ""))
            filepath = os.path.join(self.get_prompt_dir(), filename)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(data.get("content", ""))
            return {"success": True, "message": "文件保存成功"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def delete_prompt_file(self, request: Request) -> Dict[str, Union[bool, str]]:
        try:
            data = await request.json()
            filename = self._sanitize_filename(data.get("filename", ""))
            filepath = os.path.join(self.get_prompt_dir(), filename)
            if os.path.exists(filepath):
                os.remove(filepath)
                return {"success": True, "message": f"文件 {filename} 已删除"}
            return {"success": False, "error": "文件不存在"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _sanitize_filename(self, filename: str) -> str:
        filename = filename.replace("/", "").replace("\\", "")
        return filename if filename.endswith(".txt") else f"{filename}.txt"

    def get_translation(self, translation_request: TranslationRequest) -> Dict[str, str]:
        try:
            req = urllib.request.Request(
                shared.opts.gptp_deepl_api_url,
                method="POST",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"DeepL-Auth-Key {shared.opts.gptp_deepl_api_key.strip()}",
                },
                data=json.dumps({
                    "text": [translation_request.text],
                    "target_lang": translation_request.target_lang,
                }).encode("utf-8"),
            )
            with urllib.request.urlopen(req) as response:
                response_json = json.loads(response.read().decode("utf-8"))
                return {"text": response_json["translations"][0]["text"]}
        except urllib.error.HTTPError as e:
            return {"error": f"HTTP error {e.code}: {e.reason}"}
        except Exception as e:
            return {"error": f"翻译错误: {str(e)}"}

    def get_deepseek_prompt(self, request: DeepSeekRequest) -> Dict[str, str]:
        try:
            client = OpenAI(
                api_key=shared.opts.gptp_deepseek_api_key.strip(),
                base_url=shared.opts.gptp_deepseek_api_url.rstrip("/"),
            )
            messages = [{"role": "system", "content": request.system_message.strip()}] if request.system_message else []
            messages.append({"role": "user", "content": request.text})
            response = client.chat.completions.create(
                model=request.model,
                messages=messages,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                top_p=request.top_p,
            )
            content = response.choices[0].message.content.strip()
            if not content:
                return {"error": "DeepSeek API 返回空内容"}
            return {"text": content}
        except openai.APIError as e:
            return {"error": f"DeepSeek API 错误: {e.message if hasattr(e, 'message') else str(e)}"}
        except Exception as e:
            return {"error": f"处理错误: {str(e)}"}

    def get_siliconflow_prompt(self, request: SiliconFlowRequest) -> Dict[str, str]:
        try:
            response = requests.post(
                f"{shared.opts.gptp_siliconflow_api_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {shared.opts.gptp_siliconflow_api_key.strip()}",
                    "Content-Type": "application/json",
                },
                json=request.dict(),
                timeout=60,
            )
            response.raise_for_status()
            data = response.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
            if not content:
                return {"error": "SiliconFlow API 返回空内容"}
            return {"text": content}
        except requests.RequestException as e:
            return {"error": f"SiliconFlow API 错误: {str(e)}"}

    def _process_image_message(self, message: Dict, api_type: str) -> Dict:
        """处理包含图片的消息"""
        if isinstance(message.get("content"), list):
            processed_content = []
            for item in message["content"]:
                if isinstance(item, dict) and item.get("type") == "image":
                    # 处理base64图片
                    if item.get("image_url", "").startswith("data:image"):
                        processed_content.append(item)
                    # 处理本地图片路径
                    elif os.path.exists(item.get("image_url", "")):
                        try:
                            processed_image = process_image_for_api(item["image_url"], api_type)
                            processed_content.append(processed_image)
                        except ValueError as e:
                            processed_content.append({"type": "text", "text": f"[图片处理错误: {str(e)}]"})
                else:
                    processed_content.append(item)
            message["content"] = processed_content
        return message

    def _process_messages(self, messages: List[Dict], api_type: str) -> List[Dict]:
        """处理消息中的图片，适配不同API的格式要求"""
        # 分离system消息和其他消息
        system_messages = [msg for msg in messages if msg.get("role") == "system"]
        other_messages = [msg for msg in messages if msg.get("role") != "system"]
        
        processed_messages = []
        
        # 处理其他消息
        for message in other_messages:
            # 检查消息结构
            if isinstance(message.get("content"), list):
                # 已经是多模态格式，不需要处理
                processed_messages.append(message)
                continue
                
            # 处理图片URL
            if "image_url" in message and message["image_url"]:
                if api_type == "hunyuan":
                    # 腾讯混元API的图片格式
                    processed_messages.append({
                        "Role": message["role"].capitalize(),  # 首字母大写
                        "Content": [
                            {"type": "text", "text": message.get("content", "")},
                            {"type": "image", "image_url": {"url": message["image_url"]}}
                        ]
                    })
                elif api_type == "volcengine_ark":
                    # 火山引擎方舟API的图片格式
                    processed_messages.append({
                        "role": message["role"],
                        "content": [
                            {"type": "text", "text": message.get("content", "")},
                            {"type": "image", "image_url": message["image_url"]}
                        ]
                    })
                elif api_type == "baidu_qianfan":
                    # 百度千帆API的图片格式
                    processed_messages.append({
                        "role": message["role"],
                        "content": [
                            {"type": "text", "text": message.get("content", "")},
                            {"type": "image", "image_url": message["image_url"]}
                        ]
                    })
                else:
                    # 默认格式，简单添加
                    processed_messages.append(message)
            else:
                # 普通文本消息，根据API类型处理
                if api_type == "hunyuan":
                    # 腾讯混元API需要首字母大写的Role
                    processed_messages.append({
                        "Role": message["role"].capitalize(),
                        "Content": message.get("content", "")
                    })
                else:
                    # 其他API保持原样
                    processed_messages.append(message)
        
        # 根据API类型处理system消息
        if api_type == "hunyuan":
            # 腾讯混元要求system消息在最开始，并且Role首字母大写
            sys_messages = []
            for msg in system_messages:
                sys_messages.append({
                    "Role": "System",
                    "Content": msg.get("content", "")
                })
            return sys_messages + processed_messages
        elif api_type in ["volcengine_ark", "baidu_qianfan"]:
            # 某些API可能不支持system消息，需要转换成user消息
            if system_messages and processed_messages:
                # 将system消息内容添加到第一个user消息前面
                system_content = system_messages[0].get("content", "")
                for i, msg in enumerate(processed_messages):
                    if msg.get("role") == "user" or msg.get("Role") == "User":
                        if isinstance(msg.get("content"), list):
                            # 如果是多模态消息
                            for item in msg["content"]:
                                if item.get("type") == "text":
                                    item["text"] = system_content + "\n\n" + item["text"]
                                    break
                        else:
                            # 普通文本消息
                            if "content" in msg:
                                processed_messages[i]["content"] = system_content + "\n\n" + msg.get("content", "")
                            elif "Content" in msg:
                                processed_messages[i]["Content"] = system_content + "\n\n" + msg.get("Content", "")
                        break
            return processed_messages
        
        # 默认情况下返回所有消息
        return system_messages + processed_messages

    def get_hunyuan_prompt(self, request: HunyuanRequest) -> Dict[str, Union[str, Dict]]:
        try:
            client = OpenAI(
                api_key=shared.opts.gptp_hunyuan_api_key.strip(),
                base_url=f"{shared.opts.gptp_hunyuan_api_url.rstrip('/')}/v1",
            )
            
            # 处理消息
            processed_messages = self._process_messages(request.messages, "hunyuan")
            
            # 确保消息以user结尾
            if processed_messages and processed_messages[-1].get("Role") not in ["User", "user"]:
                # 添加一个空的用户消息
                processed_messages.append({"Role": "User", "Content": "请继续"})
            
            # 构建请求参数
            request_params = request.dict()
            request_params["messages"] = processed_messages
            
            response = client.chat.completions.create(**request_params)
            content = response.choices[0].message.content.strip()
            if not content:
                return {"error": "Hunyuan API 返回空内容"}
            return {"text": content, "usage": dict(response.usage)}
        except Exception as e:
            return {"error": f"Hunyuan API 错误: {str(e)}"}

    def get_volcengine_ark_prompt(self, request: VolcengineArkRequest) -> Dict[str, str]:
        """调用 Volcengine Ark API 生成提示"""
        try:
            # 处理消息
            processed_messages = []
            
            # 检查是否包含图片
            image_data = None
            if request.image_url:
                try:
                    # 处理图片
                    max_size = getattr(shared.opts, "gptp_volcengine_ark_max_image_size", 5)
                    supported_types = getattr(shared.opts, "gptp_volcengine_ark_supported_image_types", "jpg,jpeg,png")
                    
                    # 验证图片
                    is_valid, error_msg = validate_image(request.image_url, max_size, supported_types)
                    if not is_valid:
                        raise ValueError(error_msg)
                    
                    # 压缩图片
                    compressed_image = compress_image(
                        request.image_url,
                        max_size_mb=max_size,
                        max_dimension=shared.opts.gptp_max_image_dimension,
                        quality=shared.opts.gptp_image_compression_quality
                    )
                    
                    # 转换为base64
                    image_data = base64.b64encode(compressed_image).decode('utf-8')
                except Exception as e:
                    return {"error": f"图片处理错误: {str(e)}"}
            
            # 处理消息
            for message in request.messages:
                message_copy = dict(message)
                
                # 处理图片（如果第一条用户消息且有图片）
                if image_data and message_copy.get("role") == "user" and len(processed_messages) == 0:
                    if "content" not in message_copy or not message_copy["content"]:
                        message_copy["content"] = ""
                        
                    # 转换为兼容格式
                    message_copy["content"] = [
                        {"type": "text", "text": message_copy["content"]},
                        {"type": "image", "image_url": f"data:image/jpeg;base64,{image_data}"}
                    ]
                
                processed_messages.append(message_copy)
            
            # 构建API请求
            headers = {
                "Authorization": f"Bearer {shared.opts.gptp_volcengine_ark_api_key.strip()}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": request.model,
                "messages": processed_messages,
                "temperature": request.temperature,
                "top_p": request.top_p,
                "max_tokens": request.max_tokens,
                "stream": request.stream
            }
            
            response = requests.post(
                f"{shared.opts.gptp_volcengine_ark_api_url.rstrip('/')}/api/v3/chat/completions",
                headers=headers,
                json=payload,
                timeout=60
            )
            
            if response.status_code == 422:
                return {"error": f"火山引擎方舟 API 参数错误: {response.text}. 请检查API文档确认参数格式。"}
            
            response.raise_for_status()
            data = response.json()
            
            if "choices" in data and len(data["choices"]) > 0:
                content = data["choices"][0]["message"]["content"].strip()
                if not content:
                    return {"error": "火山引擎方舟 API 返回空内容"}
                return {"text": content}
            else:
                return {"error": f"火山引擎方舟 API 响应格式错误: {data}"}
                
        except requests.RequestException as e:
            return {"error": f"火山引擎方舟 API 错误: {str(e)}"}
        except Exception as e:
            return {"error": f"处理错误: {str(e)}"}

    def get_baidu_qianfan_prompt(self, request: BaiduQianfanRequest) -> Dict[str, str]:
        """调用百度千帆 API 生成提示"""
        try:
            # 优先使用请求中的API密钥，其次使用设置中的API密钥
            client_id = request.dict().get("client_id", "")
            client_secret = request.dict().get("client_secret", "")
            
            if not client_id:
                client_id = shared.opts.gptp_baidu_qianfan_api_key.strip()
            if not client_secret:
                client_secret = shared.opts.gptp_baidu_qianfan_secret_key.strip()
            
            if not all([client_id, client_secret]):
                return {"error": "请在设置中配置百度千帆的 API Key 和 Secret Key"}
                
            # 处理消息
            processed_messages = request.messages
            
            # 检查是否包含图片
            image_data = None
            if request.image_url and request.image_url != "placeholder":
                try:
                    # 处理图片
                    max_size = getattr(shared.opts, "gptp_baidu_qianfan_max_image_size", 5)
                    supported_types = getattr(shared.opts, "gptp_baidu_qianfan_supported_image_types", "jpg,jpeg,png")
                    
                    # 验证图片
                    is_valid, error_msg = validate_image(request.image_url, max_size, supported_types)
                    if not is_valid:
                        raise ValueError(error_msg)
                    
                    # 压缩图片
                    compressed_image = compress_image(
                        request.image_url,
                        max_size_mb=max_size,
                        max_dimension=shared.opts.gptp_max_image_dimension,
                        quality=shared.opts.gptp_image_compression_quality
                    )
                    
                    # 转换为base64
                    image_data = base64.b64encode(compressed_image).decode('utf-8')
                except Exception as e:
                    return {"error": f"图片处理错误: {str(e)}"}
            
            # 获取访问令牌
            token_params = {}
            if client_id and client_secret:
                token_params = {
                    "grant_type": "client_credentials",
                    "client_id": client_id,
                    "client_secret": client_secret
                }
            else:
                return {"error": "API Key和Secret Key不能为空"}
            
            # 发送请求获取访问令牌
            token_response = requests.post(
                "https://aip.baidubce.com/oauth/2.0/token",
                params=token_params,
                headers={"Content-Type": "application/json"}
            )
            
            if token_response.status_code != 200:
                error_info = token_response.json() if token_response.text else {"error": f"HTTP错误: {token_response.status_code}"}
                error_msg = error_info.get("error_description", "") if isinstance(error_info, dict) else ""
                return {"error": f"获取百度千帆访问令牌失败: {error_msg or token_response.text}"}
                
            result = token_response.json()
            if "access_token" not in result:
                return {"error": f"获取百度千帆访问令牌失败，返回内容中没有access_token: {result}"}
                
            access_token = result["access_token"]
            
            # 构建请求参数
            payload = {
                "messages": processed_messages,
                "model": request.model,
                "temperature": request.temperature,
                "top_p": request.top_p,
                "stream": request.stream
            }
            
            # 百度千帆使用max_output_tokens而不是max_tokens
            if request.max_tokens:
                payload["max_output_tokens"] = request.max_tokens
            
            # 构建API URL
            model_name = request.model.lower()
            api_url = f"{shared.opts.gptp_baidu_qianfan_api_url.rstrip('/')}/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/{model_name}?access_token={access_token}"
            
            response = requests.post(
                api_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=60
            )
            
            if response.status_code == 422:
                return {"error": f"百度千帆 API 参数错误: {response.text}. 请检查API文档确认参数格式。"}
                
            if response.status_code != 200:
                error_info = response.json() if response.text else {"error": f"HTTP错误: {response.status_code}"}
                error_msg = error_info.get("error_msg", "") if isinstance(error_info, dict) else ""
                return {"error": f"百度千帆 API 错误: {error_msg or response.text}"}
                
            data = response.json()
            
            if "result" in data:
                content = data["result"].strip()
                if not content:
                    return {"error": "百度千帆 API 返回空内容"}
                return {"text": content}
            elif "error_code" in data and "error_msg" in data:
                return {"error": f"百度千帆 API 错误 {data['error_code']}: {data['error_msg']}"}
            else:
                return {"error": f"百度千帆 API 响应格式错误: {data}"}
                
        except requests.RequestException as e:
            return {"error": f"百度千帆 API 错误: {str(e)}"}
        except Exception as e:
            return {"error": f"处理错误: {str(e)}"}

    def get_hunyuan_native_prompt(self, request: HunyuanNativeRequest) -> Dict[str, Union[str, Dict]]:
        """使用腾讯混元签名模式获取提示词"""
        try:
            secret_id = shared.opts.gptp_hunyuan_secret_id
            secret_key = shared.opts.gptp_hunyuan_secret_key
            
            if not all([secret_id, secret_key]):
                raise ValueError("请在设置中配置腾讯混元的 SecretId 和 SecretKey")

            # 处理消息中的图片
            messages = self._process_messages(request.messages, "hunyuan")
            
            # 确保消息以user结尾
            if messages and messages[-1].get("Role") not in ["User", "user"]:
                # 添加一个空的用户消息
                messages.append({"Role": "User", "Content": "请继续"})
            
            # 构建请求体 - 腾讯混元API需要首字母大写
            request_body = {
                "Messages": messages,
                "Temperature": request.temperature,
                "TopP": request.top_p,
                "MaxTokens": request.max_tokens,
                "Model": request.model
            }
            
            # 请求方法和域名 - 使用专门的签名模式URL
            service = "hunyuan"
            host = "hunyuan.tencentcloudapi.com"  # 官方签名模式API域名
            endpoint = "https://" + host
            region = "ap-guangzhou"  # 腾讯混元默认区域
            action = "ChatCompletion"  # 修正为正确的Action名称
            version = "2023-11-01"  # 使用最新API版本
            
            # 生成签名和请求头
            headers = self._generate_tc3_headers(service, host, region, action, version, request_body, secret_id, secret_key)
            
            # 发送请求
            response = requests.post(
                endpoint,
                json=request_body,
                headers=headers,
                timeout=60
            )
            
            if response.status_code != 200:
                raise ValueError(f"腾讯混元 API 错误: {response.status_code} {response.text}")
            
            result = response.json()
            # 根据腾讯混元API的响应格式，提取内容
            if "Response" in result and "Choice" in result["Response"]:
                content = result["Response"]["Choice"]["Message"]["Content"]
                return {"text": content}
            elif "Response" in result and "Choices" in result["Response"]:
                content = result["Response"]["Choices"][0]["Message"]["Content"]
                return {"text": content}
            else:
                raise ValueError(f"腾讯混元 API 响应格式错误: {result}")
        except Exception as e:
            # 错误信息处理
            return {"error": f"腾讯混元 API 错误: {str(e)}"}

    def _generate_tc3_headers(self, service, host, region, action, version, body, secret_id, secret_key):
        """生成腾讯云API签名v3的请求头"""
        algorithm = "TC3-HMAC-SHA256"
        timestamp = int(time.time())
        date_time = datetime.datetime.utcfromtimestamp(timestamp).strftime('%Y-%m-%d')
        
        # 规范请求字符串
        http_request_method = "POST"
        canonical_uri = "/"
        canonical_querystring = ""
        
        # 规范请求头
        canonical_headers = "content-type:application/json; charset=utf-8\n"
        canonical_headers += f"host:{host}\n"
        signed_headers = "content-type;host"
        
        # 规范请求体
        payload = json.dumps(body)
        hashed_request_payload = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        
        # 组合规范请求字符串
        canonical_request = (http_request_method + '\n' +
                             canonical_uri + '\n' +
                             canonical_querystring + '\n' +
                             canonical_headers + '\n' +
                             signed_headers + '\n' +
                             hashed_request_payload)
        
        # 组合签名字符串
        credential_scope = date_time + "/" + service + "/tc3_request"
        hashed_canonical_request = hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()
        string_to_sign = (algorithm + "\n" +
                          str(timestamp) + "\n" +
                          credential_scope + "\n" +
                          hashed_canonical_request)
        
        # 计算签名
        def sign(key, msg):
            return hmac.new(key, msg.encode('utf-8'), hashlib.sha256).digest()
        
        secret_date = sign(("TC3" + secret_key).encode("utf-8"), date_time)
        secret_service = sign(secret_date, service)
        secret_signing = sign(secret_service, "tc3_request")
        signature = hmac.new(secret_signing, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()
        
        # 组合Authorization
        authorization = (algorithm + " " +
                         "Credential=" + secret_id + "/" + credential_scope + ", " +
                         "SignedHeaders=" + signed_headers + ", " +
                         "Signature=" + signature)
        
        # 设置请求头
        headers = {
            "Authorization": authorization,
            "Content-Type": "application/json; charset=utf-8",
            "Host": host,
            "X-TC-Action": action,
            "X-TC-Timestamp": str(timestamp),
            "X-TC-Version": version,
            "X-TC-Region": region
        }
        
        return headers

    def get_volcengine_ark_native_prompt(self, request: VolcengineArkNativeRequest) -> Dict[str, str]:
        """使用火山引擎方舟签名模式获取提示词"""
        try:
            # 从请求中获取AccessKey和SecretKey
            access_key = request.dict().get("access_key", "")
            secret_key = request.dict().get("secret_key", "")
            
            # 如果请求中没有提供，则从设置中获取
            if not access_key:
                access_key = shared.opts.gptp_volcengine_ark_ak
            if not secret_key:
                secret_key = shared.opts.gptp_volcengine_ark_sk
            
            if not all([access_key, secret_key]):
                raise ValueError("请在设置中配置火山引擎方舟的 AccessKey 和 SecretKey")

            # 处理消息
            processed_messages = request.messages
            
            # 处理消息中的图片
            image_data = None
            if request.image_url and request.image_url != "placeholder":
                try:
                    # 处理图片
                    max_size = getattr(shared.opts, "gptp_volcengine_ark_max_image_size", 5)
                    supported_types = getattr(shared.opts, "gptp_volcengine_ark_supported_image_types", "jpg,jpeg,png")
                    
                    # 验证图片
                    is_valid, error_msg = validate_image(request.image_url, max_size, supported_types)
                    if not is_valid:
                        raise ValueError(error_msg)
                    
                    # 压缩图片
                    compressed_image = compress_image(
                        request.image_url,
                        max_size_mb=max_size,
                        max_dimension=shared.opts.gptp_max_image_dimension,
                        quality=shared.opts.gptp_image_compression_quality
                    )
                    
                    # 转换为base64
                    image_data = base64.b64encode(compressed_image).decode('utf-8')
                except Exception as e:
                    return {"error": f"图片处理错误: {str(e)}"}
            
            # 构建请求参数
            params = {
                "messages": processed_messages,
                "model": request.model,
                "temperature": request.temperature,
                "top_p": request.top_p,
                "max_tokens": request.max_tokens
            }
            
            # 获取API地址 - 使用专门的签名模式URL
            api_url = shared.opts.gptp_volcengine_ark_native_api_url.rstrip('/')
            url_parts = api_url.replace("https://", "").replace("http://", "").split("/")
            host = url_parts[0]
            endpoint = f"{api_url}/api/v3/chat/completions"
            path = "/api/v3/chat/completions"
            
            # 获取请求时间
            timestamp = time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime())
            
            # 计算签名 - 使用火山引擎标准签名方式
            # 1. 创建规范请求
            content_type = "application/json"
            body_json = json.dumps(params)
            content_md5 = hashlib.md5(body_json.encode('utf-8')).hexdigest()
            
            # 构建StringToSign
            string_to_sign = f"POST\n{content_md5}\n{content_type}\n{timestamp}\n{path}"
            
            # 计算签名
            signature = hmac.new(
                secret_key.encode('utf-8'),
                string_to_sign.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            # 构建请求头
            headers = {
                "Content-Type": content_type,
                "Content-MD5": content_md5,
                "Date": timestamp,
                "Host": host,
                "Authorization": f"HMAC-SHA256 AccessKey={access_key}, Signature={signature}"
            }
            
            # 发送请求
            response = requests.post(
                endpoint,
                json=params,
                headers=headers,
                timeout=60
            )
            
            if response.status_code == 422:
                return {"error": f"火山引擎方舟 API 参数错误: {response.text}. 请检查API文档确认参数格式。"}
                
            if response.status_code != 200:
                raise ValueError(f"火山引擎方舟 API 错误: {response.status_code} {response.text}")
            
            result = response.json()
            if "data" in result and "text" in result["data"]:
                return {"text": result["data"]["text"]}
            elif "choices" in result and len(result["choices"]) > 0:
                return {"text": result["choices"][0]["message"]["content"]}
            else:
                raise ValueError(f"火山引擎方舟 API 响应格式错误: {result}")
        except Exception as e:
            # 错误信息处理
            return {"error": f"火山引擎方舟 API 错误: {str(e)}"}

    def get_baidu_qianfan_native_prompt(self, request: BaiduQianfanNativeRequest) -> Dict[str, str]:
        """使用百度千帆签名模式获取提示词"""
        try:
            # 优先使用请求中的API密钥，其次使用设置中的API密钥
            client_id = request.dict().get("client_id", "")
            client_secret = request.dict().get("client_secret", "")
            
            if not client_id:
                client_id = shared.opts.gptp_baidu_qianfan_api_key_native.strip()
            if not client_secret:
                client_secret = shared.opts.gptp_baidu_qianfan_secret_key.strip()
            
            if not all([client_id, client_secret]):
                return {"error": "请在设置中配置百度千帆的 API Key 和 Secret Key"}

            # 处理消息
            processed_messages = request.messages
            
            # 处理消息中的图片
            image_data = None
            if request.image_url and request.image_url != "placeholder":
                try:
                    # 处理图片
                    max_size = getattr(shared.opts, "gptp_baidu_qianfan_max_image_size", 5)
                    supported_types = getattr(shared.opts, "gptp_baidu_qianfan_supported_image_types", "jpg,jpeg,png")
                    
                    # 验证图片
                    is_valid, error_msg = validate_image(request.image_url, max_size, supported_types)
                    if not is_valid:
                        raise ValueError(error_msg)
                    
                    # 压缩图片
                    compressed_image = compress_image(
                        request.image_url,
                        max_size_mb=max_size,
                        max_dimension=shared.opts.gptp_max_image_dimension,
                        quality=shared.opts.gptp_image_compression_quality
                    )
                    
                    # 转换为base64
                    image_data = base64.b64encode(compressed_image).decode('utf-8')
                except Exception as e:
                    return {"error": f"图片处理错误: {str(e)}"}

            # 获取访问令牌
            token_params = {}
            if client_id and client_secret:
                token_params = {
                    "grant_type": "client_credentials",
                    "client_id": client_id,
                    "client_secret": client_secret
                }
            else:
                return {"error": "API Key和Secret Key不能为空"}
            
            # 发送请求获取访问令牌
            token_response = requests.post(
                "https://aip.baidubce.com/oauth/2.0/token",
                params=token_params,
                headers={"Content-Type": "application/json"}
            )
            
            if token_response.status_code != 200:
                error_info = token_response.json() if token_response.text else {"error": f"HTTP错误: {token_response.status_code}"}
                error_msg = error_info.get("error_description", "") if isinstance(error_info, dict) else ""
                return {"error": f"获取百度千帆访问令牌失败: {error_msg or token_response.text}"}
                
            result = token_response.json()
            if "access_token" not in result:
                return {"error": f"获取百度千帆访问令牌失败，返回内容中没有access_token: {result}"}
                
            access_token = result["access_token"]
            
            # 构建请求参数
            params = {
                "messages": processed_messages,
                "temperature": request.temperature,
                "top_p": request.top_p
            }
            
            # 百度千帆使用max_output_tokens而不是max_tokens
            if request.max_tokens:
                params["max_output_tokens"] = request.max_tokens
            
            # 构建API URL
            model_name = request.model.lower()
            api_url = f"{shared.opts.gptp_baidu_qianfan_native_api_url.rstrip('/')}/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/{model_name}?access_token={access_token}"
            
            # 发送请求
            response = requests.post(
                api_url,
                json=params,
                headers={"Content-Type": "application/json"},
                timeout=60
            )
            
            if response.status_code == 422:
                return {"error": f"百度千帆 API 参数错误: {response.text}. 请检查API文档确认参数格式。"}
                
            if response.status_code != 200:
                error_info = response.json() if response.text else {"error": f"HTTP错误: {response.status_code}"}
                error_msg = error_info.get("error_msg", "") if isinstance(error_info, dict) else ""
                return {"error": f"百度千帆 API 错误: {error_msg or response.text}"}
            
            result = response.json()
            if "result" in result:
                content = result["result"].strip()
                if not content:
                    return {"error": "百度千帆 API 返回空内容"}
                return {"text": content}
            elif "error_code" in result and "error_msg" in result:
                return {"error": f"百度千帆 API 错误 {result['error_code']}: {result['error_msg']}"}
            else:
                return {"error": f"百度千帆 API 响应格式错误: {result}"}
        except Exception as e:
            # 错误信息处理
            return {"error": f"百度千帆 API 错误: {str(e)}"}

# 启动 API
try:
    api = GptpApi()
    script_callbacks.on_app_started(api.start)
    ## script_callbacks.on_ui_settings(on_ui_settings)
except Exception as e:
    print(f"API 启动失败: {str(e)}")
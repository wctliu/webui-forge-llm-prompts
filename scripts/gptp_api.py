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
    messages: List[Dict[str, Union[str, Dict]]]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 800
    top_p: Optional[float] = 1.0
    stream: Optional[bool] = False

class BaiduQianfanRequest(BaseModel):
    model: str
    messages: List[Dict[str, Union[str, Dict]]]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[float] = 800
    top_p: Optional[float] = 0.8
    stream: Optional[bool] = False

class HunyuanNativeRequest(BaseModel):
    model: str
    messages: List[Dict[str, Union[str, List[Dict], Dict]]]
    temperature: Optional[float] = 0.7
    top_p: Optional[float] = 1.0
    max_tokens: Optional[int] = 800
    stream: Optional[bool] = False

class VolcengineArkNativeRequest(BaseModel):
    model: str
    messages: List[Dict[str, Union[str, Dict]]]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 800
    top_p: Optional[float] = 1.0
    stream: Optional[bool] = False

class BaiduQianfanNativeRequest(BaseModel):
    model: str
    messages: List[Dict[str, Union[str, Dict]]]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[float] = 800
    top_p: Optional[float] = 0.8
    stream: Optional[bool] = False

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
                        "role": message["role"],
                        "content": [
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
                # 普通文本消息，直接添加
                processed_messages.append(message)
        
        # 根据API类型处理system消息
        if api_type == "hunyuan":
            # 腾讯混元要求system消息在最开始
            return system_messages + processed_messages
        elif api_type in ["volcengine_ark", "baidu_qianfan"]:
            # 某些API可能不支持system消息，需要转换成user消息
            if system_messages and processed_messages:
                # 将system消息内容添加到第一个user消息前面
                system_content = system_messages[0].get("content", "")
                for i, msg in enumerate(processed_messages):
                    if msg.get("role") == "user":
                        if isinstance(msg.get("content"), list):
                            # 如果是多模态消息
                            for item in msg["content"]:
                                if item.get("type") == "text":
                                    item["text"] = system_content + "\n\n" + item["text"]
                                    break
                        else:
                            # 普通文本消息
                            processed_messages[i]["content"] = system_content + "\n\n" + msg.get("content", "")
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
            processed_messages = self._process_messages(request.messages, "volcengine_ark")
            
            headers = {
                "Authorization": f"Bearer {shared.opts.gptp_volcengine_ark_api_key.strip()}",
                "Content-Type": "application/json"
            }
            
            payload = request.dict()
            payload["messages"] = processed_messages
            
            response = requests.post(
                f"{shared.opts.gptp_volcengine_ark_api_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            data = response.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
            if not content:
                return {"error": "Volcengine Ark API 返回空内容"}
            return {"text": content}
        except requests.RequestException as e:
            return {"error": f"Volcengine Ark API 错误: {str(e)}"}

    def get_baidu_qianfan_prompt(self, request: BaiduQianfanRequest) -> Dict[str, str]:
        """调用百度千帆 API 生成提示"""
        try:
            # 处理消息
            processed_messages = self._process_messages(request.messages, "baidu_qianfan")
            
            # 获取访问令牌
            token_response = requests.post(
                f"{shared.opts.gptp_baidu_qianfan_api_url}/oauth/2.0/token",
                params={
                    "grant_type": "client_credentials",
                    "client_id": shared.opts.gptp_baidu_qianfan_api_key.strip(),
                    "client_secret": shared.opts.gptp_baidu_qianfan_secret_key.strip()
                }
            )
            token_response.raise_for_status()
            access_token = token_response.json().get("access_token")
            
            if not access_token:
                return {"error": "获取百度千帆访问令牌失败"}
            
            # 发送请求
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}"
            }
            
            payload = request.dict()
            payload["messages"] = processed_messages
            
            response = requests.post(
                f"{shared.opts.gptp_baidu_qianfan_api_url}/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/{request.model}",
                headers=headers,
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            data = response.json()
            content = data.get("result", "").strip()
            if not content:
                return {"error": "百度千帆 API 返回空内容"}
            return {"text": content}
        except requests.RequestException as e:
            return {"error": f"百度千帆 API 错误: {str(e)}"}

    def get_hunyuan_native_prompt(self, request: HunyuanNativeRequest) -> Dict[str, Union[str, Dict]]:
        """使用腾讯混元签名模式获取提示词"""
        try:
            secret_id = shared.opts.gptp_hunyuan_secret_id
            secret_key = shared.opts.gptp_hunyuan_secret_key
            
            if not all([secret_id, secret_key]):
                raise ValueError("请在设置中配置腾讯混元的 SecretId 和 SecretKey")

            # 处理消息中的图片
            messages = self._process_messages(request.messages, "hunyuan")
            
            # 构建请求体
            request_body = {
                "Messages": messages,
                "Temperature": request.temperature,
                "TopP": request.top_p,
                "MaxTokens": request.max_tokens,
                "Model": request.model
            }
            
            # 请求方法和域名
            service = "hunyuan"
            host = "hunyuan.tencentcloudapi.com"
            endpoint = "https://" + host
            region = "ap-guangzhou"  # 腾讯混元默认区域
            action = "ChatCompletion"
            version = "2023-10-17"  # API版本
            
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
                return {"content": result["Response"]["Choice"]["Message"]["Content"]}
            elif "choices" in result and len(result["choices"]) > 0:
                return {"content": result["choices"][0]["message"]["content"]}
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
            access_key = shared.opts.gptp_volcengine_ark_ak
            secret_key = shared.opts.gptp_volcengine_ark_sk
            
            if not all([access_key, secret_key]):
                raise ValueError("请在设置中配置火山引擎方舟的 AccessKey 和 SecretKey")

            # 处理消息中的图片
            messages = self._process_messages(request.messages, "volcengine_ark")
            
            # 构建请求参数
            params = {
                "messages": messages,
                "model": request.model,
                "temperature": request.temperature,
                "top_p": request.top_p,
                "max_tokens": request.max_tokens
            }
            
            # 获取API地址
            api_url = shared.opts.gptp_volcengine_ark_api_url.rstrip('/')
            endpoint = f"{api_url}/chat/completions"
            
            # 获取请求时间
            timestamp = str(int(time.time()))
            nonce = str(int(time.time() * 1000))
            
            # 构建待签名字符串
            string_to_sign = f"{timestamp}\n{nonce}\n{json.dumps(params)}"
            
            # 计算签名
            signature = hmac.new(
                secret_key.encode('utf-8'),
                string_to_sign.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            # 构建请求头
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"HMAC-SHA256 AccessKey={access_key}, Timestamp={timestamp}, Nonce={nonce}, Signature={signature}"
            }
            
            # 发送请求
            response = requests.post(
                endpoint,
                json=params,
                headers=headers,
                timeout=60
            )
            
            if response.status_code != 200:
                raise ValueError(f"火山引擎方舟 API 错误: {response.status_code} {response.text}")
            
            result = response.json()
            if "choices" in result and len(result["choices"]) > 0:
                return {"content": result["choices"][0]["message"]["content"]}
            else:
                raise ValueError(f"火山引擎方舟 API 响应格式错误: {result}")
        except Exception as e:
            # 错误信息处理
            return {"error": f"火山引擎方舟 API 错误: {str(e)}"}

    def get_baidu_qianfan_native_prompt(self, request: BaiduQianfanNativeRequest) -> Dict[str, str]:
        """使用百度千帆签名模式获取提示词"""
        try:
            api_key = shared.opts.gptp_baidu_qianfan_api_key_native
            secret_key = shared.opts.gptp_baidu_qianfan_secret_key
            
            if not all([api_key, secret_key]):
                raise ValueError("请在设置中配置百度千帆的 API Key 和 Secret Key")

            # 获取访问令牌
            access_token = self._get_baidu_access_token(api_key, secret_key)
            
            # 处理消息中的图片
            messages = self._process_messages(request.messages, "baidu_qianfan")
            
            # 构建请求参数
            params = {
                "messages": messages,
                "temperature": request.temperature,
                "top_p": request.top_p,
                "max_output_tokens": request.max_tokens  # 百度千帆使用 max_output_tokens 而不是 max_tokens
            }
            
            # 构建API URL
            api_base = shared.opts.gptp_baidu_qianfan_api_url.rstrip('/')
            model_name = request.model.lower()
            api_url = f"{api_base}/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/{model_name}"
            
            # 发送请求
            response = requests.post(
                api_url,
                json=params,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {access_token}"
                },
                timeout=60
            )
            
            if response.status_code != 200:
                raise ValueError(f"百度千帆 API 错误: {response.status_code} {response.text}")
            
            result = response.json()
            if "result" in result:
                return {"content": result["result"]}
            elif "error_code" in result:
                error_msg = result.get("error_msg", "未知错误")
                raise ValueError(f"百度千帆 API 错误 {result['error_code']}: {error_msg}")
            else:
                raise ValueError(f"百度千帆 API 响应格式错误: {result}")
        except Exception as e:
            # 错误信息处理
            return {"error": f"百度千帆 API 错误: {str(e)}"}

    def _get_baidu_access_token(self, api_key: str, secret_key: str) -> str:
        """获取百度千帆访问令牌"""
        try:
            # 构建请求参数
            params = {
                "grant_type": "client_credentials",
                "client_id": api_key,
                "client_secret": secret_key
            }
            
            # 发送请求获取访问令牌
            # 注意：这里使用的是正确的token获取URL
            response = requests.post(
                "https://aip.baidubce.com/oauth/2.0/token",
                params=params,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code != 200:
                raise ValueError(f"获取百度千帆访问令牌失败: {response.status_code} {response.text}")
            
            result = response.json()
            if "access_token" not in result:
                raise ValueError(f"获取百度千帆访问令牌失败，返回内容中没有access_token: {result}")
                
            return result["access_token"]
        except Exception as e:
            raise ValueError(f"获取百度千帆访问令牌时出错: {str(e)}")

# 启动 API
try:
    api = GptpApi()
    script_callbacks.on_app_started(api.start)
except Exception as e:
    print(f"API 启动失败: {str(e)}")
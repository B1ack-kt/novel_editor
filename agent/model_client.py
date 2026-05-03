"""
AI模型API统一客户端
支持：多模型切换、API密钥管理、调用频率控制、上下文传入
所有通信仅通过用户本地网络与模型接口直连，不经过产品服务器
"""

import time
import json
import threading
from typing import Optional, Dict, List, Callable
from collections import deque

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False


class RateLimiter:
    """API调用频率控制"""

    def __init__(self, max_calls_per_minute: int = 5):
        self._max_calls = max_calls_per_minute
        self._call_times: deque = deque()

    def can_call(self) -> bool:
        """检查是否允许调用"""
        now = time.time()
        # 清理过期记录
        while self._call_times and self._call_times[0] < now - 60:
            self._call_times.popleft()
        return len(self._call_times) < self._max_calls

    def record_call(self):
        """记录一次调用"""
        self._call_times.append(time.time())

    def wait_time(self) -> float:
        """返回需要等待的秒数"""
        if not self._call_times:
            return 0
        if len(self._call_times) < self._max_calls:
            return 0
        oldest = self._call_times[0]
        return max(0, 60 - (time.time() - oldest))


class ModelClient:
    """
    AI模型API统一客户端
    支持多模型API调用，统一接口
    """

    def __init__(self, timeout: int = 30):
        self._timeout = timeout
        self._rate_limiter = RateLimiter()
        self._models: Dict[str, dict] = {}
        self._current_model_id: str = ""
        self._offline_mode: bool = False

        # 回调
        self._on_status_change: Optional[Callable] = None
        self._on_response: Optional[Callable] = None
        self._on_error: Optional[Callable] = None

    def set_offline_mode(self, offline: bool):
        """设置离线模式"""
        self._offline_mode = offline

    def add_model(self, model_id: str, config: dict):
        """添加模型配置

        Args:
            model_id: 模型标识
            config: {"name", "api_url", "api_key", "model_type", "parameters"}
        """
        self._models[model_id] = config

    def remove_model(self, model_id: str):
        """移除模型"""
        self._models.pop(model_id, None)
        if self._current_model_id == model_id:
            self._current_model_id = ""

    def set_current_model(self, model_id: str):
        """设置当前模型"""
        if model_id in self._models:
            self._current_model_id = model_id

    def get_models(self) -> Dict[str, dict]:
        """获取所有模型"""
        return self._models

    def set_status_callback(self, callback: Callable):
        """设置状态变化回调"""
        self._on_status_change = callback

    def set_response_callback(self, callback: Callable):
        """设置响应回调"""
        self._on_response = callback

    def set_error_callback(self, callback: Callable):
        """设置错误回调"""
        self._on_error = callback

    def _notify_status(self, status: str, **kwargs):
        """通知状态变化"""
        if self._on_status_change:
            self._on_status_change(status, **kwargs)

    def chat(
        self,
        messages: List[dict],
        system_prompt: str = "",
        max_tokens: int = 4096,
        temperature: float = 0.7,
        callback: Optional[Callable] = None
    ) -> Optional[str]:
        """
        调用AI模型进行对话

        Args:
            messages: 对话历史 [{"role": "user"/"assistant", "content": "..."}, ...]
            system_prompt: 系统提示词
            max_tokens: 最大token数
            temperature: 温度参数
            callback: 结果回调 callback(response_text, error)

        Returns:
            AI响应文本(同步调用时)
        """
        if self._offline_mode:
            error = "离线模式下无法调用AI模型"
            if callback:
                callback(None, error)
            return None

        if not self._current_model_id:
            error = "未选择AI模型"
            if callback:
                callback(None, error)
            return None

        model = self._models.get(self._current_model_id)
        if not model:
            error = "模型配置不存在"
            if callback:
                callback(None, error)
            return None

        # 频率控制
        if not self._rate_limiter.can_call():
            wait = self._rate_limiter.wait_time()
            error = f"调用频率过高，请等待 {wait:.1f} 秒"
            if callback:
                callback(None, error)
            return None

        self._rate_limiter.record_call()
        self._notify_status("calling", model_name=model.get("name", ""))

        # 在后台线程执行
        if callback:
            thread = threading.Thread(
                target=self._do_chat,
                args=(model, messages, system_prompt, max_tokens, temperature, callback),
                daemon=True
            )
            thread.start()
            return None
        else:
            return self._do_chat(
                model, messages, system_prompt, max_tokens, temperature
            )

    def _do_chat(
        self,
        model: dict,
        messages: List[dict],
        system_prompt: str,
        max_tokens: int,
        temperature: float,
        callback: Optional[Callable] = None
    ) -> Optional[str]:
        """执行实际的API调用"""
        try:
            import httpx

            api_url = model.get("api_url", "")
            api_key = model.get("api_key", "")
            model_type = model.get("model_type", "openai").lower()

            # 构建请求体（适配不同模型格式）
            if model_type in ("openai", "custom", "llama", "chatglm"):
                request_body = {
                    "model": model.get("parameters", {}).get("model", "gpt-3.5-turbo"),
                    "messages": [],
                    "max_tokens": max_tokens,
                    "temperature": temperature
                }
                if system_prompt:
                    request_body["messages"].append({
                        "role": "system", "content": system_prompt
                    })
                for msg in messages:
                    request_body["messages"].append(msg)
            elif model_type == "claude":
                request_body = {
                    "model": model.get("parameters", {}).get("model", "claude-3-opus-20240229"),
                    "max_tokens": max_tokens,
                    "system": system_prompt,
                    "messages": messages
                }
            elif model_type == "wenxin":
                request_body = {
                    "messages": []
                }
                if system_prompt:
                    request_body["messages"].append({
                        "role": "system", "content": system_prompt
                    })
                for msg in messages:
                    request_body["messages"].append(msg)
            elif model_type == "tongyi":
                request_body = {
                    "model": model.get("parameters", {}).get("model", "qwen-turbo"),
                    "input": {
                        "messages": []
                    },
                    "parameters": {
                        "max_tokens": max_tokens,
                        "temperature": temperature
                    }
                }
                if system_prompt:
                    request_body["input"]["messages"].append({
                        "role": "system", "content": system_prompt
                    })
                for msg in messages:
                    request_body["input"]["messages"].append(msg)
            else:
                # 通用格式
                request_body = {
                    "messages": [],
                    "max_tokens": max_tokens,
                    "temperature": temperature
                }
                if system_prompt:
                    request_body["messages"].append({
                        "role": "system", "content": system_prompt
                    })
                for msg in messages:
                    request_body["messages"].append(msg)

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            }

            # 发送请求
            with httpx.Client(timeout=self._timeout) as client:
                response = client.post(api_url, json=request_body, headers=headers)
                response.raise_for_status()
                result = response.json()

            # 解析响应
            response_text = self._parse_response(result, model_type)

            self._notify_status("success", model_name=model.get("name", ""))

            if callback:
                callback(response_text, None)
            return response_text

        except Exception as e:
            error_msg = f"API调用失败: {str(e)}"
            self._notify_status("error", model_name=model.get("name", ""))
            if callback:
                callback(None, error_msg)
            if self._on_error:
                self._on_error(error_msg)
            return None

    def _parse_response(self, result: dict, model_type: str) -> str:
        """解析不同模型的响应格式"""
        if model_type in ("openai", "custom", "llama", "chatglm"):
            choices = result.get("choices", [])
            if choices:
                return choices[0].get("message", {}).get("content", "")
        elif model_type == "claude":
            content = result.get("content", [])
            if content:
                return content[0].get("text", "")
        elif model_type == "wenxin":
            return result.get("result", "")
        elif model_type == "tongyi":
            output = result.get("output", {})
            return output.get("text", "")
        else:
            # 通用解析
            if "choices" in result:
                return result["choices"][0].get("message", {}).get("content", "")
            if "content" in result:
                return result["content"]
            if "result" in result:
                return result["result"]
            if "response" in result:
                return result["response"]
        return str(result)

    def test_connection(self, model_id: str) -> tuple:
        """测试模型连接

        Returns:
            (success: bool, message: str)
        """
        model = self._models.get(model_id)
        if not model:
            return False, "模型配置不存在"

        try:
            import httpx
            api_url = model.get("api_url", "")
            api_key = model.get("api_key", "")

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            }

            # 发送最小测试请求
            test_body = {
                "messages": [{"role": "user", "content": "test"}],
                "max_tokens": 1
            }

            with httpx.Client(timeout=10) as client:
                response = client.post(api_url, json=test_body, headers=headers)
                return response.status_code < 500, f"状态码: {response.status_code}"
        except Exception as e:
            return False, str(e)


class AgentWorker:
    """Agent后台工作线程 - 统一管理AI调用任务"""

    def __init__(self, model_client: ModelClient):
        self._client = model_client
        self._tasks: List[dict] = []
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def add_task(self, action_id: str, context: dict, callback: Callable):
        """添加Agent任务"""
        self._tasks.append({
            "action_id": action_id,
            "context": context,
            "callback": callback
        })

    def start(self):
        """启动工作线程"""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        """停止工作线程"""
        self._running = False

    def _run(self):
        """工作线程主循环"""
        while self._running:
            if self._tasks:
                task = self._tasks.pop(0)
                try:
                    # 构建提示词
                    prompt = self._build_prompt(task["action_id"], task["context"])
                    self._client.chat(
                        messages=[{"role": "user", "content": prompt}],
                        callback=task["callback"]
                    )
                except Exception as e:
                    task["callback"](None, str(e))
            else:
                time.sleep(0.5)

    def _build_prompt(self, action_id: str, context: dict) -> str:
        """根据action类型构建提示词"""
        prompts = {
            "plot_generate": (
                "你是一位小说创作顾问。根据以下创作背景，请生成3个有创意的情节分支建议。"
                "每个建议应包含发展方向、可能的冲突点和预期效果。\n\n"
                f"创作背景:\n{json.dumps(context, ensure_ascii=False, indent=2)}"
            ),
            "polish": (
                "请润色以下文本，保持原意和风格，优化表达、修辞和流畅度。"
                "如需要，提供润色后的全文和修改说明。\n\n"
                f"原文:\n{context.get('selected_text', '')}"
            ),
            "check_settings": (
                "请校验以下正文内容是否与人设和世界观设定一致。"
                "列出所有冲突项，并给出修改建议。\n\n"
                f"正文:\n{context.get('chapter_content', '')}\n\n"
                f"人设库:\n{json.dumps(context.get('characters', {}), ensure_ascii=False)}\n\n"
                f"世界观库:\n{json.dumps(context.get('world_rules', {}), ensure_ascii=False)}"
            ),
            "outline": (
                "请根据以下小说项目和已写章节，生成后续章节大纲建议。"
                "大纲应包含每章的核心情节和衔接过渡。\n\n"
                f"项目信息:\n{json.dumps(context, ensure_ascii=False, indent=2)}"
            ),
            "fill_details": (
                "请根据当前场景和设定库，补充场景/人物细节描写。"
                "重点补充画面感、感官细节和人物动作神态。\n\n"
                f"当前场景:\n{context.get('current_text', '')}\n\n"
                f"可用设定:\n{json.dumps(context.get('settings', {}), ensure_ascii=False)}"
            ),
        }

        return prompts.get(
            action_id,
            f"请根据以下上下文提供创作建议:\n{json.dumps(context, ensure_ascii=False, indent=2)}"
        )

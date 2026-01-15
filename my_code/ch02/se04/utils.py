# === 标准库 ===
import os
import re
import json
import base64
import mimetypes
from pathlib import Path

# === 第三方库 ===
import pandas as pd
import matplotlib.pyplot as plt
from PIL import Image  # (如果其他地方需要可保留)
from dotenv import load_dotenv
from openai import OpenAI
from anthropic import Anthropic
from html import escape

# === 环境变量和客户端 ===
load_dotenv()

openai_base_url = os.getenv("OPENAI_BASE_URL")
openai_api_key = os.getenv("OPENAI_API_KEY")

anthropic_base_url = os.getenv("ANTHROPIC_BASE_URL")
anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")


class ClientManager:
    """管理 OpenAI 和 Anthropic 客户端的类，支持自定义 URL 和 api_key"""
    
    def __init__(self, openai_api_key=None, openai_base_url=None, anthropic_api_key=None, anthropic_base_url=None):
        # 如果未提供参数，则使用环境变量
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self.openai_base_url = openai_base_url or os.getenv("OPENAI_BASE_URL")
        self.anthropic_api_key = anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")
        self.anthropic_base_url = anthropic_base_url or os.getenv("ANTHROPIC_BASE_URL")
        
        # 初始化 OpenAI 客户端
        if self.openai_api_key:
            self.openai_client = OpenAI(api_key=self.openai_api_key, base_url=self.openai_base_url) if self.openai_base_url else OpenAI(api_key=self.openai_api_key)
        else:
            self.openai_client = OpenAI(base_url=self.openai_base_url) if self.openai_base_url else OpenAI()
        
        # 初始化 Anthropic 客户端
        if self.anthropic_api_key:
            self.anthropic_client = Anthropic(api_key=self.anthropic_api_key, base_url=self.anthropic_base_url) if self.anthropic_base_url else Anthropic(api_key=self.anthropic_api_key)
        else:
            self.anthropic_client = Anthropic(base_url=self.anthropic_base_url) if self.anthropic_base_url else Anthropic()


# 创建默认客户端实例（使用环境变量）
client_manager = ClientManager()
openai_client = client_manager.openai_client
anthropic_client = client_manager.anthropic_client


def create_custom_clients(openai_api_key=None, openai_base_url=None, anthropic_api_key=None, anthropic_base_url=None):
    """
    创建具有自定义设置的客户端
    
    参数:
    - openai_api_key: OpenAI API 密钥
    - openai_base_url: OpenAI API 基础 URL
    - anthropic_api_key: Anthropic API 密钥
    - anthropic_base_url: Anthropic API 基础 URL
    
    返回:
    - tuple: (openai_client, anthropic_client)
    """
    custom_manager = ClientManager(
        openai_api_key=openai_api_key,
        openai_base_url=openai_base_url,
        anthropic_api_key=anthropic_api_key,
        anthropic_base_url=anthropic_base_url
    )
    return custom_manager.openai_client, custom_manager.anthropic_client


def get_response(model: str, prompt: str, openai_client=None, anthropic_client=None) -> str:
    # 如果没有提供客户端，则使用默认客户端
    openai_client = openai_client or globals()['openai_client']
    anthropic_client = anthropic_client or globals()['anthropic_client']
    
    if "claude" in model.lower() or "anthropic" in model.lower():
        # Anthropic Claude 格式
        message = anthropic_client.messages.create(
            model=model,
            max_tokens=1000,
            messages=[{"role": "user", "content": [{"type": "text", "text": prompt}]}],
        )
        return message.content[0].text

    else:
        # 默认对所有其他模型使用 OpenAI 格式 (gpt-4, o3-mini, o1, 等.)
        response = openai_client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1000,
        )
        return response.choices[0].message.content
    
# === 数据加载 ===
def load_and_prepare_data(csv_path: str) -> pd.DataFrame:
    """加载 CSV 并派生图表中常用的日期部分。"""
    df = pd.read_csv(csv_path)
    # 如果存在 'date' 列则保持宽容处理
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df["quarter"] = df["date"].dt.quarter
        df["month"] = df["date"].dt.month
        df["year"] = df["date"].dt.year
    return df

# === 辅助函数 ===
def make_schema_text(df: pd.DataFrame) -> str:
    """从 DataFrame 返回一个人类可读的模式。"""
    return "\n".join(f"- {c}: {dt}" for c, dt in df.dtypes.items())

def ensure_execute_python_tags(text: str) -> str:
    """规范化代码以包装在 <execute_python>...</execute_python> 中。"""
    text = text.strip()
    # 如果存在则去除 ```python 围栏
    text = re.sub(r"^```(?:python)?\s*|\s*```$", "", text).strip()
    if "<execute_python>" not in text:
        text = f"<execute_python>\n{text}\n</execute_python>"
    return text

def encode_image_b64(path: str) -> tuple[str, str]:
    """为图像文件路径返回 (media_type, base64_str)。"""
    mime, _ = mimetypes.guess_type(path)
    media_type = mime or "image/png"
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    return media_type, b64


import base64
from IPython.display import HTML, display
import pandas as pd
from typing import Any

def print_html(content: Any, title: str | None = None, is_image: bool = False):
    """
    在样式化的卡片内格式化打印。
    - 如果 is_image=True 且 content 是字符串：视为图像路径/URL 并渲染 <img>。
    - 如果 content 是 pandas DataFrame/Series：渲染为 HTML 表格。
    - 否则 (字符串/其他)：显示为 <pre><code> 中的代码/文本。
    """
    try:
        from html import escape as _escape
    except ImportError:
        _escape = lambda x: x

    def image_to_base64(image_path: str) -> str:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode("utf-8")

    # 渲染内容
    if is_image and isinstance(content, str):
        b64 = image_to_base64(content)
        rendered = f'<img src="data:image/png;base64,{b64}" alt="Image" style="max-width:100%; height:auto; border-radius:8px;">'
    elif isinstance(content, pd.DataFrame):
        rendered = content.to_html(classes="pretty-table", index=False, border=0, escape=False)
    elif isinstance(content, pd.Series):
        rendered = content.to_frame().to_html(classes="pretty-table", border=0, escape=False)
    elif isinstance(content, str):
        rendered = f"<pre><code>{_escape(content)}</code></pre>"
    else:
        rendered = f"<pre><code>{_escape(str(content))}</code></pre>"

    css = """
    <style>
    .pretty-card{
      font-family: ui-sans-serif, system-ui;
      border: 2px solid transparent;
      border-radius: 14px;
      padding: 14px 16px;
      margin: 10px 0;
      background: linear-gradient(#fff, #fff) padding-box,
                  linear-gradient(135deg, #3b82f6, #9333ea) border-box;
      color: #111;
      box-shadow: 0 4px 12px rgba(0,0,0,.08);
    }
    .pretty-title{
      font-weight:700;
      margin-bottom:8px;
      font-size:14px;
      color:#111;
    }
    /* 🔒 Only affects INSIDE the card */
    .pretty-card pre, 
    .pretty-card code {
      background: #f3f4f6;
      color: #111;
      padding: 8px;
      border-radius: 8px;
      display: block;
      overflow-x: auto;
      font-size: 13px;
      white-space: pre-wrap;
    }
    .pretty-card img { max-width: 100%; height: auto; border-radius: 8px; }
    .pretty-card table.pretty-table {
      border-collapse: collapse;
      width: 100%;
      font-size: 13px;
      color: #111;
    }
    .pretty-card table.pretty-table th, 
    .pretty-card table.pretty-table td {
      border: 1px solid #e5e7eb;
      padding: 6px 8px;
      text-align: left;
    }
    .pretty-card table.pretty-table th { background: #f9fafb; font-weight: 600; }
    </style>
    """

    title_html = f'<div class="pretty-title">{title}</div>' if title else ""
    card = f'<div class="pretty-card">{title_html}{rendered}</div>'
    display(HTML(css + card))

    

    
def image_anthropic_call(model_name: str, prompt: str, media_type: str, b64: str, anthropic_client=None) -> str:
    """
    使用文本+图像调用 Anthropic Claude (messages.create) 并返回连接的 *所有* 文本块。
    添加系统消息以强制严格的 JSON 输出。
    
    参数:
    - model_name: 模型名称
    - prompt: 提示文本
    - media_type: 媒体类型
    - b64: Base64 编码的图像数据
    - anthropic_client: 可选的 Anthropic 客户端实例
    """
    # 如果没有提供客户端，则使用默认客户端
    anthropic_client = anthropic_client or globals()['anthropic_client']
    
    msg = anthropic_client.messages.create(
        model=model_name,
        max_tokens=2000,
        temperature=0,
        system=(
            "You are a careful assistant. Respond with a single valid JSON object only. "
            "Do not include markdown, code fences, or commentary outside JSON."
        ),
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": b64}},
            ],
        }],
    )

    # Anthropic 返回内容块列表；收集所有文本
    parts = []
    for block in (msg.content or []):
        if getattr(block, "type", None) == "text":
            parts.append(block.text)
    return "".join(parts).strip()


def image_openai_call(model_name: str, prompt: str, media_type: str, b64: str, openai_client=None) -> str:
    """
    使用文本+图像调用 OpenAI 模型并返回响应内容。
    
    参数:
    - model_name: 模型名称
    - prompt: 提示文本
    - media_type: 媒体类型
    - b64: Base64 编码的图像数据
    - openai_client: 可选的 OpenAI 客户端实例
    """
    # 如果没有提供客户端，则使用默认客户端
    openai_client = openai_client or globals()['openai_client']
    
    data_url = f"data:{media_type};base64,{b64}"
    response = openai_client.chat.completions.create(
        model=model_name,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            }
        ],
        max_tokens=1000,
    )
    content = (response.choices[0].message.content or "").strip()
    return content


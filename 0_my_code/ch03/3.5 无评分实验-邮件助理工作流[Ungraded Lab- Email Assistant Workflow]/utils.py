# ================================
# 导入
# ================================

# --- 标准库 ---
import os
import json
from html import escape
from datetime import datetime  # 如果稍后使用则保留
from urllib.parse import urljoin

# --- 第三方库 ---
import requests
import pandas as pd
from dotenv import load_dotenv
from IPython.display import display, HTML

import base64
from typing import Any

# --- 本地/项目 ---
# (在此处添加您的本地导入，例如 `import utils`)

# ================================
# 环境和HTTP会话
# ================================
load_dotenv()  # 从工作目录加载 .env 文件

BASE_URL = os.getenv("M3_EMAIL_SERVER_API_URL")

session = requests.Session()
session.headers.update({"User-Agent": "LF-ADP-EmailClient/1.0"})


# ================================
# 辅助函数
# ================================
def print_html(content: Any, title: str | None = None, is_image: bool = False):
    """
    在带样式的卡片中精美打印。
    - 如果 is_image=True 且 content 是字符串：视为图片路径/URL并渲染 <img>。
    - 如果 content 是 pandas DataFrame/Series：渲染为HTML表格。
    - 否则（字符串/其他）：在 <pre><code> 中显示为代码/文本。
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
    /* 🔒 仅影响卡片内部 */
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

def pretty_display(title: str, response: requests.Response):
    """在带样式的块中渲染HTTP响应；如果可能，返回解析后的内容（JSON）。"""
    status = response.status_code
    try:
        content = response.json()
        body = json.dumps(content, indent=2)
    except Exception:
        content = response.text
        body = content

    html = f"""
    <div style='border:1px solid #ccc; border-left:5px solid #007bff; padding:10px; margin:10px 0; background:#f9f9f9; color:#000;'>
        <strong style='color:#007bff'>{escape(title)}:</strong>
        <span style='color:{"green" if status == 200 else "red"}'> Status {status}</span>
        <pre style='font-size:12px; margin-top:10px; white-space:pre-wrap; color:#000;'>{escape(body)}</pre>
    </div>
    """
    display(HTML(html))
    return content

# ================================
# API 调用
# ================================
def reset_database() -> dict:
    """调用 /reset_database 端点并返回确认消息。"""
    r = session.get(f"{BASE_URL}/reset_database")
    r.raise_for_status()
    return r.json()

def test_send_email():
    payload = {
        "recipient": "test@example.com",
        "subject": "Test Subject",
        "body": "This is a test email body.",
    }
    r = session.post(f"{BASE_URL}/send", json=payload)
    return pretty_display("POST /send", r)

def test_list_emails():
    r = session.get(f"{BASE_URL}/emails")
    return pretty_display("GET /emails", r)

def test_search_emails(q: str = "report"):
    r = session.get(f"{BASE_URL}/emails/search", params={"q": q})
    return pretty_display(f"GET /emails/search?q={q}", r)

def test_filter_emails(recipient: str | None = None, date_from: str | None = None, date_to: str | None = None):
    params = {}
    if recipient:
        params["recipient"] = recipient
    if date_from:
        params["date_from"] = date_from
    if date_to:
        params["date_to"] = date_to
    r = session.get(f"{BASE_URL}/emails/filter", params=params)
    return pretty_display("GET /emails/filter", r)

def test_unread_emails():
    r = session.get(f"{BASE_URL}/emails/unread")
    return pretty_display("GET /emails/unread", r)

def test_get_email(email_id: str):
    r = session.get(f"{BASE_URL}/emails/{email_id}")
    return pretty_display(f"GET /emails/{email_id}", r)

def test_mark_read(email_id: str):
    r = session.patch(f"{BASE_URL}/emails/{email_id}/read")
    return pretty_display(f"PATCH /emails/{email_id}/read", r)

def test_mark_unread(email_id: str):
    r = session.patch(f"{BASE_URL}/emails/{email_id}/unread")
    return pretty_display(f"PATCH /emails/{email_id}/unread", r)

def test_delete_email(email_id: str):
    r = session.delete(f"{BASE_URL}/emails/{email_id}")
    return pretty_display(f"DELETE /emails/{email_id}", r)


def call_llm_email_agent(prompt: str,
                         api_url: str | None = None,
                         timeout: int = 30) -> dict:
    """
    使用自然语言指令调用 M3 LLM 服务器。

    参数:
        prompt: 给代理的指令 (例如, "检查未读邮件...")。
        api_url: LLM 服务器的基础URL。如果为 None, 则使用环境变量 M3_LLM_SERVER_URL。
        timeout: HTTP 超时时间（秒）。

    返回:
        一个字典，包含键: ok (bool), status (int), response (str|None), raw (dict|str)
    """
    # 解析 API 基础 URL
    base = api_url or os.getenv("M3_LLM_SERVER_URL")
    if not base:
        raise RuntimeError("M3_LLM_SERVER_URL 未设置。请在 .env 文件中设置 (例如, http://127.0.0.1:5001)。")

    # 构建最终端点；接受带或不带 /prompt 的结尾
    endpoint = base if base.rstrip("/").endswith("/prompt") else urljoin(base.rstrip("/") + "/", "prompt")

    try:
        r = requests.post(endpoint, json={"prompt": prompt}, timeout=timeout)
    except requests.RequestException as e:
        return {"ok": False, "status": None, "response": None, "raw": str(e)}

    try:
        data = r.json()
    except ValueError:
        data = r.text

    ok = (r.status_code == 200)
    return {"ok": ok, "status": r.status_code, "response": (data.get("response") if isinstance(data, dict) else None), "raw": data}



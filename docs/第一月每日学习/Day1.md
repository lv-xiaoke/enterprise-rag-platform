# Day 1：项目初始化完整操作

下面默认你使用 **Windows + VS Code + PowerShell**。今天的目标不是实现真正的 RAG，而是把项目环境和最小 FastAPI 服务搭起来。

---

## 一、检查基础环境

打开 PowerShell 或 VS Code 终端，依次执行：

```powershell
python --version
git --version
```

正常情况下会看到类似：

```text
Python 3.12.4
git version 2.50.0.windows.1
```

建议使用 Python 3.10 及以上版本。

如果提示：

```text
python 不是内部或外部命令
```

说明 Python 没安装好，或者安装时没有加入环境变量。

---

# 二、创建项目目录

先进入你想存放代码的位置，例如桌面：

```powershell
cd Desktop
```

创建项目：

```powershell
mkdir mini-rag-backend
cd mini-rag-backend
```

查看当前位置：

```powershell
pwd
```

你现在应该位于类似：

```text
C:\Users\你的用户名\Desktop\mini-rag-backend
```

用 VS Code 打开当前目录：

```powershell
code .
```

如果 `code .` 无法使用，也可以直接打开 VS Code，然后选择：

```text
文件 → 打开文件夹 → mini-rag-backend
```

---

# 三、创建虚拟环境

在项目根目录执行：

```powershell
python -m venv .venv
```

执行完成后，项目中会出现：

```text
mini-rag-backend/
└── .venv/
```

`.venv` 是一个独立的 Python 环境。你在里面安装的 FastAPI、httpx 等包，只属于当前项目，不会影响其他 Python 项目。([Python documentation](https://docs.python.org/3/tutorial/venv.html?highlight=virtual&utm_source=chatgpt.com "12. Virtual Environments and Packages — Python 3.14.6 documentation"))

## 激活虚拟环境

### PowerShell

```powershell
.\.venv\Scripts\Activate.ps1
```

成功后，终端开头会出现：

```text
(.venv) PS C:\Users\...\mini-rag-backend>
```

看到 `(.venv)` 就表示激活成功。

### CMD

如果你使用的是 CMD，命令为：

```cmd
.venv\Scripts\activate.bat
```

### Git Bash

```bash
source .venv/Scripts/activate
```

## PowerShell 禁止执行脚本怎么办

如果出现类似：

```text
无法加载文件 Activate.ps1，因为在此系统上禁止运行脚本
```

可以只对当前终端临时放开限制：

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

然后重新激活：

```powershell
.\.venv\Scripts\Activate.ps1
```

关闭当前终端后，这项临时设置会失效。

---

# 四、确认当前 Python 来自虚拟环境

执行：

```powershell
where.exe python
```

正常情况下，第一行应该指向：

```text
mini-rag-backend\.venv\Scripts\python.exe
```

也可以执行：

```powershell
python -c "import sys; print(sys.executable)"
```

输出应该类似：

```text
C:\Users\...\mini-rag-backend\.venv\Scripts\python.exe
```

这一步非常重要：以后安装依赖之前，都先确认终端前面有 `(.venv)`。

---

# 五、安装项目依赖

先升级 pip：

```powershell
python -m pip install --upgrade pip
```

安装今天需要的包：

```powershell
python -m pip install fastapi uvicorn python-dotenv httpx
```

这里推荐写：

```powershell
python -m pip
```

而不是只写：

```powershell
pip
```

因为前者能更明确地保证：使用当前这个 Python 对应的 pip。

安装完成后查看：

```powershell
python -m pip list
```

你应该能看到：

```text
fastapi
uvicorn
python-dotenv
httpx
```

以及它们依赖的其他包。

---

# 六、生成 requirements.txt

执行：

```powershell
python -m pip freeze > requirements.txt
```

查看文件：

```powershell
Get-Content requirements.txt
```

里面会有类似：

```text
annotated-types==...
anyio==...
fastapi==...
httpx==...
pydantic==...
python-dotenv==...
starlette==...
uvicorn==...
```

不只是你手动安装的四个包，还会包括它们依赖的包，这是正常的。

`pip freeze` 会把当前环境中已经安装的包和版本按 requirements 格式输出；它更像当前环境的版本快照，而不是依赖求解器生成的严格锁文件。([pip](https://pip.pypa.io/en/stable/cli/pip_freeze/?utm_source=chatgpt.com "pip freeze - pip documentation v26.1.2"))

以后其他人在新环境中可以执行：

```powershell
python -m pip install -r requirements.txt
```

重新安装相同版本的依赖。

---

# 七、创建项目目录结构

推荐直接在 VS Code 左侧文件栏创建。

最终结构：

```text
mini-rag-backend/
├── .venv/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   └── services/
│       ├── __init__.py
│       └── llm_service.py
├── .env
├── .gitignore
└── requirements.txt
```

也可以在 PowerShell 中执行：

```powershell
mkdir app
mkdir app\services

New-Item app\__init__.py -ItemType File
New-Item app\main.py -ItemType File
New-Item app\config.py -ItemType File

New-Item app\services\__init__.py -ItemType File
New-Item app\services\llm_service.py -ItemType File

New-Item .env -ItemType File
New-Item .gitignore -ItemType File
```

如果文件已经存在，PowerShell 提示文件存在也没有关系。

---

# 八、编写每个文件

## 1. `app/__init__.py`

今天先保持为空：

这个文件告诉 Python：

```text
app 是一个 Python 包
```

---

## 2. `app/services/__init__.py`

同样保持为空：

它表示：

```text
services 是一个 Python 子包
```

之后才能方便地进行这种导入：

```python
from app.services.llm_service import LLMService
```

---

## 3. `.env`

填写：

```env
LLM_API_KEY=
LLM_BASE_URL=
LLM_MODEL=
```

今天还没有配置真正的大模型，所以等号后可以先留空。

以后接入 DeepSeek 时可能类似：

```env
LLM_API_KEY=你的真实密钥
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-chat
```

真实 API Key 只能放在 `.env` 中，不要直接写进 Python 代码。

---

## 4. `app/config.py`

写入：

```python
import os
from pathlib import Path

from dotenv import load_dotenv


# 项目根目录：
# app/config.py 的上一级是 app
# 再上一级就是 mini-rag-backend
BASE_DIR = Path(__file__).resolve().parent.parent
# __file__表示当前python文件的路径，Path则是将普通的路径字符串转为Path对象，方便处理，.resovle() 则是把路径转为完整的绝对路径


# 加载项目根目录下的 .env
load_dotenv(BASE_DIR / ".env")
# `os.getenv()` 只负责读取已经存在的环境变量，而 `.env` 只是一个普通文本文件。需要 `load_dotenv()` 先把文件内容加载进去

LLM_API_KEY = os.getenv("LLM_API_KEY", "")
# os.getenv("环境变量名", "默认值")

LLM_BASE_URL = os.getenv("LLM_BASE_URL", "")
LLM_MODEL = os.getenv("LLM_MODEL", "")
```

这段代码完成三件事：

```text
1. 找到项目根目录
2. 加载 .env
3. 从环境变量中读取配置
```

其中：

```python
os.getenv("LLM_API_KEY", "")
```

表示：

> 查找名为 `LLM_API_KEY` 的环境变量；如果找不到，就返回空字符串。

---

## 5. `app/services/llm_service.py`

写入：

```python
from app.config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL


class LLMService:
    """大语言模型服务。

    Day 1 暂时只保存配置，不真正请求模型。
    """

    def __init__(self) -> None:
        self.api_key = LLM_API_KEY
        self.base_url = LLM_BASE_URL
        self.model = LLM_MODEL

    def is_configured(self) -> bool:
        """判断大模型配置是否完整。"""
        return bool(
            self.api_key
            and self.base_url
            and self.model
        )
```

今天只需要理解：

```python
class LLMService:
```

定义了一个类。

```python
def __init__(self):
```

创建 `LLMService` 对象时会自动运行。

```python
self.api_key
```

表示当前对象自己的 `api_key` 属性。

```python
return bool(...)
```

判断三个配置是否都填写了。

---

## 6. `app/main.py`

写入：

```python
from fastapi import FastAPI
from app.services.llm_service import LLMService

app = FastAPI(
    title="Mini RAG Backend",
    description="一个用于学习RAG和AI应用开发的后端项目",
    version="0.1.0",
)
# 创建了一个 FastAPI 应用对象，并赋值给变量 `app`。这个对象是整个应用的核心，负责处理请求、路由、响应等功能。
# title、description 和 version 这些信息主要会显示在 FastAPI 自动生成的接口文档中
# 运行项目以后，可以打开：http://127.0.0.1:8000/docs ,你会看到项目名称、描述和接口列表。

llm_service = LLMService()

# 这叫作装饰器。它的意思是：当用户使用 GET 请求访问 / 时，执行下面的 root() 函数。
# 假设服务器地址是：http://127.0.0.1:8000 那么访问：http://127.0.0.1:8000/ 就会执行 root()。
@app.get("/")

async def root() -> dict[str, str]:
    # 这是定义一个异步函数。async 的详细原理后面学习异步编程时再深入。
    return {
        "message":"Mini RAG Backend is running"
    }
# 定义健康检查接口 /health 当用户访问：http://127.0.0.1:8000/health FastAPI 就会执行： health()

@app.get("/health")

async def health() -> dict[str, str | bool ]:
    return {
        "status":"ok",
        "llm_configured":llm_service.is_configured(),
    }
```

FastAPI 的基本结构是：

```python
app = FastAPI()
```

创建应用对象。

```python
@app.get("/")
```

注册一个 GET 接口。

```python
async def root():
```

定义访问接口时要执行的函数。

FastAPI 会把 Python 字典自动转换成 JSON，并且自动生成交互式接口文档。([FastAPI](https://fastapi.tiangolo.com/tutorial/first-steps/?utm_source=chatgpt.com "First Steps - FastAPI"))

---

## 7. `.gitignore`

写入：

```gitignore
# Python 虚拟环境
.venv/

# 环境变量和密钥
.env

# Python 缓存
__pycache__/
*.py[cod]

# 测试和工具缓存
.pytest_cache/
.mypy_cache/
.ruff_cache/

# IDE 配置
.vscode/
.idea/

# 操作系统文件
.DS_Store
Thumbs.db
```

最重要的是：

```gitignore
.venv/
.env
```

原因：

- `.venv` 文件很多，而且可以根据 `requirements.txt` 重新生成。
    
- `.env` 可能包含 API Key，绝对不能提交到 GitHub。
    

`.gitignore` 中的规则用于告诉 Git 哪些未跟踪文件或目录应该被忽略。([Git](https://git-scm.com/docs/gitignore.html?utm_source=chatgpt.com "Git - gitignore Documentation"))

---

# 九、检查项目结构

PowerShell 中执行：

```powershell
tree /F
```

应该看到类似：

```text
mini-rag-backend
│  .env
│  .gitignore
│  requirements.txt
│
└─app
    │  __init__.py
    │  config.py
    │  main.py
    │
    └─services
        │  __init__.py
        │  llm_service.py
```

`tree /F` 通常不会显示隐藏目录 `.venv`，这不代表它不存在。

可以执行：

```powershell
Get-ChildItem -Force
```

检查 `.venv` 和 `.env`。

---

# 十、启动 FastAPI 项目

确保：

1. 当前目录是 `mini-rag-backend`
    
2. 虚拟环境已经激活
    
3. 终端前有 `(.venv)`
    

执行：

```powershell
python -m uvicorn app.main:app --reload
```

正常输出类似：

```text
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete.
```

这个命令可以拆开理解：

```text
app.main:app
│   │     │
│   │     └── main.py 中的 app 对象
│   └──────── main.py 模块
└──────────── app 包
```

相当于：

```python
from app.main import app
```

`--reload` 表示开发时修改 Python 文件后，服务器自动重新加载。Uvicorn 的应用参数采用 `<模块>:<属性>` 的形式，默认运行在 `127.0.0.1:8000`。([Uvicorn](https://www.uvicorn.org/settings/?utm_source=chatgpt.com "Settings - Uvicorn"))

---

# 十一、访问接口

浏览器打开：

```text
http://127.0.0.1:8000
```

应该看到：

```json
{
  "message": "Mini RAG Backend is running"
}
```

再打开：

```text
http://127.0.0.1:8000/health
```

因为 `.env` 中还没有填写配置，所以应该看到：

```json
{
  "status": "ok",
  "llm_configured": false
}
```

打开自动生成的接口文档：

```text
http://127.0.0.1:8000/docs
```

这里可以直接点击接口，然后点击：

```text
Try it out → Execute
```

测试接口。FastAPI 默认提供 `/docs` 交互式文档和 `/redoc` 备用文档。([FastAPI](https://fastapi.tiangolo.com/tutorial/first-steps/?utm_source=chatgpt.com "First Steps - FastAPI"))

停止服务器：

```text
Ctrl + C
```

---

# 十二、初始化 Git

在项目根目录执行：

```powershell
git init
```

这个命令会在当前项目中创建一个 Git 仓库。([Git](https://git-scm.com/docs/git-init/2.21.0?utm_source=chatgpt.com "Git - git-init Documentation"))

检查文件状态：

```powershell
git status
```

重点确认下面两个内容没有出现在待提交文件中：

```text
.env
.venv/
```

进一步检查 `.env` 是否被忽略：

```powershell
git check-ignore -v .env
```

正常会显示 `.gitignore` 中匹配到的规则。

添加项目文件：

```powershell
git add .
```

再次检查：

```powershell
git status
```

正常应该看到类似：

```text
new file:   .gitignore
new file:   requirements.txt
new file:   app/__init__.py
new file:   app/config.py
new file:   app/main.py
new file:   app/services/__init__.py
new file:   app/services/llm_service.py
```

不应该看到：

```text
.env
.venv/
```

创建第一次提交：

```powershell
git commit -m "chore: initialize FastAPI project"
```

如果提示没有配置用户名和邮箱，可以执行：

```powershell
git config --global user.name "你的名字"
git config --global user.email "你的邮箱"
```

然后重新提交：

```powershell
git commit -m "chore: initialize FastAPI project"
```

查看提交记录：

```powershell
git log --oneline
```

---

# 十三、退出虚拟环境

完成学习后执行：

```powershell
deactivate
```

终端前面的：

```text
(.venv)
```

会消失。

退出虚拟环境不会删除它，只是让当前终端不再使用它。

---

# 十四、下次继续项目时怎么操作

下次不需要重新创建虚拟环境，也不需要重新安装依赖。

只需要：

```powershell
cd Desktop\mini-rag-backend
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload
```

如果你重新下载了项目，而项目中没有 `.venv`，才需要执行：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

---

# Day 1 完成检查

今天结束前，确保下面这些都能做到：

```text
[✓] 知道虚拟环境为什么存在
[✓] 能创建和激活 .venv
[✓] 知道 pip 把包装在哪里
[✓] 能用 pip freeze 生成 requirements.txt
[✓] 能创建 Python 包和模块
[✓] 能加载 .env 配置
[✓] 能启动 FastAPI
[✓] 能打开 /docs 测试接口
[✓] 知道 .env 为什么不能提交
[✓] 完成第一次 Git commit
```

最终启动命令是：

```powershell
python -m uvicorn app.main:app --reload
```

最终验证地址是：

```text
http://127.0.0.1:8000/docs
```
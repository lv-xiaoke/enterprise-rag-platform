# Day 25：用 Dockerfile 容器化 FastAPI RAG 后端

Day 24 已经让 `/rag/chat` 的每条来源同时返回文本、PDF 页码和相似度，最小 RAG 链路以及评估、来源解释都已经完成。按照月计划，今天进入 Docker 基础：不再增加 RAG 功能，而是把当前 FastAPI 项目放进一个可以重复构建和运行的容器镜像中。

当前电脑的 WSL 已经可用，但终端还无法识别 `docker` 命令；项目根目录中也没有 `Dockerfile` 和 `.dockerignore`。今天最终要创建这两个文件，理解镜像、容器和端口映射，并在 Docker Desktop 准备好后完成一次“构建镜像 → 启动容器 → 访问 `/health` → 上传 PDF”的验证。

[[使用docker的好处]]

---

# 一、先复习当前项目是怎样启动的

现在本机启动项目时使用：

```powershell
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload
```

这条命令依赖当前电脑已经具备：

```text
合适版本的 Python
已经安装 requirements.txt 中的依赖
项目源码
LLM 环境变量
能够运行程序的操作系统环境
```

如果把代码交给另一台电脑，对方还要重新准备这些内容。Docker 今天解决的核心问题是：把应用运行所需的基础环境、Python 依赖、代码和启动命令写成一份可重复执行的说明。

先尝试不看下面的答案，解释当前项目为什么不能只复制 `app/` 文件夹就直接在另一台电脑上运行。

可以从这几个方面回答：

```text
Python 版本可能不同
FastAPI、FAISS、PyTorch 等依赖可能没有安装
依赖版本可能不同
启动命令和监听地址可能不正确
LLM_API_KEY 等秘密配置不能写进代码
```

今天不修改 `app/` 中的业务代码，也不更新仍然停留在旧进度的 README。月计划 Day 26 会专门整理 README 和架构图。

---

# 二、理解镜像、容器和 Dockerfile

先把三个概念区分开。

## 1. Dockerfile：制作说明书

`Dockerfile` 是一个普通文本文件，里面按顺序写明：

```text
使用哪个基础 Python 环境
把哪些项目文件复制进去
安装哪些依赖
容器启动时运行什么命令
```

它本身不是正在运行的程序，可以把它理解成制作环境的配方。

## 2. 镜像：按照说明书做好的模板

执行：

```powershell
docker build -t mini-rag-backend:day25 .
```

Docker 会读取 `Dockerfile` 并生成镜像。镜像中包含 Python、依赖、项目代码和默认启动命令，可以把它理解成一个已经打包好的只读模板。

## 3. 容器：镜像的一次运行实例

执行 `docker run` 后，Docker 会根据镜像创建并启动容器：

```text
Dockerfile
→ docker build
→ 镜像
→ docker run
→ 正在运行的容器
```

同一个镜像可以启动多个容器，就像同一份安装包可以安装并运行多个独立实例。

Docker 官方的 [Dockerfile 概览](https://docs.docker.com/build/concepts/dockerfile/) 也把 `FROM`、`RUN`、`WORKDIR`、`COPY` 和 `CMD` 列为最常用的构建指令。今天只掌握当前项目真正需要的部分，不学习 Docker Compose、镜像仓库、Kubernetes 或多阶段构建。

---

# 三、先准备 Windows 上的 Docker 环境

在项目根目录执行：

```powershell
docker --version
```

当前电脑会提示无法识别 `docker`，说明 Docker Desktop 还没有安装，或者安装后尚未启动。

再检查 WSL：

```powershell
wsl --version
```

当前已经能输出 WSL 版本，并且版本高于 Docker Desktop 官方要求的 WSL 2.1.5，因此不需要重复执行 `wsl --install`。

按照 [Docker Desktop for Windows 官方安装说明](https://docs.docker.com/desktop/setup/install/windows-install/) 下载并安装 Docker Desktop：

```text
1. 使用默认推荐的 per-user 安装方式
2. 使用 WSL 2 backend
3. 安装完成后从开始菜单启动 Docker Desktop
4. 等待界面显示 Docker Engine 已经运行
5. 重新打开一个 PowerShell 终端
```

重新验证：

```powershell
docker --version
docker info
```

预期结果：

```text
docker --version 能输出版本号
docker info 能显示 Client 和 Server 信息
```

如果 `docker --version` 成功而 `docker info` 提示无法连接 daemon，通常是 Docker Desktop 还没有完全启动。先打开 Docker Desktop 并等待引擎就绪，不要反复重装。

Docker Desktop 的安装、首次启动或系统重启可能占用较长时间。如果今天的一小时内还没有完成环境准备，仍然继续写完下面的 `Dockerfile` 和 `.dockerignore`，把安装状态记录在文末；但不要把尚未执行的镜像构建和容器测试提前勾选为完成。

---

# 四、创建 `.dockerignore`

在项目根目录新建：

```text
.dockerignore
```

写入：

```dockerignore
# 本地 Python 环境和缓存
.venv/
__pycache__/
*.py[cod]
.pytest_cache/

# 密钥和本地配置
.env

# Git、编辑器和系统文件
.git/
.gitignore
.vscode/
.idea/
.DS_Store
Thumbs.db

# 当前镜像运行不需要的学习资料和本地数据
docs/
scripts/
data/
README.md
```

执行：

```powershell
Get-Content .dockerignore
```

重点确认其中包含：

```text
.env
.venv/
.git/
data/
```

`.dockerignore` 和 `.gitignore` 的作用对象不同：

```text
.gitignore
→ 告诉 Git 哪些文件不要进入版本提交

.dockerignore
→ 告诉 Docker 哪些文件不要进入镜像构建上下文
```

构建命令末尾的点：

```powershell
docker build -t mini-rag-backend .
```

表示把当前目录作为 build context。-t mini-rag-backend 表示给构建出来的镜像起名字为 mini-rag-backend 

Docker 构建时只能使用上下文中的文件；`.dockerignore` 会先排除不需要发送给构建器的内容。这样能减少构建数据，也能避免 `.env`、本地数据库、PDF、虚拟环境和 Git 历史意外进入构建过程。

注意：`.dockerignore` 只是额外保护。接下来 `Dockerfile` 还会使用明确的 `COPY requirements.txt` 和 `COPY app`，而不是无条件把项目中所有内容都复制进镜像。

---

# 五、创建适合当前项目的 `Dockerfile`

在项目根目录新建一个没有扩展名的文件：

```text
Dockerfile
```

写入：

```dockerfile
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt

COPY app ./app

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

先不要急着构建，逐段理解每条指令。

## 1. `FROM`

```dockerfile
FROM python:3.11-slim
```

表示以带有 Python 3.11 的轻量 Linux 镜像为基础。当前项目此前已经在 Python 3.11 环境中运行，代码也使用了 `list[str]`、`str | Path` 等现代类型语法。

这里使用 Linux 容器，不是把本机 Windows 目录原样复制成一个 Windows 虚拟机。

## 2. `ENV`

```dockerfile
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
```

第一行避免在容器中生成不必要的 `.pyc` 文件；第二行让 Python 日志及时输出到 Docker 终端，方便看到 Uvicorn 的启动和报错信息。

这里没有写入：

```text
LLM_API_KEY
LLM_BASE_URL
LLM_MODEL
```

因为真实配置不应该固化进镜像，运行容器时再从本机 `.env` 注入。

## 3. `WORKDIR`

```dockerfile
WORKDIR /app
```

把容器内后续命令的工作目录设为 `/app`。复制完成后的结构会类似：

```text
/app/
├── requirements.txt
└── app/
    ├── main.py
    └── services/
```

这样 Python 能从 `/app` 找到 `app.main` 包。

## 4. 安装 `libgomp1`

```dockerfile
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*
```

当前项目使用 FAISS、NumPy、PyTorch 和 Sentence Transformers。`python:3.11-slim` 刻意省略了很多 Linux 系统库，`libgomp1` 为这类科学计算依赖提供常用的 OpenMP 运行库。

最后删除 apt 的软件包列表，是为了不把安装阶段的缓存留在最终镜像层中。

## 5. 先复制并安装依赖

```dockerfile
COPY requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt
```

先只复制变化较少的 `requirements.txt`，再安装依赖。以后只修改 `app/` 代码而依赖文件没变时，Docker 有机会复用已经安装依赖的缓存层，不必每次重新安装 PyTorch、FAISS 等较大的包。

`--no-cache-dir` 表示 pip 不在镜像中保留下载缓存，但安装好的包仍然存在。

## 6. 再复制业务代码

```dockerfile
COPY app ./app
```

今天的运行镜像只需要业务代码和依赖，不需要复制：

```text
.env
.venv
docs
scripts
data/evaluation
本地 sample.pdf
```

应用启动时，`app/database.py` 会在容器内创建 `/app/data/chat.db`。它属于当前容器的运行数据；今天不学习 volume，因此删除容器后聊天记录也会消失。

## 7. `EXPOSE` 与端口映射

```dockerfile
EXPOSE 8000
```

它是在镜像中说明应用预计监听 8000 端口，并不会自动让本机访问这个端口。Docker 官方 [Dockerfile reference](https://docs.docker.com/reference/dockerfile#expose) 明确说明，真正发布端口仍然要在 `docker run` 时使用 `-p`。

## 8. `CMD`

```dockerfile
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

`CMD` 是容器启动时默认运行的命令。这里没有使用本地开发时的 `--reload`，因为容器中运行的是已经构建好的代码，不需要监听源码修改。

`--host 0.0.0.0` 很重要。容器有自己的网络空间，如果 Uvicorn 只监听容器内部的 `127.0.0.1`，即使设置了端口映射，宿主机也可能无法访问。监听 `0.0.0.0` 表示接收容器所有网络接口上的连接。

---

# 六、构建 Docker 镜像

确认 Docker Desktop 已经运行，然后在项目根目录执行：

```powershell
docker build -t mini-rag-backend:day25 .
```

这条命令可以拆成：

```text
docker build
→ 根据 Dockerfile 构建镜像

-t mini-rag-backend:day25
→ 给镜像设置名称 mini-rag-backend 和标签 day25

.
→ 使用当前项目根目录作为 build context
```

当前 `requirements.txt` 包含 PyTorch、Transformers、Sentence Transformers 和 FAISS，第一次下载基础镜像与依赖可能较慢，镜像也会比较大。终端持续显示下载和安装日志时，先等待其完成，不要同时重复执行第二次构建。

构建成功后检查：

```powershell
docker image ls mini-rag-backend
```

预期能够看到：

```text
REPOSITORY          TAG
mini-rag-backend    day25
```

如果构建在：

```dockerfile
RUN python -m pip install ...
```

这一步失败，先阅读错误中指出的具体包和网络原因，不要立即删除 `requirements.txt` 中的依赖。当前 FastAPI 应用导入时就需要 Sentence Transformers 和 FAISS，随意删包可能让镜像虽然构建成功，却无法启动真实项目。

如果出现：

```text
no space left on device
```

说明 Docker Desktop 的镜像磁盘空间不足。今天先记录错误，不要在不了解目标的情况下批量清理所有镜像或 Docker 数据。

---

# 七、启动容器并理解端口和环境变量

构建成功后，使用终端 A 运行容器：

```powershell
docker run `
    --name mini-rag-day25 `
    --rm `
    -p 127.0.0.1:8000:8000 `
    --env-file .env `
    mini-rag-backend:day25
```

逐项理解：

```text
--name mini-rag-day25
→ 给容器一个容易识别的名称

--rm
→ 容器停止后自动删除这个容器实例，但不会删除镜像

-p 127.0.0.1:8000:8000
→ 把本机 127.0.0.1:8000 映射到容器的 8000 端口

--env-file .env
→ 运行时把本机 .env 中的配置注入容器环境

mini-rag-backend:day25
→ 使用刚才构建的镜像
```

端口顺序可以记成：

```text
-p 本机地址:本机端口:容器端口
```

这里把端口只绑定到本机 `127.0.0.1`，适合今天的本地学习测试。[Docker 容器运行文档](https://docs.docker.com/engine/containers/run/#published-ports) 中的 `-p` 也表示显式发布并映射容器端口。

`.env` 没有被复制进镜像；`--env-file` 只是在运行时向容器传入配置。不要执行会打印全部容器环境变量的命令，也不要把 `.env` 加入 Git。

第一次启动时，`EmbeddingService()` 会加载 `BAAI/bge-small-zh-v1.5`。如果镜像中还没有 Hugging Face 模型缓存，容器会先下载模型，因此看到 `Application startup complete` 前可能需要等待。今天不额外引入模型缓存 volume 或在镜像构建阶段预下载模型。

预期终端 A 最终出现：

```text
Application startup complete
Uvicorn running on http://0.0.0.0:8000
```

保持终端 A 不要关闭，再打开终端 B。

---

# 八、验证容器中的 FastAPI 和 RAG 依赖

## 1. 查看正在运行的容器

在终端 B 执行：

```powershell
docker ps
```

预期能看到名为：

```text
mini-rag-day25
```

的运行中容器，以及 `8000` 端口映射。

## 2. 测试根接口和健康接口

执行：

```powershell
Invoke-RestMethod `
    -Uri "http://127.0.0.1:8000/" `
    -Method Get
```

预期返回：

```text
message
-------
Mini RAG Backend is running
```

再执行：

```powershell
Invoke-RestMethod `
    -Uri "http://127.0.0.1:8000/health" `
    -Method Get
```

如果本机 `.env` 中三项 LLM 配置完整，预期得到：

```text
status = ok
llm_configured = True
```

如果 `status` 正常而 `llm_configured=False`，说明 FastAPI 容器已经运行，但模型配置没有正确注入。先检查启动命令是否包含：

```powershell
--env-file .env
```

不要通过打印 `.env` 或容器全部环境变量来排查真实密钥。

浏览器还可以访问：

```text
http://127.0.0.1:8000/docs
```

确认 Swagger 中仍然存在：

```text
POST /upload
POST /rag/chat
GET  /health
POST /chat
GET  /history
```

## 3. 上传 PDF，验证容器内的解析、Embedding 和 FAISS

本机的 `sample.pdf` 没有复制到镜像，但可以像普通客户端一样通过 HTTP 上传给容器：

```powershell
curl.exe `
    -X POST `
    -F "file=@data/documents/sample.pdf;type=application/pdf" `
    "http://127.0.0.1:8000/upload"
```

预期返回类似：

```json
{
  "filename": "sample.pdf",
  "page_count": 3,
  "chunk_count": 10
}
```

`chunk_count` 以实际返回为准，但必须大于 0。这个测试不调用 LLM，不消耗模型 API 额度，却能验证容器内的这些依赖已经正常工作：

```text
pypdf
Sentence Transformers
PyTorch
FAISS
```

今天不需要再调用 `/rag/chat`。Docker 的学习重点是构建和运行环境，Day 24 已经验证过 RAG 回答与来源结构。

---

# 九、停止容器并观察容器的临时状态

测试完成后回到终端 A，按：

```text
Ctrl + C
```

由于启动时使用了：

```text
--rm
```

容器停止后会自动删除。执行：

```powershell
docker ps -a --filter "name=mini-rag-day25"
```

正常情况下不会看到这个容器。

再执行：

```powershell
docker image ls mini-rag-backend
```

镜像仍然存在。这说明：

```text
容器
→ 一次运行实例，已经删除

镜像
→ 启动容器使用的模板，仍然保留
```

容器运行期间产生的 `/app/data/chat.db` 和上传后建立的内存 FAISS 索引也会随容器消失。今天只理解这个限制，不增加 volume、Compose 或索引持久化。

---

# 十、检查改动并提交 Git

执行：

```powershell
git status --short
git diff -- Dockerfile .dockerignore docs/Day25.md
```

因为 `Dockerfile` 和 `.dockerignore` 是新文件，普通 `git diff` 可能暂时不显示它们的内容，可以直接在 VS Code 中复查，或者执行：

```powershell
Get-Content Dockerfile
Get-Content .dockerignore
```

确认：

```text
Dockerfile 使用 Python 3.11 并安装 requirements.txt
Uvicorn 监听 0.0.0.0:8000
容器启动命令没有使用 --reload
.dockerignore 排除了 .env、.venv、.git 和 data
Dockerfile 中没有 API Key、Base URL 或模型名称等真实秘密
今天没有修改 app、requirements.txt、评估结果或 README
容器中的 /health 和 /upload 已按实际情况完成验证
```

测试成功后添加：

```powershell
git add Dockerfile .dockerignore docs/Day25.md
git diff --cached --stat
git status
```

再次确认 `.env`、本地 PDF、数据库和模型缓存没有进入暂存区，然后提交：

```powershell
git commit -m "build: containerize FastAPI application"
```

最后查看：

```powershell
git log -1 --oneline
git status --short
```

尝试不看笔记讲清楚：Dockerfile、镜像和容器分别是什么；为什么要先复制 `requirements.txt` 再复制业务代码；为什么 Uvicorn 在容器中监听 `0.0.0.0`；`EXPOSE 8000` 和 `-p 127.0.0.1:8000:8000` 有什么区别；以及为什么 `.env` 应在运行时注入，而不能写进镜像。

---

# Day 25 完成标准

- [ ] 能解释 Dockerfile、镜像和容器三者的关系
- [ ] 已安装并启动 Docker Desktop，`docker version` 和 `docker info` 能正常执行
- [ ] 能解释 build context 与 `.dockerignore` 的作用
- [ ] 已创建 `.dockerignore`，并排除 `.env`、`.venv`、`.git` 和本地数据
- [ ] 已创建项目根目录下的 `Dockerfile`
- [ ] 能解释 `FROM`、`WORKDIR`、`RUN`、`COPY`、`EXPOSE` 和 `CMD` 的作用
- [ ] 已使用 `python:3.11-slim`、安装 `libgomp1` 和 `requirements.txt` 中的 Python 依赖
- [ ] Uvicorn 会在容器内监听 `0.0.0.0:8000`，并且没有使用 `--reload`
- [ ] 已成功构建 `mini-rag-backend:day25` 镜像
- [ ] 已使用 `--env-file .env` 在运行时注入配置，没有把 `.env` 复制进镜像
- [ ] 已理解 `EXPOSE` 只说明端口，而 `-p` 才真正进行宿主机与容器端口映射
- [ ] 容器中的 `/` 和 `/health` 能正常返回结果
- [ ] 已通过 `/upload` 验证容器内的 PDF、Embedding 和 FAISS 依赖可以工作
- [ ] 能说明当前 SQLite、模型缓存和内存 FAISS 状态为什么会随临时容器消失
- [ ] 已确认今天没有引入 Docker Compose、volume、镜像仓库或其他部署工具
- [ ] 测试成功后完成 Git 提交，并确认工作区干净

实际完成：已完成

遇到的卡点：暂无

Git commit：已提交

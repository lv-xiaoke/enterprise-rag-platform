# 0 元试用服务器：SSH 私有演示

适用：Ubuntu 24.04 LTS x86_64、单人演示。2GB 内存先实测，采用 CPU 依赖、单生成并发、2MB 上传上限和受限容器内存；需要时增加约 2GB swap，不覆盖已有 swap 文件。

此配置没有公网 Web 入口：数据库/API 不发布端口，Web 只监听服务器 `127.0.0.1:8080`。浏览器通过 SSH 隧道访问，远程链路加密。本轮不买域名，不产生自动续费，不将私有演示描述为公开上线。

## 1. 准备连接

在云端网页终端检查：

```bash
whoami
free -h
df -h /
swapon --show
sudo -n true
command -v docker
```

当前服务器 `162.14.71.180`，用户 `ubuntu`。本机使用独立配置，不修改全局 SSH 设置：

```powershell
ssh -F "$env:USERPROFILE/.ssh/enterprise_rag_demo.config" rag-demo
```

服务器 ED25519 指纹已通过腾讯云 TAT 核对：`SHA256:i5Mg1znvLINjRepcrFVkwP7z/689sy4nOL2Nkh0dirw`。私钥只留在本机，不提交、不上传。安全组建议仅允许本机公网 IP 访问 SSH 端口；不需要开放 80、443、8000、8080、5432。

## 2. 本机准备文件

在项目根目录执行；`init` 从现有 `.env` 读取三项模型配置并生成独立数据库密码，拒绝覆盖已有文件。

```powershell
.\.venv\Scripts\python.exe scripts/cloud_deploy.py init
.\.venv\Scripts\python.exe scripts/cloud_deploy.py validate
.\.venv\Scripts\python.exe scripts/package_cloud.py source --output artifacts/fullstack/cloud/source.tar.gz
.\.venv\Scripts\python.exe scripts/package_cloud.py model --output artifacts/fullstack/cloud/bge-cache.tar.gz
```

源码包不含 `.env`、用户数据、Git 或本地依赖；模型包只含指定 BGE 缓存。`.env.cloud` 含密钥，只单独传输到已确认的本人服务器，禁止提交 Git。已有打包文件不覆盖，可以选新的明确输出文件名。

## 3. 云端部署

先验证 SSH 主机指纹，再传输源码、模型包和私有环境文件。源码解压到新的独立发布目录；模型包放在发布目录外；环境文件放为发布目录的 `.env.cloud` 并设权限 600。安装 Docker Engine/Compose 的步骤以 [Ubuntu 官方安装说明](https://docs.docker.com/engine/install/ubuntu/) 为准。

在发布目录按顺序执行；Docker 权限不足时使用 sudo，不把环境文件内容打印到终端。

```bash
python3 scripts/cloud_deploy.py validate
python3 scripts/cloud_deploy.py build
python3 scripts/cloud_deploy.py seed-model --archive ../bge-cache.tar.gz
python3 scripts/cloud_deploy.py up
python3 scripts/cloud_deploy.py status
```

CPU 镜像的真实体积、内存占用、首次模型加载和网络可达性必须在实际构建/运行后记录。构建失败不能沿用旧镜像冒充成功。默认固定 Compose 项目 `rag-cloud-demo`，更换发布目录不会换数据库卷。

腾讯云实例拉取 Docker Hub 超时时，可按[官方说明](https://cloud.tencent.com/document/product/213/8623)在 Docker 的 `registry-mirrors` 中添加 `https://mirror.ccs.tencentyun.com`；该入口仅供腾讯云内网使用。保留已有 daemon 配置后重启 Docker。云端 Compose 为 Debian 和普通 Python 软件包配置腾讯镜像，已逐项核对锁定版本可用；普通 Dockerfile 默认仍使用原源，CPU PyTorch 始终使用官方源。CPU wheel 单独成层，其余依赖安装后运行 `pip check` 并检查 CUDA 不存在。

## 4. 浏览器验收

在本机终端使用实际 SSH 主机别名运行：

```powershell
ssh -F "$env:USERPROFILE/.ssh/enterprise_rag_demo.config" -N -L 127.0.0.1:18080:127.0.0.1:8080 -o ExitOnForwardFailure=yes rag-demo
```

打开 `http://127.0.0.1:18080`，验证注册、仓库虚构 PDF 入库、问答、来源、刷新、退出和错误请求 ID。只对已授权的虚构资料调用外部模型。重启 API/Web 后核对数据仍保留；观察容器内存、swap 和错误日志。

## 5. 备份与更新

```bash
python3 scripts/cloud_deploy.py backup
python3 scripts/cloud_deploy.py restore --archive backups/实际备份文件.dump --database rag_restore_probe
```

备份通过二进制管道写 custom dump；恢复始终创建新的 `rag_restore_*` 数据库，已有名称或业务库会被拒绝。恢复后还需核对用户/文档/消息行数与向量维度，不能仅以命令退出 0 宣称完整恢复。备份含用户数据，须安全下载保存，试用到期前留副本。

更新时使用新发布目录和唯一 `RELEASE_TAG`，沿用原 `.env.cloud` 的数据库凭据与项目名。仅在数据库 schema 与旧代码兼容时回到旧镜像；不自动 downgrade、不覆盖业务库。云端验收完成后，再重建本地 Docker；禁止 `down -v` 和批量删除。

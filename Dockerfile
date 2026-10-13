FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

ARG DEBIAN_MIRROR
RUN if [ -n "$DEBIAN_MIRROR" ]; then \
      python -c "import os,pathlib; p=pathlib.Path('/etc/apt/sources.list.d/debian.sources'); p.write_text(p.read_text().replace('http://deb.debian.org',os.environ['DEBIAN_MIRROR'].rstrip('/')))"; \
    fi \
    && apt-get update \
    && apt-get install -y --no-install-recommends libgomp1

COPY requirements.txt ./
ARG TORCH_VERSION=2.13.0
RUN python -m pip install --no-deps --index-url https://download.pytorch.org/whl/cpu "torch==${TORCH_VERSION}+cpu"
ARG PIP_INDEX_URL=https://pypi.org/simple
RUN python -m pip install -r requirements.txt \
    && python -m pip check \
    && python -c "import torch; assert torch.version.cuda is None, 'CPU-only image required'"

COPY alembic.ini ./
COPY migrations ./migrations
COPY app ./app
COPY scripts/assign_legacy_knowledge_bases.py ./scripts/assign_legacy_knowledge_bases.py

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

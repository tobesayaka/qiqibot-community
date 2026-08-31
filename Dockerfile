FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# 先复制依赖声明，利用 Docker 层缓存
COPY pyproject.toml uv.lock ./

# 安装运行时依赖（--frozen 不更新 lock，--no-dev 跳过 dev/scripts 依赖）
RUN uv sync --frozen --no-dev

COPY bot.py ./
COPY plugins/ plugins/
COPY middlewares/ middlewares/
COPY utils/ utils/
COPY assets/ assets/

RUN mkdir -p data downloads config

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

CMD ["python", "bot.py"]

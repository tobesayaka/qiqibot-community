FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml bot.py ./
COPY plugins/ plugins/
COPY middlewares/ middlewares/
COPY utils/ utils/

RUN uv venv .venv && \
    uv pip install --python .venv/bin/python \
    aiosqlite greenlet httpx \
    "nonebot-adapter-onebot>=2.4.6" \
    "nonebot-plugin-localstore>=0.7.4" \
    "nonebot2[fastapi]>=2.5.0,<3.0.0" \
    "sqlalchemy>=2.0.52" \
    uvicorn \
    yt-dlp

RUN mkdir -p data downloads

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

CMD ["python", "bot.py"]

FROM pyd4vinci/scrapling

# scrapling의 실제 의존성(lxml 등)은 시스템 pip가 아니라 uv가 관리하는 /app/.venv에 있음 — 같은 venv에 맞춰 설치
RUN uv pip install --python /app/.venv/bin/python3 discord.py python-dotenv

COPY bot.py config.py db.py scheduler.py ./
COPY crawlers ./crawlers

ENTRYPOINT []
CMD ["uv", "run", "python3", "bot.py"]

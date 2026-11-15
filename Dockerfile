FROM python:3.11-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt && useradd --create-home --uid 10001 appuser
COPY yield-data-service/app /app/app
COPY yield-data-service/scripts /app/scripts
COPY yield-telegram-bot/bot /app/bot
COPY yield-telegram-bot/alembic /app/alembic
COPY yield-telegram-bot/alembic.ini /app/alembic.ini
COPY scripts/init_database.py scripts/create_admin.py /app/scripts/
COPY demo /app/demo
COPY VERSION /app/VERSION
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN mkdir -p /app/logs && chown -R appuser:appuser /app && chmod +x /docker-entrypoint.sh
USER appuser
EXPOSE 8000
CMD ["/docker-entrypoint.sh"]

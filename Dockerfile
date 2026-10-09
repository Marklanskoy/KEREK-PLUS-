FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 KEREK_MODE=demo KEREK_DB=/data/kerek.sqlite3
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt && useradd --create-home --uid 10001 kerek
COPY server ./server
COPY public ./public
RUN mkdir -p /data /app/public/assets/uploads && chown -R kerek:kerek /data /app/public/assets/uploads
USER kerek
EXPOSE 8000
CMD ["python","-m","uvicorn","server.app:app","--host","0.0.0.0","--port","8000"]

FROM node:20-bookworm-slim AS cli

RUN npm config set fetch-retries 5 \
    && npm config set fetch-retry-factor 2 \
    && npm config set fetch-retry-mintimeout 2000 \
    && npm config set fetch-retry-maxtimeout 120000 \
    && npm install -g @openai/codex @google/gemini-cli


FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONUTF8=1
ENV PYTHONIOENCODING=UTF-8
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8

RUN apt-get update \
    && apt-get install -y --no-install-recommends git gh ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY --from=cli /usr/local/bin/node /usr/local/bin/node
COPY --from=cli /usr/local/bin/npm /usr/local/bin/npm
COPY --from=cli /usr/local/bin/npx /usr/local/bin/npx
COPY --from=cli /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -sf ../lib/node_modules/@openai/codex/bin/codex.js /usr/local/bin/codex \
    && ln -sf ../lib/node_modules/@google/gemini-cli/dist/index.js /usr/local/bin/gemini

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY templates ./templates
COPY static ./static
COPY data ./data
COPY docs ./docs
COPY scripts ./scripts
COPY mvp ./mvp

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

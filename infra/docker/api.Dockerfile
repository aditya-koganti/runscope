FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app
COPY pyproject.toml README.md ./
COPY services/api ./services/api
COPY services/worker ./services/worker
COPY services/scheduler ./services/scheduler
COPY packages/contracts ./packages/contracts

FROM runtime AS development
RUN pip install -e ".[dev]"

FROM runtime AS production
RUN pip install .
RUN groupadd --system --gid 10001 runscope \
    && useradd --system --uid 10001 --gid runscope --no-create-home runscope
USER runscope

EXPOSE 8000
CMD ["uvicorn", "runscope_api.main:app", "--host", "0.0.0.0", "--port", "8000"]

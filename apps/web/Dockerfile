FROM python:3.12-slim-bookworm
ARG BUNDLE_JAVA=false
LABEL org.opencontainers.image.title="DRACula" \
      org.opencontainers.image.version="0.1.1" \
      org.opencontainers.image.licenses="Apache-2.0" \
      org.opencontainers.image.source="https://github.com/Greaper88/DRACula" \
      org.opencontainers.image.description="DRAC 5 and IPMI management with confirmed actions and isolated legacy KVM"
RUN dpkg --add-architecture i386 && apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates ipmitool xvfb xauth fonts-dejavu-core \
    libc6:i386 libstdc++6:i386 libx11-6:i386 libxext6:i386 libxrender1:i386 \
    libxtst6:i386 libxi6:i386 libfreetype6:i386 libfontconfig1:i386 libasound2:i386 \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY apps/web/requirements.txt /app/apps/web/requirements.txt
RUN pip install --no-cache-dir -r apps/web/requirements.txt
COPY src /app/src
COPY launcher /app/launcher
COPY apps/web/static /app/apps/web/static
COPY LICENSE NOTICE THIRD_PARTY_NOTICES.md /usr/share/doc/dracula/
COPY apps/web/THIRD_PARTY.md /usr/share/doc/dracula/RUNTIME_NOTICES.md
ENV PYTHONPATH=/app/src PYTHONUNBUFFERED=1 DRACULA_DATA=/data DRACULA_KEYS=/keys HOME=/tmp
RUN useradd --uid 1000 --create-home app && mkdir -p /app/.local /data /keys \
    && if [ "$BUNDLE_JAVA" = true ]; then python3 -c 'from dracula.launcher import CACHE,setup_java; CACHE.mkdir(exist_ok=True); setup_java()'; fi \
    && rm -f /app/.local/java32.tar.gz \
    && chown -R app:app /app/.local /data /keys
USER app
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=180s CMD python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/healthz',timeout=3)"
CMD ["python3","-m","dracula.web_start"]

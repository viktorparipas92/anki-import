# Anki Desktop with KasmVNC, from chrislongros/anki-desktop-docker.
#
# Rebuilt on Ubuntu noble rather than upstream's Debian bookworm: Anki pins
# pyqt6-qt6 >= 6.8.1, whose only aarch64 wheels are manylinux_2_39, and bookworm
# ships glibc 2.36. Noble has 2.39, so the launcher can install Anki on ARM.
FROM ghcr.io/linuxserver/baseimage-kasmvnc:ubuntunoble

ARG ANKI_LAUNCHER_VERSION="25.09"

ENV TITLE="Anki" \
    CUSTOM_PORT=3000 \
    CUSTOM_HTTPS_PORT=3001 \
    START_DOCKER=false \
    PUID=1000 \
    PGID=1000 \
    ANKI_LAUNCHER_VERSION=${ANKI_LAUNCHER_VERSION}

RUN \
    echo "**** install dependencies ****" && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        python3-venv \
        python3-xdg \
        libxcb-xinerama0 \
        libxcb-cursor0 \
        libxcb-icccm4 \
        libxcb-image0 \
        libxcb-keysyms1 \
        libxcb-render-util0 \
        libxcb-shape0 \
        libnss3 \
        libxcomposite1 \
        libxdamage1 \
        libxrandr2 \
        libgbm1 \
        libasound2t64 \
        libpango-1.0-0 \
        libpangocairo-1.0-0 \
        libatk1.0-0 \
        libatk-bridge2.0-0 \
        libcups2 \
        libdrm2 \
        libgtk-3-0 \
        libegl1 \
        libgl1 \
        libxkbcommon0 \
        libxkbcommon-x11-0 \
        libatomic1 \
        # Qt WebEngine links these dynamically; bookworm's base had them, noble's
        # does not.
        libevent-2.1-7t64 \
        libminizip1t64 \
        libjsoncpp25 \
        libnspr4 \
        libxss1 \
        libopus0 \
        libvpx9 \
        libwebpdemux2 \
        libxslt1.1 \
        libpulse0 \
        libxtst6 \
        libgles2 \
        libsnappy1v5 \
        libavif16 \
        zstd \
        xdg-utils \
        curl \
        ca-certificates \
        fonts-liberation \
        fonts-noto \
        fonts-noto-color-emoji \
    && \
    echo "**** download Anki launcher ${ANKI_LAUNCHER_VERSION} to staging ****" && \
    mkdir -p /opt/anki-launcher-staging && \
    curl -fLo /tmp/anki-launcher.tar.zst \
        "https://github.com/ankitects/anki/releases/download/${ANKI_LAUNCHER_VERSION}/anki-launcher-${ANKI_LAUNCHER_VERSION}-linux.tar.zst" && \
    cd /tmp && \
    tar --use-compress-program=unzstd -xf anki-launcher.tar.zst && \
    cp -a anki-launcher-${ANKI_LAUNCHER_VERSION}-linux/. /opt/anki-launcher-staging/ && \
    chmod +x /opt/anki-launcher-staging/anki && \
    echo "${ANKI_LAUNCHER_VERSION}" > /opt/anki-launcher-staging/version.txt && \
    echo "**** cleanup ****" && \
    rm -rf /tmp/anki* && \
    apt-get remove -y zstd && \
    apt-get autoremove -y && \
    apt-get clean && \
    rm -rf \
        /var/lib/apt/lists/* \
        /var/tmp/* \
        /tmp/*

COPY root/ /

EXPOSE 3000 3001 8765

HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=3 \
    CMD curl -sf http://localhost:3000/ || exit 1

VOLUME /config

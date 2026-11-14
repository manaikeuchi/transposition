FROM ubuntu:22.04

ARG AUDIVERIS_VERSION=5.11.0
ARG AUDIVERIS_DEB=Audiveris-${AUDIVERIS_VERSION}-ubuntu22.04-x86_64.deb

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      curl ca-certificates \
      libxext6 libxrender1 libxi6 libxtst6 libasound2 fontconfig fonts-dejavu-core libgtk-3-0 && \
    curl -L -o /tmp/audiveris.deb \
      "https://github.com/Audiveris/audiveris/releases/download/${AUDIVERIS_VERSION}/${AUDIVERIS_DEB}" && \
    dpkg-deb -x /tmp/audiveris.deb /tmp/audiveris_extract && \
    mv /tmp/audiveris_extract/opt/audiveris /opt/audiveris && \
    rm -rf /tmp/audiveris.deb /tmp/audiveris_extract && \
    apt-get purge -y curl && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /data
ENTRYPOINT ["/opt/audiveris/bin/Audiveris", "-batch"]

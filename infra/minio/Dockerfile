FROM golang:1.24.2-bookworm AS build
ARG MINIO_RELEASE=RELEASE.2025-04-22T22-12-26Z
WORKDIR /src
RUN git clone --depth 1 --branch ${MINIO_RELEASE} https://github.com/minio/minio.git .
RUN CGO_ENABLED=0 go build -trimpath -o /out/minio .

FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*
COPY --from=build /out/minio /usr/local/bin/minio
ENTRYPOINT ["minio"]

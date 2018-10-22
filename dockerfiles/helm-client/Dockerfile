ARG HELM_VERSION=v2.12.0
FROM debian:sid-slim

ARG HELM_VERSION

RUN apt-get update \
    && apt-get install -y \
        curl \
        bash \
    && curl -o helm.tar.gz https://storage.googleapis.com/kubernetes-helm/helm-${HELM_VERSION}-linux-amd64.tar.gz \
    && mkdir -p helm \
    && tar zxvf helm.tar.gz -C helm \
    && cp helm/linux-amd64/helm /usr/local/bin \
    && chmod +x /usr/local/bin/helm \
    && rm -rf helm*

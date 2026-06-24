#!/bin/sh
# Reference file — NOT sourced at runtime.
#
# Reconciler delivery is auto-upgrading. The write-heat-params scripts no longer
# pin a version: they pass RECONCILER_VERSION / RECONCILER_BINARY_URL through
# (empty by default). On every run the launcher
# (install-reconciler-launcher.sh) resolves the latest published release, and:
#
#   - downloads + installs it when it differs from what is installed,
#   - verifies the SHA256 (from RECONCILER_BINARY_URL_SHA256 if set, else the
#     <binary>.sha256 sidecar in the release),
#   - silently falls back to the currently-installed binary on any failure
#     (latest-resolution, download, or checksum mismatch).
#
# Pinning: set RECONCILER_VERSION (or RECONCILER_BINARY_URL) via a cluster label
# to lock an exact build and disable auto-upgrade. e2e uses RECONCILER_BINARY_URL
# to inject a locally-built binary.
#
# The last-resort fallback version (used only when nothing is installed AND the
# latest release cannot be resolved) is hardcoded as `fallback_version` inside
# install-reconciler-launcher.sh.
#
# Current values:
RECONCILER_DEFAULT_REPOSITORY="https://github.com/ventus-ag/magnum-bootstrap"

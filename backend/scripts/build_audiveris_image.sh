#!/usr/bin/env bash
# Builds the audiveris-omr Docker image used by the backend for OMR.
# Run once per machine (or whenever docker/audiveris/Dockerfile changes).
set -euo pipefail
cd "$(dirname "$0")/../docker/audiveris"
docker build -t audiveris-omr:5.11.0 .

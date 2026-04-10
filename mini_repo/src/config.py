"""Static service configuration and deploy markers (no secrets)."""

from __future__ import annotations

SERVICE_NAME = "reminder-svc"
DEPLOY_IMAGE_TAG = "reminder-svc_0.4.2_sha441"
API_VERSION = "v1"
DEFAULT_CADENCE_HOURS = 24
FEATURE_SHADOW_PARSE = False
# Mirrors deploy tag suffix in sample logs (forensic correlation only).
GIT_REVISION_SHORT = "sha441"

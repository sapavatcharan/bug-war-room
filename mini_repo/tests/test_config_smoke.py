"""Deploy marker and defaults stay stable for log correlation tests."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import config


def test_deploy_image_tag_format():
    assert "0.4.2" in config.DEPLOY_IMAGE_TAG
    assert config.SERVICE_NAME == "reminder-svc"

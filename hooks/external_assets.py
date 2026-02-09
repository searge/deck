"""MkDocs hook: include assets/ from project root into the build.

The assets/ directory lives outside docs_dir (core/) so MkDocs
doesn't see it by default. This hook copies it into the built
site so that relative paths like ../../assets/image.png resolve.
"""

import shutil
from pathlib import Path


def on_post_build(config: dict) -> None:
    project_root = Path(config["docs_dir"]).parent
    assets_src = project_root / "assets"
    assets_dest = Path(config["site_dir"]) / "assets"

    if assets_src.is_dir():
        shutil.copytree(assets_src, assets_dest, dirs_exist_ok=True)

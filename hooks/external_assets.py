"""MkDocs hook: include assets/ from project root into the build.

The assets/ directory lives outside docs_dir (core/) so MkDocs
doesn't see it by default. This hook:
1. Registers asset files in the MkDocs file collection
2. Adjusts relative paths in markdown during build

Obsidian vault root is the project root (one level above docs_dir).
So Obsidian paths have one extra ../ that MkDocs doesn't need.
Example: ../../assets/img.png (Obsidian) → ../assets/img.png (MkDocs)
"""

import re
from pathlib import Path

from mkdocs.structure.files import File, Files


def on_files(files: Files, config: dict) -> Files:
    """Add assets/ to the MkDocs file collection."""
    project_root = Path(config["docs_dir"]).parent
    assets_dir = project_root / "assets"

    if not assets_dir.is_dir():
        return files

    for asset in assets_dir.rglob("*"):
        if not asset.is_file():
            continue
        rel_path = "assets/" + str(asset.relative_to(assets_dir))
        f = File(
            rel_path,
            config["docs_dir"],
            config["site_dir"],
            config["use_directory_urls"],
        )
        f.abs_src_path = str(asset)
        files.append(f)

    return files


def on_page_markdown(markdown: str, **kwargs) -> str:
    """Strip one ../ from asset paths (vault root → docs_dir root)."""
    return re.sub(
        r"\]\((\.\./)+(assets/[^)]+)\)",
        lambda m: "]("
        + "../" * (m.group(0).count("../") - 1)
        + m.group(2)
        + ")",
        markdown,
    )

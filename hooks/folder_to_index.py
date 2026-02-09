"""MkDocs hook: treat folder/folder.md as folder/index.md.

Obsidian uses folder/folder.md as section entry points.
MkDocs expects folder/index.md for clean URLs.
This hook bridges the gap without touching files on disk.

Keeps original src_path so that obsidian-bridge and other plugins
can still resolve wikilinks like [[hacks]] → hacks/hacks.md.
Only dest_path is rewritten for clean output URLs.
"""

import os
from pathlib import Path

from mkdocs.structure.files import Files


def on_files(files: Files, config: dict) -> Files:
    site_dir = config["site_dir"]

    for file in files:
        if not file.src_path.endswith(".md"):
            continue
        path = Path(file.src_path)
        if path.stem == path.parent.name:
            file.dest_path = str(path.parent / "index.html")
            file.abs_dest_path = os.path.join(site_dir, file.dest_path)
            file.name = "index"
            file.url = str(path.parent) + "/"

    return files

"""MkDocs hook: treat folder/folder.md as folder/index.md.

Obsidian uses folder/folder.md as section entry points.
MkDocs expects folder/index.md for clean URLs.
This hook bridges the gap without touching files on disk.
"""

from pathlib import Path

from mkdocs.structure.files import File, Files


def on_files(files: Files, config: dict) -> Files:
    new_files = []
    docs_dir = config["docs_dir"]
    site_dir = config["site_dir"]
    use_directory_urls = config["use_directory_urls"]

    for file in files:
        if file.src_path.endswith(".md"):
            path = Path(file.src_path)
            if path.stem == path.parent.name:
                index_path = str(path.parent / "index.md")
                new_file = File(index_path, docs_dir, site_dir, use_directory_urls)
                new_file.abs_src_path = file.abs_src_path
                new_files.append(new_file)
                continue
        new_files.append(file)

    return Files(new_files)

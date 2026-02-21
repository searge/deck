# Coding Guidelines — Deck

Standards for contributing to this project: content, hooks, and skel templates.

## Content (Markdown)

### Frontmatter

Every page in `core/` requires frontmatter:

```yaml
---
tags:
  - go
  - architecture
aliases:
  - Go Coding Guidelines # wikilink target in Obsidian
title: Coding Guidelines # shown in nav and social cards
description: One sentence. Used in social cards and search.
---
```

`title` and `description` are required. `tags` and `aliases` are recommended.

### File naming

- Lowercase, underscores: `coding_guidelines.md`, `project_skeleton.md`
- Section index: `folder/folder.md` — the `folder_to_index` hook maps it
  to `folder/index.html` for clean URLs. Do not create `index.md` manually.

### Structure limits

- Maximum 3 levels of nesting in `core/`
- New topic area → new directory in `core/`
- New subtopic → new `.md` file in that directory

### Code blocks

Always specify language:

````markdown
```bash
echo "always tag code blocks"
```
````

Supported fenced: `bash`, `python`, `go`, `yaml`, `toml`, `json`, `text`.
Mermaid diagrams work with ` ```mermaid `.

### Callouts

Use Obsidian-style callouts (rendered by `obsidian_callouts`):

```markdown
> [!info] Title
> Informational note.

> [!warning] Title
> Something to watch out for.

> [!tip] Title
> Helpful shortcut.
```

### Links

- Always use markdown links for compatibility
  - Wikilinks work: `[[page_name]]` or `[[page_name|display text]]`
  - Relative markdown links also work: `[text](../other/page.md)`
- Asset paths: write as in Obsidian (`../../assets/img.png`) — the
  `external_assets` hook corrects paths during build automatically

## Local development

```bash
uv sync                    # install dependencies
uv run mkdocs serve        # live preview at http://localhost:8000
uv run mkdocs build        # build to site/ (run before push)
markdownlint 'core/**/*.md' --ignore node_modules
```

Build must pass cleanly before pushing to `main`.

## CI/CD

Push to `main` triggers `deploy.yml`:

1. `uv sync` — install dependencies
2. `uv run mkdocs build` — generate `site/`
3. `ghp-import` — push `site/` to the `site` branch

**Never push broken markdown or missing frontmatter** — the build will fail
and the site won't deploy.

## Hooks (`hooks/`)

Hooks are MkDocs event handlers. Two exist:

| Hook                 | Event                          | Purpose                                       |
| -------------------- | ------------------------------ | --------------------------------------------- |
| `folder_to_index.py` | `on_files`                     | Maps `folder/folder.md` → `folder/index.html` |
| `external_assets.py` | `on_files`, `on_page_markdown` | Includes `assets/` and fixes Obsidian paths   |

When writing a new hook:

- One hook file = one responsibility
- Use `on_files` or `on_page_markdown` — not both unless necessary
- Pure functions where possible; no global state
- Follow [core/py/coding_guidelines](../core/py/coding_guidelines.md)

Register in `mkdocs.yml`:

```yaml
hooks:
  - hooks/your_hook.py
```

## Skel templates (`skel/`)

Templates live in `skel/roles/skel/templates/<type>/`. Adding content =
dropping a `.j2` file in the right subdirectory.

Conventions:

- `dot_` prefix → dotfile: `dot_gitignore.j2` → `.gitignore`
- Jinja2 variables from `skel/roles/skel/defaults/<type>.yml`
- Scaffold a new project type by adding playbook + defaults + templates

Available skeletons:

```bash
task python -- '{"project_name":"my-tool","target_dir":"~/Code/lrn/my-tool"}'
task go     -- '{"project_name":"my-tool","target_dir":"~/Code/lrn/my-tool"}'
```

## What to avoid

| Don't                            | Do instead                                |
| -------------------------------- | ----------------------------------------- |
| `index.md` in `core/`            | `folder/folder.md` — hook handles routing |
| Missing `title` or `description` | Always fill frontmatter                   |
| Unnamed code blocks              | Always specify language tag               |
| Nesting deeper than 3 levels     | Split into a new module                   |
| Business logic in hooks          | Pure functions, single responsibility     |
| Committing `site/` to `main`     | CI deploys to `site` branch automatically |

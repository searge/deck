Transform notes from raw/current_focus/ into a deck page for core/.

Read all files in raw/current_focus/. Then:

1. Identify the target module from the content (net/, hacks/, unix/, ct/, emb/, py/, go/, ci/, cloud/).
2. Determine the appropriate file path in core/.
3. Apply deck structure:
   - Front matter (tags, aliases, title, description)
   - One-liner definition
   - Concept section (only if needed to understand the commands)
   - Practical examples with real commands
   - No theoretical filler

Rules:
- Use only content from raw/current_focus/ — do not supplement from general knowledge.
- Apply operator voice: direct, lowercase headings, code-first.
- If raw notes contain a command — include it exactly.
- If something is unclear or missing — flag it, do not fill it in.

Output:
1. Proposed file path in core/
2. Complete page content (ready to save as-is)
3. Gaps list — things the operator needs to fill from memory before publishing

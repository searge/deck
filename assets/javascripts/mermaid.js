// Initialize Mermaid for MkDocs Material
// https://squidfunk.github.io/mkdocs-material/reference/diagrams/#mermaid
window.addEventListener("DOMContentLoaded", function () {
  if (!window.mermaid) return;
  window.mermaid.initialize({
    startOnLoad: true,
    theme: document.body.getAttribute("data-md-color-scheme") === "nord-dark" ? "dark" : "default",
  });
});

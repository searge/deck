// Initialize Mermaid for MkDocs Material (supports instant navigation)
// https://squidfunk.github.io/mkdocs-material/reference/diagrams/#mermaid
(function () {
  function renderMermaid() {
    if (!window.mermaid) return;
    window.mermaid.initialize({
      startOnLoad: false,
      theme: document.body.getAttribute("data-md-color-scheme") === "nord-dark" ? "dark" : "default",
    });
    var nodes = document.querySelectorAll(".mermaid");
    if (nodes.length) window.mermaid.init(undefined, nodes);
  }

  if (typeof window.document$ !== "undefined") {
    window.document$.subscribe(renderMermaid);
  } else {
    window.addEventListener("DOMContentLoaded", renderMermaid);
  }
})();

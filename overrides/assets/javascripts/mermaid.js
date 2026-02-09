// Initialize Mermaid for MkDocs Material (supports instant navigation)
// https://squidfunk.github.io/mkdocs-material/reference/diagrams/#mermaid
(function () {
  function renderMermaid() {
    if (!window.mermaid) return;
    window.mermaid.initialize({
      startOnLoad: false,
      theme: document.body.getAttribute("data-md-color-scheme") === "nord-dark" ? "dark" : "default",
    });

    // Normalize Mermaid fences rendered as code blocks into div.mermaid
    var codeBlocks = document.querySelectorAll("code.language-mermaid");
    codeBlocks.forEach(function (code) {
      var pre = code.closest("pre");
      if (!pre) return;
      var container = document.createElement("div");
      container.className = "mermaid";
      container.textContent = code.textContent;
      pre.replaceWith(container);
    });

    var nodes = document.querySelectorAll(".mermaid");
    if (!nodes.length) return;
    if (typeof window.mermaid.run === "function") {
      window.mermaid.run({ nodes: nodes });
    } else {
      window.mermaid.init(undefined, nodes);
    }
  }

  if (typeof window.document$ !== "undefined") {
    window.document$.subscribe(renderMermaid);
  } else {
    window.addEventListener("DOMContentLoaded", renderMermaid);
  }
})();

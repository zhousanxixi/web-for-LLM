// Render the supported answer formatting with DOM nodes, never model-provided HTML.
(() => {
  const internal = /^(?:place-\d+|guide-[\w-]+):\d+$/i;
  function clean(text) {
    return String(text ?? "")
      .replace(/\[((?:place-\d+|guide-[\w-]+):\d+)\](?:[ \t]*\n?[ \t]*\((https?:\/\/[^\s)]+)\))?/gi,
        (_, id, url) => url ? `[参考来源](${url})` : "")
      .replace(/\[(?:place-\d*|guide-[\w-]*)(?::\d*)?$/, "");
  }
  function appendInline(parent, value) {
    const pattern = /\*\*([^\n]+?)\*\*|\[([^\]\n]+)\]\(([^\s)]+)\)/g;
    let last = 0, match;
    while ((match = pattern.exec(value))) {
      parent.append(document.createTextNode(value.slice(last, match.index)));
      if (match[1] !== undefined) {
        const strong = document.createElement("strong");
        strong.textContent = match[1].trim();
        parent.append(strong);
      } else {
        let url;
        try { url = new URL(match[3]); } catch (_) { url = null; }
        if (url && ["https:", "http:"].includes(url.protocol)) {
          const a = document.createElement("a");
          a.href = url.href;
          a.target = "_blank";
          a.rel = "noopener noreferrer";
          a.textContent = internal.test(match[2]) ? "参考来源" : match[2];
          parent.append(a);
        } else parent.append(document.createTextNode(match[2]));
      }
      last = pattern.lastIndex;
    }
    parent.append(document.createTextNode(value.slice(last)));
  }
  function render(target, text) {
    const fragment = document.createDocumentFragment();
    appendInline(fragment, clean(text));
    target.replaceChildren(fragment);
  }
  window.chatFormat = { render, clean };
})();

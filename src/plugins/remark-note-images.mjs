import { visit } from "unist-util-visit";
const esc = (value = "") => String(value).replaceAll("&", "&amp;").replaceAll('"', "&quot;").replaceAll("<", "&lt;").replaceAll(">", "&gt;");
// These public assets are already losslessly optimized. Keep native URLs so
// Astro does not emit a second full copy of the historical image collection.
export function remarkNoteImages() {
  return (tree) => visit(tree, "image", (node, index, parent) => {
    if (!node.url?.startsWith("/notes-assets/") || !parent || index === undefined) return;
    const title = node.title ? ` title="${esc(node.title)}"` : "";
    parent.children[index] = {type: "html", value: `<img src="${esc(node.url)}" alt="${esc(node.alt)}"${title} loading="lazy" decoding="async">`};
  });
}

# MkDocs Site Tree -- Full Setup Guide

Want a collapsible HTML **site tree** for your MkDocs documentation?
Here's a complete setup you can follow. 📑

------------------------------------------------------------------------

## 1️⃣ Install Dependencies

Install MkDocs (if not already installed):

``` bash
pip install mkdocs
```

Install the **sitemap plugin**:

``` bash
pip install mkdocs-sitemap-plugin
```

If you have a `requirements.txt`, add:

``` text
mkdocs-sitemap-plugin
```

------------------------------------------------------------------------

## 2️⃣ Configure `mkdocs.yml`

Enable the plugin under `plugins:`. Keep `search` if you already have
it.

``` yaml
plugins:
  - search
  - sitemap:
      hostname: http://127.0.0.1:8010/event-management-strategy-documentation/
```

> 💡 Use your production hostname if deploying publicly (e.g.,
> `https://docs.mydomain.com`).\
> For local dev, the above `127.0.0.1` works fine.

------------------------------------------------------------------------

## 3️⃣ Rebuild Your Site

Generate a fresh build so that `sitemap.xml` is created inside the
`site/` folder.

``` bash
mkdocs build
```

------------------------------------------------------------------------

## 4️⃣ Add `tree.html`

Save the following file as `tree.html` inside your `site/` folder:

``` html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>Site Tree</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <style>
    :root { --font: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial; }
    body { font-family: var(--font); margin: 24px; }
    h1 { margin: 0 0 12px; font-size: 22px; }
    #status { color: #666; margin-bottom: 12px; }
    details { margin: 4px 0 4px 18px; }
    summary { cursor: pointer; list-style: none; }
    ul { margin: 4px 0 4px 18px; padding-left: 0; }
    li { margin: 3px 0; }
    a { text-decoration: none; }
    a:hover { text-decoration: underline; }
    .folder::before { content: "📁 "; }
    .file::before   { content: "📄 "; }
    .small { font-size: 12px; color: #888; }
  </style>
</head>
<body>
  <h1>Website Tree</h1>
  <div id="status" class="small">Loading sitemap.xml…</div>
  <div id="tree"></div>

  <script>
    function insertPath(root, parts, url) {
      if (!parts.length) return;
      const [head, ...rest] = parts;
      root.children = root.children || {};
      root.children[head] = root.children[head] || { name: head, children: {}, url: null };
      if (rest.length === 0) {
        root.children[head].url = url;
      } else {
        insertPath(root.children[head], rest, url);
      }
    }

    function renderNode(node, basePath="") {
      const container = document.createDocumentFragment();
      const names = Object.keys(node.children || {}).sort();
      names.forEach(name => {
        const child = node.children[name];
        const isLeaf = !child.children || Object.keys(child.children).length === 0;
        const label = document.createElement(isLeaf ? "div" : "details");

        if (isLeaf) {
          const li = document.createElement("li");
          const a = document.createElement("a");
          a.href = child.url;
          a.textContent = name || "(index)";
          a.className = "file";
          li.appendChild(a);
          container.appendChild(li);
        } else {
          const summary = document.createElement("summary");
          summary.textContent = name || "(index)";
          summary.className = "folder";
          label.appendChild(summary);

          const ul = document.createElement("ul");
          ul.appendChild(renderNode(child));
          label.appendChild(ul);

          if (basePath.split("/").filter(Boolean).length < 1) label.setAttribute("open","");

          container.appendChild(label);
        }
      });
      return container;
    }

    async function main() {
      const status = document.getElementById("status");
      try {
        const res = await fetch("./sitemap.xml");
        if (!res.ok) throw new Error("sitemap.xml not found (enable the sitemap plugin in mkdocs.yml)");
        const xml = await res.text();

        const parser = new DOMParser();
        const doc = parser.parseFromString(xml, "application/xml");
        const urls = [...doc.querySelectorAll("url > loc")].map(n => n.textContent);

        const paths = urls
          .map(u => {
            try {
              const url = new URL(u);
              return url.pathname;
            } catch { return null; }
          })
          .filter(Boolean)
          .map(p => p.replace(/\/+/g, "/"));

        const root = { name: "", children: {} };
        paths.forEach(p => {
          let clean = p.replace(/^\/+/, "");
          const parts = clean.split("/").filter(Boolean);
          insertPath(root, parts, p);
        });

        const mount = document.getElementById("tree");
        const ul = document.createElement("ul");
        ul.appendChild(renderNode(root));
        mount.appendChild(ul);

        status.textContent = `Loaded ${paths.length} pages from sitemap.xml`;
      } catch (e) {
        status.textContent = "Failed to load tree: " + e.message;
      }
    }
    main();
  </script>
</body>
</html>
```

------------------------------------------------------------------------

## 5️⃣ Open in Browser

-   For `mkdocs serve`: open
    <http://127.0.0.1:8010/event-management-strategy-documentation/tree.html>
-   For a built site: just double-click `site/tree.html`.

------------------------------------------------------------------------

✅ **Done!** You now have a live, collapsible HTML site tree that
reflects the current build.

> **Optional:** If you prefer **not to install the sitemap plugin**, you
> can tweak the JS to parse `search/search_index.json` instead. I can
> generate that version for you too.

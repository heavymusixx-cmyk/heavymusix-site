# HeavyMusix site: standing rules for anyone working here

The owner's public name is "Heavy". Never put his real name anywhere: site, code comments, commit messages.

## Site quality standard (always)

Keep improving the site. Every page must meet all of these:

- **Current web standards.** Valid, semantic HTML5: one `<h1>`, landmarks (`header`, `nav`, `main id="main"`, `footer`), and a skip link as the first thing in `<body>`. Use modern CSS and no deprecated markup.
- **Accessibility: WCAG 2.2 Level AA (ADA).**
  - Text contrast is at least 4.5:1. Use `--blood-text` for red text on dark backgrounds, never `--blood-hot`.
  - Keyboard focus is always visible, and everything works with a keyboard and a screen reader.
  - Images have alt text, and every form field and button has a label or name.
  - Nothing relies on color alone.
  - Respect `prefers-reduced-motion`.
  - Touch targets are at least 24px, ideally 44px.
- **Responsive and adaptive design.** Pages work on phones, tablets and desktops: fluid layouts, no sideways scrolling, text readable without zooming. The hamburger menu shows at 1000px and below. The radio player stays usable on small screens.

Fixes and improvements toward this standard never need approval. New features, new sections and anything involving money need the owner's approval first.

## How the site is built

- Hand-made pages (`index.html`, `news.html` and so on) share the header and footer. **Change the header or footer in every hand-made page AND in `article.html`.** `scripts/build_pages.py` copies its header and footer from `article.html` into every generated story, band, genre, history and episode page, and wraps each page body in `<main id="main">`.
- `radio.js` runs on every page. It is the player, the pop-out player, the hamburger menu and in-place page loading (so the music keeps playing). Bump its `?v=` number in every page when you change it, and do the same for `style.css`.
- Visitors stay on the site: internal links load in place, and outside links open in a new tab.
- Test before pushing: `node --check` on changed JS, run `python3 scripts/build_pages.py`, and render pages at 390px and 1280px wide.

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
- **Responsive and adaptive design.** Pages work on phones, tablets and desktops: fluid layouts, no sideways scrolling, text readable without zooming. The hamburger menu shows on every screen size (owner's choice); on computers it drops down as a panel at the right. The radio player stays usable on small screens.

- **Polished, organized and easy to use (owner's request, Nov 21, 2026).** Pages look attractive and finished, the most useful things come first, related things are grouped, long lists show a sensible amount at a time ("Show more"), and nothing feels cluttered or repeated. Every Saturday review looks for one or two concrete ways to make the site easier and more inviting, and makes them.

Fixes and improvements toward this standard never need approval. New features, new sections and anything involving money need the owner's approval first.

## How the site is built

- Hand-made pages (`index.html`, `news.html` and so on) share the header and footer. **Change the header or footer in every hand-made page AND in `article.html`.** `scripts/build_pages.py` copies its header and footer from `article.html` into every generated story, band, genre, history and episode page, and wraps each page body in `<main id="main">`.
- `radio.js` runs on every page. It is the player, the pop-out player, the hamburger menu and in-place page loading (so the music keeps playing). Bump its `?v=` number in every page when you change it, and do the same for `style.css`.
- Visitors stay on the site: internal links load in place, and outside links open in a new tab.
- Test before pushing: `node --check` on changed JS, run `python3 scripts/build_pages.py`, and render pages at 390px and 1280px wide.

## Schedule: Eastern time

The site updates by **5 AM Eastern** every day: stories (Claude task, 4:23 AM ET), headlines (4:51 AM ET, then every 4 hours), playlist reshuffle (5:05 AM ET), social clips (5:11 AM ET), Radio Show builder (5:20 AM ET), song info (album and year, 5:40 AM ET). GitHub schedules are in UTC and set for Eastern Standard Time. **On the second Sunday of March, move each of those UTC hours 1 earlier, and on the first Sunday of November, move them back**, so they stay at the same Eastern time. Auto-post times and the nightly Arizona shows roll stay as they are.

## Skins (owner-approved, automatic)

`skin.js` (in every page's head) picks the look by date; `style.css` holds the colors and art. Every skin stays dark, evil and metal, with metal lettering, and must pass AA contrast.
- Weekly rotation every Monday: Blood, Crypt, Toxic, Frost (counted from Mon Nov 16, 2026).
- Holidays override the week: Valentine's (Feb 7-14), St. Patrick's (Mar 14-17), 4th of July (Jun 28-Jul 5), Halloween (Oct 15-31), Thanksgiving (Mon-Sun of the 4th-Thursday week), Christmas (Dec 1-26), New Year's (Dec 27-Jan 2). Holiday skins use the holiday's colors across the whole page, a skull in a holiday hat, and a garland under the banner. Art lives in `images/skins/`.
- Preview with `?skin=<name>` (lasts only while browsing in that tab; a normal visit always follows the schedule). The owner will fine-tune the looks later.

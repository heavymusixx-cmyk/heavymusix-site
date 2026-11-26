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

Fixes and improvements toward this standard never need approval.

**Standing permission (owner, Nov 21, 2026: "No more asking me permission to do what needs to be done").** Always review, analyze, fix and change the site to make it efficient, attention-getting, organized and polished, without asking: design, layout, page organization, navigation, how content is presented, interactive touches, speed. This overrides any older "new features need approval" wording for site work. Just do it, test it, and log it in the playbook's Work log. Still ask the owner first for: new accounts, anything that brings in money (store, ads, sponsors, prices), anything with legal effect (opening band submissions, terms, collecting personal data), and big new services or whole new sections (a gig board, a store, band sign-ups).

## Brand lines (owner, Nov 26, 2026)

- The one brand line is **"Where every MetalHead and Band belongs."** (capital M, H and B), with a ™ after it in the header. It sits under the logo on every page and in the footer.
- **Do not use "Every band gets a turn" anywhere** (owner dropped it). Home page headline is the brand line itself (the small line under the logo is hidden on the home page only, via body class "home"); "Arizona's home for metal." is the headline of the Arizona page (arizona.html).
- Use ™ (never ®) on HeavyMusix and the brand line until the USPTO registers them.

## How the site is built

- Hand-made pages (`index.html`, `news.html` and so on) share the header and footer. **Change the header or footer in every hand-made page AND in `article.html`.** `scripts/build_pages.py` copies its header and footer from `article.html` into every generated story, band, genre, history and episode page, and wraps each page body in `<main id="main">`.
- `radio.js` runs on every page. It is the player, the pop-out player, the hamburger menu and in-place page loading (so the music keeps playing). Bump its `?v=` number in every page when you change it, and do the same for `style.css`.
- Header (Nov 21, 2026): logo, then a **Follow** button and the hamburger. Follow opens a panel built by `radio.js` from its `FOLLOW` list (email sign-up first, then Instagram, Threads, YouTube, Bluesky, Discord, Get the app). To add a link (e.g. the Bluesky profile or Discord invite), fill in that entry's `href` and `note` in `FOLLOW` and bump radio.js's `?v=`; an empty `href` shows "Coming soon". Any button with `data-follow` opens the panel. The menu has search on top and two columns on computers. Unsubscribing must always stay one click and easy to find (owner: "we are honest and fair and love the community").
- **No genre labels anywhere (owner, Nov 21, 2026): it's metal, period.** No subgenre pages, tags, filters, search terms or labels on band pages, Band of the Day, menus or the submit form. News stories and history may still describe a band's style in their own words ("Bay Area thrash legends"); the rule is that the site never sorts, labels, tags or advertises anything by genre. Old /genres/ links redirect to Find a band (404.html).
- Visitors stay on the site: internal links load in place. Outside links open in a new tab on computers; on phones and tablets radio.js strips target="_blank" and lets the phone follow the tap itself in the same tab (never location.href or window.open), so app links open the app and HeavyMusix stays put (a new tab was left as a blank white page when the phone handed the link to an app; owner reported Nov 26, 2026).
- Fan email: when you make a change fans would notice (a new button, page or feature), add one plain, friendly line to `social/updates.json` (date, text, link; newest first, keep about 20). The weekly fan email shows the last 7 days under "New on HeavyMusix". Big moments (launch day, submissions open, merch) get a one-off email: write `social/announcement.json` (id, subject, title, text, link, button), show it to the owner, and only after he approves run the "Weekly fan email" workflow with "announce" on.
- Test before pushing: `node --check` on changed JS, run `python3 scripts/build_pages.py`, and render pages at 390px and 1280px wide.

## Schedule: Eastern time

The site updates by **5 AM Eastern** every day: stories (Claude task, 4:23 AM ET), headlines (4:51 AM ET, then every 4 hours), playlist reshuffle (5:05 AM ET), social clips (5:11 AM ET), Radio Show builder (5:20 AM ET), song info (album and year, 5:40 AM ET). GitHub schedules are in UTC and set for Eastern Standard Time. **On the second Sunday of March, move each of those UTC hours 1 earlier, and on the first Sunday of November, move them back**, so they stay at the same Eastern time. Auto-post times and the nightly Arizona shows roll stay as they are.

## Skins (owner-approved, automatic)

`skin.js` (in every page's head) picks the look by date; `style.css` holds the colors and art. Every skin stays dark, evil and metal, with metal lettering, and must pass AA contrast.
- Weekly rotation every Monday: Blood, Crypt, Toxic, Frost (counted from Mon Nov 16, 2026).
- Holidays override the week: Valentine's (Feb 7-14), St. Patrick's (Mar 14-17), 4th of July (Jun 28-Jul 5), Halloween (Oct 15-31), Thanksgiving (the Sunday before through the Sunday after the 4th Thursday; owner moved the start up a day, Nov 22, 2026), Christmas (Dec 1-26), New Year's (Dec 27-Jan 2). Holiday skins use the holiday's colors across the whole page, a skull in a holiday hat, and a garland under the banner. Art lives in `images/skins/`.
- Preview with `?skin=<name>` (lasts only while browsing in that tab; a normal visit always follows the schedule). The owner will fine-tune the looks later.

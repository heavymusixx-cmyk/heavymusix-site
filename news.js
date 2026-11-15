/*
  HEAVYMUSIX NEWS
  To add a news post: copy one block below (from { to },), paste it at the TOP of the list,
  and change the date, title, tag and text. Newest post goes first.
  Each line of "text" becomes its own paragraph.
*/
var NEWS = [
  {
    date: "2026-11-15",
    tag: "Shows",
    title: "Phoenix metal this week: DragonForce tonight, Imminence and Trivium coming",
    text: [
      "Power metal takes over The Van Buren tonight: DragonForce, with Ensiferum and Rhapsody of Fire, Sunday Nov 15 at 7:30 PM.",
      "Coming up: Imminence with Dying Wish at The Van Buren on Nov 27, and Trivium at Arizona Financial Theatre on Dec 2.",
      "Heading out? Tag @heavymusixradio in your show pics. And if your band is opening a local bill, send it to submit@heavymusix.com."
    ]
  },
  {
    date: "2026-11-15",
    tag: "Releases",
    title: "Big week ahead: Trivium, Down, Disfear and Wolf all drop new albums Nov 20",
    text: [
      "Friday, November 20 is stacked. Trivium release \"Crown In The Grave\" on Roadrunner, Down return with \"Volume V\" on Nuclear Blast, Sweden's Disfear (with At The Gates frontman Tomas Lindberg) unleash \"The Last Nail\" on Relapse, and Swedish traditional metallers Wolf bring their tenth album, \"Hour Of The Wolf.\"",
      "Planning ahead: Powerwolf just announced their \"Moral & Madness\" 2027 European tour, hitting arenas from Luxembourg to Berlin and Cologne next autumn.",
      "Trivium is already in rotation on HeavyMusix Radio. Which of these are you spinning first?"
    ]
  },
  {
    date: "2026-11-15",
    tag: "Site",
    title: "Welcome to heavymusix.com (work in progress)",
    text: [
      "HeavyMusix is being built in public, and this site is the new home base.",
      "HeavyMusix Radio is live right now on the home page. Coming soon: the Band Survival Kit animated series, merch and band tools in the shop, and features on hand-picked unsigned bands.",
      "Follow @heavymusixradio on Instagram and Threads to see each piece as it lands."
    ]
  },
  {
    date: "2026-11-15",
    tag: "Coming soon",
    title: "Band Survival Kit: an animated series for unsigned bands",
    text: [
      "Meet Grave Budget: a broke Phoenix metal band learning to run like a business the hard way.",
      "Each episode covers one real problem: finding members, splitting money, budgeting, contracts, merch, booking, and not getting ripped off. Each one comes with a free checklist right here on the site.",
      "Episode 1, \"Wanted: Screamer,\" is in production."
    ]
  },
  {
    date: "2026-11-14",
    tag: "Bands",
    title: "Submissions are open",
    text: [
      "Unsigned metal band, anywhere in the world? Send your music, bio, photos and contact info to submit@heavymusix.com.",
      "Send a full album or EP, or at least 4 to 5 tracks. Every submission is reviewed, but not every band is selected, and reviews take time. Full details are on the Submit page. It's free, always."
    ]
  },
  {
    date: "2026-11-14",
    tag: "Radio",
    title: "HeavyMusix Radio is live",
    text: [
      "HeavyMusix Radio: Underground + Heavy Hitters mixes unsigned bands with the heavy hitters you already love.",
      "The playlist reshuffles every day so every band in it gets a turn. Hit play at the top of the home page, or save it in YouTube Music."
    ]
  }
];

function fmtDate(d){
  const [y,m,day] = d.split("-").map(Number);
  return new Date(y, m-1, day).toLocaleDateString("en-US",{month:"long",day:"numeric",year:"numeric"});
}
function esc(s){return String(s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;"}[c]));}

/* Each story has its own page: article.html?p=<slug> */
function slugOf(n){return n.date+"-"+n.title.toLowerCase().replace(/[^a-z0-9]+/g,"-").replace(/^-|-$/g,"").slice(0,60);}
function storyUrl(n){return "article.html?p="+encodeURIComponent(slugOf(n));}
function bodyHtml(n){return n.text.map(p=>/^Source:/i.test(p)?`<p class="src">${esc(p)}</p>`:`<p>${esc(p)}</p>`).join("");}

/* Home page: latest 3 headlines, each opening our own story */
function renderLatest(el){
  el.innerHTML = NEWS.slice(0,3).map(n=>`
    <div class="card">
      <span class="tag">${esc(n.tag)}</span>
      <div class="date">${fmtDate(n.date)}</div>
      <h3><a class="hl" href="${storyUrl(n)}">${esc(n.title)}</a></h3>
      <p class="muted">${esc(n.text[0])}</p>
      <a href="${storyUrl(n)}">Read the story</a>
    </div>`).join("");
}
/* News page: every headline, newest first */
function renderAll(el){
  el.innerHTML = NEWS.map(n=>`
    <article class="post">
      <span class="tag">${esc(n.tag)}</span>
      <div class="date muted">${fmtDate(n.date)}</div>
      <h2><a class="hl" href="${storyUrl(n)}">${esc(n.title)}</a></h2>
      <p>${esc(n.text[0])}</p>
      <a href="${storyUrl(n)}">Read the story</a>
    </article>`).join("");
}
/* Story page: the full HeavyMusix story, plus more headlines */
function renderArticle(el){
  const p=new URLSearchParams(location.search).get("p");
  const n=NEWS.find(x=>slugOf(x)===p)||NEWS[0];
  document.title=n.title+" | HeavyMusix";
  const more=NEWS.filter(x=>x!==n).slice(0,6);
  el.innerHTML=`
    <article class="post story">
      <span class="tag">${esc(n.tag)}</span>
      <div class="date muted">${fmtDate(n.date)}</div>
      <h1>${esc(n.title)}</h1>
      ${bodyHtml(n)}
    </article>
    <h2 class="sub">More metal news</h2>
    <ul class="morenews">${more.map(m=>`<li><a href="${storyUrl(m)}">${esc(m.title)}</a><span class="wsrc">${fmtDate(m.date)}</span></li>`).join("")}</ul>
    <div class="btns"><a class="btn ghost" href="news.html">All news</a></div>`;
}

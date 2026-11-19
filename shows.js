/*
  HEAVYMUSIX ARIZONA SHOWS
  Upcoming metal shows in Arizona. Updated every morning by the daily news task.
  Add a show: copy one line, keep dates as "YYYY-MM-DD". Past shows hide themselves.
*/
var SHOWS = [
  {date:"2026-11-15", bands:"DragonForce, Ensiferum, Rhapsody of Fire", venue:"The Van Buren", city:"Phoenix"},
  {date:"2026-11-15", bands:"Alice Cooper", venue:"Findlay Toyota Center", city:"Prescott Valley"},
  {date:"2026-11-17", bands:"GWAR, Midnight, Mac Sabbath", venue:"Marquee Theatre", city:"Tempe"},
  {date:"2026-11-18", bands:"The Amity Affliction, Blessthefall, Orthodox, Buried in Spring", venue:"Rialto Theatre", city:"Tucson"},
  {date:"2026-11-18", bands:"Static Dress, I Promised the World, Car Underwater, Sherane", venue:"Nile Theater", city:"Mesa"},
  {date:"2026-11-20", bands:"Ladrones", venue:"The Rock", city:"Tucson"},
  {date:"2026-11-21", bands:"Three Days Grace, I Prevail, The Funeral Portrait", venue:"Talking Stick Resort Amphitheatre", city:"Phoenix"},
  {date:"2026-11-21", bands:"Alter Bridge, Big Wreck, Tim Montana", venue:"The Events Center at Harrah's Ak-Chin", city:"Maricopa"},
  {date:"2026-11-23", bands:"Big Ass Truck I.E., Chamber, Mugshot, Lie", venue:"Rosetta Room", city:"Mesa"},
  {date:"2026-11-23", bands:"Ladrones", venue:"Rebel Lounge", city:"Phoenix"},
  {date:"2026-11-24", bands:"A Killer's Confession, Dizasterpiece, Dead Things", venue:"The 44", city:"Glendale"},
  {date:"2026-11-27", bands:"Imminence, Dying Wish, Gaerea", venue:"The Van Buren", city:"Phoenix"},
  {date:"2026-11-28", bands:"Ho99o9, N8NOFACE, Slay Squad", venue:"191 Toole", city:"Tucson"},
  {date:"2026-11-29", bands:"Ho99o9, N8NOFACE, Slay Squad", venue:"Rebel Lounge", city:"Phoenix"},
  {date:"2026-12-02", bands:"Trivium, In Flames, Orbit Culture, Fit For An Autopsy, Frozen Soul", venue:"Arizona Financial Theatre", city:"Phoenix"},
  {date:"2026-12-03", bands:"Born of Osiris, Miss May I, Convictions, Downswing", venue:"Nile Theater", city:"Mesa"},
  {date:"2026-12-04", bands:"Silent Civilian", venue:"The Bisbee Grand", city:"Bisbee"},
  {date:"2026-12-06", bands:"Amorphis, Insomnium, Hinayana", venue:"Nile Theater", city:"Mesa"},
  {date:"2026-12-09", bands:"Whitechapel, Chelsea Grin, The Acacia Strain, Netherwalker", venue:"The Van Buren", city:"Phoenix"},
  {date:"2026-12-16", bands:"Beartooth, Don Broco, Magnolia Park, Windwaker", venue:"Arizona Financial Theatre", city:"Phoenix"},
  {date:"2026-12-16", bands:"Kingdom of Giants, Deadlands, Holy Wars, Night Rider", venue:"Rosetta Room", city:"Mesa"},
  {date:"2026-12-18", bands:"Eyes Set to Kill, Sicksense, Twist It", venue:"The Rock", city:"Tucson"},
  {date:"2026-12-19", bands:"Eyes Set to Kill, Sicksense, Twist It", venue:"Crescent Ballroom", city:"Phoenix"},
  {date:"2027-01-19", bands:"Dopethrone, -(16)-, Armed for Apocalypse", venue:"The Bisbee Grand", city:"Bisbee"},
  {date:"2027-01-22", bands:"Tesseract, Entheos, Sunborn", venue:"Nile Theater", city:"Mesa"},
  {date:"2027-01-22", bands:"Dopethrone, -(16)-, Armed for Apocalypse", venue:"Queen B Vinyl", city:"Cottonwood"},
  {date:"2027-01-23", bands:"Dopethrone, -(16)-, Armed for Apocalypse", venue:"Rosetta Room", city:"Mesa"},
  {date:"2027-02-05", bands:"Polyphia, Ladrones, RJ Pasin", venue:"Arizona Financial Theatre", city:"Phoenix"},
  {date:"2027-02-05", bands:"Wolves in the Throne Room, Stygian Bough, Spirit Possession", venue:"Nile Theater", city:"Mesa"},
  {date:"2027-02-14", bands:"Northlane, Allt, Aviana, Reliqa", venue:"Nile Theater", city:"Mesa"},
  {date:"2027-02-20", bands:"Beast in Black, Gloryhammer", venue:"Nile Theater", city:"Mesa"},
  {date:"2027-02-22", bands:"Capstan, Fire From the Gods, Midwinter", venue:"Rosetta Room", city:"Mesa"},
  {date:"2027-03-07", bands:"Dying Fetus, Cryptopsy, Gorgasm", venue:"Rebel Lounge", city:"Phoenix"},
  {date:"2027-03-30", bands:"Týr, Dynazty, Dominum, Edge of Paradise", venue:"Nile Theater", city:"Mesa"},
  {date:"2027-04-26", bands:"Iron Maiden", venue:"Talking Stick Resort Amphitheatre", city:"Phoenix"},
  {date:"2027-05-15", bands:"Avatar, The Barbarians of California", venue:"Marquee Theatre", city:"Tempe"}
];

function azToday(){
  var d = new Date(Date.now() - 7 * 3600 * 1000);
  return d.toISOString().slice(0, 10);
}
function showDate(s){
  var p = s.split("-").map(Number), d = new Date(p[0], p[1] - 1, p[2]);
  return {dow: d.toLocaleDateString("en-US", {weekday: "short"}), md: d.toLocaleDateString("en-US", {month: "short", day: "numeric"})};
}
function showEsc(s){ return String(s).replace(/[&<>"]/g, function(c){ return {"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;"}[c]; }); }
/* Upcoming Arizona shows; pass a number to show only the next few */
function renderShows(el, limit){
  if (!el) return;
  var today = azToday();
  var list = SHOWS.filter(function(s){ return s.date >= today; }).sort(function(a, b){ return a.date < b.date ? -1 : a.date > b.date ? 1 : 0; });
  if (limit) list = list.slice(0, limit);
  if (!list.length){ el.innerHTML = '<p class="lead">New Arizona shows are added every morning.</p>'; return; }
  el.innerHTML = '<ul class="shows">' + list.map(function(s){
    var d = showDate(s.date), tonight = s.date === today;
    return '<li' + (tonight ? ' class="tonight"' : '') + '><span class="sdate"><b>' + d.md + '</b>' + (tonight ? 'Tonight' : d.dow) + '</span>' +
      '<span class="sinfo"><strong>' + showEsc(s.bands) + '</strong><span>' + showEsc(s.venue) + ' &middot; ' + showEsc(s.city) + ', AZ</span></span></li>';
  }).join('') + '</ul>';
}

/* HeavyMusix Radio player.
   - Pinned to the corner; keeps playing while you browse the site.
   - Plays the Radio Show episodes in order and moves to the next one automatically.
     When there is no newer episode it starts over at Episode 1.
     With no episodes yet, it plays the HeavyMusix Radio playlist (24/7).
   - Fans can play any single song; when it ends, the radio picks back up. */
(function(){
  if (window.__hmxRadio) return;
  window.__hmxRadio = true;

  /* Header menus: the hamburger (site menu) and Follow (email, socials, app).
     One opens at a time. Close with the X, Escape, a click outside, or by picking something. */
  var FOLLOW = [
    {k: 'email', name: 'Get the HeavyMusix email', note: 'Free, once a week. Unsubscribe any time with one click.', href: 'newsletter.html', icon: 'M3 6h18v12H3zM3 6l9 7 9-7'},
    {k: 'instagram', name: 'Instagram', note: '@heavymusixradio', href: 'https://www.instagram.com/heavymusixradio/', icon: 'M4 8h3l2-3h6l2 3h3v11H4zM12 10a3.5 3.5 0 1 0 0 7 3.5 3.5 0 0 0 0-7z'},
    {k: 'threads', name: 'Threads', note: '@heavymusixradio', href: 'https://www.threads.com/@heavymusixradio', icon: 'M16 12a4 4 0 1 1-1.2-2.8M16 9v4.5a2.5 2.5 0 0 0 5 0V12a9 9 0 1 0-3.5 7.1'},
    {k: 'youtube', name: 'YouTube', note: '@HeavyMusix', href: 'https://www.youtube.com/@HeavyMusix', icon: 'M8 5v14l11-7z'},
    {k: 'bluesky', name: 'Bluesky', note: 'Coming soon', href: '', icon: 'M7 18h10a4 4 0 0 0 .5-8A6 6 0 0 0 6 9.5 4.3 4.3 0 0 0 7 18z'},
    {k: 'discord', name: 'Discord', note: 'Coming soon', href: '', icon: 'M4 5h16v10H9l-5 4z'}
  ];
  function hdr(){ return document.querySelector('header.site'); }
  function followPanel(){
    var h = hdr(); if (!h) return null;
    var p = document.getElementById('hmx-follow');
    if (p && h.contains(p)) return p;
    p = document.createElement('div');
    p.id = 'hmx-follow'; p.className = 'followpanel'; p.hidden = true;
    p.setAttribute('role', 'region'); p.setAttribute('aria-labelledby', 'hmx-follow-h');
    var svg = function(d){ return '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="' + d + '"/></svg>'; };
    p.innerHTML = '<p class="followh" id="hmx-follow-h">Follow HeavyMusix</p><ul>' + FOLLOW.map(function(f){
      var inner = svg(f.icon) + '<span><strong>' + f.name + '</strong><small>' + f.note + '</small></span>';
      if (!f.href) return '<li class="f-' + f.k + ' is-soon"><span class="frow" aria-disabled="true">' + inner + '</span></li>';
      var out = /^https?:/.test(f.href);
      return '<li class="f-' + f.k + '"><a class="frow" href="' + f.href + '"' + (out ? ' target="_blank" rel="noopener" aria-label="' + f.name + ' ' + f.note + ' (opens a new tab)"' : '') + '>' + inner + (out ? '<span class="fout" aria-hidden="true">&#8599;</span>' : '') + '</a></li>';
    }).join('') +
    '<li class="f-app"><button type="button" class="frow" data-install>' + svg('M12 3v11M7 10l5 5 5-5M4 20h16') + '<span><strong>Get the app</strong><small>HeavyMusix Radio on your home screen</small></span></button></li></ul>' +
    '<p class="followfine">Free, always. Unfollow or unsubscribe any time, no questions asked.</p>';
    h.querySelector('.wrap').appendChild(p);
    return p;
  }
  function setBtns(sel, open, labels){
    document.querySelectorAll(sel).forEach(function(b){
      b.setAttribute('aria-expanded', open ? 'true' : 'false');
      if (labels) b.setAttribute('aria-label', open ? labels[1] : labels[0]);
    });
  }
  function closeMenus(focusBack){
    var h = hdr(); if (!h) return;
    var wasMenu = h.classList.contains('open'), wasFollow = h.classList.contains('following');
    h.classList.remove('open', 'following');
    var p = document.getElementById('hmx-follow'); if (p) p.hidden = true;
    setBtns('.navtoggle', false, ['Open menu', 'Close menu']);
    setBtns('[data-follow]', false);
    if (focusBack){
      var b = wasMenu ? h.querySelector('.navtoggle') : wasFollow ? h.querySelector('.followbtn') : null;
      if (b) b.focus();
    }
  }
  function openMenu(){
    var h = hdr(); if (!h) return;
    closeMenus(false);
    h.classList.add('open');
    setBtns('.navtoggle', true, ['Open menu', 'Close menu']);
    var n = h.querySelector('nav.main'); if (n) n.scrollTop = 0;
  }
  function openFollow(from){
    var h = hdr(); if (!h) return;
    closeMenus(false);
    var p = followPanel(); if (!p) return;
    h.classList.add('following'); p.hidden = false;
    setBtns('[data-follow]', true);
    if (from && !h.contains(from)) window.scrollTo(0, 0);   // opened from a button lower on the page: show the panel under the banner
    var first = p.querySelector('a,button'); if (first) first.focus({preventScroll: true});
  }
  document.addEventListener('click', function(e){
    if (!e.target.closest) return;
    var h = hdr(); if (!h) return;
    var t = e.target.closest('.navtoggle');
    if (t){ h.classList.contains('open') ? closeMenus(false) : openMenu(); return; }
    var f = e.target.closest('[data-follow]');
    if (f){ e.preventDefault(); h.classList.contains('following') && h.contains(f) ? closeMenus(false) : openFollow(f); return; }
    if (!h.classList.contains('open') && !h.classList.contains('following')) return;
    if (e.target.closest('nav.main a, .followpanel a, .followpanel button') || !e.target.closest('header.site')) closeMenus(false);
  });
  document.addEventListener('keydown', function(e){
    var h = hdr();
    if (e.key === 'Escape' && h && (h.classList.contains('open') || h.classList.contains('following'))) closeMenus(true);
  });
  /* Keyboard users who Tab past the end of an open menu leave it closed behind them. */
  document.addEventListener('focusin', function(e){
    var h = hdr();
    if (h && (h.classList.contains('open') || h.classList.contains('following')) && !h.contains(e.target) && !e.target.closest('#hmx-app')) closeMenus(false);
  });
  var POPW = 232, POPH = 350;   // pop-out window: just big enough for the 200x200 video plus the buttons
  var PL = 'PLcJENP7Pnf5xXQk-R_SlBiDXeaSlSSJ6M';
  var player = null, ready = false, pending = null;
  var mode = null;          // {kind:'radio'} | {kind:'episode', i} | {kind:'song', v, label}
  var episodes = null;      // live episodes, oldest first

  /* Pop-out player: a separate small window (player.html) that keeps playing
     after the fan leaves heavymusix.com or closes its tab. */
  var POPOUT = !!window.HMX_POPOUT;
  var ALIVE = 'hmxPopoutAlive';
  var chan = null;
  try { chan = new BroadcastChannel('hmx-radio'); } catch (x) {}
  function popoutAlive(){
    if (POPOUT) return false;
    // Background windows may slow their timers, so allow a long gap; the window clears this when it closes.
    try { return Date.now() - Number(localStorage.getItem(ALIVE) || 0) < 90000; } catch (x) { return false; }
  }
  var waiting = {};
  /* Send a request to the pop-out window. If it does not answer within 1.5 s (closed or crashed),
     forget it and run the request here instead, so a click always plays something. */
  function tellPopout(msg, fallback){
    if (!chan || !popoutAlive()) return false;
    msg.id = String(Math.random()).slice(2);
    waiting[msg.id] = setTimeout(function(){
      delete waiting[msg.id];
      try { localStorage.removeItem(ALIVE); } catch (x) {}
      if (fallback) fallback();
    }, 1500);
    chan.postMessage(msg);
    return true;
  }
  if (chan && !POPOUT) chan.onmessage = function(e){
    var m = e.data || {};
    if (m.ack && waiting[m.ack]){ clearTimeout(waiting[m.ack]); delete waiting[m.ack]; }
  };
  function openPopout(){
    remember();
    var w = window.open('player.html', 'hmxPlayer', 'popup,width=' + POPW + ',height=' + POPH);
    if (!w){ setLabel(' \u00b7 allow pop-ups to pop out'); return; }
    try { player.stopVideo(); player.destroy(); } catch (x) {}
    player = null; ready = false; pending = null; mode = null;
    try { sessionStorage.removeItem(KEY); } catch (x) {}   // this tab no longer holds the music
    var d = dock(); if (d) d.remove();
    var r = document.getElementById('radio');
    if (r) r.innerHTML = '<button class="playcover" type="button" onclick="startRadio()">' +
      '<span class="pc-kicker">Popped out</span>' +
      '<span class="pc-title">HeavyMusix <em>Radio</em></span>' +
      '<span class="pc-cta">The radio is playing in its own window. Go anywhere on the web and it keeps rolling until you close it.</span></button>';
  }

  function dock(){ return document.getElementById('hmx-dock'); }

  /* Songs whose owners turned off playing on other sites, or that were removed (found weekly by the song check robot). */
  var BAD = {};
  fetch('show/unplayable.json', {cache: 'no-cache'}).then(function(r){ return r.ok ? r.json() : {songs: []}; })
    .then(function(d){ (d.songs || []).forEach(function(s){ BAD[s.v] = 1; }); }).catch(function(){});
  window.hmxUnplayable = function(v){ return !!BAD[v]; };

  /* A short notice at the bottom of the screen, read out by screen readers. */
  function notice(html){
    var n = document.getElementById('hmx-notice');
    if (!n){ n = document.createElement('div'); n.id = 'hmx-notice'; n.setAttribute('role', 'status'); document.body.appendChild(n); }
    n.innerHTML = html; n.classList.add('show');
    clearTimeout(n._t); n._t = setTimeout(function(){ n.classList.remove('show'); }, 8000);
  }
  function cantPlay(v, label){
    notice((label ? esc(label) + ': ' : 'That song: ') + 'the owner only allows it on YouTube. ' +
      '<a href="https://www.youtube.com/watch?v=' + encodeURIComponent(v) + '" target="_blank" rel="noopener">Play it on YouTube &#8599;</a>');
  }
  function esc(s){ return String(s).replace(/[&<>"]/g, function(c){ return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]; }); }

  function loadEpisodes(){
    if (episodes) return Promise.resolve(episodes);
    return fetch('show/episodes.json', {cache: 'no-cache'}).then(function(r){ return r.ok ? r.json() : {episodes: []}; })
      .catch(function(){ return {episodes: []}; })
      .then(function(d){
        episodes = (d.episodes || []).filter(function(e){ return e.status === 'live' && e.play && e.play.length; });
        return episodes;
      });
  }
  window.hmxEpisodes = loadEpisodes;

  function setLabel(t){
    var el = document.querySelector('#hmx-dock .dock-now');
    if (el) el.textContent = t;
  }

  function markHome(){
    var r = document.getElementById('radio');
    if (!r || POPOUT) return;
    if (!dock()){
      if (popoutAlive()) r.innerHTML = '<button class="playcover" type="button" onclick="startRadio()">' +
        '<span class="pc-kicker">Popped out</span>' +
        '<span class="pc-title">HeavyMusix <em>Radio</em></span>' +
        '<span class="pc-cta">The radio is playing in its own window. Close that window to stop it.</span></button>';
      return;
    }
    r.classList.add('cover');
    r.innerHTML = '<button class="playcover" type="button" onclick="startRadio()">' +
      '<span class="pc-kicker">Now playing</span>' +
      '<span class="pc-title">HeavyMusix <em>Radio</em></span>' +
      '<span class="pc-cta">The player is pinned to the corner of your screen. Keep browsing and the music keeps going.</span></button>';
  }

  function buildDock(){
    var d = document.createElement('aside');
    d.id = 'hmx-dock';
    d.setAttribute('aria-label', 'HeavyMusix Radio video');
    d.innerHTML =
      '<div class="dock-bar dock-top">' +
      (POPOUT ? '' : '<span class="dock-grip" title="Drag to move the video" aria-hidden="true">&#8942;&#8942;</span>') +
      '<button type="button" class="now-btn" data-act="prev" aria-label="Back" title="Back">&#9198;&#xFE0E;</button>' +
      '<button type="button" class="now-btn now-main" data-act="toggle" aria-label="Stop" title="Stop">&#9632;&#xFE0E;</button>' +
      '<button type="button" class="now-btn" data-act="next" aria-label="Forward" title="Forward">&#9197;&#xFE0E;</button>' +
      (POPOUT ? '' : '<button type="button" class="now-btn" data-act="size" aria-label="Full size video" title="Full">&#10530;&#xFE0E;</button>') +
      '<a class="now-btn now-ytm" href="https://music.youtube.com/playlist?list=' + PL + '" target="_blank" rel="noopener" aria-label="Open the HeavyMusix Radio playlist in the YouTube Music app (opens a new tab)" title="YouTube Music app">&#9835;&#8599;&#xFE0E;</a>' +
      '<button type="button" class="now-btn now-off" data-act="off" aria-label="Turn the radio off" title="Off">&#10005;&#xFE0E;</button>' +
      '</div>' +
      '<div class="dock-video"><div id="hmx-yt"></div></div>';
    d.addEventListener('click', function(e){ var t = e.target.closest('.now-btn'); if (t) act(t.dataset.act); });
    document.body.appendChild(d);
    if (!POPOUT){ makeDraggable(d); markHome(); }
    syncControls();
    var go = function(){
      player = new YT.Player('hmx-yt', {
        width: '100%', height: '100%',
        playerVars: {autoplay: 1, playsinline: 1, rel: 0, modestbranding: 1},
        events: {
          onReady: function(){ ready = true; if (pending){ var p = pending; pending = null; p(); } },
          onStateChange: onState,
          onError: onError
        }
      });
    };
    if (window.YT && YT.Player) go();
    else {
      var prev = window.onYouTubeIframeAPIReady;
      window.onYouTubeIframeAPIReady = function(){ if (prev) prev(); go(); };
      var s = document.createElement('script'); s.src = 'https://www.youtube.com/iframe_api'; document.head.appendChild(s);
    }
  }


  /* Drag the player anywhere by its red title bar (mouse or finger). Remembers the spot. */
  function place(d, x, y){
    var w = d.offsetWidth, h = d.offsetHeight;
    x = Math.max(4, Math.min(x, window.innerWidth - w - 4));
    var floor = (POPOUT && document.getElementById('hmx-now')) ? 51 : 4;   // pop-out: never cover the bar at the bottom
    y = Math.max(4, Math.min(y, window.innerHeight - h - floor));
    d.style.left = x + 'px'; d.style.top = y + 'px';
    d.style.right = 'auto'; d.style.bottom = 'auto';
    return [x, y];
  }
  function makeDraggable(d){
    var bar = d.querySelector('.dock-bar'), start = null;
    try { var saved = JSON.parse(localStorage.getItem('hmxDockPos') || 'null'); if (saved && saved[1] > 60) place(d, saved[0], saved[1]); } catch (x) {}   // phones and computers remember where the fan put it
    bar.addEventListener('pointerdown', function(e){
      if (e.target.closest('.dock-btn, .now-btn')) return;
      var r = d.getBoundingClientRect();
      start = {dx: e.clientX - r.left, dy: e.clientY - r.top};
      d.classList.add('dragging');
      bar.setPointerCapture(e.pointerId);
      e.preventDefault();
    });
    bar.addEventListener('pointermove', function(e){
      if (!start) return;
      place(d, e.clientX - start.dx, e.clientY - start.dy);
    });
    function end(){
      if (!start) return;
      start = null;
      d.classList.remove('dragging');
      try { var r = d.getBoundingClientRect(); localStorage.setItem('hmxDockPos', JSON.stringify([r.left, r.top])); } catch (x) {}
    }
    bar.addEventListener('pointerup', end);
    bar.addEventListener('pointercancel', end);
    window.addEventListener('resize', function(){
      if (d.style.left){ var r = d.getBoundingClientRect(); place(d, r.left, r.top); }
    });
  }

  /* Player controls live on the pinned bar: Back, Play/Stop, Forward, Full/Small, Off.
     When the music is in the pop-out window, the bar on the site's pages remote-controls it. */
  function setBig(on){
    var d = dock(); if (!d) return;
    d.classList.toggle('big', on); document.body.classList.toggle('hmx-big', on);
    var dim = document.getElementById('hmx-dim');
    if (on && !dim){ dim = document.createElement('div'); dim.id = 'hmx-dim'; dim.addEventListener('click', function(){ setBig(false); }); document.body.insertBefore(dim, d); }
    if (!on && dim) dim.remove();
    syncControls();
  }
  document.addEventListener('keydown', function(e){ if (e.key === 'Escape' && document.body.classList.contains('hmx-big')) setBig(false); });
  function togglePlay(){
    if (!mode || !player){ window.startRadio(); return; }
    try { if (player.getPlayerState() === 1 || player.getPlayerState() === 3) player.pauseVideo(); else player.playVideo(); } catch (x) {}
  }
  function skip(){
    if (!player || !mode){ window.startRadio(); return; }
    try {
      if (mode.kind === 'song'){ startDefault(); return; }
      if (atEpisodeEnd()){ if (mode.kind === 'radio') nextChunk(); else nextEpisode(); return; }
      player.nextVideo();
    } catch (x) {}
  }
  function back(){
    if (!player || !mode){ window.startRadio(); return; }
    try {
      if (player.getCurrentTime && player.getCurrentTime() > 8){ player.seekTo(0, true); return; }   // like a CD player: first press restarts the song
      var idx = player.getPlaylistIndex();
      if (idx > 0){ player.previousVideo(); return; }
      if (mode.kind === 'radio'){ loadChunk(chunkStart - 1); return; }
      player.seekTo(0, true);
    } catch (x) {}
  }
  function turnOff(){
    forget();
    if (POPOUT){ try { localStorage.removeItem(ALIVE); localStorage.removeItem(NOWKEY); } catch (x) {} window.close(); return; }
    try { player.stopVideo(); player.destroy(); } catch (x) {}
    player = null; ready = false; pending = null; mode = null;
    setBig(false);
    var d = dock(); if (d) d.remove();
    markHome(); refreshNow(); syncControls();
  }
  function act(cmd){
    if (!POPOUT && !mode && popoutAlive() && tellPopout({cmd: cmd}, function(){ act(cmd); })) return;
    if (cmd === 'toggle') togglePlay();
    if (cmd === 'next') skip();
    if (cmd === 'prev') back();
    if (cmd === 'size') setBig(!(dock() && dock().classList.contains('big')));
    if (cmd === 'off') turnOff();
  }
  window.hmxAct = act;
  function syncControls(){
    var d = dock(); if (!d) return;
    var st = -1; try { st = player.getPlayerState(); } catch (x) {}
    var playing = st === 1 || st === 3 || st === -1;
    var p = d.querySelector('[data-act="toggle"]');
    if (p){ p.innerHTML = playing ? '&#9632;&#xFE0E;' : '&#9654;&#xFE0E;'; p.setAttribute('aria-label', playing ? 'Stop' : 'Play'); p.title = playing ? 'Stop' : 'Play'; }
    var z = d.querySelector('[data-act="size"]'), big = d.classList.contains('big');
    if (z){ z.innerHTML = big ? '&#10529;&#xFE0E;' : '&#10530;&#xFE0E;'; z.setAttribute('aria-label', big ? 'Small video' : 'Full size video'); z.title = big ? 'Small' : 'Full'; }
  }


  function withPlayer(fn){
    if (!dock()) buildDock();
    if (ready) fn(); else pending = fn;
  }

  /* The 24/7 radio walks the WHOLE playlist (show/catalog.json, already in the rotator's
     artist-spread order) in chunks, because YouTube's embed only loads the first 200 songs
     of a playlist (a start spot past 200 fell back to song 1, so fans heard the same first
     song again and never got past song 200). Each fan's place is saved, so the next visit
     continues where they left off and nothing repeats until the whole list has played. */
  var CHUNK = 50, POS = 'hmxRadioPos';
  var catalog = null, CAT = null, chunkStart = 0;
  var catalogReady = fetch('show/catalog.json', {cache: 'no-cache'}).then(function(r){ return r.json(); })
    .then(function(c){ CAT = c || []; catalog = CAT.map(function(x){ return x.v; }).filter(Boolean); return catalog; })
    .catch(function(){ catalog = []; return catalog; });
  /* Pinned "now playing" bar along the bottom of every page: band, song, year and country.
     Stays when the player is closed, showing what's up next with a Listen button.
     Album and year come from show/songinfo.json (the Song info robot, MusicBrainz). */
  function TICK_HTML(cls){
    return '<div class="hmx-tick ' + cls + '" hidden><div class="tick-move"><span class="tick-text"></span><span class="tick-text" aria-hidden="true"></span></div></div>';
  }

  var SONGS = {}, INFO = {}, lastTick = '', NOWKEY = 'hmxNowText';
  catalogReady.then(function(){ (CAT || []).forEach(function(x){ if (x.v) SONGS[x.v] = x; }); orderCache = null; refreshNow(); });
  fetch('show/songinfo.json', {cache: 'no-cache'}).then(function(r){ return r.ok ? r.json() : {}; })
    .then(function(d){ INFO = d || {}; refreshNow(); }).catch(function(){});
  var BANDS = {};   // band key -> {country, ...} from show/bands.json, for the country in the scroll
  fetch('show/bands.json', {cache: 'no-cache'}).then(function(r){ return r.ok ? r.json() : {}; })
    .then(function(d){ BANDS = d || {}; refreshNow(); }).catch(function(){});
  function songLine(id, fallback){   // Band - Song (Year) - Country
    var s = SONGS[id], i = INFO[id] || {};
    var title = s ? s.t.replace(/\s*[\(\[][^\)\]]*(remaster|official|video|audio|lyric|visuali[sz]er|\bhd\b|4k|explicit)[^\)\]]*[\)\]]/gi, '').trim() : '';
    var text = s ? s.n + ' \u2014 ' + (title || s.t) : (fallback || '');
    if (!text) return '';
    if (i.y) text += ' (' + i.y + ')';   // owner, Nov 22, 2026: band, song, year, country (no album)
    var c = s && BANDS[s.b] && BANDS[s.b].country;
    if (c && c !== 'International') text += ' \u00b7 ' + c;
    return text;
  }
  function bandOf(id){ var s = SONGS[id]; return s ? s.n : ''; }
  function nextId(){   // the song after the one playing (24/7 radio only)
    if (!mode || mode.kind !== 'radio') return '';
    var list = goodSongs(); if (!list.length) return '';
    return list[(radioIndex() + 1) % list.length];
  }

  function playingHere(){ try { var st = player.getPlayerState(); return st === 1 || st === 3 || st === 2; } catch (x) { return false; } }
  function nowPlaying(){
    var vd = null; try { vd = player.getVideoData && player.getVideoData(); } catch (x) {}
    var id = vd && vd.video_id; if (!id) return;
    var text = songLine(id, vd.title);
    if (!text) return;
    var next = bandOf(nextId());
    setTicker(text, next, true);
    if (POPOUT){ try { localStorage.setItem(NOWKEY, JSON.stringify({text: text, next: next, ts: Date.now()})); } catch (x) {} }
  }

  function refreshNow(){
    lastTick = '';
    if (player && mode && playingHere()){ nowPlaying(); return; }
    if (!POPOUT && popoutAlive()){
      var n = null; try { n = JSON.parse(localStorage.getItem(NOWKEY) || 'null'); } catch (x) {}
      if (n && n.text){ setTicker(n.text, n.next || '', true); return; }
    }
    if (POPOUT) return;
    var list = goodSongs(); if (!list.length) return;
    var p = savedPos();
    if (p === null){ p = Math.floor(Math.random() * list.length) - 1; savePos(p); }   // new listener: pick their starting song now, so tapping plays exactly this one
    var L = list.length, id = list[((p + 1) % L + L) % L], nx = list[((p + 2) % L + L) % L];
    setTicker(songLine(id), bandOf(nx), false);
  }

  function setTicker(text, next, live){
    var tk = document.querySelector('#hmx-now .hmx-tick');
    if (!tk || !text) return;
    var key = text + '|' + next + '|' + live;
    if (key === lastTick) return;
    lastTick = key;
    var parts = tk.querySelectorAll('.tick-text');
    var hint = live ? 'Live now on HeavyMusix Radio: ' + text + '. Show the player.' : 'Live now on HeavyMusix Radio: ' + text + '. Play it.';
    var line = function(copy){
      return '<button type="button" class="tick-live"' + (copy ? ' tabindex="-1"' : '') + ' aria-label="' + esc(hint) + '">' +
        '<span class="tick-label">LIVE NOW:</span> ' + esc(text) + '</button>' +
        (next ? '<span class="tick-next"><span class="tick-label">NEXT:</span> ' + esc(next) + '</span>' : '');
    };
    parts[0].innerHTML = line(false); parts[1].innerHTML = line(true);
    tk.hidden = false;
    var liveEl = document.querySelector('.hmx-live');
    if (liveEl && live) liveEl.textContent = 'Live now: ' + text + (next ? '. Next: ' + next : '');
    tk.classList.remove('scroll');
    requestAnimationFrame(function(){
      var w = parts[0].offsetWidth;
      if (w > tk.clientWidth - 16){ tk.style.setProperty('--dur', Math.max(12, Math.round(w / 45)) + 's'); tk.classList.add('scroll'); }
    });
  }

  function attachBar(b){
    var h = document.querySelector('header.site');
    if (h && !POPOUT){ h.appendChild(b); document.body.classList.remove('has-now'); }   // right under the HeavyMusix banner, sticks with it
    else { document.body.appendChild(b); document.body.classList.add('has-now'); }      // pop-out window: along the bottom
  }
  function buildNowBar(){
    if (document.getElementById('hmx-now')) return;
    var b = document.createElement('div');
    b.id = 'hmx-now';
    b.setAttribute('role', 'region');
    b.setAttribute('aria-label', 'HeavyMusix Radio: now playing');
    b.innerHTML = TICK_HTML('now-tick') + '<span class="hmx-sr hmx-live" aria-live="polite"></span>';
    attachBar(b);
    window.addEventListener('storage', function(e){ if (e.key === NOWKEY || e.key === ALIVE) refreshNow(); });
    setInterval(function(){ if (!mode){ refreshNow(); syncControls(); } }, 15000);   // pop-out closed or song changed there
    refreshNow(); syncControls();
  }
  document.addEventListener('click', function(e){
    if (!e.target.closest) return;
    var lv = e.target.closest('#hmx-now .hmx-tick');   // a tap anywhere on the scroll plays the radio (or shows the player)
    if (lv){
      if (mode && player){   // already playing here: bring the player back to normal size and make sure it plays
        try { if (player.getPlayerState() !== 1) player.playVideo(); } catch (x) {}
        var d = dock(); if (d){ d.classList.remove('min'); var f = d.querySelector('.now-btn'); if (f) f.focus(); }
      } else if (!POPOUT && popoutAlive()) tellPopout({cmd: 'show'}, function(){ window.hmxPlayRadio(); });
      else window.hmxPlayRadio();
      return;
    }
  });


  /* Our own playlist: every listener gets a personal shuffle of the WHOLE song list (all songs, any size).
     Bands are spread EVENLY (same method as the YouTube reshuffle): each band's songs get evenly spaced
     spots across the pass, and a band waits up to 20 songs before playing again (bands with lots of songs
     wait a little less so they still fit), never twice in a row. Nothing repeats until every song has
     played; then it reshuffles, remembering the last bands heard so the new pass doesn't start with them.
     New songs added to the playlist slot in after the current song, away from their own band. */
  var ORDER = 'hmxOrder', ORDER_VER = 2, GAP = 20;
  function bandKey(v){ var s = SONGS[v] || {}; return s.b || (s.n || v).toLowerCase(); }
  function shuffleArr(a){ for (var i = a.length - 1; i > 0; i--){ var j = Math.floor(Math.random() * (i + 1)); var t = a[i]; a[i] = a[j]; a[j] = t; } return a; }
  function bandSpread(ids, recent){   // recent = band keys heard just before this stretch (oldest first)
    var by = {}, bands = [];
    ids.forEach(function(v){ var b = bandKey(v); if (!by[b]){ by[b] = []; bands.push(b); } by[b].push(v); });
    var spot = {}, wait = {}, lastAt = {}, left = ids.length, pos = 0;
    bands.forEach(function(b){
      var a = shuffleArr(by[b]), n = a.length, u = Math.random();
      a.forEach(function(v, j){ spot[v] = (j + u) / n; });
      wait[b] = Math.max(1, Math.min(GAP, Math.floor(0.75 * left / n)));
    });
    (recent || []).forEach(function(b, i, r){ lastAt[b] = i - r.length; });   // negative spots: heard before this pass
    var out = [];
    while (left){
      var active = bands.filter(function(b){ return by[b].length; }), cap = active.length - 1;
      var ok = cap > 0 ? active.filter(function(b){ return !(b in lastAt) || pos - lastAt[b] - 1 >= Math.min(wait[b], cap); }) : [];
      if (!ok.length) ok = active.filter(function(b){ return lastAt[b] !== pos - 1; });
      if (!ok.length) ok = active;
      var pick = ok[0];
      ok.forEach(function(b){ if (spot[by[b][0]] < spot[by[pick][0]]) pick = b; });
      out.push(by[pick].shift()); lastAt[pick] = pos; pos++; left--;
    }
    return out;
  }
  function bandsBefore(ids, i){ return ids.slice(Math.max(0, i - GAP + 1), i + 1).map(bandKey); }   // bands of the last GAP songs up to spot i
  function slotIn(ids, v, from){   // put a new song somewhere after `from`, at least 5 songs away from its own band
    var b = bandKey(v), room = ids.length - from, at = ids.length;
    for (var t = 0; t < 40; t++){
      var c = from + Math.floor(Math.random() * Math.max(1, room)), clear = true;
      for (var k = Math.max(0, c - 5); k < Math.min(ids.length, c + 5); k++) if (bandKey(ids[k]) === b){ clear = false; break; }
      if (clear){ at = c; break; }
    }
    ids.splice(Math.min(at, ids.length), 0, v);
  }
  function personalOrder(recent){
    var all = (catalog || []).filter(function(v){ return !BAD[v]; });
    if (!all.length) return [];
    var o = null; try { o = JSON.parse(localStorage.getItem(ORDER) || 'null'); } catch (x) {}
    var ids = o && o.ids ? o.ids : null;
    if (!ids){ ids = bandSpread(all, recent); }
    else {
      var have = {}; all.forEach(function(v){ have[v] = 1; });
      ids = ids.filter(function(v){ return have[v]; });                       // drop songs removed from the playlist
      var p = savedPos(); p = p === null ? -1 : Math.min(p, ids.length - 1);
      if (o.ver !== ORDER_VER && p + 1 < ids.length)                          // order made by the old shuffle: re-deal what's left
        ids = ids.slice(0, p + 1).concat(bandSpread(ids.slice(p + 1), p >= 0 ? bandsBefore(ids, p) : []));
      var inList = {}; ids.forEach(function(v){ inList[v] = 1; });
      var fresh = all.filter(function(v){ return !inList[v]; });              // new songs: slot them in after the listener's spot
      shuffleArr(fresh).forEach(function(v){ slotIn(ids, v, Math.max(0, p + 2)); });
    }
    try { localStorage.setItem(ORDER, JSON.stringify({ids: ids, ver: ORDER_VER, made: (o && o.ids && o.made) || Date.now()})); } catch (x) {}
    return ids;
  }
  function reshuffle(prev){   // prev = the order just finished, so the new pass doesn't open with the same bands
    var recent = prev && prev.length ? bandsBefore(prev, prev.length - 1) : [];
    try { localStorage.removeItem(ORDER); } catch (x) {}
    return personalOrder(recent);
  }
  var orderCache = null;
  function goodSongs(){ if (!orderCache) orderCache = personalOrder(); return orderCache; }
  function savedPos(){ try { var p = JSON.parse(localStorage.getItem(POS) || 'null'); return p && typeof p.i === 'number' ? p.i : null; } catch (x) { return null; } }
  function savePos(i){ try { localStorage.setItem(POS, JSON.stringify({i: i, ts: Date.now()})); } catch (x) {} }
  function radioIndex(){ try { return chunkStart + Math.max(0, player.getPlaylistIndex()); } catch (x) { return chunkStart; } }
  function loadChunk(from, startSeconds){
    var list = goodSongs();
    if (!list.length){   // no catalog: fall back to the playlist itself (first 200 only)
      player.loadPlaylist({list: PL, listType: 'playlist', index: 0});
      player.setLoop(true); return;
    }
    if (from >= list.length){ orderCache = reshuffle(list); list = orderCache; from = 0; savePos(-1); }   // heard every song: new full shuffle
    from = ((from % list.length) + list.length) % list.length;
    chunkStart = from;
    var ids = list.slice(from, from + CHUNK);
    player.setLoop(false);
    player.loadPlaylist(ids, 0, startSeconds || 0);
    savePos(from);
  }
  function nextChunk(){ loadChunk(chunkStart + ((player.getPlaylist() || []).length || CHUNK)); }
  function playRadio(){
    mode = {kind: 'radio'};
    catalogReady.then(function(){
      withPlayer(function(){
        var p = savedPos();
        // New listener: start at a random spot. Returning listener: carry on from their place.
        loadChunk(p !== null ? p + 1 : Math.floor(Math.random() * Math.max(1, goodSongs().length)));
        setLabel(' · 24/7 playlist');
      });
    });
  }

  function playEpisode(i){
    loadEpisodes().then(function(eps){
      if (!eps.length){ playRadio(); return; }
      i = ((i % eps.length) + eps.length) % eps.length;
      mode = {kind: 'episode', i: i};
      var list = eps[i].play.filter(function(v){ return !BAD[v]; });
      withPlayer(function(){
        player.setLoop(false);
        player.loadPlaylist(list.length ? list : eps[i].play, 0);
        setLabel(' · Show #' + eps[i].n);
      });
    });
  }

  function startDefault(){
    loadEpisodes().then(function(eps){
      if (eps.length) playEpisode(eps.length - 1);   // newest episode first
      else playRadio();                                // no episodes yet: the playlist
    });
  }

  var errors = 0;
  function nextEpisode(){
    var next = mode.i + 1;
    playEpisode(next >= episodes.length ? 0 : next);   // next episode, or start over at #1
  }
  function atEpisodeEnd(){
    var idx = player.getPlaylistIndex(), list = player.getPlaylist() || [];
    return idx >= list.length - 1;
  }
  function onState(e){
    if (e.data === 1 && mode && mode.kind === 'radio') savePos(radioIndex());
    if (e.data === 1) nowPlaying();
    syncControls();
    if (e.data === 1){ errors = 0; var r = document.querySelector('#hmx-dock .dock-resume'); if (r) r.remove(); }
    if (e.data !== 0 || !mode) return;               // 0 = ended
    if (mode.kind === 'song'){ startDefault(); return; }
    if (mode.kind === 'episode' && atEpisodeEnd()) nextEpisode();
    if (mode.kind === 'radio' && atEpisodeEnd()) nextChunk();
  }

  /* A song that won't play (removed, private, or not allowed on other sites): skip to the next one. */
  function onError(){
    if (!mode) return;
    errors++;
    if (mode.kind === 'song'){
      var v = mode.v; BAD[v] = 1; cantPlay(v, mode.label);
      startDefault(); return;
    }
    if (errors > 10){ setLabel(' \u00b7 trouble loading, tap \u25c9 to try again'); errors = 0; return; }   // never skip forever
    try { var vd = player.getVideoData && player.getVideoData(); if (vd && vd.video_id) BAD[vd.video_id] = 1; } catch (x) {}
    if (mode.kind === 'episode' && atEpisodeEnd()){ nextEpisode(); return; }
    if (mode.kind === 'radio' && atEpisodeEnd()){ nextChunk(); return; }
    setTimeout(function(){ try { player.nextVideo(); } catch (x) {} }, 400);
  }


  /* Remember where the music is, so a refresh picks it back up */
  var KEY = 'hmxNowPlaying';
  function remember(){
    if (!player || !ready || !mode || !player.getCurrentTime) return;
    try {
      var st = {m: mode.kind, t: Math.floor(player.getCurrentTime() || 0), ts: Date.now()};
      if (mode.kind === 'radio') st.idx = radioIndex();
      if (mode.kind === 'episode'){ st.i = mode.i; st.idx = player.getPlaylistIndex(); }
      if (mode.kind === 'song'){ var vd = player.getVideoData && player.getVideoData(); st.v = (vd && vd.video_id) || mode.v; st.label = mode.label || ''; }
      sessionStorage.setItem(KEY, JSON.stringify(st));
      localStorage.setItem(KEY, JSON.stringify(st));
    } catch (x) {}
  }
  function forget(){ try { sessionStorage.removeItem(KEY); localStorage.removeItem(KEY); } catch (x) {} }
  setInterval(remember, 4000);
  window.addEventListener('pagehide', remember);
  function showResume(){
    var box = document.querySelector('#hmx-dock .dock-video'); if (!box || box.querySelector('.dock-resume')) return;
    var b = document.createElement('button');
    b.type = 'button'; b.className = 'dock-resume'; b.innerHTML = '&#9654; Keep listening';
    b.addEventListener('click', function(){ try { player.playVideo(); } catch (x) {} b.remove(); });
    box.appendChild(b);
  }
  function checkStarted(){
    setTimeout(function(){
      try { if (player.getPlayerState() !== 1 && player.getPlayerState() !== 3) showResume(); } catch (x) {}
    }, 2500);
  }
  function resumeIfPlaying(){
    var st = null;
    try { st = JSON.parse(sessionStorage.getItem(KEY) || localStorage.getItem(KEY) || 'null'); } catch (x) {}
    if (!POPOUT && popoutAlive()) return true;   // the pop-out window has the music
    if (!st || !st.ts || Date.now() - st.ts > 30 * 60 * 1000) return false;
    if (st.m === 'song' && st.v){
      mode = {kind: 'song', v: st.v, label: st.label};
      withPlayer(function(){ player.setLoop(false); player.loadVideoById({videoId: st.v, startSeconds: st.t || 0}); setLabel(st.label ? ' \u00b7 ' + st.label : ''); checkStarted(); });
    } else if (st.m === 'episode'){
      loadEpisodes().then(function(eps){
        if (!eps.length) return;
        var i = Math.min(st.i || 0, eps.length - 1);
        mode = {kind: 'episode', i: i};
        withPlayer(function(){ player.setLoop(false); player.loadPlaylist(eps[i].play, st.idx || 0, st.t || 0); setLabel(' \u00b7 Show #' + eps[i].n); checkStarted(); });
      });
    } else {
      mode = {kind: 'radio'};
      catalogReady.then(function(){ withPlayer(function(){ loadChunk(st.idx || 0, st.t || 0); setLabel(' \u00b7 24/7 playlist'); checkStarted(); }); });
    }
    return true;
  }

  /* Computers (mouse + big screen): music always plays in the pop-out window, so it keeps
     going after the fan leaves heavymusix.com. Browsers only allow opening a window on a click,
     so this happens on the fan's first play click. Phones keep the pinned player
     (phone browsers pause background tabs anyway). */
  var START = 'hmxStartCmd';
  function wantsPopout(){
    if (POPOUT || dock()) return false;
    try { return window.matchMedia('(pointer: fine) and (min-width: 900px)').matches; } catch (x) { return false; }
  }
  function launchPopout(cmd){
    try { localStorage.setItem(START, JSON.stringify(cmd)); } catch (x) {}
    var w = window.open('player.html', 'hmxPlayer', 'popup,width=' + POPW + ',height=' + POPH);
    if (!w){ try { localStorage.removeItem(START); } catch (x) {} return false; }   // pop-ups blocked: use the pinned player
    try { localStorage.setItem(ALIVE, String(Date.now())); } catch (x) {}
    var r = document.getElementById('radio');
    if (r) r.innerHTML = '<button class="playcover" type="button" onclick="startRadio()">' +
      '<span class="pc-kicker">Playing in its own window</span>' +
      '<span class="pc-title">HeavyMusix <em>Radio</em></span>' +
      '<span class="pc-cta">The radio opened in a small window. Browse anywhere on the web and it keeps rolling until you close it.</span></button>';
    return true;
  }
  function runCmd(m){
    if (m.cmd === 'song'){ mode = {kind: 'song', v: m.v, label: m.label}; withPlayer(function(){ player.setLoop(false); player.loadVideoById(m.v); setLabel(m.label ? ' \u00b7 ' + m.label : ''); checkStarted(); }); }
    if (m.cmd === 'episode') window.hmxPlayEpisode(m.n);
    if (m.cmd === 'radio') playRadio();
    if (m.cmd === 'toggle' || m.cmd === 'next' || m.cmd === 'prev' || m.cmd === 'size' || m.cmd === 'off') act(m.cmd);
    if (m.cmd === 'show'){ try { window.focus(); } catch (x) {} if (!mode) startDefault(); }
  }

  window.startRadio = function(){
    if (tellPopout({cmd: 'show'}, window.startRadio)) return;
    if (dock() && mode){ dock().classList.remove('min'); return; }
    if (wantsPopout() && launchPopout({cmd: 'show'})) return;
    startDefault();
  };
  window.hmxPlaySong = function(v, label){
    if (BAD[v]){ cantPlay(v, label); return; }
    if (tellPopout({cmd: 'song', v: v, label: label}, function(){ window.hmxPlaySong(v, label); })) return;
    if (wantsPopout() && launchPopout({cmd: 'song', v: v, label: label})) return;
    mode = {kind: 'song', v: v, label: label};
    withPlayer(function(){ player.setLoop(false); player.loadVideoById(v); setLabel(label ? ' · ' + label : ''); });
  };
  window.hmxPlayEpisode = function(n){
    if (tellPopout({cmd: 'episode', n: n}, function(){ window.hmxPlayEpisode(n); })) return;
    if (wantsPopout() && launchPopout({cmd: 'episode', n: n})) return;
    loadEpisodes().then(function(eps){
      for (var i = 0; i < eps.length; i++) if (eps[i].n === n) return playEpisode(i);
      playRadio();
    });
  };
  window.hmxPlayRadio = function(){
    if (tellPopout({cmd: 'radio'}, window.hmxPlayRadio)) return;
    if (wantsPopout() && launchPopout({cmd: 'radio'})) return;
    playRadio();
  };

  /* Keep the player alive: while it is playing, load other pages of the site in place. */
  function sameSite(a){
    if (!a || !a.href || a.target === '_blank' || a.hasAttribute('download')) return false;
    var u = new URL(a.href, location.href);
    if (u.origin !== location.origin) return false;
    if (u.pathname === location.pathname && u.search === location.search && u.hash) return false;
    return /(\.html|\/)$/.test(u.pathname);
  }

  function runScripts(nodes){
    var chain = Promise.resolve();
    nodes.forEach(function(old){
      chain = chain.then(function(){
        if (old.src && /radio\.js/.test(old.src)) return;
        return new Promise(function(done){
          var s = document.createElement('script');
          if (old.src){ s.src = old.src; s.onload = s.onerror = done; }
          else { s.textContent = old.textContent; }
          document.body.insertBefore(s, dock());
          if (!old.src) done();
        });
      });
    });
    return chain;
  }

  function load(url, push){
    return fetch(url, {credentials: 'same-origin'}).then(function(r){
      if (!r.ok) throw new Error(r.status);
      return r.text();
    }).then(function(html){
      var doc = new DOMParser().parseFromString(html, 'text/html');
      var d = dock();
      document.title = doc.title;
      document.body.className = doc.body.className;
      var nb = document.getElementById('hmx-now'); if (nb) nb.remove();
      Array.prototype.slice.call(document.body.childNodes).forEach(function(n){ if (n !== d && n !== nb) n.remove(); });
      var scripts = [];
      Array.prototype.slice.call(doc.body.childNodes).forEach(function(n){
        if (n.nodeName === 'SCRIPT'){ if (!/goatcounter/.test(n.outerHTML)) scripts.push(n); return; }
        if (n.querySelectorAll) n.querySelectorAll('script').forEach(function(s){ scripts.push(s); s.remove(); });
        document.body.insertBefore(document.importNode(n, true), d);
      });
      if (nb) attachBar(nb);
      if (push) history.pushState({hmx: 1}, '', url);
      try { if (window.goatcounter && goatcounter.count) goatcounter.count({path: location.pathname + location.search, title: document.title}); } catch(e){}
      var hash = new URL(url, location.href).hash;
      var target = hash && document.getElementById(hash.slice(1));
      if (target) target.scrollIntoView(); else window.scrollTo(0, 0);
      return runScripts(scripts).then(markHome);
    }).catch(function(){ location.href = url; });
  }

  function isPhone(){ return matchMedia('(pointer: coarse)').matches && !matchMedia('(any-pointer: fine)').matches; }
  /* Phones: take target="_blank" off outside links before the tap lands, so the phone opens them in this tab. */
  function sameTabOnPhone(e){
    if (!isPhone()) return;
    var a = e.target && e.target.closest && e.target.closest('a[target]');
    if (a && /^https?:/.test(a.href) && new URL(a.href).origin !== location.origin){ a.removeAttribute('target'); }
  }
  ['touchstart', 'pointerdown', 'click'].forEach(function(t){ document.addEventListener(t, sameTabOnPhone, {capture: true, passive: true}); });

  /* Outside links (news stories, YouTube, Instagram...) always open in a new tab,
     so HeavyMusix stays open and the music keeps playing. */
  document.addEventListener('click', function(e){
    if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    var a = e.target.closest('a');
    if (a && /^https?:/.test(a.href) && new URL(a.href).origin !== location.origin){
      /* Phones and tablets: let the phone follow the link itself, in this same tab (no new tab, no script
         navigation). A real tap on an Instagram, YouTube, Threads or Maps link hands it to the app and leaves
         HeavyMusix open right where it was; any other site opens in this tab and Back returns here. A new tab
         (or a script-made jump) was left behind as a blank white page (owner, Nov 26, 2026). */
      if (isPhone()){ return; }
      e.preventDefault();
      window.open(a.href, '_blank', 'noopener');
      return;
    }
    if (!dock()) return;
    if (!sameSite(a)) return;
    e.preventDefault();
    load(a.href, true);
  });

  /* Search boxes: open the results in place too, so the music never stops. */
  document.addEventListener('submit', function(e){
    var f = e.target;
    if (e.defaultPrevented || !dock() || (f.method || 'get').toLowerCase() !== 'get') return;
    var u = new URL(f.getAttribute('action') || location.href, location.href);
    if (u.origin !== location.origin || !/(\.html|\/)$/.test(u.pathname)) return;
    e.preventDefault();
    u.search = new URLSearchParams(new FormData(f)).toString();
    load(u.href, true);
  });

  window.addEventListener('popstate', function(){
    if (dock()) load(location.href, false);
  });

  function boot(){
    if (!POPOUT){ buildNowBar(); resumeIfPlaying(); markHome(); return; }
    /* Pop-out window: say it is alive, take requests from the site's pages, start the music. */
    buildNowBar();
    /* Shrink the window to fit: the 200x200 video (YouTube's smallest allowed) plus the two button rows. */
    setTimeout(function(){ try { var top = document.querySelector('#hmx-dock .dock-top'), nb = document.getElementById('hmx-now'); var need = 200 + (top ? top.offsetHeight + 2 : 42) + (nb ? nb.offsetHeight : 47); window.resizeTo(Math.max(232, window.outerWidth - window.innerWidth + 204), window.outerHeight - window.innerHeight + need); } catch (x) {} }, 300);
    var beat = function(){ try { localStorage.setItem(ALIVE, String(Date.now())); } catch (x) {} };
    beat(); setInterval(beat, 2000);
    window.addEventListener('pagehide', function(){ forget(); try { localStorage.removeItem(ALIVE); } catch (x) {} });   // closing the window stops the radio
    if (chan) chan.onmessage = function(e){ var m = e.data || {}; if (!m.cmd) return; chan.postMessage({ack: m.id}); runCmd(m); };
    var first = null;
    try { first = JSON.parse(localStorage.getItem(START) || 'null'); localStorage.removeItem(START); } catch (x) {}
    if (first && first.cmd !== 'show'){ runCmd(first); return; }
    if (first){ forget(); startDefault(); setTimeout(function(){ if (player) checkStarted(); }, 1500); return; }
    if (!resumeIfPlaying()){ startDefault(); setTimeout(function(){ if (player) checkStarted(); }, 1500); }
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot); else boot();
})();

/* Get the app: fans can put HeavyMusix Radio on their phone's home screen or their computer
   (it opens straight to the site and the radio). Any button with data-install opens it. */
(function(){
  if (window.hmxAppReady) return; window.hmxAppReady = true;
  var deferred = null;
  var standalone = function(){ try { return matchMedia('(display-mode: standalone)').matches || navigator.standalone === true; } catch (x) { return false; } };
  if ('serviceWorker' in navigator && location.protocol === 'https:') {
    window.addEventListener('load', function(){ navigator.serviceWorker.register('/sw.js').catch(function(){}); });
  }
  window.addEventListener('beforeinstallprompt', function(e){ e.preventDefault(); deferred = e; });
  window.addEventListener('appinstalled', function(){ deferred = null; hideButtons(); });
  function hideButtons(){ if (standalone()) document.querySelectorAll('[data-install]').forEach(function(b){ b.hidden = true; }); }
  function steps(){
    var ua = navigator.userAgent, ios = /iPhone|iPad|iPod/.test(ua) || (/Macintosh/.test(ua) && navigator.maxTouchPoints > 1);
    var android = /Android/.test(ua), mac = /Macintosh/.test(ua) && !ios, safari = /Safari/.test(ua) && !/Chrome|CriOS|FxiOS|Edg|OPR/.test(ua);
    var firefox = /Firefox|FxiOS/.test(ua);
    if (ios) return '<li>Tap the <strong>Share</strong> button (the square with an arrow).</li><li>Scroll and tap <strong>Add to Home Screen</strong>, then <strong>Add</strong>.</li><li>Tap the HeavyMusix skull on your home screen any time to open the radio.</li>';
    if (android) return '<li>Tap your browser&rsquo;s menu (&#8942;).</li><li>Tap <strong>Install app</strong> or <strong>Add to Home screen</strong>.</li><li>Tap the HeavyMusix skull on your home screen any time to open the radio.</li>';
    if (mac && safari) return '<li>In the Safari menu bar, choose <strong>File &gt; Add to Dock</strong>.</li><li>Click the HeavyMusix skull in your Dock any time to open the radio.</li>';
    if (firefox) return '<li>Press <strong>Ctrl+D</strong> (or <strong>Cmd+D</strong> on a Mac) to bookmark HeavyMusix.</li><li>Or make it your home page: <strong>Settings &gt; Home &gt; Homepage</strong>, then enter heavymusix.com/radio.</li>';
    return '<li>Click the <strong>install</strong> icon at the right end of the address bar, or open the browser menu (&#8942;) and choose <strong>Install HeavyMusix</strong> (in Edge: <strong>Apps &gt; Install this site as an app</strong>).</li><li>HeavyMusix gets its own icon on your desktop and taskbar.</li>';
  }
  function showHelp(opener){
    var d = document.getElementById('hmx-app');
    if (!d){
      d = document.createElement('dialog'); d.id = 'hmx-app'; d.setAttribute('aria-labelledby', 'hmx-app-h');
      document.body.appendChild(d);
      d.addEventListener('click', function(e){ if (e.target === d || e.target.closest('.app-close')) d.close(); });
      d.addEventListener('close', function(){ if (d._opener) try { d._opener.focus(); } catch (x) {} });
    }
    d.innerHTML = '<h2 id="hmx-app-h">Put HeavyMusix Radio on your phone or computer</h2>' +
      '<ol>' + steps() + '</ol>' +
      '<p class="muted">Want it to open every time you start your browser? Set your browser&rsquo;s start page or home page to <strong>heavymusix.com/radio</strong> (Settings &gt; On startup, or Settings &gt; Home page).</p>' +
      '<button type="button" class="btn app-close">Got it</button>';
    d._opener = opener;
    try { d.showModal(); } catch (x) { d.setAttribute('open', ''); }
    var c = d.querySelector('.app-close'); if (c) c.focus();
  }
  document.addEventListener('click', function(e){
    var b = e.target.closest && e.target.closest('[data-install]');
    if (!b) return;
    e.preventDefault();
    if (deferred){
      var p = deferred; deferred = null;
      p.prompt();
      p.userChoice.then(function(r){ if (r.outcome !== 'accepted') deferred = p; }).catch(function(){});
      return;
    }
    showHelp(b);
  });
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', hideButtons); else hideButtons();
  if (standalone()) new MutationObserver(hideButtons).observe(document.body, {childList: true});   // pages load in place: keep the buttons hidden inside the app
})();

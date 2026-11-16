/* HeavyMusix Radio player.
   - Pinned to the corner; keeps playing while you browse the site.
   - Plays the Radio Show episodes in order and moves to the next one automatically.
     When there is no newer episode it starts over at Episode 1.
     With no episodes yet, it plays the HeavyMusix Radio playlist (24/7).
   - Fans can play any single song; when it ends, the radio picks back up. */
(function(){
  if (window.__hmxRadio) return;
  window.__hmxRadio = true;

  /* Hamburger menu: the button opens and closes the menu on phones and tablets. */
  document.addEventListener('click', function(e){
    var t = e.target.closest && e.target.closest('.navtoggle');
    var h = document.querySelector('header.site');
    if (!h) return;
    if (t){
      var open = h.classList.toggle('open');
      t.setAttribute('aria-expanded', open ? 'true' : 'false');
      t.setAttribute('aria-label', open ? 'Close menu' : 'Open menu');
      return;
    }
    if (h.classList.contains('open') && (e.target.closest('nav.main a') || !e.target.closest('header.site'))){
      h.classList.remove('open');
      var b = h.querySelector('.navtoggle'); if (b){ b.setAttribute('aria-expanded', 'false'); b.setAttribute('aria-label', 'Open menu'); }
    }
  });
  document.addEventListener('keydown', function(e){
    var h = document.querySelector('header.site');
    if (e.key === 'Escape' && h && h.classList.contains('open')){ h.classList.remove('open'); var b = h.querySelector('.navtoggle'); if (b){ b.setAttribute('aria-expanded', 'false'); b.setAttribute('aria-label', 'Open menu'); b.focus(); } }
  });
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
    var w = window.open('player.html', 'hmxPlayer', 'popup,width=460,height=320');
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
    d.setAttribute('aria-label', 'HeavyMusix Radio player');
    d.innerHTML =
      '<div class="dock-bar"' + (POPOUT ? '' : ' title="Drag to move the player"') + '>' +
      (POPOUT ? '' : '<span class="dock-grip" aria-hidden="true">&#8942;&#8942;</span>') +
      '<span class="dock-title">HeavyMusix Radio<span class="dock-now"></span></span>' +
      '<button type="button" class="dock-btn" data-act="radio" aria-label="Back to the radio" title="Back to the radio">&#9673;</button>' +
      (POPOUT ? '' :
      '<button type="button" class="dock-btn" data-act="pop" aria-label="Pop out the player so it keeps playing when you leave the site" title="Pop out: keeps playing when you leave the site">&#10697;</button>' +
      '<button type="button" class="dock-btn" data-act="min" aria-label="Shrink or expand the player" title="Shrink or expand">&#8211;</button>') +
      '<button type="button" class="dock-btn" data-act="close" aria-label="Stop and close the player" title="Stop">&#215;</button></div>' +
      '<div class="dock-video"><div id="hmx-yt"></div></div>';
    d.addEventListener('click', function(e){
      var b = e.target.closest('.dock-btn'); if (!b) return;
      if (b.dataset.act === 'min') d.classList.toggle('min');
      if (b.dataset.act === 'radio') startDefault();
      if (b.dataset.act === 'pop') openPopout();
      if (b.dataset.act === 'close'){
        forget();
        if (POPOUT){ try { localStorage.removeItem(ALIVE); } catch (x) {} window.close(); return; }
        d.remove(); location.reload();
      }
    });
    document.body.appendChild(d);
    if (!POPOUT){ makeDraggable(d); markHome(); }
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
    y = Math.max(4, Math.min(y, window.innerHeight - h - 4));
    d.style.left = x + 'px'; d.style.top = y + 'px';
    d.style.right = 'auto'; d.style.bottom = 'auto';
    return [x, y];
  }
  function makeDraggable(d){
    var bar = d.querySelector('.dock-bar'), start = null;
    try { var saved = JSON.parse(localStorage.getItem('hmxDockPos') || 'null'); if (saved && saved[1] > 130 && window.innerWidth > 600) place(d, saved[0], saved[1]); } catch (x) {}   // never cover the menu; phones keep the corner
    bar.addEventListener('pointerdown', function(e){
      if (e.target.closest('.dock-btn')) return;
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

  function withPlayer(fn){
    if (!dock()) buildDock();
    else dock().classList.remove('min');
    if (ready) fn(); else pending = fn;
  }

  var PL_SIZE = 650;   // about how many songs are in the playlist (updated from show/catalog.json)
  fetch('show/catalog.json', {cache: 'no-cache'}).then(function(r){ return r.json(); })
    .then(function(c){ if (c && c.length) PL_SIZE = c.length; }).catch(function(){});
  function playRadio(){
    mode = {kind: 'radio'};
    withPlayer(function(){
      // Start at a random spot so every visit sounds different (the playlist order itself keeps the artist rules).
      player.loadPlaylist({list: PL, listType: 'playlist', index: Math.floor(Math.random() * Math.max(1, PL_SIZE - 5))});
      player.setLoop(true);
      setLabel(' · 24/7 playlist');
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
    if (e.data === 1){ errors = 0; var r = document.querySelector('#hmx-dock .dock-resume'); if (r) r.remove(); }
    if (e.data !== 0 || !mode) return;               // 0 = ended
    if (mode.kind === 'song'){ startDefault(); return; }
    if (mode.kind === 'episode' && atEpisodeEnd()) nextEpisode();
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
    setTimeout(function(){ try { player.nextVideo(); } catch (x) {} }, 400);
  }


  /* Remember where the music is, so a refresh picks it back up */
  var KEY = 'hmxNowPlaying';
  function remember(){
    if (!player || !ready || !mode || !player.getCurrentTime) return;
    try {
      var st = {m: mode.kind, t: Math.floor(player.getCurrentTime() || 0), ts: Date.now()};
      if (mode.kind === 'radio') st.idx = player.getPlaylistIndex();
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
      withPlayer(function(){ player.loadPlaylist({list: PL, listType: 'playlist', index: st.idx || 0, startSeconds: st.t || 0}); player.setLoop(true); setLabel(' \u00b7 24/7 playlist'); checkStarted(); });
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
    var w = window.open('player.html', 'hmxPlayer', 'popup,width=460,height=320');
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
      Array.prototype.slice.call(document.body.childNodes).forEach(function(n){ if (n !== d) n.remove(); });
      var scripts = [];
      Array.prototype.slice.call(doc.body.childNodes).forEach(function(n){
        if (n.nodeName === 'SCRIPT'){ if (!/goatcounter/.test(n.outerHTML)) scripts.push(n); return; }
        if (n.querySelectorAll) n.querySelectorAll('script').forEach(function(s){ scripts.push(s); s.remove(); });
        document.body.insertBefore(document.importNode(n, true), d);
      });
      if (push) history.pushState({hmx: 1}, '', url);
      try { if (window.goatcounter && goatcounter.count) goatcounter.count({path: location.pathname + location.search, title: document.title}); } catch(e){}
      var hash = new URL(url, location.href).hash;
      var target = hash && document.getElementById(hash.slice(1));
      if (target) target.scrollIntoView(); else window.scrollTo(0, 0);
      return runScripts(scripts).then(markHome);
    }).catch(function(){ location.href = url; });
  }

  /* Outside links (news stories, YouTube, Instagram...) always open in a new tab,
     so HeavyMusix stays open and the music keeps playing. */
  document.addEventListener('click', function(e){
    if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    var a = e.target.closest('a');
    if (a && /^https?:/.test(a.href) && new URL(a.href).origin !== location.origin){
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
    if (!POPOUT){ resumeIfPlaying(); markHome(); return; }
    /* Pop-out window: say it is alive, take requests from the site's pages, start the music. */
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

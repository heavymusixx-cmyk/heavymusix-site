/* HeavyMusix Radio player.
   - Pinned to the corner; keeps playing while you browse the site.
   - Plays the Radio Show episodes in order and moves to the next one automatically.
     When there is no newer episode it starts over at Episode 1.
     With no episodes yet, it plays the HeavyMusix Radio playlist (24/7).
   - Fans can play any single song; when it ends, the radio picks back up. */
(function(){
  if (window.__hmxRadio) return;
  window.__hmxRadio = true;
  var PL = 'PLcJENP7Pnf5xXQk-R_SlBiDXeaSlSSJ6M';
  var player = null, ready = false, pending = null;
  var mode = null;          // {kind:'radio'} | {kind:'episode', i} | {kind:'song', v, label}
  var episodes = null;      // live episodes, oldest first

  function dock(){ return document.getElementById('hmx-dock'); }
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
    if (!r || !dock()) return;
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
      '<div class="dock-bar" title="Drag to move the player"><span class="dock-grip" aria-hidden="true">&#8942;&#8942;</span><span class="dock-title">HeavyMusix Radio<span class="dock-now"></span></span>' +
      '<button type="button" class="dock-btn" data-act="radio" aria-label="Back to the radio" title="Back to the radio">&#9673;</button>' +
      '<button type="button" class="dock-btn" data-act="min" aria-label="Shrink or expand the player" title="Shrink or expand">&#8211;</button>' +
      '<button type="button" class="dock-btn" data-act="close" aria-label="Stop and close the player" title="Stop">&#215;</button></div>' +
      '<div class="dock-video"><div id="hmx-yt"></div></div>';
    d.addEventListener('click', function(e){
      var b = e.target.closest('.dock-btn'); if (!b) return;
      if (b.dataset.act === 'min') d.classList.toggle('min');
      if (b.dataset.act === 'radio') startDefault();
      if (b.dataset.act === 'close'){ d.remove(); location.reload(); }
    });
    document.body.appendChild(d);
    makeDraggable(d);
    markHome();
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
    try { var saved = JSON.parse(localStorage.getItem('hmxDockPos') || 'null'); if (saved) place(d, saved[0], saved[1]); } catch (x) {}
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

  function playRadio(){
    mode = {kind: 'radio'};
    withPlayer(function(){
      player.loadPlaylist({list: PL, listType: 'playlist', index: 0});
      player.setLoop(true);
      setLabel(' · 24/7 playlist');
    });
  }

  function playEpisode(i){
    loadEpisodes().then(function(eps){
      if (!eps.length){ playRadio(); return; }
      i = ((i % eps.length) + eps.length) % eps.length;
      mode = {kind: 'episode', i: i};
      withPlayer(function(){
        player.setLoop(false);
        player.loadPlaylist(eps[i].play, 0);
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

  function onState(e){
    if (e.data !== 0 || !mode) return;               // 0 = ended
    if (mode.kind === 'song'){ startDefault(); return; }
    if (mode.kind === 'episode'){
      var idx = player.getPlaylistIndex(), list = player.getPlaylist() || [];
      if (idx >= list.length - 1){
        var next = mode.i + 1;
        playEpisode(next >= episodes.length ? 0 : next);   // next episode, or start over at #1
      }
    }
  }

  function onError(){
    if (!mode) return;
    if (mode.kind === 'song'){ startDefault(); return; }
    try { player.nextVideo(); } catch (x) {}
  }

  window.startRadio = function(){ if (dock() && mode){ dock().classList.remove('min'); return; } startDefault(); };
  window.hmxPlaySong = function(v, label){
    mode = {kind: 'song', v: v};
    withPlayer(function(){ player.setLoop(false); player.loadVideoById(v); setLabel(label ? ' · ' + label : ''); });
  };
  window.hmxPlayEpisode = function(n){
    loadEpisodes().then(function(eps){
      for (var i = 0; i < eps.length; i++) if (eps[i].n === n) return playEpisode(i);
      playRadio();
    });
  };
  window.hmxPlayRadio = playRadio;

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
      Array.prototype.slice.call(document.body.childNodes).forEach(function(n){ if (n !== d) n.remove(); });
      var scripts = [];
      Array.prototype.slice.call(doc.body.childNodes).forEach(function(n){
        if (n.nodeName === 'SCRIPT'){ scripts.push(n); return; }
        if (n.querySelectorAll) n.querySelectorAll('script').forEach(function(s){ scripts.push(s); s.remove(); });
        document.body.insertBefore(document.importNode(n, true), d);
      });
      if (push) history.pushState({hmx: 1}, '', url);
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

  window.addEventListener('popstate', function(){
    if (dock()) load(location.href, false);
  });
})();

/* HeavyMusix Radio: pinned player that keeps playing while you browse the site. */
(function(){
  if (window.__hmxRadio) return;
  window.__hmxRadio = true;
  var PL = 'PLcJENP7Pnf5xXQk-R_SlBiDXeaSlSSJ6M';

  function dock(){ return document.getElementById('hmx-dock'); }

  function markHome(){
    var r = document.getElementById('radio');
    if (!r || !dock()) return;
    r.classList.add('cover');
    r.innerHTML = '<button class="playcover" type="button" onclick="startRadio()">' +
      '<span class="pc-kicker">Now playing</span>' +
      '<span class="pc-title">HeavyMusix <em>Radio</em></span>' +
      '<span class="pc-cta">The player is pinned to the corner of your screen. Keep browsing and the music keeps going.</span></button>';
  }

  window.startRadio = function(){
    var d = dock();
    if (d){ d.classList.remove('min'); return; }
    d = document.createElement('aside');
    d.id = 'hmx-dock';
    d.setAttribute('aria-label', 'HeavyMusix Radio player');
    d.innerHTML =
      '<div class="dock-bar"><span class="dock-title">HeavyMusix Radio</span>' +
      '<button type="button" class="dock-btn" data-act="min" aria-label="Shrink or expand the player">&#8211;</button>' +
      '<button type="button" class="dock-btn" data-act="close" aria-label="Stop and close the player">&#215;</button></div>' +
      '<div class="dock-video"><iframe src="https://www.youtube.com/embed/videoseries?list=' + PL + '&autoplay=1&loop=1" ' +
      'title="HeavyMusix Radio playlist" allow="autoplay; encrypted-media; picture-in-picture" allowfullscreen></iframe></div>';
    d.addEventListener('click', function(e){
      var b = e.target.closest('.dock-btn'); if (!b) return;
      if (b.dataset.act === 'min') d.classList.toggle('min');
      if (b.dataset.act === 'close'){ d.remove(); location.reload(); }
    });
    document.body.appendChild(d);
    markHome();
  };

  /* Keep the player alive: while it is playing, load other pages of the site in place. */
  function sameSite(a){
    if (!a || !a.href || a.target === '_blank' || a.hasAttribute('download')) return false;
    var u = new URL(a.href, location.href);
    if (u.origin !== location.origin) return false;
    if (u.pathname === location.pathname && u.hash) return false;
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

  document.addEventListener('click', function(e){
    if (!dock() || e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    var a = e.target.closest('a');
    if (a && /^https?:/.test(a.href) && new URL(a.href).origin !== location.origin){
      e.preventDefault();
      window.open(a.href, '_blank', 'noopener');
      return;
    }
    if (!sameSite(a)) return;
    e.preventDefault();
    load(a.href, true);
  });

  window.addEventListener('popstate', function(){
    if (dock()) load(location.href, false);
  });
})();

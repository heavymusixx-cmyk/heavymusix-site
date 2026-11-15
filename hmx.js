/* HeavyMusix pages: Radio Show, Find a band, band pages. Data is refreshed by the show robot. */
var HMX = window.HMX || {};
(function(){
  function esc(s){ return String(s == null ? '' : s).replace(/[&<>"]/g, function(c){ return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]; }); }
  function get(f){ return fetch('show/' + f, {cache: 'no-cache'}).then(function(r){ if (!r.ok) throw 0; return r.json(); }); }
  function data(){
    if (HMX._d) return HMX._d;
    HMX._d = Promise.all([get('catalog.json').catch(function(){ return []; }),
                          get('bands.json').catch(function(){ return {}; }),
                          get('episodes.json').catch(function(){ return {episodes: []}; })])
      .then(function(r){ return {catalog: r[0], bands: r[1], eps: r[2].episodes || []}; });
    return HMX._d;
  }
  function where(b){ return [b.city, b.region, b.country].filter(Boolean).join(', '); }
  function playBtn(v, label){
    return '<button type="button" class="playbtn" data-v="' + esc(v) + '" data-label="' + esc(label) + '" aria-label="Play ' + esc(label) + '">&#9654; Play</button>';
  }
  document.addEventListener('click', function(e){
    var b = e.target.closest('.playbtn');
    if (b && window.hmxPlaySong){ hmxPlaySong(b.dataset.v, b.dataset.label); return; }
    var p = e.target.closest('.playep');
    if (p && window.hmxPlayEpisode){ hmxPlayEpisode(+p.dataset.n); }
  });

  HMX.renderShow = function(el){
    if (!el) return;
    data().then(function(d){
      var live = d.eps.filter(function(e){ return e.status === 'live'; }).reverse();
      var coming = d.eps.filter(function(e){ return e.status !== 'live'; }).length;
      var h = '';
      if (!live.length){
        h += '<div class="card"><h3>Episode 1 is in the works</h3><p>The first HeavyMusix Radio Show is being recorded now. Until it drops, HeavyMusix Radio plays the full playlist around the clock.</p>' +
             '<div class="btns"><button type="button" class="btn" onclick="startRadio()">Listen now</button></div></div>';
      } else {
        h += '<div class="eplist">' + live.map(function(e){
          return '<article class="card ep"><p class="date">Show #' + e.n + (e.live ? ' &middot; ' + esc(e.live) : '') + '</p><h3>' + esc(e.title) + '</h3>' +
            '<ol class="tracks">' + e.songs.map(function(s){ return '<li><a href="band.html?b=' + esc(s.b) + '">' + esc(s.band) + '</a> &ndash; ' + esc(s.song) + '</li>'; }).join('') + '</ol>' +
            '<button type="button" class="btn playep" data-n="' + e.n + '">&#9654; Play Show #' + e.n + '</button></article>';
        }).join('') + '</div>';
      }
      if (coming) h += '<p class="wupd">' + coming + ' more episode' + (coming > 1 ? 's are' : ' is') + ' in the works.</p>';
      el.innerHTML = h;
    });
  };

  HMX.renderBands = function(el){
    if (!el) return;
    data().then(function(d){
      var countries = {};
      Object.keys(d.bands).forEach(function(k){ var c = d.bands[k].country; if (c) countries[c] = 1; });
      el.innerHTML =
        '<form class="finder" onsubmit="return false" role="search">' +
        '<label for="q">Search bands, songs, cities or countries</label>' +
        '<input id="q" type="search" placeholder="Try Death Angel, Tornado of Souls, Sweden or Arizona" autocomplete="off">' +
        '<div class="filters"><select id="fc" aria-label="Country"><option value="">All countries</option>' +
        Object.keys(countries).sort().map(function(c){ return '<option>' + esc(c) + '</option>'; }).join('') + '</select>' +
        '<label class="chk"><input type="checkbox" id="fu"> Unsigned picks only</label></div></form>' +
        '<div id="results" aria-live="polite"></div>';
      var q = el.querySelector('#q'), fc = el.querySelector('#fc'), fu = el.querySelector('#fu'), out = el.querySelector('#results');
      var epsBy = {};
      d.eps.filter(function(e){ return e.status === 'live'; }).forEach(function(e){ e.songs.forEach(function(s){ (epsBy[s.v] = epsBy[s.v] || []).push(e.n); }); });
      function draw(){
        var term = q.value.trim().toLowerCase(), country = fc.value, onlyU = fu.checked;
        var bandsOk = {};
        Object.keys(d.bands).forEach(function(k){
          var b = d.bands[k];
          if (country && b.country !== country) return;
          if (onlyU && !b.unsigned) return;
          bandsOk[k] = b;
        });
        if (!term){
          var keys = Object.keys(bandsOk).filter(function(k){ return bandsOk[k].songs; }).sort(function(a, b){ return bandsOk[a].name.localeCompare(bandsOk[b].name); });
          out.innerHTML = '<h2 class="sub">' + keys.length + ' bands A&ndash;Z</h2><ul class="az">' + keys.map(function(k){
            var b = bandsOk[k];
            return '<li><a href="band.html?b=' + esc(k) + '">' + esc(b.name) + '</a>' + (b.unsigned ? ' <span class="badge">Unsigned</span>' : '') + '<span class="wsrc">' + esc(where(b) || '') + '</span></li>';
          }).join('') + '</ul>';
          return;
        }
        var hits = d.catalog.filter(function(s){
          var b = bandsOk[s.b]; if (!b) return false;
          return (s.t + ' ' + b.name + ' ' + where(b) + ' ' + (b.genre || '')).toLowerCase().indexOf(term) > -1;
        }).slice(0, 120);
        out.innerHTML = hits.length ? '<h2 class="sub">' + hits.length + (hits.length === 120 ? '+' : '') + ' songs</h2><ul class="songs">' + hits.map(function(s){
          var b = bandsOk[s.b], ep = epsBy[s.v];
          return '<li>' + playBtn(s.v, b.name + ' – ' + s.t) + '<span class="sinfo"><strong>' + esc(s.t) + '</strong><a href="band.html?b=' + esc(s.b) + '">' + esc(b.name) + '</a>' +
            (b.unsigned ? ' <span class="badge">Unsigned</span>' : '') + '<span class="wsrc">' + esc(where(b)) + (ep ? ' &middot; Played on Show #' + ep.join(', #') : '') + '</span></span></li>';
        }).join('') + '</ul>' : '<p class="lead">Nothing matches that yet. Try a band name, a song, a city or a country.</p>';
      }
      q.addEventListener('input', draw); fc.addEventListener('change', draw); fu.addEventListener('change', draw);
      var pre = new URLSearchParams(location.search).get('q'); if (pre) q.value = pre;
      draw();
    });
  };

  HMX.renderBand = function(el){
    if (!el) return;
    var key = new URLSearchParams(location.search).get('b');
    data().then(function(d){
      var b = d.bands[key];
      if (!b){ el.innerHTML = '<h1>Band not found</h1><p class="lead"><a href="bands.html">Search all bands</a></p>'; return; }
      document.title = b.name + ' | HeavyMusix';
      var songs = d.catalog.filter(function(s){ return s.b === key; });
      var eps = d.eps.filter(function(e){ return e.status === 'live' && e.songs.some(function(s){ return s.b === key; }); });
      var links = b.links || {};
      var linkHtml = Object.keys(links).filter(function(k){ return links[k]; }).map(function(k){
        return '<a class="btn ghost" href="' + esc(links[k]) + '">' + esc(k === 'merch' ? 'Band merch' : k.charAt(0).toUpperCase() + k.slice(1)) + '</a>';
      }).join('');
      el.innerHTML =
        '<p class="kicker">' + (b.unsigned ? 'HeavyMusix unsigned pick' : 'On HeavyMusix Radio') + '</p>' +
        '<h1>' + esc(b.name) + '</h1>' +
        '<p class="lead">' + esc([b.genre, where(b)].filter(Boolean).join(' · ')) + '</p>' +
        (b.bio ? '<p>' + esc(b.bio) + '</p>' : '') +
        (linkHtml ? '<div class="btns">' + linkHtml + '</div>' : '') +
        '<h2 class="sub">' + songs.length + ' song' + (songs.length === 1 ? '' : 's') + ' on HeavyMusix Radio</h2>' +
        '<ul class="songs">' + songs.map(function(s){ return '<li>' + playBtn(s.v, b.name + ' – ' + s.t) + '<span class="sinfo"><strong>' + esc(s.t) + '</strong></span></li>'; }).join('') + '</ul>' +
        (eps.length ? '<p class="wupd">Played on ' + eps.map(function(e){ return 'Show #' + e.n; }).join(', ') + '.</p>' : '');
    });
  };
  window.HMX = HMX;
})();

/* HeavyMusix skins: the evil look changes every Monday and on metal holidays.
   Runs in <head> before the page paints, so there is no flash.
   Weekly rotation: Blood, Crypt, Toxic, Frost. Halloween (Oct 15-31) overrides the week,
   with evil jack-o'-lanterns.
   Preview any skin with ?skin=crypt (or blood, toxic, frost, halloween; ?skin=auto to reset). */
(function(){
  var d = new Date(), m = d.getMonth() + 1, day = d.getDate(), skin;
  if (m === 10 && day >= 15) skin = 'halloween';
  else {
    var mon = new Date(d.getFullYear(), d.getMonth(), d.getDate() - ((d.getDay() + 6) % 7));   // this week's Monday
    var weeks = Math.floor((mon - new Date(2026, 10, 16)) / 6048e5);                           // weeks since Mon Nov 16, 2026
    skin = ['blood', 'crypt', 'toxic', 'frost'][((weeks % 4) + 4) % 4];
  }
  try {
    var q = /[?&]skin=([a-z]+)/.exec(location.search);
    if (q && !/^(blood|crypt|toxic|frost|halloween|auto)$/.test(q[1])) q = null;
    if (q) { if (q[1] === 'auto') sessionStorage.removeItem('hmxSkin'); else sessionStorage.setItem('hmxSkin', q[1]); }
    var keep = sessionStorage.getItem('hmxSkin');
    if (keep && /^(blood|crypt|toxic|frost|halloween)$/.test(keep)) skin = keep;
  } catch (e) {}
  document.documentElement.setAttribute('data-skin', skin);
})();

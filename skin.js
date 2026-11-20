/* HeavyMusix skins: the evil look changes every Monday and on metal holidays.
   Runs in <head> before the page paints, so there is no flash.
   Weekly rotation: Blood, Crypt, Toxic, Frost. Holidays override the week:
   Halloween (Oct 15-31), Krampus (Dec 1-26), Friday the 13th.
   Preview any skin with ?skin=crypt (or blood, toxic, frost, halloween, krampus, slasher; ?skin=auto to reset). */
(function(){
  var d = new Date(), m = d.getMonth() + 1, day = d.getDate(), skin;
  if (m === 10 && day >= 15) skin = 'halloween';
  else if (m === 12 && day <= 26) skin = 'krampus';
  else if (d.getDay() === 5 && day === 13) skin = 'slasher';
  else {
    var mon = new Date(d.getFullYear(), d.getMonth(), d.getDate() - ((d.getDay() + 6) % 7));   // this week's Monday
    var weeks = Math.floor((mon - new Date(2026, 10, 16)) / 6048e5);                           // weeks since Mon Nov 16, 2026
    skin = ['blood', 'crypt', 'toxic', 'frost'][((weeks % 4) + 4) % 4];
  }
  try {
    var q = /[?&]skin=([a-z]+)/.exec(location.search);
    if (q) { if (q[1] === 'auto') sessionStorage.removeItem('hmxSkin'); else sessionStorage.setItem('hmxSkin', q[1]); }
    skin = sessionStorage.getItem('hmxSkin') || skin;
  } catch (e) {}
  document.documentElement.setAttribute('data-skin', skin);
})();

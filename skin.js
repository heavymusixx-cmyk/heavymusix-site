/* HeavyMusix skins: the evil look changes every Monday and on holidays.
   Runs in <head> before the page paints, so there is no flash.
   Weekly rotation: Blood, Crypt, Toxic, Frost. Holidays override the week (dates are inclusive):
     Valentine's Day   Feb 7-14     dagger through a bleeding heart
     St. Patrick's Day Mar 14-17    clover skull
     4th of July       Jun 28-Jul 5 red, white and blue firework skull
     Halloween         Oct 15-31    evil jack-o'-lanterns
     Thanksgiving      Mon-Sun of Thanksgiving week (4th Thursday of November)   turkey skull
     Christmas         Dec 1-26     skull ornaments
     New Year's        Dec 27-Jan 2 gold firework skull
   Preview any skin with ?skin=crypt (or blood, toxic, frost, valentine, stpatrick, july4, halloween,
   thanksgiving, christmas, newyear). A preview never sticks: open heavymusix.com normally to see the scheduled skin. */
(function(){
  var d = new Date(), m = d.getMonth() + 1, day = d.getDate(), skin;
  var y = d.getFullYear(), nov1 = new Date(y, 10, 1).getDay();
  var tday = 1 + ((4 - nov1 + 7) % 7) + 21;                      // Thanksgiving: 4th Thursday of November
  if (m === 2 && day >= 7 && day <= 14) skin = 'valentine';
  else if (m === 3 && day >= 14 && day <= 17) skin = 'stpatrick';
  else if (m === 11 && day >= tday - 3 && day <= tday + 3) skin = 'thanksgiving';
  else if (m === 10 && day >= 15) skin = 'halloween';
  else if (m === 12 && day <= 26) skin = 'christmas';
  else if ((m === 12 && day >= 27) || (m === 1 && day <= 2)) skin = 'newyear';
  else if ((m === 6 && day >= 28) || (m === 7 && day <= 5)) skin = 'july4';
  else {
    var mon = new Date(d.getFullYear(), d.getMonth(), d.getDate() - ((d.getDay() + 6) % 7));   // this week's Monday
    var weeks = Math.floor((mon - new Date(2026, 10, 16)) / 6048e5);                           // weeks since Mon Nov 16, 2026
    skin = ['blood', 'crypt', 'toxic', 'frost'][((weeks % 4) + 4) % 4];
  }
  try {
    // A ?skin= preview only lasts while you browse in that tab (pages load in place, so the look stays);
    // a fresh visit always follows the schedule. Old saved previews are cleared.
    sessionStorage.removeItem('hmxSkin');
    var q = /[?&]skin=([a-z0-9]+)/.exec(location.search);
    if (q && /^(blood|crypt|toxic|frost|valentine|stpatrick|july4|halloween|thanksgiving|christmas|newyear)$/.test(q[1])) skin = q[1];
  } catch (e) {}
  document.documentElement.setAttribute('data-skin', skin);
})();

/* Auto-generated daily by scripts/wire.py. Do not edit by hand. */
window.WIRE={
 "updated": "not yet",
 "items": []
};

function renderWire(el,limit){
  if(!el)return;
  var w=window.WIRE||{items:[]};var items=w.items.slice(0,limit||w.items.length);
  if(!items.length){el.innerHTML='<p class="lead">Headlines load here every morning.</p>';return;}
  function esc(s){return String(s).replace(/[&<>"]/g,function(c){return{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]})}
  function fmt(d){var p=d.split('-');var m=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];return m[+p[1]-1]+' '+(+p[2])}
  el.innerHTML='<ul class="wire">'+items.map(function(i){return '<li><a href="'+esc(i.u)+'" target="_blank" rel="noopener">'+esc(i.t)+'</a><span class="wsrc">'+esc(i.s)+' &middot; '+fmt(i.d)+'</span></li>'}).join('')+'</ul>'+
    '<p class="wupd">Updated automatically every morning. Stories open on the original site.</p>';
}

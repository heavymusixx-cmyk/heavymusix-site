/*
  HEAVYMUSIX ARIZONA VENUES
  Street address, city and phone for every venue in shows.js, so each show can offer
  tap-to-call and a Directions button (owner's request; no email).
  Key = the venue name exactly as written in shows.js. Phone "" = the venue publishes none we could confirm.
  Details come from the venue's own site or its official ticket seller, checked Nov 21, 2026 (Last Exit Live and Yucca Tap Room added Nov 24, 2026 from their own sites). Never guess one.
*/
var VENUES = {
  "191 Toole": {address: "191 E Toole Ave", city: "Tucson", zip: "85701", phone: "520-740-1000"},
  "Arizona Financial Theatre": {address: "400 W Washington St", city: "Phoenix", zip: "85003", phone: "602-379-2800"},
  "Chase Field": {address: "401 E Jefferson St", city: "Phoenix", zip: "85004", phone: "602-514-8400"},
  "Crescent Ballroom": {address: "308 N 2nd Ave", city: "Phoenix", zip: "85003", phone: "602-716-2222"},
  "Findlay Toyota Center": {address: "3201 N Main St", city: "Prescott Valley", zip: "86314", phone: ""},
  "Last Exit Live": {address: "717 S Central Ave", city: "Phoenix", zip: "85004", phone: "602-271-7000"},
  "Marquee Theatre": {address: "730 N Mill Ave", city: "Tempe", zip: "85281", phone: "480-829-0607"},
  "Nile Theater": {address: "105 W Main St", city: "Mesa", zip: "85201", phone: "480-494-7580"},
  "Queen B Vinyl": {address: "102 E Pima St", city: "Cottonwood", zip: "86326", phone: ""},
  "Rebel Lounge": {address: "2303 E Indian School Rd", city: "Phoenix", zip: "85016", phone: ""},
  "Rialto Theatre": {address: "318 E Congress St", city: "Tucson", zip: "85701", phone: "520-740-1000"},
  "Rosetta Room": {address: "104 E 1st Ave", city: "Mesa", zip: "85201", phone: ""},
  "Talking Stick Resort Amphitheatre": {address: "2121 N 83rd Ave", city: "Phoenix", zip: "85035", phone: "602-254-7200"},
  "The 44": {address: "4494 W Peoria Ave", city: "Glendale", zip: "85302", phone: "623-842-1053"},
  "The Bisbee Grand": {address: "61 Main St", city: "Bisbee", zip: "85603", phone: "520-432-5900"},
  "The Events Center at Harrah's Ak-Chin": {address: "15406 N Maricopa Rd", city: "Maricopa", zip: "85139", phone: "480-802-3353"},
  "The Rock": {address: "136 N Park Ave", city: "Tucson", zip: "85719", phone: "520-629-9211"},
  "The Van Buren": {address: "401 W Van Buren St", city: "Phoenix", zip: "85003", phone: "480-659-1641"},
  "Yucca Tap Room": {address: "29 W Southern Ave", city: "Tempe", zip: "85282", phone: "480-967-4777"}
};

/* Address, tap-to-call and Directions for one venue (used by shows.js and the Arizona pages). */
function venueDetails(name){
  var v = (typeof VENUES !== "undefined") && VENUES[name];
  if (!v) return "";
  var e = function(s){ return String(s).replace(/[&<>"]/g, function(c){ return {"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;"}[c]; }); };
  var full = v.address + ", " + v.city + ", AZ " + (v.zip || "");
  var maps = "https://www.google.com/maps/dir/?api=1&destination=" + encodeURIComponent(name + ", " + full);
  return '<span class="vdet"><span class="vaddr">' + e(full.trim()) + '</span><span class="vlinks">' +
    (v.phone ? '<a class="vcall" href="tel:+1' + v.phone.replace(/\D/g, "") + '" aria-label="Call ' + e(name) + ' at ' + e(v.phone) + '">&#9742;&#xFE0E; ' + e(v.phone) + '</a>' : '') +
    '<a class="vdir" href="' + maps + '" target="_blank" rel="noopener" aria-label="Directions to ' + e(name) + ' (opens Google Maps in a new tab)">&#10148;&#xFE0E; Directions</a>' +
    '</span></span>';
}

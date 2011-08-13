$(function() {

  var debug_div = $('<div>').hide().appendTo($('div#menu'));
  debug_div.html('hi');

  var X = $('<a href="javascript:;">?!</a>').click(function(evt) {
    debug_div.toggle();
  }).appendTo($('span#debug-button-container'));

});

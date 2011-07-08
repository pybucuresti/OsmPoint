$(function() {
  window.M = {};
  $('#map').empty();
  M.proj_wgs1984 = new OpenLayers.Projection("EPSG:4326");
  M.proj_mercator = new OpenLayers.Projection("EPSG:900913");
  M.project = function(point) {
    return point.clone().transform(M.proj_wgs1984, M.proj_mercator);
  };
  M.map = new OpenLayers.Map({
    'div': "map",
    'controls': [
      new OpenLayers.Control.Navigation(),
      new OpenLayers.Control.ZoomPanel(),
      new OpenLayers.Control.Attribution()
    ]});
  M.map.addControl(new OpenLayers.Control.TouchNavigation({
    'dragPanOptions': {'enableKinetic': true}
  }));
  M.map.addLayer(new OpenLayers.Layer.OSM());
  M.map.setCenter(M.project(new OpenLayers.LonLat(26.10, 44.43)), 13);

  var points_layer = new OpenLayers.Layer.Vector("Points");
  M.map.addLayer(points_layer);

  var draw_control = new OpenLayers.Control.DrawFeature(
    points_layer,
    OpenLayers.Handler.Point,
    {'featureAdded': function() { console.log(arguments); }}
  );
  M.map.addControl(draw_control);
  draw_control.activate();
});

$(function() {
  window.navigator.geolocation.getCurrentPosition(function(position){
      var lon = position.coords.longitude, lat = position.coords.latitude;
      var center = new OpenLayers.LonLat(lon, lat);
      M.map.setCenter(M.project(center), 16);
      $('#poi-form form input[name=lat]').val(lat);
      $('#poi-form form input[name=lon]').val(lon);
  });
});

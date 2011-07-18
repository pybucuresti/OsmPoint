(function() {

OpenLayers.Control.Click = OpenLayers.Class(OpenLayers.Control, {
    mapClicked: function() {},

    initialize: function(mapClicked, options) {
        OpenLayers.Control.prototype.initialize.apply(this, [options]);
        if(mapClicked) this.mapClicked = mapClicked;
        this.handler = new OpenLayers.Handler.Click(
            this, {'click': this.trigger});
    },

    trigger: function(e) {
        this.mapClicked(e.xy);
    }
});

if(window.M == null) window.M = {};
M.proj_wgs1984 = new OpenLayers.Projection("EPSG:4326");
M.proj_mercator = new OpenLayers.Projection("EPSG:900913");
M.project = function(point) {
  return point.clone().transform(M.proj_wgs1984, M.proj_mercator);
};
M.reverse_project = function(point) {
  return point.clone().transform(M.proj_mercator, M.proj_wgs1984);
};

M.init_map = function() {
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
}

M.mark_point = function(lon, lat) {
  var center = M.project(new OpenLayers.LonLat(lon, lat));
  var size = new OpenLayers.Size(21,25);
  var offset = new OpenLayers.Pixel(-(size.w/2), -size.h);
  var icon = new OpenLayers.Icon(M.config['poi_marker'], size, offset);
  M.point_layer.addMarker(new OpenLayers.Marker(center, icon));
}

M.center_to_gps = function() {
  window.navigator.geolocation.getCurrentPosition(function(position){
      var lon = position.coords.longitude, lat = position.coords.latitude;
      var center = new OpenLayers.LonLat(lon, lat);
      M.map.setCenter(M.project(center), 16);
  });
}

M.center_to_coordinates = function(lon, lat) {
  $('body').addClass('poi-page');
  $('#edit-form').show();
  $('#map').show();
  var center = M.project(new OpenLayers.LonLat(lon, lat));
  M.map.setCenter(center, 16);

  var size = new OpenLayers.Size(21,25);
  var offset = new OpenLayers.Pixel(-(size.w/2), -size.h);
  var icon = new OpenLayers.Icon(M.config['poi_marker'], size, offset);

  M.init_points_layer = new OpenLayers.Layer.Markers("Markers");
  M.map.addLayer(M.init_points_layer);
  M.init_points_layer.addMarker(new OpenLayers.Marker(center, icon));
}

M.enable_editing_point = function(lon, lat) {
  $('body').addClass('poi-page');
  $('#edit-form').show();
  var edit_poi_box = $('#edit-poi-box');
  edit_poi_box.show();
  $('form input[name=lat]', edit_poi_box).val(lat);
  $('form input[name=lon]', edit_poi_box).val(lon);

  M.points_layer = new OpenLayers.Layer.Markers("Markers");
  M.map.addLayer(M.points_layer);
  var add_point = new OpenLayers.Control.Click(M.map_click_to_edit);
  M.map.addControl(add_point);
  add_point.activate();
}

M.map_click_to_edit = function(xy) {
  var lonlat = M.reverse_project(M.map.getLonLatFromViewPortPx(xy));
  var edit_poi_box = $('#edit-poi-box');
  $('form input[name=lat]', edit_poi_box).val(lonlat.lat);
  $('form input[name=lon]', edit_poi_box).val(lonlat.lon);
  edit_poi_box.show();
  M.map.updateSize();
  M.draw_marker(lonlat);
}

M.enable_adding_points = function() {
  M.points_layer = new OpenLayers.Layer.Markers("Markers");
  M.map.addLayer(M.points_layer);
  var add_point = new OpenLayers.Control.Click(M.map_clicked);
  M.map.addControl(add_point);
  add_point.activate();
};

M.map_clicked = function(xy) {
  if(! M.config['logged_in']) {
    $('#add-poi-box').text("To add points, please log in.").show();
    $('body').addClass('menu-form');
    M.map.updateSize();
    return;
  }

  var lonlat = M.reverse_project(M.map.getLonLatFromViewPortPx(xy));
  var add_poi_box = $('#add-poi-box');
  $('form input[name=lat]', add_poi_box).val(lonlat.lat);
  $('form input[name=lon]', add_poi_box).val(lonlat.lon);
  add_poi_box.show();
  $('body').addClass('menu-form');
  M.map.updateSize();
  M.draw_marker(lonlat);
}

M.draw_marker = function(lonlat) {
  var map_coords = M.project(lonlat);
  var size = new OpenLayers.Size(32, 32);
  var offset = new OpenLayers.Pixel(-(size.w/2), -(size.h/2));
  var icon = new OpenLayers.Icon(M.config['marker_image_src'], size, offset);
  M.points_layer.clearMarkers();
  M.points_layer.addMarker(new OpenLayers.Marker(map_coords, icon));
  M.map.panTo(map_coords);
};

})();

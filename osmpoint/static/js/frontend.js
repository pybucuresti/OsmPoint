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
  M.map.addLayer(new OpenLayers.Layer.CloudMade("", {
      key: '87d74b5d089842f98679496ee6aef22e',
      styleId: 42918
  }));
  M.restore_map_position();
  M.map.events.register("moveend", M.map, M.save_map_position);
};

M.restore_map_position = function() {
  var position_json = localStorage['map_position'];
  //var position;
  if(position_json) {
    var position = JSON.parse(position_json);
  }
  else {
    var position = {lon: 26.10, lat: 44.43, zoom: 13};
  }
  var center = M.project(new OpenLayers.LonLat(position.lon, position.lat));
  M.map.setCenter(center, position.zoom);
};

M.save_map_position = function(evt) {
  var center = M.reverse_project(M.map.center);
  var position = {
    lat: center.lat,
    lon: center.lon,
    zoom: M.map.zoom
  };
  localStorage['map_position'] = JSON.stringify(position);
};

M.mark_point = function(lon, lat, marker_url, type, name) {
  var center = M.project(new OpenLayers.LonLat(lon, lat));
  var size = new OpenLayers.Size(18,18);
  var offset = new OpenLayers.Pixel(-(size.w/2), -size.h);
  var icon = new OpenLayers.Icon(marker_url, size, offset);
  var marker = new OpenLayers.Marker(center, icon);
  M.point_layer.addMarker(marker);

  marker.events.register("mousedown", marker, function() {
    var message = name.toString() + '<br>(' + type.toString() + ')';
    var popupsize = new OpenLayers.Size(100,100);
    popup = new OpenLayers.Popup.AnchoredBubble("popup", center, popupsize,
                                                message, icon, true);
    M.map.addPopup(popup);
  });

}

M.enable_geolocation = function() {
  M.center_on_next_geolocation = false;
  M.geolocate = new OpenLayers.Control.Geolocate({
    bind: false, watch: true,
    geolocationOptions: {enableHighAccuracy: true}
  });
  M.map.addControl(M.geolocate);
  M.geolocation_layer = new OpenLayers.Layer.Vector('geolocation');
  M.map.addLayer(M.geolocation_layer);
  M.geolocate.events.register("locationupdated", M.geolocate, function(evt) {
      M.draw_geolocation(evt.point, evt.position.coords.accuracy);
      if (M.center_on_next_geolocation) {
        M.map.zoomToExtent(M.geolocation_layer.getDataExtent());
        M.center_on_next_geolocation = false;
      }
  });
};

M.draw_geolocation = function(coordinates, accuracy) {
  M.geolocation_layer.removeAllFeatures();
  var circle_style = {
      fillColor: '#00f',
      fillOpacity: 0.3,
      strokeColor: '#00f',
      strokeOpacity: 0.5,
      strokeWidth: 2
  };
  var center_style = {
    strokeColor: '#00f',
    strokeWidth: 1,
    fillOpacity: 0,
    pointRadius: 5
  };
  var point = new OpenLayers.Geometry.Point(coordinates.x, coordinates.y);
  var poly = OpenLayers.Geometry.Polygon.createRegularPolygon(
        point, accuracy/2, 40, 0);
  var circle = new OpenLayers.Feature.Vector(poly, {}, circle_style);
  var center = new OpenLayers.Feature.Vector(coordinates, {}, center_style);
  M.geolocation_layer.addFeatures([center, circle]);
};

M.center_to_gps = function() {
  M.geolocate.deactivate();
  //M.center_on_next_geolocation = true;
  M.geolocate.activate();
};

M.center_to_coordinates = function(lon, lat) {
  var center = M.project(new OpenLayers.LonLat(lon, lat));
  M.map.setCenter(center, 16);

  var size = new OpenLayers.Size(21,25);
  var offset = new OpenLayers.Pixel(-(size.w/2), -size.h);
  var icon = new OpenLayers.Icon(M.config['poi_marker'], size, offset);

  M.init_points_layer = new OpenLayers.Layer.Markers("Markers");
  M.map.addLayer(M.init_points_layer);
  M.init_points_layer.addMarker(new OpenLayers.Marker(center, icon));
};

M.enable_editing_point = function() {
  M.points_layer = new OpenLayers.Layer.Markers("Markers");
  M.map.addLayer(M.points_layer);
  var add_point = new OpenLayers.Control.Click(M.map_click_to_edit);
  M.map.addControl(add_point);
  add_point.activate();
};

M.map_click_to_edit = function(xy) {
  var lonlat = M.reverse_project(M.map.getLonLatFromViewPortPx(xy));
  var edit_poi_box = $('#edit-poi-box');
  $('form input[name=lat]', edit_poi_box).val(lonlat.lat);
  $('form input[name=lon]', edit_poi_box).val(lonlat.lon);
  M.map.updateSize();
  M.draw_marker(lonlat);
};

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
    M.map.updateSize();
    return;
  }

  M.center_on_next_geolocation = false;
  var lonlat = M.reverse_project(M.map.getLonLatFromViewPortPx(xy));
  var add_poi_box = $('#add-poi-box');
  $('form input[name=lat]', add_poi_box).val(lonlat.lat);
  $('form input[name=lon]', add_poi_box).val(lonlat.lon);
  add_poi_box.show();
  M.map.updateSize();
  M.draw_marker(lonlat);
};

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

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

M.cloudmade_xyz_layer = function(name, key, style_id) {
  var url = 'http://a.tile.cloudmade.com/' + key + '/' + style_id +
            '/256/${z}/${x}/${y}.png';
  return new OpenLayers.Layer.XYZ(name, url, {
    attribution: "Data &copy; <a href='http://openstreetmap.org/'>" +
                 "OpenStreetMap</a>. Rendering &copy; " +
                 "<a href='http://cloudmade.com'>CloudMade</a>.",
    sphericalMercator: true,
    wrapDateLine: true
  });
};

M.default_position = {lon: 26.10, lat: 44.43, zoom: 13};

M.offset = {
  bottom: function(w, h) { return new OpenLayers.Pixel(-w/2, -h); },
  center: function(w, h) { return new OpenLayers.Pixel(-w/2, -h/2); }
};

M.new_icon = function(path, width, height, offset_name) {
  var size = new OpenLayers.Size(width, height);
  var offset = M.offset[offset_name](width, height);
  return new OpenLayers.Icon(path, size, offset);
};

M.new_center_to_gps_control = function(callback) {
  var panel = new OpenLayers.Control.Panel({
    displayClass: "center-to-gps-control"
  });
  var button = new OpenLayers.Control({
    type: OpenLayers.Control.TYPE_BUTTON,
    trigger: callback
  });
  panel.addControls([button]);
  return panel;
};

M.new_map = function(div_id) {
  /*
  Constructor for `map` objects that encapsulate an `OpenLayers.Map` and
  some methods.
  */
  var map = {};

  map.olmap = new OpenLayers.Map({
    'div': div_id,
    'controls': [
      new OpenLayers.Control.Navigation(),
      new OpenLayers.Control.ZoomPanel(),
      new OpenLayers.Control.Attribution()
    ]
  });

  map.olmap.addControl(new OpenLayers.Control.TouchNavigation({
    'dragPanOptions': {'enableKinetic': true}
  }));

  map.olmap.addLayer(M.cloudmade_xyz_layer("CloudMade",
    '87d74b5d089842f98679496ee6aef22e', '42918'));

  map.set_position = function(position) {
    var center = M.project(new OpenLayers.LonLat(position.lon, position.lat));
    map.olmap.setCenter(center, position.zoom);
  };

  map.olmap.zoomToMaxExtent = function() {
    map.set_position(M.default_position);
  };

  map.restore_position = function() {
    var position_json = localStorage['map_position'];
    if(position_json) {
      map.set_position(JSON.parse(position_json));
    }
    else {
      map.set_position(M.default_position);
    }
  };

  map.save_position = function(evt) {
    var center = M.reverse_project(map.olmap.center);
    var position = {
      lat: center.lat,
      lon: center.lon,
      zoom: map.olmap.zoom
    };
    localStorage['map_position'] = JSON.stringify(position);
  };

  map.enable_position_memory = function() {
    map.restore_position();
    map.olmap.events.register("moveend", map.olmap, map.save_position);
  };

  map.enable_geolocation = function() {
    map.center_on_next_geolocation = false;
    map.geolocate_control = new OpenLayers.Control.Geolocate({
      bind: false, watch: true,
      geolocationOptions: {enableHighAccuracy: true}
    });
    map.olmap.addControl(map.geolocate_control);
    map.geolocation_layer = new OpenLayers.Layer.Vector('geolocation');
    map.olmap.addLayer(map.geolocation_layer);
    map.geolocate_control.events.register("locationupdated", null, function(evt) {
        map.draw_geolocation(evt.point, evt.position.coords.accuracy);
        if (map.center_on_next_geolocation) {
          map.olmap.zoomToExtent(map.geolocation_layer.getDataExtent());
          map.center_on_next_geolocation = false;
        }
    });
    map.geolocate_control.activate();
    map.center_to_gps_control = M.new_center_to_gps_control(center_to_gps);
    map.olmap.addControl(map.center_to_gps_control);
    map.center_to_gps_control.activate();

    function center_to_gps() {
      map.geolocate_control.deactivate();
      map.center_on_next_geolocation = true;
      map.geolocate_control.activate();
    };
  };

  map.draw_geolocation = function(coordinates, accuracy) {
    map.geolocation_layer.removeAllFeatures();
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
    map.geolocation_layer.addFeatures([center, circle]);
  };

  map.new_markers_collection = function(name) {
    var collection = {};
    var layer = new OpenLayers.Layer.Markers(name);
    map.olmap.addLayer(layer);
    collection.new_marker = function(lon, lat, icon) {
      var center = M.project(new OpenLayers.LonLat(lon, lat));
      var marker = new OpenLayers.Marker(center, icon)
      layer.addMarker(marker);
      return marker;
    };
    return collection;
  };

  return map;
};

M.init_map = function() {
  M.single_map = M.new_map('map');
  M.map = M.single_map.olmap;
  M.single_map.set_position(M.default_position);
};

M.init_fullscreen_map = function() {
  M.fullscreen_map = M.new_map('map');
  M.map = M.fullscreen_map.olmap;
  M.fullscreen_map.enable_position_memory();
  M.fullscreen_map.enable_geolocation();
};

M.mark_point = function(lon, lat, marker_url, type, name) {
  var center = M.project(new OpenLayers.LonLat(lon, lat));
  var size = new OpenLayers.Size(18,18);
  var offset = new OpenLayers.Pixel(-(size.w/2), -size.h);
  var icon = new OpenLayers.Icon(marker_url, size, offset);
  var base_marker = new OpenLayers.Marker(center, icon);

  var feature = new OpenLayers.Feature(M.point_layer, center, base_marker);
  feature.closeBox = true;
  feature.data.overflow = "auto";
  var border = '<div style="border-style: solid; border-width: 2px;">';
  feature.data.popupContentHTML = border + name.toString() + '<br>(' +
                                  type.toString() + ')' + '</div>';
  feature.popupClass = OpenLayers.Class(OpenLayers.Popup.AnchoredBubble,
                                        { 'autoSize': true });

  var marker = feature.createMarker();
  M.point_layer.addMarker(marker);

  marker.events.register('click', feature, M.click_marker);
  marker.events.register('touch', feature, M.click_marker);
};

M.click_marker = function (evt) {
  if (this.popup == null) {
    this.popup = this.createPopup(this.closeBox);
    M.map.addPopup(this.popup);
    this.popup.show();
  } else {
    this.popup.toggle();
  }
};

M.open_popup = function (lon, lat, marker_url, type, name) {
  var center = M.project(new OpenLayers.LonLat(lon, lat));
  var size = new OpenLayers.Size(20,20);
  var offset = new OpenLayers.Pixel(-(size.w/2), -size.h);
  var icon = new OpenLayers.Icon(marker_url, size, offset);
  var base_marker = new OpenLayers.Marker(center, icon);

  M.point_layer.addMarker(base_marker);
  var border = '<div style="border-style: solid; border-width: 2px;">';
  var message = border + name.toString() + '<br>(' +
                type.toString() + ')' + '</div>';
  var popupsize = new OpenLayers.Size(100,100);
  popup = new OpenLayers.Popup.AnchoredBubble ("popup", center, popupsize,
                                               message, icon, true);
  popup.autoSize = true;
  M.map.addPopup(popup);
};

M.show_one_point = function(lon, lat) {
  M.single_map.set_position({lon: lon, lat: lat, zoom: 16});
  var markers = M.single_map.new_markers_collection("Markers");
  markers.new_marker(lon, lat, M.config['generic_icon']);
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

M.auto_toggle_enter_type_manually = function() {
  $('select[name=amenity]').change(function() {
    var manual_input = $('input#enter-type-manually');
    if($(this).val() == "_other") {
      manual_input.show();
    }
    else {
      manual_input.hide();
    }
  });
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

  M.fullscreen_map.center_on_next_geolocation = false;
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

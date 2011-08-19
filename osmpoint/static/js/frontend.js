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
    var layer = new OpenLayers.Layer.Markers(name);
    map.olmap.addLayer(layer);

    var collection = {map: map, layer: layer};

    collection.show_marker = function(lon, lat, icon) {
      var center = M.project(new OpenLayers.LonLat(lon, lat));
      var marker = new OpenLayers.Marker(center, icon)
      layer.addMarker(marker);
      return marker;
    };

    collection.show_marker_with_popup = function(lon, lat, icon, popup_html) {
      var xy = M.project(new OpenLayers.LonLat(lon, lat));
      var base_marker = new OpenLayers.Marker(xy, icon);
      var feature = new OpenLayers.Feature(collection.layer, xy, base_marker);
      feature.data.overflow = "auto";
      feature.data.popupContentHTML = popup_html;
      feature.popupClass = OpenLayers.Class(OpenLayers.Popup.AnchoredBubble,
                                            { 'autoSize': true });

      var marker = feature.createMarker();
      layer.addMarker(marker);
      M._mark = marker

      marker.events.register('click', null, marker_clicked);
      marker.events.register('touchstart', null, marker_clicked);

      function marker_clicked(evt) {
        evt.preventDefault();
        if (feature.popup != null) {
          close_popup();
          return;
        }
        if(M.close_current_popup != null) {
          M.close_current_popup();
        }
        create_popup();
      }

      function create_popup() {
        var popup = feature.createPopup(false);
        popup.setBackgroundColor('#7b8');
        popup.setOpacity(0.9);
        collection.map.olmap.addPopup(popup);
        popup.show();
        popup.events.register('click', null, close_popup);
        $(feature.marker.icon.imageDiv).addClass('poi-selected');
        M.close_current_popup = close_popup;
      }

      function close_popup() {
        $(feature.marker.icon.imageDiv).removeClass('poi-selected');
        feature.destroyPopup();
        M.close_current_popup = null;
      }
    };

    collection.empty = function() {
      layer.clearMarkers();
    };

    return collection;
  };

  map.enable_coordinates_selector = function(callback) {
    var selection_layer = map.new_markers_collection('Select coordinates');
    var add_point = new OpenLayers.Control.Click(map_clicked);
    map.olmap.addControl(add_point);
    add_point.activate();

    function map_clicked(xy) {
      var lonlat = M.reverse_project(map.olmap.getLonLatFromViewPortPx(xy));
      var lon = lonlat.lon, lat = lonlat.lat;

      selection_layer.empty();
      selection_layer.show_marker(lon, lat, M.config['crosshair_icon']);
      map.olmap.panTo(M.project(lonlat));

      map.center_on_next_geolocation = false;
      callback(lonlat);
    };
  };

  return map;
};

M.init_map = function() {
  var map = M.new_map('map');
  map.set_position(M.default_position);
  return map;
};

M.init_fullscreen_map = function() {
  var map = M.new_map('map');
  map.enable_position_memory();
  map.enable_geolocation();
  return map;
};

M.show_location = function(map, collection, point_info) {
  var icon_url = M.config['marker_prefix'] + point_info['marker']
  var icon = M.new_icon(icon_url, 18, 18, 'center');
  var popup_html = point_info['name'] + ' (' + point_info['type'] + ')';
  collection.show_marker_with_popup(
      point_info['longitude'], point_info['latitude'], icon, popup_html);
};

M.show_one_point = function(map, lon, lat) {
  map.set_position({lon: lon, lat: lat, zoom: 16});
  var markers = map.new_markers_collection("Markers");
  markers.show_marker(lon, lat, M.config['generic_icon']);
};

M.enable_editing_point = function(map) {
  map.enable_coordinates_selector(updated_coordinates_value);

  function updated_coordinates_value(lonlat) {
    var edit_poi_box = $('#edit-poi-box');
    $('form input[name=lat]', edit_poi_box).val(lonlat.lat);
    $('form input[name=lon]', edit_poi_box).val(lonlat.lon);
  }
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

M.enable_adding_points = function(map) {
  map.enable_coordinates_selector(updated_coordinates_value);

  function updated_coordinates_value(lonlat) {
    var add_poi_box = $('#add-poi-box');
    $('form input[name=lat]', add_poi_box).val(lonlat.lat);
    $('form input[name=lon]', add_poi_box).val(lonlat.lon);
    add_poi_box.show();
  }
};

M.apply_filter = function(map, collection, form_input, point_data) {
  var checked_options = [];

  for(var i=0; i<form_input.length - 1; i++) {
    if(form_input[i].checked) {
      checked_options.push(form_input[i].name);
    }
  }

  checked_options.toString();
  $.each(point_data, function(i, point_info) {
    if(checked_options.indexOf(point_info['type']) != -1) {
      M.show_location(map, collection, point_info);
    }
  });
};

})();

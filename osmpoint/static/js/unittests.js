(function() {

var MT = window.MT = {};

MT.run_tests = function() {
    var jasmineEnv = jasmine.getEnv();
    jasmineEnv.updateInterval = 1000;

    var trivialReporter = new jasmine.TrivialReporter();

    jasmineEnv.addReporter(trivialReporter);

    jasmineEnv.specFilter = function(spec) {
        return trivialReporter.specFilter(spec);
    };

    jasmineEnv.execute();
};

MT.ajax = function(url, data, type) {
    if(type == null) type = 'GET';
    var req = $.ajax(url, {async: false, type: type, data: data});
    if(req.status != 200) console.log(url, 'error:', req);
    return req;
};

MT.reset_database = function() {
    MT.ajax('/reset_database', {}, 'POST');
};

MT.log_in_as = function(user_id) {
    MT.ajax('/log_in_as', {user_id: user_id}, 'POST');
};

MT.add_point = function(data) {
    MT.ajax('/save_poi', data, 'POST');
};

MT.load_points = function() {
    return JSON.parse(MT.ajax('/points.json').responseText).points;
    //return JSON.parse(resp).points;
};

describe("Load points from server", function() {

    MT.reset_database();
    MT.log_in_as('some-test-user');
    MT.add_point({lat: 13, lon: 22, name: "ze pub", amenity: "bar"});

    it('loads the point', function() {
        var points = MT.load_points();
        expect(points.length).toEqual(1);
        var point = points[0];
        expect(points[0]['lat']).toEqual(13);
        expect(points[0]['lon']).toEqual(22);
        expect(points[0]['type']).toEqual('bar');
    });
});

})();

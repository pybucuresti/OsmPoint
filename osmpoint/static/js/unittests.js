(function() {

var MT = window.MT = {};

describe("Thingie one", function() {
    it('can say hi', function() {
        console.log('hi');
    });
    it('will fail', function() {
        expect(11).toEqual(11);
    });
});

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

})();

var app = require('express')();
var server = require('http').Server(app);
var io = require('socket.io')(server);
var watchr = require('watchr');
var fs = require('fs');
var async = require('async');
var request = require('request');

server.listen(8080);

app.get('/', function (req, res) {
  res.sendfile(__dirname + '/index.html');
});
io.on('connection', function (socket) {
  socket.emit('news', { hello: 'world' });
  socket.on('my other event', function (data) {
    console.log(data);
  });
  socket.on('role', function (data) {
    var checkerDOT = {
      url: data.jolokiaEndpoint + '/jolokia/exec/' + encodeURIComponent(data.role) + '/checkerDOT',
      method: 'GET'
    };
    var checkerXML = {
      url: data.jolokiaEndpoint + '/jolokia/exec/' + encodeURIComponent(data.role) + '/checkerXML',
      method: 'GET'
    };
    async.parallel({
      checkerDOT: function (callback) {
        request(checkerDOT, function (error, response, body) {
          if (response !== undefined && error === null) {
            switch (response.statusCode) {
              case 200:
                callback(null, JSON.parse(body).value);
                break;
              default:
                callback('ERROR', { 'code': 500, 'message': 'Graph load failed' });
                break;
            }
          } else {
            callback('ERROR', { 'code': 500, 'message': 'Graph load failed' });
          }
        });
      },
      checkerXML: function (callback) {
        request(checkerXML, function (error, response, body) {
          if (response !== undefined && error === null) {
            switch (response.statusCode) {
              case 200:
                callback(null, JSON.parse(body).value);
                break;
              default:
                callback('ERROR', { 'code': 500, 'message': 'Graph load failed' });
                break;
            }
          } else {
            callback('ERROR', { 'code': 500, 'message': 'Graph load failed' });
          } [45 / 1913]
        });
      }
    },
      function (err, results) {
        console.log(err, results);
        if (err) {
          console.log('error');
          socket.emit('graph', { 'code': 500, 'message': 'Graph load failed' });
        } else {
          console.log('graph stuff', results);
          socket.emit('graph', { dotOutput: results.checkerDOT, xmlOutput: results.checkerXML, id: data.role.match(/.*scope=\"([a-zA-Z0-9_]+)\".*/)[1] });
        }
      })
  });
  socket.on('reposeCheck', function (reposeEndpoint, jolokiaEndpoint) {
    console.log(reposeEndpoint, jolokiaEndpoint);
    var repose = {
      url: reposeEndpoint,
      method: 'GET'
    };
    var jolokia = {
      url: jolokiaEndpoint + '/jolokia/search/%22com.rackspace.com.papi.components.checker%22:type=%22Validator%22,scope=*,name=%22checker%22',
      method: 'GET'
    };
    async.parallel({
      reposeCheck: function (callback) {
        request(repose, function (error, response, body) {
          if (response !== undefined && error === null) {
            switch (response.statusCode) {
              case 500:
              case 502:
              case 503:
                callback(null, false);
                break;
              default:
                callback(null, true);
            }
          } else {
            callback({ 'code': 500, 'message': 'Repose check failed' });
          }
        });
      },
      validatorSearch: function (callback) {
        request(jolokia, function (error, response, body) {
          if (response !== undefined && error === null) {
            switch (response.statusCode) {
              case 200:
                callback(null, JSON.parse(body));
                break;
              default:
                callback(null, []);
            }
          } else {
            callback({ 'code': 500, 'message': 'Jolokia check failed' });
          }
        });
      }
    },
      function (err, results) {
        console.log(err, results);
        if (err) {
          console.log('error');
          socket.emit('roles', { repose: err, jolokia: [] });
        } else {
          console.log('roles stuff', results);
          //socket.emit('roles', {repose: results.reposeCheck});
          socket.emit('roles', { repose: results.reposeCheck, jolokia: results.validatorSearch.value });
        }
      })
  });

  console.log('watch paths');
  watchr.watch({
    paths: ['/var/log/repose-coverage/coverage.log'],
    listeners: {
      change: function (changeType, filePath, fileCurrentStat, filePreviousStat) {
        console.log('a change event occured:');
        fs.readFile('/var/log/repose-coverage/coverage.log', 'utf-8', function (err, data) {
          if (err) throw err;

          var lines = data.trim().split('\n');
          var lastLine = lines.slice(-1)[0];

          console.log('LAST LINE: ', lastLine);
          socket.emit('path', { path: lastLine });
        });
      },
      error: function (err) {
        console.log('an error occured:', err);
      },
      watching: function (err, watcherInstance, isWatching) {
        if (err) {
          console.log("watching the path " + watcherInstance.path + " failed with error", err);
        } else {
          console.log("watching the path " + watcherInstance.path + " completed");
        }
      }
    }
  });
});
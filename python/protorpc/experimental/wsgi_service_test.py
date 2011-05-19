import cgi
import unittest
import urllib2
from wsgiref import simple_server
from wsgiref import validate

from protorpc import end2end_test
from protorpc.experimental import filters
from protorpc.experimental import util as wsgi_util
from protorpc.experimental import wsgi_service
from protorpc import protojson
from protorpc import test_util
from protorpc import transport
from protorpc import webapp_test_util


class ServiceAppTest(end2end_test.EndToEndTest):

  '''def setUp(self):
    self.port = test_util.pick_unused_port()
    self.server, self.application = self.StartWebServer(self.port)
    self.connection = webapp_test_util.ServerTransportWrapper(
      self.server,
      transport.HttpTransport('http://localhost:%d/my/service' % self.port,
                              protocol=protojson))
    self.stub = webapp_test_util.TestService.Stub(self.connection)'''

  def tearDown(self):
    self.server.shutdown()

  def StartWebServer(self, port):
    """Start web server."""
    protocols = wsgi_util.Protocols()
    protocols.add_protocol(protojson, 'json', 'application/json')

    application = wsgi_service.service_app(webapp_test_util.TestService,
                                           service_path='/my/service',
                                           protocols=protocols)
    validated_application = validate.validator(application)
    server = simple_server.make_server('localhost', port, validated_application)
    server = webapp_test_util.ServerThread(server)
    server.start()
    server.wait_until_running()
    return server, application



if __name__ == '__main__':
  unittest.main()

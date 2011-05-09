from google.appengine.ext.webapp import util

from protorpc.experimental import wsgi_handlers
from protorpc.experimental import wsgi_filters
from protorpc import protobuf
from protorpc import protojson

from protorpc import registry

protocols = wsgi_handlers.Protocols()
protocols.add_protocol(protobuf, 'protobuf')
protocols.add_protocol(protojson, 'json')

reg = {'/protorpc': registry.RegistryService}
registry_service = registry.RegistryService.new_factory(reg)
application = wsgi_handlers.ServiceApp(registry_service,
                                       '/protorpc')
application = wsgi_filters.use_protocols(protocols,
                                         app=application)


def main():
  util.run_bare_wsgi_app(application)


if __name__ == '__main__':
  main()

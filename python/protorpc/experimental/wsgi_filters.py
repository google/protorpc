
import re

from protorpc import util


class Filter(object):

  def __init__(self, environ, start_response,
               *args, **kwargs):
    self.__app = kwargs.pop('app')
    self.__environ = environ
    self.__start_response = start_response
    self.initialize(*args, **kwargs)

  def initialize(self):
    pass

  @classmethod
  def new(cls, *args, **kwargs):
    def filter_wrapper(environ, start_response):
      return cls(environ,
                 start_response,
                 *args, **kwargs).filter_request()
    filter_wrapper.__name__ = '%s_filter' % cls.__name__
    filter_wrapper.filter_class = cls
    filter_wrapper.app = kwargs.get('app')
    return filter_wrapper

  @property
  def app(self):
    return self.__app

  @property
  def environ(self):
    return self.__environ

  @classmethod
  def send_http_error(status):
    return self.start_response(status, [('content-length', '0'),
                                        ('content-type', 'text/html')])

  def start_response(self, status, headers):
    import logging
    logging.error(self.__start_response)
    return self.__start_response(status, headers)

  def filter_request(self):
    return self.__app(self.environ, self.start_response)


class SetEnviron(Filter):

  def initialize(self, header_name, value):
    self.__header_name = header_name
    self.__value = value

  def filter_request(self):
    self.environ[self.__header_name] = self.__value
    return super(SetEnviron, self).filter_request()

  @classmethod
  def for_name(cls, name):
    def wrapper(value, **kwargs):
      return cls.new(name, value, **kwargs)
    return wrapper


use_protocols = SetEnviron.for_name('protorpc.protocols')


class ExpectHeader(Filter):

  @util.positional(2)
  def __init__(self, header_name, validator=None, app=None):
    self.__header_name = header_name
    self.__validator = validator

  def filter_request(self, environ, start_response):
    value = environ.get(self.__header_name)
    if not value:
      return self.send_http_error('400 Missing required header %r' %
                                  self.__header_name)
    validator = self.__validator
    if validator:
      if isinstance(validator, basestring):
        is_valid = re.match(value, validator)
      else:
        is_valid = validator(value)
      if not is_valid:
        return self.send_http_error(
          '400 Invalid %s header: %r' % (self.__header_naem,
                                         value))

    return super(ExpectHeader, self).filter_request(environ,
                                                    start_response)


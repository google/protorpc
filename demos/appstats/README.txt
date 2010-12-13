Appstats service.

This utility can be integrated in to an existing application that uses
appstats to turn appstats in to a service that can be remotely
queried.

For more information about appstats, please see:

  http://code.google.com/appengine/docs/python/tools/appstats.html

The file appstats.descriptor is a binary FileSet descriptor encoded in
protocol buffer format as defined in protorpc.descriptor.FileSet.  The
defintions were described from yet to be published .proto file.  The
generated classes are the same as defined in:

  google.appengine.ext.appstats.datamodel_pb.py

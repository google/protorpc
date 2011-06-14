from protorpc import messages
from protorpc import remote
package = 'guestbook'


class GetNotesRequest(messages.Message):
  
  
  class Order(messages.Enum):
  
    WHEN = 1
    TEXT = 2
  
  limit = messages.IntegerField(1, default=10)
  on_or_before = messages.IntegerField(2)
  order = messages.EnumField('guestbook.GetNotesRequest.Order', 3, default=1)


class Note(messages.Message):
  
  text = messages.StringField(1, required=True)
  when = messages.IntegerField(2)


class Notes(messages.Message):
  
  notes = messages.MessageField('guestbook.Note', 1, repeated=True)


class PostService(remote.Service):
  
  @remote.method('guestbook.GetNotesRequest', 'guestbook.Notes')
  def get_notes(self, request):
    raise NotImplementedError('Method get_notes is not implemented')
  
  @remote.method('guestbook.Note', 'protorpc.message_types.VoidMessage')
  def post_note(self, request):
    raise NotImplementedError('Method post_note is not implemented')

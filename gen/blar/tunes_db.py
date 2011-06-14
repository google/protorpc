from protorpc import messages
from protorpc import remote
package = 'tunes_db'


class AddAlbumRequest(messages.Message):
  
  name = messages.StringField(1, required=True)
  artist_id = messages.StringField(2, required=True)
  released = messages.IntegerField(3)


class AddAlbumResponse(messages.Message):
  
  album_id = messages.StringField(1, required=True)


class AddArtistRequest(messages.Message):
  
  name = messages.StringField(1, required=True)


class AddArtistResponse(messages.Message):
  
  artist_id = messages.StringField(1, required=True)


class Album(messages.Message):
  
  album_id = messages.StringField(1, required=True)
  artist_id = messages.StringField(2, required=True)
  name = messages.StringField(3, required=True)
  released = messages.IntegerField(4)


class Artist(messages.Message):
  
  artist_id = messages.StringField(1, required=True)
  name = messages.StringField(2, required=True)
  album_count = messages.IntegerField(3)


class DeleteAlbumRequest(messages.Message):
  
  album_id = messages.StringField(1, required=True)


class DeleteAlbumResponse(messages.Message):
  
  album_deleted = messages.BooleanField(1, default=true)


class DeleteArtistRequest(messages.Message):
  
  artist_id = messages.StringField(1, required=True)


class DeleteArtistResponse(messages.Message):
  
  artist_deleted = messages.BooleanField(1, default=true)


class FetchAlbumRequest(messages.Message):
  
  album_id = messages.StringField(1, required=True)


class FetchAlbumResponse(messages.Message):
  
  album = messages.MessageField('tunes_db.Album', 1)


class FetchArtistRequest(messages.Message):
  
  artist_id = messages.StringField(1, required=True)


class FetchArtistResponse(messages.Message):
  
  artist = messages.MessageField('tunes_db.Artist', 1)


class SearchAlbumsRequest(messages.Message):
  
  continuation = messages.StringField(1)
  fetch_size = messages.IntegerField(2, default=10)
  name_prefix = messages.StringField(3)
  artist_id = messages.StringField(4)


class SearchAlbumsResponse(messages.Message):
  
  albums = messages.MessageField('tunes_db.Album', 1, repeated=True)
  continuation = messages.StringField(2)


class SearchArtistsRequest(messages.Message):
  
  continuation = messages.StringField(1)
  fetch_size = messages.IntegerField(2, default=10)
  name_prefix = messages.StringField(3)


class SearchArtistsResponse(messages.Message):
  
  artists = messages.MessageField('tunes_db.Artist', 1, repeated=True)
  continuation = messages.StringField(2)


class UpdateAlbumRequest(messages.Message):
  
  album = messages.MessageField('tunes_db.Album', 1, required=True)


class UpdateAlbumResponse(messages.Message):
  
  album_updated = messages.BooleanField(1, required=True)


class UpdateArtistRequest(messages.Message):
  
  artist = messages.MessageField('tunes_db.Artist', 1, required=True)


class UpdateArtistResponse(messages.Message):
  
  artist_updated = messages.BooleanField(1, required=True)


class MusicLibraryService(remote.Service):
  
  @remote.method('tunes_db.AddAlbumRequest', 'tunes_db.AddAlbumResponse')
  def add_album(self, request):
    raise NotImplementedError('Method add_album is not implemented')
  
  @remote.method('tunes_db.AddArtistRequest', 'tunes_db.AddArtistResponse')
  def add_artist(self, request):
    raise NotImplementedError('Method add_artist is not implemented')
  
  @remote.method('tunes_db.DeleteAlbumRequest', 'tunes_db.DeleteAlbumResponse')
  def delete_album(self, request):
    raise NotImplementedError('Method delete_album is not implemented')
  
  @remote.method('tunes_db.DeleteArtistRequest', 'tunes_db.DeleteArtistResponse')
  def delete_artist(self, request):
    raise NotImplementedError('Method delete_artist is not implemented')
  
  @remote.method('tunes_db.FetchAlbumRequest', 'tunes_db.FetchAlbumResponse')
  def fetch_album(self, request):
    raise NotImplementedError('Method fetch_album is not implemented')
  
  @remote.method('tunes_db.FetchArtistRequest', 'tunes_db.FetchArtistResponse')
  def fetch_artist(self, request):
    raise NotImplementedError('Method fetch_artist is not implemented')
  
  @remote.method('tunes_db.SearchAlbumsRequest', 'tunes_db.SearchAlbumsResponse')
  def search_albums(self, request):
    raise NotImplementedError('Method search_albums is not implemented')
  
  @remote.method('tunes_db.SearchArtistsRequest', 'tunes_db.SearchArtistsResponse')
  def search_artists(self, request):
    raise NotImplementedError('Method search_artists is not implemented')
  
  @remote.method('tunes_db.UpdateAlbumRequest', 'tunes_db.UpdateAlbumResponse')
  def update_album(self, request):
    raise NotImplementedError('Method update_album is not implemented')
  
  @remote.method('tunes_db.UpdateArtistRequest', 'tunes_db.UpdateArtistResponse')
  def update_artist(self, request):
    raise NotImplementedError('Method update_artist is not implemented')

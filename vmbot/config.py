from ConfigParser import SafeConfigParser

from .helpers.files import CONFIG

_parser = SafeConfigParser()
_parser.read(CONFIG)

config = {
    # Log level
    'loglevel': _parser.get('Logging', 'level'),
    # Jabber configuration
    'jabber': {
        'username': _parser.get('Jabber', 'username'),
        'password': _parser.get('Jabber', 'password'),
        'res': _parser.get('Jabber', 'resource'),
        'nickname': _parser.get('Jabber', 'nickname'),
        'chatrooms': (
            _parser.get('Jabber', 'chatroom1'),
            _parser.get('Jabber', 'chatroom2'),
            _parser.get('Jabber', 'chatroom3')
        )
    },
    # GSF broadcast API
    'bcast': {
        'url': _parser.get('GSF Broadcast', 'url'),
        'id': _parser.get('GSF Broadcast', 'id'),
        'key': _parser.get('GSF Broadcast', 'key'),
        'target': _parser.get('GSF Broadcast', 'target')
    },
    # RC blacklist API
    'blacklist': {
        'url': _parser.get('RC Blacklist', 'url'),
        'key': _parser.get('RC Blacklist', 'key')
    }
}

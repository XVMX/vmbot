from os import path
from ConfigParser import SafeConfigParser


parser = SafeConfigParser()
parser.read(path.join(path.dirname(__file__), "data", "vmbot.cfg"))

config = {}

# Log level
config['loglevel'] = parser.get('Logging', 'level')

# Jabber configuration
config['jabber'] = _jabber = {}
_jabber['username'] = parser.get('Jabber', 'username')
_jabber['password'] = parser.get('Jabber', 'password')
_jabber['res'] = parser.get('Jabber', 'resource')
_jabber['nickname'] = parser.get('Jabber', 'nickname')
_jabber['chatroom1'] = parser.get('Jabber', 'chatroom1')
_jabber['chatroom2'] = parser.get('Jabber', 'chatroom2')
_jabber['chatroom3'] = parser.get('Jabber', 'chatroom3')

# GSF broadcast API
config['bcast'] = _bcast = {}
_bcast['url'] = parser.get('GSF Broadcast', 'url')
_bcast['id'] = parser.get('GSF Broadcast', 'id')
_bcast['key'] = parser.get('GSF Broadcast', 'key')
_bcast['target'] = parser.get('GSF Broadcast', 'target')

# RC blacklist API
config['blacklist'] = _blacklist = {}
_blacklist['url'] = parser.get('RC Blacklist', 'url')
_blacklist['key'] = parser.get('RC Blacklist', 'key')

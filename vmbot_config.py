import ConfigParser


parser = ConfigParser.SafeConfigParser()
parser.read('vmbot.cfg')

# Jabber configuration
username  = parser.get('Jabber', 'username')
password  = parser.get('Jabber', 'password')
res       = parser.get('Jabber', 'resource')
nickname  = parser.get('Jabber', 'nickname')
chatroom1 = parser.get('Jabber', 'chatroom1')
chatroom2 = parser.get('Jabber', 'chatroom2')
chatroom3 = parser.get('Jabber', 'chatroom3')

# GSF broadcast API
url    = parser.get('GSF Broadcast', 'url')
id     = parser.get('GSF Broadcast', 'id')
key    = parser.get('GSF Broadcast', 'key')
target = parser.get('GSF Broadcast', 'target')

# RC blacklist API
blurl = parser.get('RC Blacklist', 'url')
blkey = parser.get('RC Blacklist', 'key')

# SSO-CREST
client_id     = parser.get('SSO-CREST', 'client_id')
client_secret = parser.get('SSO-CREST', 'client_secret')
refresh_token = parser.get('SSO-CREST', 'refresh_token')

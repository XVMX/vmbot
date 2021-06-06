# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

import unittest
import mock

from xmpp.protocol import JID, Message

from vmbot.helpers import database as db
from vmbot.models.user import User

from vmbot.helpers.decorators import requires_role, requires_dir_chat


@requires_role("admin")
def role_acl(self, mess, args):
    return True


@requires_dir_chat
def dir_chat_acl(self, mess, args):
    return True


@mock.patch.dict("config.JABBER", {'director_chatrooms': ("DirRoom@domain.tld",)})
class TestACLDecorators(unittest.TestCase):
    db_engine = db.create_engine("sqlite://")
    default_mess = Message(frm=JID("Room@domain.tld"))
    default_args = ""
    get_uname_from_mess = mock.MagicMock(name="get_uname_from_mess",
                                         return_value=JID("user@domain.tld/res"))

    @classmethod
    def setUpClass(cls):
        db.init_db(cls.db_engine)
        db.Session.configure(bind=cls.db_engine)

        admin_usr = User("admin@domain.tld")
        admin_usr.allow_admin = True

        sess = db.Session()
        sess.add(admin_usr)
        sess.commit()
        sess.close()

    @classmethod
    def tearDownClass(cls):
        db.Session.configure(bind=db.engine)
        cls.db_engine.dispose()
        del cls.db_engine

    def test_requires_invalidrole(self):
        self.assertRaises(ValueError, requires_role, "invalid role")

    def test_requires_role(self):
        self.get_uname_from_mess = mock.MagicMock(name="get_uname_from_mess",
                                                  return_value=JID("admin@domain.tld/res"))
        self.assertTrue(role_acl(self, self.default_mess, self.default_args))
        del self.get_uname_from_mess

    def test_requires_role_denied(self):
        self.assertIsNone(role_acl(self, self.default_mess, self.default_args))

    def test_requires_dir_chat(self):
        self.assertTrue(dir_chat_acl(self, Message(frm=JID("DirRoom@domain.tld")),
                                     self.default_args))

    def test_requires_dir_chat_denied(self):
        self.assertIsNone(dir_chat_acl(self, self.default_mess, self.default_args))


if __name__ == "__main__":
    unittest.main()

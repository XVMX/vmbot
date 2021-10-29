# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

import unittest
import mock

from xmpp import JID

from .support.xmpp import (USER_JID, USER_MUC_JID, ADMIN_JID, mock_pm_mess,
                           mock_muc_mess, mock_get_uname_from_mess)
from vmbot.helpers import database as db
from vmbot.models.user import User

from vmbot.helpers.decorators import requires_role, requires_dir_chat, requires_muc

USER_DIR_MUC_JID = JID(USER_MUC_JID)
USER_DIR_MUC_JID.setNode("dirs")


class Commands(object):
    @requires_role("admin")
    def role_acl(self, mess, args):
        return True

    @requires_dir_chat
    def dir_chat_acl(self, mess, args):
        return True

    @requires_muc
    def muc_acl(self, mess, args):
        return True


@mock.patch.dict("config.JABBER", {'director_chatrooms': {USER_DIR_MUC_JID.getStripped()}})
class TestACLDecorators(unittest.TestCase):
    db_engine = db.create_engine("sqlite://")
    muc_mess = mock_muc_mess(b"")
    default_args = ""

    @classmethod
    def setUpClass(cls):
        db.init_db(cls.db_engine)
        db.Session.configure(bind=cls.db_engine)

        admin = User(ADMIN_JID.getStripped())
        admin.allow_admin = True

        with db.Session.begin() as sess:
            sess.add(admin)

    @classmethod
    def tearDownClass(cls):
        db.Session.configure(bind=db.engine)
        cls.db_engine.dispose()

    def setUp(self):
        self.cmds = Commands()
        self.cmds.get_uname_from_mess = mock_get_uname_from_mess(USER_JID)

    def tearDown(self):
        del self.cmds

    def test_requires_invalidrole(self):
        self.assertRaises(ValueError, requires_role, "invalid role")

    def test_requires_role(self):
        self.cmds.get_uname_from_mess = mock_get_uname_from_mess(ADMIN_JID)
        self.assertTrue(self.cmds.role_acl(self.muc_mess, self.default_args))

    def test_requires_role_denied(self):
        self.assertIsNone(self.cmds.role_acl(self.muc_mess, self.default_args))

    def test_requires_dir_chat(self):
        self.assertTrue(self.cmds.dir_chat_acl(mock_muc_mess(b"", frm=USER_DIR_MUC_JID),
                                               self.default_args))

    def test_requires_dir_chat_denied(self):
        self.assertIsNone(self.cmds.dir_chat_acl(self.muc_mess, self.default_args))

    def test_requires_muc(self):
        self.assertTrue(self.cmds.muc_acl(self.muc_mess, self.default_args))

    def test_requires_muc_denied(self):
        self.assertIsNone(self.cmds.muc_acl(mock_pm_mess(b""), self.default_args))


if __name__ == "__main__":
    unittest.main()

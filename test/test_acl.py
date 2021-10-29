# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

import unittest

from .support.xmpp import (BOT_JID, USER_JID, ADMIN_JID, ADMIN_MUC_JID,
                           mock_muc_mess, mock_get_uname_from_mess)
from vmbot.helpers import database as db
from vmbot.models.user import User

from vmbot.acl import ACL


class TestACL(unittest.TestCase):
    db_engine = db.create_engine("sqlite://")
    default_mess = mock_muc_mess(b"", frm=ADMIN_MUC_JID)

    @classmethod
    def setUpClass(cls):
        db.init_db(cls.db_engine)
        db.Session.configure(bind=cls.db_engine)

        usr = User(USER_JID.getStripped())
        admin = User(ADMIN_JID.getStripped())
        admin.allow_admin = admin.allow_director = admin.allow_token = True

        with db.Session.begin() as sess:
            sess.add_all([usr, admin])

    @classmethod
    def tearDownClass(cls):
        db.Session.configure(bind=db.engine)
        cls.db_engine.dispose()

    def setUp(self):
        self.acl = ACL()
        self.acl.jid = BOT_JID
        self.acl.get_uname_from_mess = mock_get_uname_from_mess(ADMIN_JID)
        self.sess = db.Session()

    def tearDown(self):
        self.sess.close()
        del self.acl

    def test_process_acl_args(self):
        args = "{} director admin".format(USER_JID.getNode())
        recv, roles = self.acl._process_acl_args(self.default_mess, args, self.sess)

        self.assertEqual(recv.jid, USER_JID.getStripped())
        self.assertListEqual(roles, ["director", "admin"])

    def test_process_acl_args_jid(self):
        args = "{} director admin".format(USER_JID.getStripped())
        recv, roles = self.acl._process_acl_args(self.default_mess, args, self.sess)

        self.assertEqual(recv.jid, USER_JID.getStripped())
        self.assertListEqual(roles, ["director", "admin"])

    def test_process_acl_args_noargs(self):
        self.assertRaises(ValueError, self.acl._process_acl_args,
                          self.default_mess, "", self.sess)
        self.assertRaises(ValueError, self.acl._process_acl_args,
                          self.default_mess, "asdf", self.sess)

    def test_process_acl_args_invalidroles(self):
        self.assertRaises(ValueError, self.acl._process_acl_args,
                          self.default_mess, "asdf xyz", self.sess)

    def test_process_acl_args_denied(self):
        self.acl.get_uname_from_mess = mock_get_uname_from_mess(USER_JID)
        self.assertRaises(ValueError, self.acl._process_acl_args,
                          self.default_mess, "asdf admin", self.sess)

    def test_promote(self):
        args = "{} director admin token".format(USER_JID.getNode())
        self.acl.promote(self.default_mess, args)

        usr = self.sess.get(User, USER_JID.getStripped())
        self.assertTrue(usr.allow_director)
        self.assertTrue(usr.allow_admin)
        self.assertTrue(usr.allow_token)

        usr.allow_director = False
        usr.allow_admin = False
        usr.allow_token = False
        self.sess.commit()

    def test_promote_denied(self):
        self.acl.get_uname_from_mess = mock_get_uname_from_mess(USER_JID)
        self.acl.promote(self.default_mess, "asdf director")

        usr = self.sess.get(User, USER_JID.getStripped())
        self.assertFalse(usr.allow_director)

    def test_promote_hasroles(self):
        args = "{} director".format(ADMIN_JID.getNode())
        self.assertEqual(self.acl.promote(self.default_mess, args),
                         "The user already has all specified roles")

    def test_demote(self):
        args = "{} director admin token".format(ADMIN_JID.getNode())
        self.acl.demote(self.default_mess, args)

        admin = self.sess.get(User, ADMIN_JID.getStripped())
        self.assertFalse(admin.allow_director)
        self.assertFalse(admin.allow_admin)
        self.assertFalse(admin.allow_token)

        admin.allow_director = True
        admin.allow_admin = True
        admin.allow_token = True
        self.sess.commit()

    def test_demote_denied(self):
        self.acl.get_uname_from_mess = mock_get_uname_from_mess(USER_JID)
        self.acl.demote(self.default_mess, "asdf director")

        admin = self.sess.get(User, ADMIN_JID.getStripped())
        self.assertTrue(admin.allow_director)

    def test_demote_noroles(self):
        args = "{} director".format(USER_JID.getNode())
        self.assertEqual(self.acl.demote(self.default_mess, args),
                         "The user doesn't have any of the specified roles")

    def test_list(self):
        self.assertEqual(self.acl.list(self.default_mess, "admin"),
                         "This role is assigned to {}".format(ADMIN_JID.getNode()))

    def test_list_invalidrole(self):
        self.assertEqual(self.acl.list(self.default_mess, "xyz"),
                         "Invalid role")

    def test_list_notassigned(self):
        admin = self.sess.get(User, ADMIN_JID.getStripped())
        admin.allow_admin = False
        self.sess.commit()

        self.assertEqual(self.acl.list(self.default_mess, "admin"),
                         "This role is not assigned to anyone")

        admin.allow_admin = True
        self.sess.commit()


if __name__ == "__main__":
    unittest.main()

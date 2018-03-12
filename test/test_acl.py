# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

import unittest
import mock

from xmpp.protocol import JID

from vmbot.helpers import database as db
from vmbot.models.user import User

from vmbot.acl import ACL


class TestACL(unittest.TestCase):
    db_engine = db.create_engine("sqlite://")
    default_mess = ""

    @classmethod
    def setUpClass(cls):
        db.init_db(cls.db_engine)
        db.Session.configure(bind=cls.db_engine)

        def_user = User("user@domain.tld")
        full_usr = User("admin@domain.tld")
        full_usr.is_admin = True
        full_usr.is_director = True

        sess = db.Session()
        sess.add_all([def_user, full_usr])
        sess.commit()
        sess.close()

    @classmethod
    def tearDownClass(cls):
        db.Session.configure(bind=db.engine)
        cls.db_engine.dispose()
        del cls.db_engine

    def setUp(self):
        self.acl = ACL()
        self.acl.jid = JID("bot@domain.tld/res")
        self.acl.get_uname_from_mess = mock.MagicMock(name="get_uname_from_mess",
                                                      return_value=JID("admin@domain.tld/res"))
        self.sess = db.Session()

    def tearDown(self):
        self.sess.close()
        del self.acl

    def test_process_args(self):
        recv, roles = self.acl._process_args(self.default_mess, "user director admin", self.sess)

        self.assertEqual(recv.jid, "user@domain.tld")
        self.assertListEqual(roles, ["director", "admin"])

    def test_process_args_noargs(self):
        self.assertRaises(ValueError, self.acl._process_args, self.default_mess, "", self.sess)
        self.assertRaises(ValueError, self.acl._process_args, self.default_mess, "user", self.sess)

    def test_process_args_invalidroles(self):
        self.assertRaises(ValueError, self.acl._process_args,
                          self.default_mess, "user xyz", self.sess)

    def test_process_args_denied(self):
        self.acl.get_uname_from_mess.return_value = JID("user@domain.tld/res")
        self.assertRaises(ValueError, self.acl._process_args,
                          self.default_mess, "user admin", self.sess)

    def test_promote(self):
        self.acl.promote(self.default_mess, "user director admin")

        usr = self.sess.query(User).get("user@domain.tld")
        self.assertTrue(usr.is_director)
        self.assertTrue(usr.is_admin)

        usr.is_director = False
        usr.is_admin = False
        self.sess.commit()

    def test_promote_denied(self):
        self.acl.get_uname_from_mess.return_value = JID("user@domain.tld/res")
        self.acl.promote(self.default_mess, "user director")

        usr = self.sess.query(User).get("user@domain.tld")
        self.assertFalse(usr.is_director)

    def test_promote_hasroles(self):
        self.assertEqual(self.acl.promote(self.default_mess, "admin director"),
                         "The user already has all specified roles")

    def test_demote(self):
        self.acl.demote(self.default_mess, "admin director admin")

        admin = self.sess.query(User).get("admin@domain.tld")
        self.assertFalse(admin.is_director)
        self.assertFalse(admin.is_admin)

        admin.is_director = True
        admin.is_admin = True
        self.sess.commit()

    def test_demote_denied(self):
        self.acl.get_uname_from_mess.return_value = JID("user@domain.tld/res")
        self.acl.demote(self.default_mess, "admin director")

        admin = self.sess.query(User).get("admin@domain.tld")
        self.assertTrue(admin.is_director)

    def test_demote_noroles(self):
        self.assertEqual(self.acl.demote(self.default_mess, "user director"),
                         "The user doesn't have any of the specified roles")


if __name__ == "__main__":
    unittest.main()

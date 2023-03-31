# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

from .botcmd import botcmd
from .helpers import database as db
from .helpers.decorators import ROLE_ATTR_MAP, generate_role_attr_map, inject_db
from .models.user import User


class ACL(object):
    def _process_acl_args(self, mess, args, session):
        args = args.strip().split()
        if len(args) < 2:
            raise ValueError("Please provide a username and at least one role: "
                             "<user> <role> [role...]")

        # Remove non-existent roles
        receiver, roles = args[0], [r for r in args[1:] if r in ROLE_ATTR_MAP]
        if not roles:
            raise ValueError("Please provide a username and at least one role: "
                             "<user> <role> [role...]")

        # Load receiver from db
        if '@' not in receiver:
            receiver += '@' + self.jid.getDomain()
        receiver = (session.execute(db.select(User).where(User.jid.ilike(receiver)))
                    .scalar_one_or_none()) or User(receiver.lower())

        # Remove roles that giver is not allowed to manage
        # Allow assignment if the role is not assigned to anybody yet
        giver = self.get_uname_from_mess(mess, full_jid=True).getStripped()
        giver = session.get(User, giver) or User(giver)

        giver_role_map = generate_role_attr_map(giver)
        roles = [
            role for role in roles if giver_role_map[role]
            or not session.execute(db.select(1).where(ROLE_ATTR_MAP[role].is_(True))).scalar()
        ]

        if not roles:
            raise ValueError(None)
        return receiver, roles

    @botcmd
    @inject_db
    def promote(self, mess, args, session):
        """<user> <role> [role...] - Adds role(s) to user

        Available roles: director, admin, token.
        """
        try:
            receiver, roles = self._process_acl_args(mess, args, session)
        except ValueError as e:
            return unicode(e)

        recv_role_map = generate_role_attr_map(receiver)
        roles = [role for role in roles if not recv_role_map[role]]
        if not roles:
            return "The user already has all specified roles"

        for role in roles:
            if role == "director":
                receiver.allow_director = True
            elif role == "admin":
                receiver.allow_admin = True
            elif role == "token":
                receiver.allow_token = True

        session.add(receiver)
        session.commit()
        return ("The following role(s) have been added to {}: ".format(receiver.jid)
                + ", ".join(roles))

    @botcmd
    @inject_db
    def demote(self, mess, args, session):
        """<user> <role> [role...] - Removes role(s) from user

        Available roles: director, admin, token.
        """
        try:
            receiver, roles = self._process_acl_args(mess, args, session)
        except ValueError as e:
            return unicode(e)

        recv_role_map = generate_role_attr_map(receiver)
        roles = [role for role in roles if recv_role_map[role]]
        if not roles:
            return "The user doesn't have any of the specified roles"

        for role in roles:
            if role == "director":
                receiver.allow_director = False
            elif role == "admin":
                receiver.allow_admin = False
            elif role == "token":
                receiver.allow_token = False

        session.add(receiver)
        session.commit()
        return ("The following role(s) have been removed from {}: ".format(receiver.jid)
                + ", ".join(roles))

    @botcmd
    @inject_db
    def listrole(self, mess, args, session):
        """<role> - Lists users with the specified role

        Available roles: director, admin, token.
        """
        args = args.strip()
        if args not in ROLE_ATTR_MAP:
            return "Invalid role"

        usrs = session.execute(db.select(User).where(ROLE_ATTR_MAP[args].is_(True))).scalars().all()
        if not usrs:
            return "This role is not assigned to anyone"

        return "This role is assigned to " + ", ".join(usr.uname for usr in usrs)

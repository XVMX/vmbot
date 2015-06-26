from jabberbot import botcmd

import shlex
import sqlite3
from datetime import datetime


class FAQ(object):
    faq_version = 2

    @botcmd
    def faq(self, mess, args):
        '''show "<needle>" - Shows the matching article

show "<needle>" [receiver] - Shows a matching article and its ID or sends it to [receiver]
                             (<needle> is either the ID, a list of keywords, a part of the title or a part of the content)
insert "<title>" "<keyword>[,keyword...]" "<text>" - Creates a new article and replies the ID
index - PMs a list of all visible entries
index all - PMs a list of all entries (including hidden ones)
edit <ID> "[keyword][,keyword][...]" "[text]" - Replaces article with <ID> with new text and/or new keywords
                                                (requires at least one keyword or text, leave other empty using "")
chown <ID> "<new Author>" - Changes ownership to <new Author> to make the article editable by him
log <ID> - Shows author and history of article with <ID>
delete <ID> - Deletes the article with <ID>
revert <ID> - Reverts deletion of article with <ID>'''
        args = shlex.split(args.strip())
        if args:
            cmd = args[0].upper()
        else:
            return "Requires one of show, index, edit, chown, log, delete or revert as an argument"
        argc = len(args)
        if cmd == "SHOW" and argc == 2:
            return self.faq_show(mess, args[1])
        elif cmd == "SHOW" and argc == 3:
            return self.faq_show(mess, args[1], args[2])
        elif cmd == "INDEX" and argc == 1:
            return self.faq_index(mess)
        elif cmd == "INDEX" and argc == 2:
            return self.faq_index(mess, True)
        elif cmd == "INSERT" and argc == 4:
            return self.faq_insert(mess, args[1], args[2], args[3])
        elif cmd == "EDIT" and argc == 4:
            return self.faq_edit(mess, args[1], args[2], args[3])
        elif cmd == "CHOWN" and argc == 3:
            return self.faq_chown(mess, args[1], args[2])
        elif cmd == "LOG" and argc == 2:
            return self.faq_log(mess, args[1])
        elif cmd == "DELETE" and argc == 2:
            return self.faq_delete(mess, args[1])
        elif cmd == "REVERT" and argc == 2:
            return self.faq_revert(mess, args[1])
        else:
            return "faq " + " ".join(args) + " is not an accepted command"

    def faq_show(self, mess, needle, receiver=None):
        def searchKeywords(needles, stack):
            needleList = [item.strip().upper() for item in needles.strip().split(",")]
            stackList = [item.strip().upper() for item in stack.strip().split(",")]
            matches = 0
            for needle in needleList:
                matches += len([s for s in stackList if needle in s])
            return matches

        conn = sqlite3.connect("faq.sqlite")
        conn.create_function("searchKeywords", 2, searchKeywords)
        cur = conn.cursor()

        # ID based search
        try:
            cur.execute(
                '''SELECT `ID`, `keywords`, `title`, `content`
                   FROM `articles`
                   WHERE `ID` = :id
                    AND NOT `hidden`;''',
                {"id": int(needle)})
        except ValueError:
            pass
        except sqlite3.OperationalError:
            return "Error: Data is missing"
        res = cur.fetchall()

        # Keyword based search
        if not res:
            try:
                keyList = [item.strip() for item in needle.strip().split(',')]
                cur.execute(
                    '''SELECT `ID`, `keywords`, `title`, `content`
                       FROM `articles`
                       WHERE searchKeywords(:keys, `keywords`)
                        AND NOT `hidden`;''',
                    {"keys": ",".join(map(str, keyList))})
            except ValueError:
                pass
            except sqlite3.OperationalError:
                return "Error: Data is missing"
            res = cur.fetchall()

        # Title based search
        if not res:
            try:
                cur.execute(
                    '''SELECT `ID`, `keywords`, `title`, `content`
                       FROM `articles`
                       WHERE `title` LIKE :title
                        AND NOT `hidden`;''',
                    {"title": "%"+str(needle)+"%"})
            except ValueError:
                pass
            except sqlite3.OperationalError:
                return "Error: Data is missing"
            res = cur.fetchall()

        # Content based search
        if not res:
            try:
                cur.execute(
                    '''SELECT `ID`, `keywords`, `title`, `content`
                       FROM articles
                       WHERE `content` LIKE :content
                        AND NOT `hidden`;''',
                    {"content": "%"+str(needle)+"%"})
            except ValueError:
                pass
            except sqlite3.OperationalError:
                return "Error: Data is missing"
            res = cur.fetchall()

        if res:
            reply = "<b>{}</b> (<i>ID: {}</i>)<br />".format(res[0][2], res[0][0])
            reply += str(res[0][3]).replace("\n", "<br />") + "<br />"
            reply += "<b>Keywords</b>: {}".format(res[0][1])
            if len(res) > 1:
                reply += "<br />Other articles like <b>'{}'</b>:".format(needle)
                for (idx, article) in enumerate(res[1:5]):
                    reply += "<br />{}) {} (<i>ID: {}</i>)".format(idx+1, article[2], article[0])
            if receiver:
                if self.longreply(mess, reply, receiver=receiver):
                    return "Sent a PM to {}".format(receiver)
                else:
                    return "{}: {}".format(receiver, reply)
            if self.longreply(mess, reply):
                return "Sent a PM to you"
            else:
                return reply
        else:
            return "No matches"

    def faq_index(self, mess, showHidden=False):
        conn = sqlite3.connect("faq.sqlite")
        cur = conn.cursor()

        try:
            cur.execute(
                '''SELECT `ID`, `title`, `hidden`
                   FROM `articles`'''
                + (" WHERE NOT `hidden`;" if not showHidden else ";"))
        except sqlite3.OperationalError:
            return "Error: Data is missing"
        res = cur.fetchall()

        reply = "1) {} (<i>ID: {}</i>)".format(res[0][1], res[0][0])
        reply += (" <i>hidden</i>" if res[0][2] else "")
        for (idx, article) in enumerate(res[1:]):
            reply += "<br />{}) {} (<i>ID: {}</i>)".format(idx+2, article[1], article[0])
            reply += (" <i>hidden</i>" if article[2] else "")
        self.longreply(mess, reply, True)
        return "Sent a PM to you"

    def faq_insert(self, mess, title, keywords, text):
        if self.get_uname_from_mess(mess) not in (self.directors + self.admins):
            return "Only directors and admins can insert new entries"

        conn = sqlite3.connect("faq.sqlite")
        cur = conn.cursor()

        cur.execute(
            '''CREATE TABLE IF NOT EXISTS `metadata` (
                `type` TEXT NOT NULL UNIQUE,
                `value` INT NOT NULL
               );''')
        conn.commit()
        cur.execute(
            '''SELECT `value`
               FROM `metadata`
               WHERE `type` = 'version';''')
        res = cur.fetchall()
        if res[0][0] != self.faq_version:
            return "Tell {} to update the FAQ database!".format(", ".join(self.admins))

        cur.execute(
            '''INSERT OR REPLACE INTO `metadata` (`type`, `value`)
               VALUES (:type, :version);''',
            {"type": "version",
             "version": self.faq_version})
        cur.execute(
            '''CREATE TABLE IF NOT EXISTS `articles` (
                `ID` INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                `keywords` TEXT NOT NULL,
                `title` TEXT NOT NULL UNIQUE ON CONFLICT ABORT,
                `content` TEXT NOT NULL,
                `createdBy` TEXT NOT NULL,
                `modifiedBy` TEXT NOT NULL,
                `hidden` INTEGER NOT NULL DEFAULT 0
               );''')
        conn.commit()

        keyList = [item.strip() for item in keywords.strip().split(',') if item]
        cur.execute(
            '''INSERT INTO `articles` (`keywords`, `title`, `content`, `createdBy`, `modifiedBy`)
               VALUES (:keys, :title, :content, :author, :history);''',
            {"keys": ",".join(map(str, keyList)),
             "title": str(title),
             "content": str(text).replace("&", "&amp;"),
             "author": str(self.get_uname_from_mess(mess)),
             "history": "{} {}".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), self.get_uname_from_mess(mess))})
        conn.commit()
        return "ID of inserted article: {!s}".format(cur.lastrowid)

    def faq_edit(self, mess, pID, keywords, newText):
        if not keywords and not newText:
            return "Please provide new text and/or new keywords"

        conn = sqlite3.connect("faq.sqlite")
        cur = conn.cursor()

        try:
            cur.execute(
                '''SELECT `createdBy`, `modifiedBy`
                   FROM `articles`
                   WHERE `ID` = :id
                    AND NOT `hidden`;''',
                {"id": int(pID)})
        except ValueError:
            return "Can't parse the ID"
        except sqlite3.OperationalError:
            return "Error: Data is missing"
        res = cur.fetchall()
        if not res:
            return "Error: No match"

        owner = res[0][0]
        sentBy = self.get_uname_from_mess(mess)
        history = "{},{} {}".format(res[0][1], datetime.now().strftime("%Y-%m-%d %H:%M:%S"), sentBy)
        keyList = [item.strip() for item in keywords.strip().split(',') if item]
        if sentBy in ([owner] + self.directors + self.admins):
            try:
                cur.execute(
                    '''UPDATE `articles`
                       SET `modifiedBy` = :hist,'''
                    + ("`content` = :content" if newText else "")
                    + (", " if newText and keyList else "")
                    + ("`keywords` = :keys" if keyList else "")
                    + " WHERE `ID` = :id;",
                    {"id": int(pID),
                     "content": str(newText).replace("&", "&amp;"),
                     "keys": ",".join(map(str, keyList)),
                     "hist": history})
                conn.commit()
            except:
                return "Edit failed"
            return "Article with ID {!s} edited".format(pID)
        else:
            return "Only {}, directors and admins can edit this entry".format(owner)

    def faq_chown(self, mess, pID, newOwner):
        conn = sqlite3.connect("faq.sqlite")
        cur = conn.cursor()

        try:
            cur.execute(
                '''SELECT `createdBy`
                   FROM `articles`
                   WHERE `ID` = :id
                    AND NOT `hidden`;''',
                {"id": int(pID)})
        except ValueError:
            return "Can't parse the ID"
        except sqlite3.OperationalError:
            return "Error: Data is missing"
        res = cur.fetchall()
        if not res:
            return "Error: No match"

        owner = res[0][0]
        sentBy = self.get_uname_from_mess(mess)
        if sentBy in ([owner] + self.directors + self.admins):
            try:
                cur.execute(
                    '''UPDATE `articles`
                       SET `createdBy` = :newAuthor
                       WHERE `ID` = :id;''',
                    {"id": int(pID),
                     "newAuthor": str(newOwner)})
            except:
                return "Chown failed"
            conn.commit()
            return "Article with ID {!s} changed ownership to {}".format(pID, newOwner)
        else:
            return "Only {}, directors and admins can change ownership of this entry".format(owner)

    def faq_log(self, mess, pID):
        conn = sqlite3.connect("faq.sqlite")
        cur = conn.cursor()

        try:
            cur.execute(
                '''SELECT `title`, `createdBy`, `modifiedBy`
                   FROM `articles`
                   WHERE `ID` = :id
                    AND NOT `hidden`;''',
                {"id": int(pID)})
        except ValueError:
            return "Can't parse the ID"
        except sqlite3.OperationalError:
            return "Error: Data is missing"
        res = cur.fetchall()
        if not res:
            return "Error: No articles"

        history = [item.strip() for item in res[0][2].strip().split(",")]
        reply = "Article '{}' was created by {}<br />".format(res[0][0], res[0][1])
        reply += "History: 1) {}".format(history[0])
        for (idx, edit) in enumerate(history[1:]):
            reply += "<br/>{}) {}".format(idx+2, edit)
        if self.longreply(mess, reply):
            return "Sent a PM to you."
        else:
            return reply

    def faq_delete(self, mess, pID):
        conn = sqlite3.connect("faq.sqlite")
        cur = conn.cursor()

        try:
            cur.execute(
                '''SELECT `createdBy`
                   FROM `articles`
                   WHERE `ID` = :id
                    AND NOT `hidden`;''',
                {"id": int(pID)})
        except ValueError:
            return "Can't parse the ID"
        except sqlite3.OperationalError:
            return "Error: Data is missing"
        res = cur.fetchall()
        if not res:
            return "Error: No match"

        owner = res[0][0]
        sentBy = self.get_uname_from_mess(mess)
        if sentBy in ([owner] + self.directors + self.admins):
            try:
                cur.execute(
                    '''UPDATE `articles`
                       SET `hidden` = 1
                       WHERE `ID` = :id;''',
                    {"id": int(pID)})
            except:
                return "Deletion failed"
            conn.commit()
            return "Article with ID {!s} deleted".format(pID)
        else:
            return "Only {}, directors and admins can delete this entry".format(owner)

    def faq_revert(self, mess, pID):
        conn = sqlite3.connect("faq.sqlite")
        cur = conn.cursor()

        try:
            cur.execute(
                '''SELECT `createdBy`
                   FROM `articles`
                   WHERE `ID` = :id
                    AND `hidden`;''',
                {"id": int(pID)})
        except ValueError:
            return "Can't parse the ID"
        except sqlite3.OperationalError:
            return "Error: Data is missing"
        res = cur.fetchall()
        if not res:
            return "Error: No match"

        owner = res[0][0]
        sentBy = self.get_uname_from_mess(mess)
        if sentBy in ([owner] + self.directors + self.admins):
            try:
                cur.execute(
                    '''UPDATE `articles`
                       SET `hidden` = 0
                       WHERE `ID` = :id;''',
                    {"id": int(pID)})
            except:
                return "Reversion failed"
            conn.commit()
            return "Article with ID {!s} reverted".format(pID)
        else:
            return "Only {}, directors and admins can delete this entry".format(owner)

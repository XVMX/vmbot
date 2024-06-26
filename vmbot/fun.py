# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

import random
import re
import cgi
import urllib

import cachetools.func
import numpy as np
from bs4 import BeautifulSoup

from .botcmd import botcmd
from .helpers.files import EMOTES, HANDEY_QUOTES
from .helpers.exceptions import APIError
from .helpers import api

import config

# 8ball answers like the original, as per https://en.wikipedia.org/wiki/Magic_8-Ball
EBALL_ANSWERS = (
    "It is certain",
    "It is decidedly so",
    "Without a doubt",
    "Yes definitely",
    "You may rely on it",
    "As I see it, yes",
    "Most likely",
    "Outlook good",
    "Yes",
    "Signs point to yes",
    "Reply hazy try again",
    "Ask again later",
    "Better not tell you now",
    "Cannot predict now",
    "Concentrate and ask again",
    "Don't count on it",
    "My reply is no",
    "My sources say no",
    "Outlook not so good",
    "Very doubtful"
)

FISHISMS = (
    "~The Python Way!~",
    "HOOOOOOOOOOOOOOOOOOOOOOO! SWISH!",
    "DIVERGENT ZONES!",
    "BONUSSCHWEIN! BONUSSCHWEIN!"
)

PIMPISMS = (
    "eabod",
    "why do you hate black people?",
    "i want a bucket full of money covered rainbows",
    "bundle of sticks",
    "that went over like a jerrys kids rodeo with live bulls"
)

ARELEISMS = (
    "PzbjWI3EhyI",
    "5R8At-Qno_o",
    "MZwXoDyj9Vc",
    "So9LshyaHd0",
    "sW4JRSzPJQo",
    "UepAzio1eyU",
    "aneUrHBRyhg",
    "9XHqg7mTizE",
    "gtM9xD-Ky7E",
    "ZTidn2dBYbY"
)

NICKISMS = (
    "D{}d!",
    "But d{}d!",
    "Come on d{}d...",
    "Oh d{}d"
)

KAIRKISMS = (
    "thanks for filling this out.",
    "voting on your application to join VM is over, and you have passed.",
    "congratulations, you passed the security check.",
    "I regret to tell you that your application to join VM has been rejected.",
    "thank you for your interest in VM, and I wish you luck in your future endeavours in Eve.",
    "in 48h your membership of Valar Morghulis. will be terminated.",
    "you've got to improve, or I'll be sending out more kick notices, and I hate doing that.",
    "you get a cavity search, your friends get a cavity search, EVERYBODY gets a cavity search!"
)

DARIUSISMS = (
    "Baby",
)

SCOTTISMS = (
    "would you like to buy a rose?",
    "Israel has a right to defend itself."
)

PUBBIESMACK = (
    "{nick}: go back to reddit fam",
    "{nick}: What are ya, some alpha clone? :frogout:",
    "{nick}: Ascendance is that way ---->",
    "{nick}: :commissar:",
    "{nick}: :frogbarf:",
    "{nick}: sup m8 baited on free iskies",
    "{nick}: Too bad I can't kick you for that anymore :argh:",
    "{nick}: Dreddit is recruiting!",
    "Andail, is that you?",
    "Me right now: :smithicide:",
    "kick {nick}, MAKE XVMX GREAT AGAIN!",
    "This is worse than the zKB comment section :cripes:"
)


@cachetools.func.lru_cache(maxsize=1)
def _read_lines(path):
    with open(path, 'r') as f:
        return f.read().splitlines()


def _scored_choice(items, scores):
    n = len(items)
    scores = np.fromiter(scores, dtype=np.float64, count=n)

    # Normalize minimum score to >= 1
    min_score = np.amin(scores, initial=0)
    if min_score < 1:
        scores += 1 - min_score

    # Every item has a uniform base probability to be selected,
    # to which an additional 4x log-score boost is applied.
    scores = np.log(scores)
    p = 0.2 / n + 0.8 * (scores / scores.sum())
    return np.random.choice(items, p=p)


class Say(object):
    def pubbiesmack(self, mess):
        """Smack that pubbie."""
        return random.choice(PUBBIESMACK).format(nick=self.get_sender_username(mess))

    @botcmd
    def fishsay(self, mess, args):
        """Fishy wisdom"""
        return random.choice(FISHISMS)

    @botcmd
    def pimpsay(self, mess, args):
        """Like fishsay but blacker"""
        if args:
            return args + ' ' + random.choice(PIMPISMS)
        else:
            return random.choice(PIMPISMS)

    @botcmd
    def arelesay(self, mess, args):
        """Like fishsay but more fuckey"""
        return "https://youtu.be/{}".format(random.choice(ARELEISMS))

    @botcmd
    def nicksay(self, mess, args):
        """Like fishsay but pubbietasticer"""
        return random.choice(NICKISMS).format('0' * int(2 + random.expovariate(.25)))

    @botcmd
    def chasesay(self, mess, args):
        """Please"""
        sender = args.strip() or self.get_sender_username(mess)
        return "{}, would you PLEASE".format(sender)

    @botcmd
    def kairksay(self, mess, args):
        """Like fishsay but more Kafkaesque"""
        sender = args.strip() or self.get_sender_username(mess)
        return "{}, {} -Kairk".format(sender, random.choice(KAIRKISMS))

    @botcmd
    def dariussay(self, mess, args):
        """Like fishsay but bordering on weird"""
        sender = args.strip() or self.get_sender_username(mess)
        return "{}, {}".format(sender, random.choice(DARIUSISMS))

    @botcmd
    def scottsay(self, mess, args):
        """Like fishsay but coming from Israel"""
        if args:
            return "{}, {}".format(args, random.choice(SCOTTISMS))
        else:
            return random.choice(SCOTTISMS)

    @botcmd
    def eksay(self, mess, args):
        """Like fishsay but more dead"""
        sender = args.strip() or self.get_sender_username(mess)
        return ":rip: {}".format(sender)

    @botcmd
    def handysay(self, mess, args):
        """Like fishsay but blame lofac for the misspelled name"""
        return random.choice(_read_lines(HANDEY_QUOTES))

    @botcmd(name="8ball")
    def bot_8ball(self, mess, args):
        """<question> - Provides insight into the future"""
        if not args:
            return "Please provide a question to answer"
        else:
            return random.choice(EBALL_ANSWERS)

    @botcmd
    def sayhi(self, mess, args):
        """[name] - Says hi to you or name if provided"""
        sender = args.strip() or self.get_sender_username(mess)
        return "Hi {}!".format(sender)


class Fun(object):
    @botcmd
    def rtd(self, mess, args):
        """Like a box of chocolates, you never know what you're gonna get"""
        return random.choice(_read_lines(EMOTES)).split()[-1]

    @botcmd
    def rtq(self, mess, args):
        """Like a box of chocolates, but without emotes this time"""
        try:
            r = api.request_api("http://bash.org/?random", timeout=5)
        except APIError as e:
            return unicode(e)
        soup = BeautifulSoup(r.text, "html.parser")

        try:
            quote = random.choice(soup.find_all("p", class_="quote"))
        except IndexError:
            return "Failed to load any quotes from http://bash.org/?random"

        quote_href = quote.find("a", title="Permanent link to this quote.")['href']
        quote_rating = int(quote.find("font").text)
        quote = quote.next_sibling.text

        return "http://bash.org/{} ({:+,})\n{}".format(quote_href, quote_rating, quote)

    @botcmd
    def rtxkcd(self, mess, args):
        """Like a box of chocolates, but with xkcds"""
        try:
            res = api.request_api("https://xkcd.com/info.0.json").json()
        except APIError as e:
            return unicode(e)
        except ValueError:
            return "Error while parsing response"

        comic_id = random.randint(1, res['num'])
        comic_url = "https://xkcd.com/{}/".format(comic_id)

        try:
            comic = api.request_api(comic_url + "info.0.json").json()
        except APIError as e:
            return unicode(e)
        except ValueError:
            return "Failed to load xkcd #{} from {}".format(comic_id, comic_url)

        return '<a href="{}">{}</a> (<em>{}/{}/{}</em>)'.format(
            comic_url, comic['safe_title'], comic['year'], comic['month'], comic['day']
        )

    @botcmd
    def rtud(self, mess, args):
        """Like a box of chocolates, but with loads of pubbie talk"""
        return self.urban(mess, "")

    @staticmethod
    def urban_link(match):
        return '<a href="https://www.urbandictionary.com/define.php?term={}">{}</a>'.format(
            urllib.quote_plus(match.group(1)), match.group(1)
        )

    @botcmd
    def urban(self, mess, args):
        """[word] - Urban Dictionary's definition of word or, if missing, of a random word"""
        if args:
            url = "https://api.urbandictionary.com/v0/define"
            params = {'term': args.strip()}
        else:
            url = "https://api.urbandictionary.com/v0/random"
            params = None

        try:
            res = api.request_api(url, params=params).json()
        except APIError as e:
            return unicode(e)
        except ValueError:
            return "Error while parsing response"

        if not res['list']:
            return 'Failed to find any definitions for "{}"'.format(args)

        entry = _scored_choice(
            res['list'],
            (desc['thumbs_up'] - desc['thumbs_down'] for desc in res['list'])
        )

        desc = cgi.escape(entry['definition'])
        desc = re.sub(r"((?:\r|\n|\r\n)+)", "<br />", desc).rstrip("<br />")
        desc = re.sub(r"\[([\S ]+?)\]", self.urban_link, desc)

        return '<a href="{}">{}</a> by <em>{}</em> rated {:+,}<br />{}'.format(
            entry['permalink'], entry['word'], entry['author'],
            entry['thumbs_up'] - entry['thumbs_down'], desc
        )

    @botcmd(disable_if=not config.IMGUR_ID)
    def corgitax(self, mess, args):
        """Like a box of chocolates, if chocolates were doggos"""
        return self.imgur(mess, "corgi")

    @botcmd(disable_if=not config.IMGUR_ID)
    def imgur(self, mess, args):
        """<query> - Viral images straight off Imgur's search bar"""
        headers = {'Authorization': "Client-ID " + config.IMGUR_ID}
        params = {'mature': "false", "album_previews": "false"}
        if args:
            url = "https://api.imgur.com/3/gallery/search/viral"
            params['q'] = args.strip()
        else:
            url = "https://api.imgur.com/3/gallery/hot/viral"

        try:
            res = api.request_api(url, params=params, headers=headers).json()
        except APIError as e:
            return unicode(e)
        except ValueError:
            return "Error while parsing response"

        if not res['data']:
            return 'Failed to find any images for "{}"'.format(args)

        image = _scored_choice(res['data'], (img['score'] for img in res['data']))
        return '<a href="{}">{}</a> ({:+,})'.format(
            image['link'], cgi.escape(image['title']), image['points']
        )


class Chains(object):
    @botcmd(hidden=True, name="every")
    def bot_every(self, mess, args):
        """Every lion except for at most one"""
        if not args and random.randint(1, 5) == 1:
            return "lion"

    @botcmd(hidden=True, name="lion")
    def bot_lion(self, mess, args):
        """Every lion except for at most one"""
        if not args and random.randint(1, 5) == 1:
            return "except"

    @botcmd(hidden=True, name="except")
    def bot_except(self, mess, args):
        """Every lion except for at most one"""
        if not args and random.randint(1, 5) == 1:
            return "for"

    @botcmd(hidden=True, name="for")
    def bot_for(self, mess, args):
        """Every lion except for at most one"""
        if not args and random.randint(1, 5) == 1:
            return "at"

    @botcmd(hidden=True, name="at")
    def bot_at(self, mess, args):
        """Every lion except for at most one"""
        if not args and random.randint(1, 5) == 1:
            return "most"

    @botcmd(hidden=True, name="most")
    def bot_most(self, mess, args):
        """Every lion except for at most one"""
        if not args and random.randint(1, 5) == 1:
            return "one"

    @botcmd(hidden=True, name="one")
    def bot_one(self, mess, args):
        """Every lion except for at most one"""
        if not args and random.randint(1, 5) == 1:
            return ":bravo:"

    @botcmd(hidden=True, name='z')
    def bot_z(self, mess, args):
        """z0r"""
        if not args and random.randint(1, 3) == 1:
            return '0'

    @botcmd(hidden=True, name='0')
    def bot_0(self, mess, args):
        """z0r"""
        if not args and random.randint(1, 3) == 1:
            return 'r'

    @botcmd(hidden=True, name='r')
    def bot_r(self, mess, args):
        """z0r"""
        if not args and random.randint(1, 3) == 1:
            return 'z'

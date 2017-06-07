# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

import random
import re
import cgi
import urllib

import requests
from bs4 import BeautifulSoup

from .botcmd import botcmd
from .helpers.files import EMOTES, HANDY_QUOTES

# 8ball answers like the original, as per http://en.wikipedia.org/wiki/Magic_8-Ball
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
    "Oh d{}d",
    "D{}d, never go full retart!"
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

JOKERISMS = (
    "dont be a retard",
    "dont ruin our zkb efficiency",
    "urbad"
)

PUBBIESMACK = (
    "{nick}: go back to reddit fam",
    "{nick}: What are you, a fuckin alpha clone? :frogout:",
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
    def jokersay(self, mess, args):
        """Like fishsay but german"""
        if args:
            return args + ' ' + random.choice(JOKERISMS)
        else:
            return random.choice(JOKERISMS)

    @botcmd
    def handysay(self, mess, args):
        """Like fishsay but blame lofac"""
        with open(HANDY_QUOTES, 'r') as says_file:
            says = says_file.read().splitlines()

        return random.choice(says)

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
        with open(EMOTES, 'r') as emotes_file:
            emotes = emotes_file.read().splitlines()

        while not emotes.pop(0) == "[default]":
            pass

        return random.choice(emotes).split()[-1]

    @botcmd
    def rtq(self, mess, args):
        """Like a box of chocolates, but without emotes this time"""
        try:
            r = requests.get("http://bash.org/?random", timeout=5)
        except requests.exceptions.RequestException as e:
            return "Error while connecting to http://bash.org: {}".format(e)
        soup = BeautifulSoup(r.text, "html.parser")

        try:
            quote = random.choice(soup.find_all("p", class_="quote"))
        except IndexError:
            return "Failed to load any quotes from http://bash.org/?random"

        quote_href = quote.find("a", title="Permanent link to this quote.")['href']
        quote_rating = int(quote.find("font").text)
        quote = quote.next_sibling.text

        return "http://bash.org/{} ({:+})\n{}".format(quote_href, quote_rating, quote)

    @botcmd
    def rtxkcd(self, mess, args):
        """Like a box of chocolates, but with xkcds"""
        try:
            res = requests.get("https://xkcd.com/info.0.json", timeout=3).json()
        except requests.exceptions.RequestException as e:
            return "Error while connecting to https://xkcd.com: {}".format(e)
        except ValueError:
            return "Error while parsing response from https://xkcd.com"

        comic_id = random.randint(1, res['num'])
        comic_url = "https://xkcd.com/{}/".format(comic_id)

        try:
            comic = requests.get(comic_url + "info.0.json", timeout=3).json()
        except requests.exceptions.RequestException as e:
            return "Error while connecting to https://xkcd.com: {}".format(e)
        except ValueError:
            return "Failed to load xkcd #{} from {}".format(comic_id, comic_url)

        return "<strong>{}</strong> (<em>{}/{}/{}</em>): {}".format(
            comic['safe_title'], comic['year'], comic['month'], comic['day'], comic_url
        )

    @botcmd
    def rtud(self, mess, args):
        """Like a box of chocolates, but with loads of pubbie talk"""
        return self.urban(mess, "")

    @botcmd
    def urban(self, mess, args):
        """[word] - Urban Dictionary's definition of word or, if missing, of a random word"""
        url = "http://api.urbandictionary.com/v0/"
        url += "random" if not args else "define"
        params = None if not args else {'term': args}

        try:
            res = requests.get(url, params=params, timeout=3).json()
        except requests.exceptions.RequestException as e:
            return "Error while connecting to https://www.urbandictionary.com: {}".format(e)
        except ValueError:
            return "Error while parsing response from https://www.urbandictionary.com"

        if not res['list']:
            return 'Failed to find any definitions for "{}"'.format(args)

        # Create a list of definitions with positive (>= 0) rating numbers
        choices = [(desc, desc['thumbs_up'] - desc['thumbs_down']) for desc in res['list']]
        min_rating = min(desc[1] for desc in choices)
        if min_rating < 0:
            abs_min = abs(min_rating)
            choices = [(desc[0], desc[1] + abs_min) for desc in choices]

        # Select a random definition using rating as weight
        rand = random.uniform(0, sum(choice[1] for choice in choices))
        entry = None

        for desc, weight in choices:
            rand -= weight
            if rand <= 0:
                entry = desc
                break

        def urban_link(match):
            return '<a href="https://www.urbandictionary.com/define.php?term={}">{}</a>'.format(
                urllib.quote_plus(match.group(1).encode("utf-8")), match.group(1)
            )

        desc = cgi.escape(entry['definition'])
        desc = re.sub("((?:\r|\n|\r\n)+)", "<br />", desc).rstrip("<br />")
        desc = re.sub("\[([\S ]+?)\]", urban_link, desc)

        desc = "<strong>{}</strong> by <em>{}</em> rated {:+}: {}<br />{}".format(
            entry['word'], entry['author'], entry['thumbs_up'] - entry['thumbs_down'],
            entry['permalink'], desc
        )

        if 'tags' in res and res['tags']:
            desc += "<br />{}".format(' '.join("#{}".format(tag) for tag in res['tags']))

        return desc


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

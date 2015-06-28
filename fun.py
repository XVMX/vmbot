from jabberbot import botcmd

import random


class Say(object):
    # 8ball answers like the original, as per http://en.wikipedia.org/wiki/Magic_8-Ball
    eball_answers = [
        'It is certain',
        'It is decidedly so',
        'Without a doubt',
        'Yes definitely',
        'You may rely on it',
        'As I see it, yes',
        'Most likely',
        'Outlook good',
        'Yes',
        'Signs point to yes',
        'Reply hazy try again',
        'Ask again later',
        'Better not tell you now',
        'Cannot predict now',
        'Concentrate and ask again',
        'Don\'t count on it',
        'My reply is no',
        'My sources say no',
        'Outlook not so good',
        'Very doubtful'
    ]
    fishisms = [
        "~The Python Way!~",
        "HOOOOOOOOOOOOOOOOOOOOOOO! SWISH!",
        "DIVERGENT ZONES!",
        "BONUSSCHWEIN! BONUSSCHWEIN!"
    ]
    pimpisms = [
        "eabod",
        "why do you hate black people?",
        "i want a bucket full of money covered rainbows",
        "bundle of sticks"
    ]
    chaseisms = ["would you PLEASE"]
    nickisms = [
        "D00d!",
        "But d00d!",
        "Come on d00d...",
        "Oh d00d",
        "D00d, never go full retart!"
    ]
    areleisms = [
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
    ]
    kairkisms = [
        "thanks for filling this out.",
        "voting on your application to join VM is over, and you have passed.",
        "congratulations, you passed the security check.",
        "I regret to tell you that your application to join VM has been rejected.",
        "thank you for your interest in VM, and I wish you luck in your future endeavours in Eve.",
        "in 48h your membership of Valar Morghulis. will be terminated.",
        "you've got to improve, or I'll be sending out more kick notices, and I hate doing that.",
        "you get a cavity search, your friends get a cavity search, EVERYBODY gets a cavity search!"
    ]
    dariusisms = [
        "Baby",
    ]

    @botcmd
    def fishsay(self, mess, args):
        'Fishy wisdom.'
        return random.choice(self.fishisms)

    @botcmd
    def pimpsay(self, mess, args):
        'Like fishsay but blacker'
        if args:
            return "{} {}".format(args, random.choice(self.pimpisms))
        else:
            return random.choice(self.pimpisms)

    @botcmd
    def arelesay(self, mess, args):
        'Like fishsay but more fuckey'
        return "https://youtu.be/" + random.choice(self.areleisms)

    @botcmd
    def nicksay(self, mess, args):
        'Like fishsay but pubbietasticer'
        nickrandom = random.choice(self.nickisms)
        return nickrandom.replace('00', '0'*int(2+random.expovariate(.25)))

    @botcmd
    def chasesay(self, mess, args):
        'Please'
        cmdname = self.chasesay._jabberbot_command_name
        if args.startswith(cmdname):
            return "nope"
        sender = (args.strip() if args else self.get_sender_username(mess))
        return "{}, {}".format(sender, self.chaseisms[0])

    @botcmd
    def kairksay(self, mess, args):
        'Like fishsay but more Kafkaesque'
        sender = (args.strip() if args else self.get_sender_username(mess))
        return "{}, {} -Kairk".format(sender, random.choice(self.kairkisms))

    @botcmd
    def dariussay(self, mess, args):
        'Like fishsay but bordering on weird'
        sender = (args.strip() if args else self.get_sender_username(mess))
        return "{}, {}".format(sender, random.choice(self.dariusisms))

    @botcmd(name="8ball")
    def bot_8ball(self, mess, args):
        '<question> - Provides insight into the future'
        if not args:
            return 'You will need to provide a question for me to answer.'
        else:
            return random.choice(self.eball_answers)

    @botcmd
    def sayhi(self, mess, args):
        '[name] - Says hi to you or name if provided!'
        sender = (args.strip() if args else self.get_sender_username(mess))
        return "Hi {}!".format(sender)


class Chains(object):
    @botcmd(hidden=True)
    def every(self, mess, args):
        '''Every lion except for at most one'''
        if not args and random.randint(1, 5) == 1:
            return "lion"

    @botcmd(hidden=True)
    def lion(self, mess, args):
        '''Every lion except for at most one'''
        if not args and random.randint(1, 5) == 1:
            return "except"

    @botcmd(hidden=True, name="except")
    def bot_except(self, mess, args):
        '''Every lion except for at most one'''
        if not args and random.randint(1, 5) == 1:
            return "for"

    @botcmd(hidden=True, name="for")
    def bot_for(self, mess, args):
        '''Every lion except for at most one'''
        if not args and random.randint(1, 5) == 1:
            return "at"

    @botcmd(hidden=True)
    def at(self, mess, args):
        '''Every lion except for at most one'''
        if not args and random.randint(1, 5) == 1:
            return "most"

    @botcmd(hidden=True, name="most")
    def bot_most(self, mess, args):
        '''Every lion except for at most one'''
        if not args and random.randint(1, 5) == 1:
            return "one"

    @botcmd(hidden=True, name="one")
    def bot_one(self, mess, args):
        '''Every lion except for at most one'''
        if not args and random.randint(1, 5) == 1:
            return ":bravo:"

    @botcmd(hidden=True, name="z")
    def bot_z(self, mess, args):
        '''z0r'''
        if not args and random.randint(1, 3) == 1:
            return "0"

    @botcmd(hidden=True, name="0")
    def bot_0(self, mess, args):
        '''z0r'''
        if not args and random.randint(1, 3) == 1:
            return "r"

    @botcmd(hidden=True, name="r")
    def bot_r(self, mess, args):
        '''z0r'''
        if not args and random.randint(1, 3) == 1:
            return "z"

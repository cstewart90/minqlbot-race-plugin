import minqlbot
import json
import re
from urllib.request import urlopen


class race(minqlbot.Plugin):
    def __init__(self):
        self.add_hook("bot_connect", self.handle_bot_connect)
        self.add_hook("map", self.handle_map)
        self.add_hook("game_end", self.handle_game_end)
        self.add_hook("console", self.handle_console)
        self.add_command(("top", "top3"), self.cmd_top)
        self.add_command("rank", self.cmd_rank)
        self.add_command(("pb", "me"), self.cmd_pb)
        self.add_command("top100", self.cmd_top100)
        self.add_command("time", self.cmd_time)
        self.add_command("ranktime", self.cmd_ranktime)
        self.add_command("avg", self.cmd_avg)
        self.add_command(("stop", "stop3"), self.cmd_stop)
        self.add_command("srank", self.cmd_srank)
        self.add_command(("spb", "sme"), self.cmd_spb)
        self.add_command("stime", self.cmd_stime)
        self.add_command("sranktime", self.cmd_sranktime)
        self.add_command("savg", self.cmd_savg)
        self.add_command("help", self.cmd_help)
        self.add_command("commands", self.cmd_commands)
        self.add_command("update", self.cmd_update)

    def write_data(self):
        data = race.get_data_online(self.game().short_map)
        with open('times.json', 'w') as outfile:
            json.dump(data, outfile)
            self.debug("wrote times.json")

    def write_data_qlstats(self):
        data = race.get_data_online_qlstats("maps/" + self.game().short_map + "?ruleset=pql&weapons=off")
        with open('times_strafe.json', 'w') as outfile:
            json.dump(data, outfile)
            self.debug("wrote times_strafe.json")

    def get_data(self, map):
        if map == self.game().short_map:
            return race.get_data_file("times.json")
        return race.get_data_online(map)

    def get_data_qlstats(self, query):
        if "maps/" in query:
            map = query.replace("maps/", "").replace("?ruleset=pql&weapons=off", "")
            if map == self.game().short_map:
                return self.get_data_file("times_strafe.json")
        return race.get_data_online_qlstats(query)

    @staticmethod
    def get_data_online(map):
        base_url = "http://quakelive.com/race/map/"
        r = urlopen(base_url + map)
        return json.loads(r.read().decode("utf-8"))

    @staticmethod
    def get_data_online_qlstats(query):
        base_url = "http://ql.leeto.fi/api/race/"
        r = urlopen(base_url + query)
        return json.loads(r.read().decode("utf-8"))

    @staticmethod
    def get_data_file(file):
        with open(file) as json_file:
            return json.load(json_file)

    @staticmethod
    def fix_time(time):
        if len(time) < 4:
            return "0." + time[-3:]
        return time[:-3] + "." + time[-3:]

    def get_map(self, msg):
        if len(msg) == 2:
            return msg[1].lower()
        else:
            return self.game().short_map

    @staticmethod
    def say_time(name, rank, last, time, first_time, map, strafe, channel):
        if rank != 1:
            time_diff = str(int(time) - int(first_time))
            time_diff = time_diff.zfill(3)
            time_diff_s = "^8[^1+" + race.fix_time(str(time_diff)) + "^8]"
        else:
            time_diff_s = ""

        time_s = race.fix_time(time)
        strafe_s = "^2(strafe)" if strafe else ""

        channel.reply(
            "^7{} ^2is rank ^3{} ^2of ^3{} ^2with ^3{}{} ^2on ^3{} {}".format(name, rank, last, time_s, time_diff_s,
                                                                              map, strafe_s))

    def get_average(self, player, msg, strafe):
        if len(msg) == 1:
            name = player.clean_name
        else:
            name = msg[1]

        strafe_s = "off" if strafe else "on"
        data = self.get_data_qlstats("players/" + name + "?ruleset=pql&weapons=" + strafe_s)

        total_maps = len(data['data']['scores'])
        if total_maps == 0:
            return name, 0

        total_rank = 0
        for score in data['data']['scores']:
            # don't include removed maps
            if score['MAP'] != "bloodlust" and score['MAP'] != "doubleimpact" and score['MAP'] != "eviscerated":
                total_rank += score['RANK']

        return name, total_rank / total_maps

    def handle_bot_connect(self):
        self.write_data()
        self.write_data_qlstats()

    def handle_map(self, map):
        self.write_data()
        self.write_data_qlstats()

    def handle_game_end(self, game, score, winner):
        self.write_data()
        self.write_data_qlstats()

    def handle_console(self, text):
        if "finished the race in in" not in text:
            return

        text_list = text.split()
        name = text_list[-7]
        name_clean = re.sub(r"\^[0-9]", "", name).lower()
        self.debug(name_clean)
        time_list = re.findall("[0-9]+", text_list[-1])
        time = int(time_list[0]) * 60000 + int(time_list[1]) * 1000 + int(time_list[2])

        data = self.get_data_file("times.json")
        pb = data['scores'][-1]['score']
        for score in data['scores']:
            if name_clean == str(score['name']).lower():
                pb = int(score['score'])

        if time < pb:
            self.send_command("say {} ^2got a new PB!".format(name))

    def cmd_top(self, player, msg, channel):
        map = self.get_map(msg)
        data = self.get_data(map)

        ranks = []
        for i in range(3):
            score = data['scores'][i]
            name = score['name']
            time = race.fix_time(score['score'])
            ranks.append("^3{}. ^4{} ^2{}".format(i + 1, name, time))

        channel.reply("^2{}: {} {} {}".format(map, ranks[0], ranks[1], ranks[2]))

    def cmd_rank(self, player, msg, channel):
        if len(msg) == 1:
            rank = 1
            map = self.game().short_map
        elif len(msg) == 2:
            if msg[1].isdigit():
                rank = int(msg[1])
                map = self.game().short_map
            else:
                rank = 1
                map = msg[1].lower()
        else:
            rank = int(msg[1])
            map = msg[2].lower()

        data = self.get_data(map)

        score = data['scores'][rank - 1]
        name = score['name']
        last = len(data['scores'])
        time = score['score']
        first_time = data['scores'][0]['score']

        race.say_time(name, rank, last, time, first_time, map, False, channel)

    def cmd_pb(self, player, msg, channel):
        map = self.get_map(msg)
        data = self.get_data(map)

        for i, score in enumerate(data['scores']):
            if player.clean_name.lower() == str(score['name']).lower():
                last = len(data['scores'])
                time = score['score']
                first_time = data['scores'][0]['score']

                race.say_time(player, i + 1, last, time, first_time, map, False, channel)
                return

        channel.reply("no time found for {} in top 100".format(player))

    def cmd_top100(self, player, msg, channel):
        map = self.get_map(msg)
        data = self.get_data(map)

        score = data['scores'][99]
        name = score['name']
        last = len(data['scores'])
        time = score['score']
        first_time = data['scores'][0]['score']

        race.say_time(name, 100, last, time, first_time, map, False, channel)

    def cmd_time(self, player, msg, channel):
        if len(msg) == 1:
            channel.reply("usage: !time player <map>")
            return
        elif len(msg) == 2:
            name = msg[1]
            map = self.game().short_map
        else:
            name = msg[1]
            map = msg[2].lower()

        data = self.get_data(map)

        for i, score in enumerate(data['scores']):
            if name.lower() == str(score['name']).lower():
                last = len(data['scores'])
                time = score['score']
                first_time = data['scores'][0]['score']
                race.say_time(name, i + 1, last, time, first_time, map, False, channel)
                return

        channel.reply("no time found for {} in top 100".format(name))

    def cmd_ranktime(self, player, msg, channel):
        if len(msg) == 2:
            time = int(float(msg[1])*1000)
            map = self.game().short_map
        elif len(msg) == 3:
            time = int(float(msg[1])*1000)
            map = msg[2].lower()
        else:
            channel.reply("usage: !ranktime time <map>")
            return

        data = self.get_data(map)
        time_s = race.fix_time(str(time))
        last = len(data['scores'])

        for i, score in enumerate(data['scores']):
            if time < int(score['score']):
                channel.reply("^3{} ^2would be rank ^3{} ^2of ^3{} ^2on ^3{}".format(time_s, i+1, last, map))
                return

        channel.reply("^3{} ^2would not be in top ^3{}".format(time_s, last))

    def cmd_avg(self, player, msg, channel):
        name, average_rank = self.get_average(player, msg, False)
        if average_rank == 0:
            channel.reply("^3{} has no records on ql.leeto.fi".format(name))
        else:
            channel.reply("^3{} ^2average rank is ^3{:.2f}".format(name, average_rank))

    def cmd_stop(self, player, msg, channel):
        map = self.get_map(msg)
        data = self.get_data_qlstats("maps/" + map + "?ruleset=pql&weapons=off")

        ranks = []
        for i in range(3):
            score = data['data']['scores'][i]
            name = score['PLAYER']
            time = race.fix_time(str(score['SCORE']))
            ranks.append("^3{}. ^4{} ^2{}".format(i + 1, name, time))

        channel.reply("^2{}(strafe): {} {} {}".format(map, ranks[0], ranks[1], ranks[2]))

    def cmd_spb(self, player, msg, channel):
        map = self.get_map(msg)

        data = self.get_data_qlstats("maps/" + map + "?ruleset=pql&weapons=off")

        for score in data['data']['scores']:
            if player.clean_name.lower() == str(score['PLAYER']).lower():
                last = len(data['data']['scores'])
                time = str(score['SCORE'])
                first_time = str(data['data']['scores'][0]['SCORE'])
                race.say_time(player, score['RANK'], last, time, first_time, map, True, channel)
                return

        channel.reply("No time was found for {}".format(player))

    def cmd_srank(self, player, msg, channel):
        if len(msg) == 1:
            rank = 1
            map = self.game().short_map
        elif len(msg) == 2:
            if msg[1].isdigit():
                rank = int(msg[1])
                map = self.game().short_map
            else:
                rank = 1
                map = msg[1].lower()
        else:
            rank = int(msg[1])
            map = msg[2].lower()

        data = self.get_data_qlstats("maps/" + map + "?ruleset=pql&weapons=off")

        score = data['data']['scores'][rank - 1]
        name = score['PLAYER']
        last = len(data['data']['scores'])
        time = str(score['SCORE'])
        first_time = str(data['data']['scores'][0]['SCORE'])
        race.say_time(name, score['RANK'], last, time, first_time, map, True, channel)

    def cmd_stime(self, player, msg, channel):
        if len(msg) == 1:
            channel.reply("usage: !stime player <map>")
            return
        elif len(msg) == 2:
            name = msg[1]
            map = self.game().short_map
        else:
            name = msg[1]
            map = msg[2].lower()

        data = self.get_data_qlstats("maps/" + map + "?ruleset=pql&weapons=off")

        for score in data['data']['scores']:
            if name.lower() == str(score['PLAYER']).lower():
                name = score['PLAYER']
                last = len(data['data']['scores'])
                time = str(score['SCORE'])
                first_time = str(data['data']['scores'][0]['SCORE'])
                race.say_time(name, score['RANK'], last, time, first_time, map, True, channel)
                return

        channel.reply("No time was found for {}".format(name))

    def cmd_sranktime(self, player, msg, channel):
        if len(msg) == 2:
            time = int(float(msg[1])*1000)
            map = self.game().short_map
        elif len(msg) == 3:
            time = int(float(msg[1])*1000)
            map = msg[2].lower()
        else:
            channel.reply("usage: !sranktime time <map>")
            return

        data = self.get_data_qlstats("maps/" + map + "?ruleset=pql&weapons=off")
        time_s = race.fix_time(str(time))
        last = len(data['data']['scores'])

        for i, score in enumerate(data['data']['scores']):
            if time < int(score['SCORE']):
                channel.reply("^3{} ^2would be rank ^3{} ^2of ^3{} ^2on ^3{}".format(time_s, i+1, last, map))
                return

        channel.reply("^3{} ^2would be rank ^3{}".format(time_s, last+1))

    def cmd_savg(self, player, msg, channel):
        name, average_rank = self.get_average(player, msg, True)
        if average_rank == 0:
            channel.reply("^3{} has no records on ql.leeto.fi".format(name))
        else:
            channel.reply("^3{} ^2average strafe rank is ^3{:.2f}".format(name, average_rank))

    def cmd_help(self, player, msg, channel):
        channel.reply("Go to ^6tinyurl.com/qlracebot ^3!commands ^2for a list of commands")

    def cmd_commands(self, player, msg, channel):
        channel.reply("Commands: ^3!(s)top !(s)pb !(s)rank !(s)time !(s)ranktime !(s)avg !top100")

    def cmd_update(self, player, msg, channel):
        self.write_data()
        self.write_data_qlstats()

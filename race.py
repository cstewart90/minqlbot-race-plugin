import minqlbot
import json
import re
import urllib.request


class race(minqlbot.Plugin):
    def __init__(self):
        self.add_hook("bot_connect", self.handle_bot_connect)
        self.add_hook("map", self.handle_map)
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
        url = base_url + map
        request = urllib.request.Request(url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; WOW64; Trident/5.0)"})
        response = urllib.request.urlopen(request)
        return json.loads(response.read().decode("utf-8"))

    @staticmethod
    def get_data_online_qlstats(query):
        base_url = "http://ql.leeto.fi/api/race/"
        url = base_url + query
        request = urllib.request.Request(url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; WOW64; Trident/5.0)"})
        response = urllib.request.urlopen(request)
        j = json.loads(response.read().decode("utf-8"))
        data = j['data']
        for score in data['scores']:
            score['name'] = score.pop('PLAYER')
            score['score'] = score.pop('SCORE')
        return data

    @staticmethod
    def get_data_file(file):
        with open(file) as json_file:
            return json.load(json_file)

    @staticmethod
    def fix_time(time):
        time = str(time)
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
            "^3{} ^2is rank ^3{} ^2of ^3{} ^2with ^3{}{} ^2on ^3{} {}".format(name, rank, last, time_s, time_diff_s,
                                                                              map, strafe_s))

    def get_rank(self, data, rank):
        score = data['scores'][rank - 1]
        name = score['name']
        time = str(score['score'])
        first_time = str(data['scores'][0]['score'])
        return name, time, first_time

    def get_pb(self, data, player):
        for i, score in enumerate(data['scores']):
            if player.lower() == str(score['name']).lower():
                time = score['score']
                rank = i + 1
                first_time = data['scores'][0]['score']
                return rank, time, first_time
        return -1, -1, -1

    def get_rank_from_time(self, data, time):
        for i, score in enumerate(data['scores']):
            if time < int(score['score']):
                return i + 1
        return -1

    def get_average(self, player, msg, strafe):
        if len(msg) == 1:
            name = player.clean_name
        else:
            name = msg[1]

        strafe_s = "off" if strafe else "on"
        data = self.get_data_qlstats("players/" + name + "?ruleset=pql&weapons=" + strafe_s)

        total_maps = len(data['scores'])
        if total_maps == 0:
            return name, 0

        total_rank = 0
        for score in data['scores']:
            # don't include removed maps
            if score['MAP'] != "bloodlust" and score['MAP'] != "doubleimpact" and score['MAP'] != "eviscerated":
                total_rank += score['RANK']

        return name, total_rank / total_maps

    def check_pb(self, text):
        text_list = text.split()
        name = text_list[-7]
        name_clean = re.sub(r"\^[0-9]", "", name).lower()
        time_list = re.findall("[0-9]+", text_list[-1])
        time = int(time_list[0]) * 60000 + int(time_list[1]) * 1000 + int(time_list[2])
        data = self.get_data_file("times.json")
        pb = int(data['scores'][-1]['score'])
        for score in data['scores']:
            if name_clean == str(score['name']).lower():
                pb = int(score['score'])
        if time < pb:
            rank = self.get_rank_from_time(data, time)
            if rank == 1:
                self.send_command("say ^3{} ^6just got a world record!".format(name))
            else:
                self.send_command("say ^3{} ^2broke their PB and is now rank ^3{}^2!".format(name, rank))

    def handle_bot_connect(self):
        self.write_data()
        self.write_data_qlstats()

    def handle_map(self, map):
        self.write_data()
        self.write_data_qlstats()

    def handle_console(self, text):
        if "finished the race in in" in text:
            self.check_pb(text)
            return

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
        name, time, first_time = self.get_rank(data, rank)
        last = len(data['scores'])

        race.say_time(name, rank, last, time, first_time, map, False, channel)

    def cmd_pb(self, player, msg, channel):
        map = self.get_map(msg)
        data = self.get_data(map)
        rank, time, first_time = self.get_pb(data, player.clean_name)
        last = len(data['scores'])
        if rank != -1:
            race.say_time(player, rank, last, time, first_time, map, False, channel)
        else:
            channel.reply("no time found for {} in top 100".format(player))

    def cmd_top100(self, player, msg, channel):
        map = self.get_map(msg)
        data = self.get_data(map)
        last = len(data['scores'])
        name, time, first_time = self.get_rank(data, last)

        race.say_time(name, last, last, time, first_time, map, False, channel)

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
        rank, time, first_time = self.get_pb(data, name)
        last = len(data['scores'])

        if rank != -1:
            race.say_time(name, rank, last, time, first_time, map, False, channel)
        else:
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
        rank = self.get_rank_from_time(data, time)
        last = len(data['scores'])

        if rank != -1:
            channel.reply("^3{} ^2would be rank ^3{} ^2of ^3{} ^2on ^3{}".format(time_s, rank, last, map))
        else:
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
            score = data['scores'][i]
            name = score['name']
            time = race.fix_time(str(score['score']))
            ranks.append("^3{}. ^4{} ^2{}".format(i + 1, name, time))

        channel.reply("^2{}(strafe): {} {} {}".format(map, ranks[0], ranks[1], ranks[2]))

    def cmd_spb(self, player, msg, channel):
        map = self.get_map(msg)
        data = self.get_data_qlstats("maps/" + map + "?ruleset=pql&weapons=off")
        rank, time, first_time = self.get_pb(data, player.clean_name)
        last = len(data['scores'])
        if rank != -1:
            race.say_time(player, rank, last, time, first_time, map, True, channel)
        else:
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
        name, time, first_time = self.get_rank(data, rank)
        last = len(data['scores'])

        race.say_time(name, rank, last, time, first_time, map, True, channel)

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
        rank, time, first_time = self.get_pb(data, name)
        last = len(data['scores'])

        if rank != -1:
            race.say_time(name, rank, last, time, first_time, map, True, channel)
        else:
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
        rank = self.get_rank_from_time(data, time)
        time_s = race.fix_time(str(time))
        last = len(data['scores'])

        if rank != -1:
            channel.reply("^3{} ^2would be rank ^3{} ^2of ^3{} ^2on ^3{}".format(time_s, rank, last, map))
        else:
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

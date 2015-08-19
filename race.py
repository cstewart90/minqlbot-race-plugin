import minqlbot
import json
import re
import urllib.request


class race(minqlbot.Plugin):
    def __init__(self):
        super().__init__()
        self.add_hook("scores", self.handle_scores)
        self.add_hook("map", self.handle_map)
        self.add_hook("game_end", self.handle_game_end)
        self.add_hook("console", self.handle_console)
        self.add_command(("top", "top3"), self.cmd_top, usage="[amount] [map]")
        self.add_command("all", self.cmd_all, usage="[map]")
        self.add_command("rank", self.cmd_rank, usage="[rank] [map]")
        self.add_command(("pb", "me"), self.cmd_pb, usage="[map]")
        self.add_command("top100", self.cmd_top100, usage="[map")
        self.add_command("time", self.cmd_time, usage="<player> [map]")
        self.add_command("ranktime", self.cmd_ranktime, usage="<time> [map]")
        self.add_command("avg", self.cmd_avg, usage="[player]")
        self.add_command(("stop", "stop3"), self.cmd_stop, usage="[amount] [map]")
        self.add_command("sall", self.cmd_sall, usage="[map]")
        self.add_command("srank", self.cmd_srank, usage="[rank] [map]")
        self.add_command(("spb", "sme"), self.cmd_spb, usage="[map]")
        self.add_command("stime", self.cmd_stime, usage="<player> [map]")
        self.add_command("sranktime", self.cmd_sranktime, usage="<time> [map]")
        self.add_command("savg", self.cmd_savg, usage="[player]")
        self.add_command(("commands", "help"), self.cmd_commands)
        self.add_command("update", self.cmd_update)
        self.add_command("join", self.cmd_join, 2)

        self.expecting_scores = False
        self.player = None
        self.weps = False
        self.end_game_timer = None

    def handle_scores(self, scores):
        if self.expecting_scores:
            for score in scores:
                name = score.player.clean_name.lower()
                if name == self.player.clean_name.lower():
                    map = self.game().short_map.lower()
                    if self.weps:
                        data = self.get_data(map)
                        cmd = "!ranktime"
                    else:
                        data = self.get_data_qlstats("maps/" + map + "?ruleset=pql&weapons=off")
                        map = "{}^2(strafe)".format(map)
                        cmd = "!sranktime"

                    time = score.score
                    if time == -1:
                        self.msg("^7Usage: ^6{0} <time> [map] ^7or just ^6{0} ^7if you have set a time.".format(cmd))
                        self.expecting_scores = False
                        return

                    time_s = race.time_string(time)
                    rank, _ = race.get_rank_from_time(data, time)
                    last = len(data["scores"])

                    if rank != -1:
                        self.msg("^3{} ^2would be rank ^3{} ^2of ^3{} ^2on ^3{}".format(time_s, rank, last, map))
                    else:
                        if self.weps:
                            self.msg("^3{} ^2would not be in top ^3{} ^2on ^3{}".format(time_s, last, map))
                        else:
                            self.msg("^3{} ^2would be rank ^3{} ^2on ^3{}".format(time_s, last+1, map))

            self.expecting_scores = False

    def handle_map(self, map):
        self.write_data()
        self.write_data_qlstats()

    def handle_game_end(self, game, score, winner):
        self.end_game_timer = self.delay(5, self.write_data)

    def handle_console(self, text):
        if "finished the race in in" not in text:
            return
        if self.game().state == "in_progress":
            text_list = text.split()
            name = text_list[-7]
            name_clean = re.sub(r"\^[0-9]", "", name).lower()
            time_s = text_list[-1]
            time = race.ms(time_s)
            data = race.get_data_file("times.json")
            for score in data["scores"]:
                if name_clean == str(score["name"]).lower():
                    pb = int(score["score"])
                    break
            else:
                pb = int(data["scores"][-1]["score"])

            if time < pb:
                rank, time_diff = race.get_rank_from_time(data, time)
                if rank == 1:
                    self.msg("^7{} ^2just broke the ^3world record! {}".format(name, time_diff))
                else:
                    self.msg("^7{} ^2broke their PB and is now rank ^3{} {}".format(name, rank, time_diff))

    def cmd_top(self, player, msg, channel):
        if len(msg) == 1:
            amount = 3
            map = self.game().short_map.lower()
        elif len(msg) == 2:
            if msg[1].isdigit():
                amount = int(msg[1])
                map = self.game().short_map.lower()
            else:
                amount = 3
                map = msg[1].lower()
        else:
            amount = int(msg[1])
            map = msg[2]

        if amount > 30:
            channel.reply("Please use value <=30")
            return

        data = self.get_data(map)
        if len(data["scores"]) == 0:
            channel.reply("No times on ql.leeto.fi for ^3{}".format(map))
        else:
            if amount > len(data["scores"]):
                amount = len(data["scores"])
            ranks = []
            for i in range(amount):
                score = data["scores"][i]
                name = score["name"]
                time = race.time_string(score["score"])
                ranks.append("^3{}. ^4{} ^2{}".format(i + 1, name, time))

            channel.reply("^2{}: {}".format(map, " ".join(ranks)))

    def cmd_all(self, player, msg, channel):
        map = self.get_map(msg)
        data = self.get_data(map)

        times = []
        for p in self.players():
            rank, time, first_time = race.get_pb(data, p.clean_name)
            if rank != -1:
                times.append("^3{}. ^7{} ^2{}".format(rank, p, race.time_string(time)))

        if len(times) == 0:
            channel.reply("No times were found for anyone in top 100 for ^3{} ^2:(".format(map))
        else:
            times.sort(key=natural_keys)
            channel.reply("{}: {}".format(map, " ".join(times)))

    def cmd_rank(self, player, msg, channel):
        if len(msg) == 1:
            rank = 1
            map = self.game().short_map.lower()
        elif len(msg) == 2:
            if msg[1].isdigit():
                rank = int(msg[1])
                map = self.game().short_map.lower()
            else:
                rank = 1
                map = msg[1].lower()
        else:
            rank = int(msg[1])
            map = msg[2].lower()

        data = self.get_data(map)
        name, time, first_time = race.get_rank(data, rank)
        last = len(data["scores"])

        race.say_time(name, rank, last, time, first_time, map, False, channel)

    def cmd_pb(self, player, msg, channel):
        map = self.get_map(msg)
        data = self.get_data(map)
        rank, time, first_time = race.get_pb(data, player.clean_name)
        last = len(data["scores"])
        if rank != -1:
            race.say_time(player, rank, last, time, first_time, map, False, channel)
        else:
            channel.reply("No time found for ^7{} ^2in top 100".format(player))

    def cmd_top100(self, player, msg, channel):
        map = self.get_map(msg)
        data = self.get_data(map)
        last = len(data["scores"])
        name, time, first_time = race.get_rank(data, last)

        race.say_time(name, last, last, time, first_time, map, False, channel)

    def cmd_time(self, player, msg, channel):
        if len(msg) == 1:
            return minqlbot.RET_USAGE
        elif len(msg) == 2:
            name = msg[1]
            map = self.game().short_map.lower()
        else:
            name = msg[1]
            map = msg[2].lower()

        data = self.get_data(map)
        rank, time, first_time = race.get_pb(data, name)
        last = len(data["scores"])

        if rank != -1:
            race.say_time(name, rank, last, time, first_time, map, False, channel)
        else:
            channel.reply("No time found for ^7{} ^2in top 100".format(name))

    def cmd_ranktime(self, player, msg, channel):
        if len(msg) == 2:
            map = self.game().short_map.lower()
        elif len(msg) == 3:
            map = msg[2].lower()
        else:
            self.expecting_scores = True
            self.player = player
            self.weps = True
            self.scores()
            return

        time = race.ms(msg[1])
        data = self.get_data(map)
        time_s = race.time_string(time)
        rank, _ = race.get_rank_from_time(data, time)
        last = len(data["scores"])

        if rank != -1:
            channel.reply("^3{} ^2would be rank ^3{} ^2of ^3{} ^2on ^3{}".format(time_s, rank, last, map))
        else:
            channel.reply("^3{} ^2would not be in top ^3{}".format(time_s, last))

    def cmd_avg(self, player, msg, channel):
        name, average_rank, total_maps, medals = self.get_average(player, msg, False)
        if average_rank == 0:
            channel.reply("^7{} ^2has no records on ql.leeto.fi".format(name))
        else:
            channel.reply("^7{} ^2average rank: ^3{:.2f}^2({} maps) ^71st: ^3{} ^72nd: ^3{} ^73rd: ^3{}"
                          .format(name, average_rank, total_maps, medals[0], medals[1], medals[2]))

    def cmd_stop(self, player, msg, channel):
        if len(msg) == 1:
            amount = 3
            map = self.game().short_map.lower()
        elif len(msg) == 2:
            if msg[1].isdigit():
                amount = int(msg[1])
                map = self.game().short_map.lower()
            else:
                amount = 3
                map = msg[1].lower()
        else:
            amount = int(msg[1])
            map = msg[2]

        if amount > 30:
            channel.reply("Please use value <=30")
            return

        data = self.get_data_qlstats("maps/" + map + "?ruleset=pql&weapons=off")
        if len(data["scores"]) == 0:
            channel.reply("No strafe times on ql.leeto.fi for ^3{}".format(map))
        else:
            if amount > len(data["scores"]):
                amount = len(data["scores"])
            ranks = []
            for i in range(amount):
                score = data["scores"][i]
                name = score["name"]
                time = race.time_string(score["score"])
                ranks.append("^3{}. ^4{} ^2{}".format(i + 1, name, time))

            channel.reply("^2{}(strafe): {}".format(map, " ".join(ranks)))

    def cmd_sall(self, player, msg, channel):
        map = self.get_map(msg)
        data = self.get_data_qlstats("maps/" + map + "?ruleset=pql&weapons=off")

        times = []
        for p in self.players():
            rank, time, first_time = race.get_pb(data, p.clean_name)
            if rank != -1:
                times.append("^3{}. ^7{} ^2{}".format(rank, p, race.time_string(time)))

        if len(times) == 0:
            channel.reply("No strafe times were found for anyone on ql.leeto.fi for ^3{} ^2:(".format(map))
        else:
            times.sort(key=natural_keys)
            channel.reply("{}(strafe): {}".format(map, " ".join(times)))

    def cmd_spb(self, player, msg, channel):
        map = self.get_map(msg)
        data = self.get_data_qlstats("maps/" + map + "?ruleset=pql&weapons=off")
        rank, time, first_time = race.get_pb(data, player.clean_name)
        last = len(data["scores"])
        if rank != -1:
            race.say_time(player, rank, last, time, first_time, map, True, channel)
        else:
            channel.reply("No strafe time was found for ^7{}".format(player))

    def cmd_srank(self, player, msg, channel):
        if len(msg) == 1:
            rank = 1
            map = self.game().short_map.lower()
        elif len(msg) == 2:
            if msg[1].isdigit():
                rank = int(msg[1])
                map = self.game().short_map.lower()
            else:
                rank = 1
                map = msg[1].lower()
        else:
            rank = int(msg[1])
            map = msg[2].lower()

        data = self.get_data_qlstats("maps/" + map + "?ruleset=pql&weapons=off")
        name, time, first_time = race.get_rank(data, rank)
        last = len(data["scores"])

        race.say_time(name, rank, last, time, first_time, map, True, channel)

    def cmd_stime(self, player, msg, channel):
        if len(msg) == 1:
            return minqlbot.RET_USAGE
        elif len(msg) == 2:
            name = msg[1]
            map = self.game().short_map.lower()
        else:
            name = msg[1]
            map = msg[2].lower()

        data = self.get_data_qlstats("maps/" + map + "?ruleset=pql&weapons=off")
        rank, time, first_time = race.get_pb(data, name)
        last = len(data["scores"])

        if rank != -1:
            race.say_time(name, rank, last, time, first_time, map, True, channel)
        else:
            channel.reply("No strafe time was found for ^7{}".format(name))

    def cmd_sranktime(self, player, msg, channel):
        if len(msg) == 2:
            map = self.game().short_map.lower()
        elif len(msg) == 3:
            map = msg[2].lower()
        else:
            self.expecting_scores = True
            self.player = player
            self.weps = False
            self.scores()
            return

        time = race.ms(msg[1])
        data = self.get_data_qlstats("maps/" + map + "?ruleset=pql&weapons=off")
        rank, _ = race.get_rank_from_time(data, time)
        time_s = race.time_string(time)
        last = len(data["scores"])

        if rank != -1:
            channel.reply("^3{} ^2would be rank ^3{} ^2of ^3{} ^2on ^3{}^2(strafe)".format(time_s, rank, last, map))
        else:
            channel.reply("^3{} ^2would be rank ^3{} ^2on ^3{}^2(strafe)".format(time_s, last+1, map))

    def cmd_savg(self, player, msg, channel):
        name, average_rank, total_maps, medals = self.get_average(player, msg, True)
        if average_rank == 0:
            channel.reply("^7{} ^2has no strafe records on ql.leeto.fi".format(name))
        else:
            channel.reply("^7{} ^2average strafe rank: ^3{:.2f}^2({} maps) ^71st: ^3{} ^72nd: ^3{} ^73rd: ^3{}"
                          .format(name, average_rank, total_maps, medals[0], medals[1], medals[2]))

    def cmd_commands(self, player, msg, channel):
        channel.reply("Commands: ^3!(s)all !(s)top !(s)pb !(s)rank !(s)time !(s)ranktime !(s)avg !top100 !join")

    def cmd_update(self, player, msg, channel):
        self.write_data()
        self.write_data_qlstats()

    def cmd_join(self, player, msg, channel):
        n = self.find_player(minqlbot.NAME)
        if n:
            self.put(n, "f")

    def write_data(self):
        data = race.get_data_online(self.game().short_map.lower())
        with open("times.json", "w") as outfile:
            json.dump(data, outfile)
            self.debug("wrote times.json")

    def write_data_qlstats(self):
        data = race.get_data_online_qlstats("maps/" + self.game().short_map.lower() + "?ruleset=pql&weapons=off")
        with open("times_strafe.json", "w") as outfile:
            json.dump(data, outfile)
            self.debug("wrote times_strafe.json")

    def get_data(self, map):
        if map == self.game().short_map.lower():
            return race.get_data_file("times.json")
        return race.get_data_online(map)

    def get_data_qlstats(self, query):
        if "maps/" in query:
            map = query.replace("maps/", "").replace("?ruleset=pql&weapons=off", "")
            if map == self.game().short_map.lower():
                return race.get_data_file("times_strafe.json")
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
        data = j["data"]
        for score in data["scores"]:
            score["name"] = score.pop("PLAYER")
            score["score"] = score.pop("SCORE")
        return data

    @staticmethod
    def get_data_file(file):
        with open(file) as json_file:
            return json.load(json_file)

    @staticmethod
    def time_string(time):
        time = int(time)
        s, ms = divmod(time, 1000)
        ms = str(ms).zfill(3)
        if s < 60:
            return "{}.{}".format(s, ms)
        time //= 1000
        m, s = divmod(time, 60)
        s = str(s).zfill(2)
        return "{}:{}.{}".format(m, s, ms)

    @staticmethod
    def ms(time_string):
        minutes, seconds = (["0"] + time_string.split(":"))[-2:]
        return int(60000 * int(minutes) + round(1000 * float(seconds)))

    def get_map(self, msg):
        if len(msg) == 2:
            return msg[1].lower()
        else:
            return self.game().short_map.lower()

    @staticmethod
    def say_time(name, rank, last, time, first_time, map, strafe, channel):
        if rank != 1:
            time_diff = str(int(time) - int(first_time))
            time_diff = time_diff.zfill(3)
            time_diff_s = "^8[^1+" + race.time_string(time_diff) + "^8]"
        else:
            time_diff_s = ""

        time_s = race.time_string(time)
        strafe_s = "^2(strafe)" if strafe else ""

        channel.reply(
            "^7{} ^2is rank ^3{} ^2of ^3{} ^2with ^3{}{} ^2on ^3{}{}".format(name, rank, last, time_s, time_diff_s,
                                                                              map, strafe_s))

    @staticmethod
    def get_rank(data, rank):
        score = data["scores"][rank - 1]
        name = score["name"]
        time = score["score"]
        first_time = data["scores"][0]["score"]
        return name, time, first_time

    @staticmethod
    def get_pb(data, player):
        for i, score in enumerate(data["scores"]):
            if player.lower() == str(score["name"]).lower():
                time = score["score"]
                rank = i + 1
                first_time = data["scores"][0]["score"]
                return rank, time, first_time
        return -1, -1, -1

    @staticmethod
    def get_rank_from_time(data, time):
        first_time = data["scores"][0]["score"]
        time_diff = abs(int(time) - int(first_time))
        rank = -1
        for i, score in enumerate(data["scores"]):
            if time < int(score["score"]):
                rank = i + 1
                break
        if rank == 1:
            return rank, "^8[^2-" + race.time_string(time_diff) + "^8]"
        else:
            return rank, "^8[^1+" + race.time_string(time_diff) + "^8]"

    def get_average(self, player, msg, strafe):
        if len(msg) == 1:
            name = player.clean_name
        else:
            name = msg[1]

        strafe_s = "off" if strafe else "on"
        data = self.get_data_qlstats("players/" + name + "?ruleset=pql&weapons=" + strafe_s)

        if len(data["scores"]) == 0:
            return name, 0, 0, []

        total_rank = 0
        total_maps = 0
        medals = [0, 0, 0]
        for score in data["scores"]:
            # don't include removed maps
            if score["MAP"] != "bloodlust" and score["MAP"] != "doubleimpact" and score["MAP"] != "eviscerated" and score["MAP"] != "industrialaccident":
                rank = score["RANK"]
                if 1 <= rank <= 3:
                    medals[rank-1] += 1
                total_rank += rank
                total_maps += 1
        return name, total_rank / total_maps, total_maps, medals


def atoi(text):
    return int(text) if text.isdigit() else text


def natural_keys(text):
    """
    alist.sort(key=natural_keys) sorts in human order
    http://nedbatchelder.com/blog/200712/human_sorting.html
    """
    return [atoi(c) for c in re.split("(\d+)", text)]

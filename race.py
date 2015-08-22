import minqlbot
import re
import random
import urllib.request
import json
import pickle

mode = "pql"
class race(minqlbot.Plugin):
    def __init__(self):
        self.add_hook("map", self.handle_map)
        self.add_hook("game_end", self.handle_game_end)
        self.add_hook("console", self.handle_console)
        self.add_hook("scores", self.handle_scores)
        self.add_command("update", self.cmd_update)
        self.add_command("rank", self.cmd_rank, usage="[rank] [map]")
        self.add_command("srank", self.cmd_srank, usage="[rank] [map]")
        self.add_command("top100", self.cmd_top100, usage="[map]")
        self.add_command(("pb", "me"), self.cmd_pb, usage="[map]")
        self.add_command(("spb", "sme"), self.cmd_spb, usage="[map]")
        self.add_command("time", self.cmd_time, usage="<player> [map]")
        self.add_command("stime", self.cmd_stime, usage="<player> [map]")
        self.add_command("ranktime", self.cmd_ranktime, usage="<time> [map]")
        self.add_command("sranktime", self.cmd_sranktime, usage="<time> [map]")
        self.add_command(("top", "top3"), self.cmd_top, usage="[amount] [map]")
        self.add_command(("stop", "stop3"), self.cmd_stop, usage="[amount] [map]")
        self.add_command("all", self.cmd_all, usage="[map]")
        self.add_command("sall", self.cmd_sall, usage="[map]")
        self.add_command("avg", self.cmd_avg, usage="[player]")
        self.add_command("savg", self.cmd_savg, usage="[player]")
        self.add_command("join", self.cmd_join)
        self.add_command("random", self.cmd_random)
        self.add_command(("help", "commands"), self.cmd_help)

        self.expecting_scores = False
        self.player = None
        self.weapons = True
        self.end_game_timer = None

    def handle_map(self, map):
        self.write_scores()

    def handle_game_end(self, game, score, winner):
        self.end_game_timer = self.delay(5, self.write_scores())

    def cmd_update(self, player, msg, channel):
        self.write_scores()

    def write_scores(self):
        scores = RaceScores(self.game().short_map, True)
        with open("python\\race_scores.pickle", "wb") as handle:
            pickle.dump(scores, handle)
        self.debug("wrote race_scores.pickle")

        scores_strafe = RaceScores(self.game().short_map, False)
        with open("python\\race_scores_strafe.pickle", "wb") as handle:
            pickle.dump(scores_strafe, handle)
        self.debug("wrote race_scores_strafe.pickle")

    def handle_console(self, text):
        if "finished the race in in" not in text or self.game().state != "in_progress":
            return

        if mode == "pql":
            text_list = text.split()
            name = text_list[-7]
            name_clean = re.sub(r"\^[0-9]", "", name).lower()
            time_s = text_list[-1]
            time = ms(time_s)

            scores = self.get_map_scores(self.game().short_map, True)
            rank, pb = scores.pb(name_clean)
            # if they don't have a time set their pb to the last time(normally 100)
            if rank == -1:
                pb = int(scores.scores[-1]["score"])
            if time < pb:
                rank = scores.rank_from_time(time)
                _, first = scores.rank(1)
                time_diff = abs(time - first)
                if rank == 1:
                    time_diff = "^8[^2-" + time_string(time_diff) + "^8]"
                    self.msg("^7{} ^2just broke the ^3world record! {}".format(name, time_diff))
                else:
                    time_diff = "^8[^1+" + time_string(time_diff) + "^8]"
                    self.msg("^7{} ^2set a new pb and is now rank ^3{} {}".format(name, rank, time_diff))

    def cmd_rank(self, player, msg, channel):
        self.rank(msg, channel, True)

    def cmd_srank(self, player, msg, channel):
        self.rank(msg, channel, False)

    def cmd_top100(self, player, msg, channel):
        if len(msg) == 1:
            self.rank(["rank", "100"], channel, True)
        elif len(msg) == 2:
            self.rank(["rank", "100"], channel, True)
        else:
            return minqlbot.RET_USAGE

    def rank(self, msg, channel, weapons):
        if len(msg) == 1:
            rank = 1
            map_name = self.game().short_map
        elif len(msg) == 2:
            if msg[1].isdigit():
                rank = int(msg[1])
                map_name = self.game().short_map
            else:
                rank = 1
                map_name = msg[1]
        elif len(msg) == 3:
            rank = int(msg[1])
            map_name = msg[2]
        else:
            channel.reply("^7Usage: ^6!{} [rank] [map]".format(msg[0]))
            return

        scores = self.get_map_scores(map_name, weapons)
        name, time = scores.rank(rank)
        if not weapons:
            map_name += "^2(strafe)"
        if time == -1:
            output = "No rank ^3{} ^2time found for ^3{}".format(rank, map_name)
        else:
            output = scores.output(name, rank, time)
        channel.reply(output)

    def cmd_pb(self, player, msg, channel):
        self.pb(player, msg, channel, True)

    def cmd_spb(self, player, msg, channel):
        self.pb(player, msg, channel, False)

    def pb(self, player, msg, channel, weapons):
        if len(msg) == 1:
            map_name = self.game().short_map
        elif len(msg) == 2:
            map_name = msg[1]
        else:
            channel.reply("^7Usage: ^6!{} [map]".format(msg[0]))
            return

        scores = self.get_map_scores(map_name, weapons)
        rank, time = scores.pb(player.clean_name)
        if not weapons:
            map_name += "^2(strafe)"
        if rank == -1:
            if scores.leeto:
                output = "No time found for ^7{} ^2on ^3{}".format(player, map_name)
            else:
                output = "No time found for ^7{} ^2in top 100 for ^3{}".format(player, map_name)
        else:
            output = scores.output(player, rank, time)
        channel.reply(output)

    def cmd_time(self, player, msg, channel):
        self.time(msg, channel, True)

    def cmd_stime(self, player, msg, channel):
        self.time(msg, channel, False)

    def time(self, msg, channel, weapons):
        if len(msg) == 2:
            name = msg[1]
            self.pb(minqlbot.DummyPlayer(name), ["pb"], channel, weapons)
        elif len(msg) == 3:
            name = msg[1]
            map_name = msg[2]
            self.pb(minqlbot.DummyPlayer(name), ["pb", map_name], channel, weapons)
        else:
            channel.reply("^7Usage: ^6!{} <player> [map]".format(msg[0]))

    def cmd_ranktime(self, player, msg, channel):
        self.ranktime(msg, player, channel, True)

    def cmd_sranktime(self, player, msg, channel):
        self.ranktime(msg, player, channel, False)

    def handle_scores(self, scores):
        if self.expecting_scores:
            for score in scores:
                if self.player == score.player.clean_name.lower():
                    time = score.score
                    self.debug(time)
                    cmd = "ranktime" if self.weapons else "sranktime"
                    if time == -1:
                        self.ranktime([cmd], "", minqlbot.CHAT_CHANNEL, self.weapons)
                    else:
                        self.ranktime([cmd, time_string(time)], "", minqlbot.CHAT_CHANNEL, self.weapons)
        self.expecting_scores = False

    def ranktime(self, msg, player, channel, weapons):
        if len(msg) == 1 and player:
            self.expecting_scores = True
            self.player = player.clean_name.lower()
            self.weapons = weapons
            self.scores()
            return
        elif len(msg) == 2:
            map_name = self.game().short_map
        elif len(msg) == 3:
            map_name = msg[2]
        else:
            channel.reply("^7Usage: ^6!{0} <time> [map] ^7or just ^6!{0} ^7 if you have set a time".format(msg[0]))
            return

        scores = self.get_map_scores(map_name, weapons)
        time = ms(msg[1])
        rank = scores.rank_from_time(time)
        if not weapons:
            map_name += "^2(strafe)"
        if rank == -1:
            if scores.leeto or scores.last_rank < 100:
                output = "^3{} ^2would be rank ^3{} ^2on ^3{}".format(time_string(time), scores.last_rank + 1, map_name)
            else:
                output = "^3{} ^2would not be in top ^3{} ^2on ^3{}".format(time_string(time), scores.last_rank, map_name)
        else:
            output = "^3{} ^2would be rank ^3{} ^2of ^3{} ^2on ^3{}".format(time_string(time), rank, scores.last_rank,
                                                                            map_name)
        channel.reply(output)

    def cmd_top(self, player, msg, channel):
        self.top(msg, channel, True)

    def cmd_stop(self, player, msg, channel):
        self.top(msg, channel, False)

    def top(self, msg, channel, weapons):
        if len(msg) == 1:
            amount = 3
            map_name = self.game().short_map
        elif len(msg) == 2:
            if msg[1].isdigit():
                amount = int(msg[1])
                map_name = self.game().short_map
            else:
                amount = 3
                map_name = msg[1]
        elif len(msg) == 3:
            amount = int(msg[1])
            map_name = msg[2]
        else:
            channel.reply("^7Usage: ^6!{} [amount] [map]".format(msg[0]))
            return

        if amount > 20:
            channel.reply("Please use value <=20")
            return

        scores = self.get_map_scores(map_name, weapons)
        if not scores.scores:
            channel.reply("No times were found on {}".format(map_name))
            return

        if amount > len(scores.scores):
            amount = len(scores.scores)
        ranks = []
        for i in range(amount):
            name, time = scores.rank(i + 1)
            ranks.append("^3{}.^8_^4{}^8_^2{}".format(i + 1, name, time_string(time)))

        if not weapons:
            map_name += "^2(strafe)"

        channel.reply("^3{}: {}".format(map_name, " ".join(ranks)))

    def cmd_all(self, player, msg, channel):
        self.all(msg, channel, True)

    def cmd_sall(self, player, msg, channel):
        self.all(msg, channel, False)

    def all(self, msg, channel, weapons):
        if len(msg) == 1:
            map_name = self.game().short_map
        elif len(msg) == 2:
            map_name = msg[1]
        else:
            channel.reply("^7Usage: ^6!{} [map]".format(msg[0]))
            return

        scores = self.get_map_scores(map_name, weapons)
        times = {}
        for p in self.players():
            rank, time = scores.pb(p.clean_name)
            if rank != -1:
                times[rank] = "^7{}^8_^2{}".format(p, time_string(time))

        if not weapons:
            map_name += "^2(strafe)"
        if times:
            times_joined = " ".join("^3{}.^8_{}".format(key, val) for (key, val) in sorted(times.items()))
            channel.reply("^3{}: {}".format(map_name, times_joined))
        else:
            if scores.leeto:
                channel.reply("No times were found for anyone on ^3{} ^2:(".format(map_name))
            else:
                channel.reply("No times were found for anyone in top 100 for ^3{} ^2:(".format(map_name))

    def cmd_avg(self, player, msg, channel):
        self.avg(player, msg, channel, True)

    def cmd_savg(self, player, msg, channel):
        self.avg(player, msg, channel, False)

    def avg(self, player, msg, channel, weapons):
        if len(msg) == 1:
            name = player.clean_name
        elif len(msg) == 2:
            name = msg[1]
        else:
            channel.reply("^7Usage: ^6!{} [player]".format(msg[0]))
            return

        weps = "on" if weapons else "off"
        url = "http://ql.leeto.fi/api/players/{}/race?ruleset={}&weapons={}".format(name, mode, weps)
        request = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; WOW64; Trident/5.0)"})
        response = urllib.request.urlopen(request)
        data = json.loads(response.read().decode("utf-8"))

        scores = data["data"]["scores"]
        strafe = "strafe " if not weapons else ""
        if not scores:
            channel.reply("^7{} ^2has no {}records on ql.leeto.fi :(".format(name, strafe))
            return

        total_rank = 0
        total_maps = 0
        medals = [0, 0, 0]
        for score in scores:
            # don't include removed maps
            if score["MAP"] != "bloodlust" and score["MAP"] != "doubleimpact" and score["MAP"] != "eviscerated" and score["MAP"] != "industrialaccident":
                rank = score["RANK"]
                if 1 <= rank <= 3:
                    medals[rank - 1] += 1
                total_rank += rank
                total_maps += 1

        avg = total_rank / total_maps
        channel.reply("^7{} ^2average {}rank: ^3{:.2f}^2({} maps) ^71st: ^3{} ^72nd: ^3{} ^73rd: ^3{}"
                   .format(name, strafe, avg, total_maps, medals[0], medals[1], medals[2]))

    def cmd_join(self, player, msg, channel):
        self.send_command("team f")

    def cmd_random(self, player, msg, channel):
        maps = ["arkinholm", "basesiege", "beyondreality", "blackcathedral", "brimstoneabbey", "campercrossings",
                "campgrounds", "citycrossings", "courtyard", "deepinside", "distantscreams", "divineintermission",
                "duelingkeeps", "electrocution" "falloutbunker", "finnegans", "fluorescent", "foolishlegacy",
                "futurecrossings", "gospelcrossings", "henhouse", "industrialrevolution", "infinity", "innersanctums",
                "ironworks", "japanesecastles", "jumpwerkz", "newcerberon", "overlord", "pillbox", "pulpfriction",
                "qzpractice1", "qzpractice2", "ragnarok", "railyard", "rebound", "reflux", "repent", "scornforge",
                "shakennotstirred", "shiningforces", "siberia", "skyward", "spacechamber", "spacectf", "spidercrossings",
                "stonekeep", "stronghold", "theatreofpain", "theedge", "trinity", "troubledwaters", "warehouse"]
        self.callvote("map " + random.choice(maps))

    def cmd_help(self, player, msg, channel):
        channel.reply("Commands: ^3!(s)all !(s)top !(s)pb !(s)rank !(s)time !(s)ranktime !(s)avg !top100 !update !join !ramdom")

    def get_map_scores(self, map_name, weapons):
        current_map = self.game().short_map
        if map_name.lower() == current_map.lower():
            if weapons:
                filename = "race_scores.pickle"
            else:
                filename = "race_scores_strafe.pickle"
            with open("python\\" + filename, "rb") as handle:
                scores = pickle.load(handle)
        else:
            scores = RaceScores(map_name, weapons)
        return scores


class RaceScores:
    def __init__(self, map_name, weapons):
        self.map_name = map_name.lower()
        self.weapons = weapons
        if self.weapons and mode == "pql":
            self.leeto = False
        else:
            self.leeto = True
        self.scores = self.get_data()
        self.last_rank = len(self.scores)
        if self.scores:
            if self.leeto:
                self.first_time = self.scores[0]["SCORE"]
            else:
                self.first_time = int(self.scores[0]["score"])

    def get_data(self):
        if self.leeto:
            weapons = "on" if self.weapons else "off"
            url = "http://ql.leeto.fi/api/race/maps/{}?ruleset={}&weapons={}".format(self.map_name, mode, weapons)
        else:
            url = "http://quakelive.com/race/map/" + self.map_name
        request = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; WOW64; Trident/5.0)"})
        response = urllib.request.urlopen(request)
        data = json.loads(response.read().decode("utf-8"))
        return data["data"]["scores"] if self.leeto else data["scores"]

    def rank(self, rank):
        try:
            score = self.scores[rank - 1]
        except IndexError:
            return -1, -1

        if self.leeto:
            name = str(score["PLAYER"])
            time = score["SCORE"]
        else:
            name = str(score["name"])
            time = int(score["score"])
        return name, time

    def rank_from_time(self, time):
        rank = -1
        for i, score in enumerate(self.scores):
            if self.leeto:
                if time < int(score["SCORE"]):
                    rank = i + 1
                    break
            else:
                if time < int(score["score"]):
                    rank = i + 1
                    break
        return rank

    def pb(self, player):
        for i, score in enumerate(self.scores):
            name = str(score["PLAYER"]) if self.leeto else str(score["name"])
            if player.lower() == name.lower():
                time = score["SCORE"] if self.leeto else int(score["score"])
                rank = i + 1
                return rank, time
        return -1, -1

    def output(self, name, rank, time):
        if rank != 1:
            time_diff = str(time - self.first_time)
            time_diff = time_diff.zfill(3)
            time_diff = "^8[^1+" + time_string(time_diff) + "^8]"
        else:
            time_diff = ""
        time = time_string(time)
        strafe = "^2(strafe)" if not self.weapons else ""
        return "^7{} ^2is rank ^3{} ^2of ^3{} ^2with ^3{}{} ^2on ^3{}{}"\
            .format(name, rank, self.last_rank, time, time_diff, self.map_name, strafe)


def ms(time_string):
    minutes, seconds = (["0"] + time_string.split(":"))[-2:]
    return int(60000 * int(minutes) + round(1000 * float(seconds)))


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

# minqlbot-race-plugin
Race plugin for [minqlbot](https://github.com/MinoMino/minqlbot)

## Installation
Follow the instruction on https://github.com/MinoMino/minqlbot to run the bot. Place [race.py](https://raw.githubusercontent.com/cstewart90/minqlbot-race-plugin/master/race.py) in python/plugins folder. 
Edit python/config.cfg and add race to plugins list. For vql replace "pql" on line 7 with "vql".

# Commands
s in front of a command means strafe. Optional arguments are surrounded by square brackets. For most commands if no map is given it will use current map.

**!commands**
>Show all the commands.

**!(s)top [amount] [map]**
>Show top x amount of times for a map. Default amount if none is given is 3.

**!(s)all [map]**
>Shows the times of everyone in the server on a map.

**!(s)pb [map]**
>Show your personal best for a map.

**!(s)rank [rank] [map]**
>Show the x rank time for a map. Default rank if none is given is 1.

**!(s)time <player> [map]**
>Show that players time for a map.

**!(s)ranktime <time> [map]**
>Show what rank the given time would be on a map.

**!(s)avg [player]**
>Show players average rank using ql.leeto.fi.

**!top100 [map]**
>Show top 100 time for a map.

**!update**
>Update local cached times for current map

**!join**
>Make the bot join the game.


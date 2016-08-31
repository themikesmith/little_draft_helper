import csv
import re
from collections import defaultdict


def abbreviate_name(name):
    name = re.sub(r'(Sr\.?|Jr\.?|I|II|III|IV|V)$', '', name)
    name = name.strip()
    space = name.index(' ')
    first_name = name[0:space]
    rest_of_name = name[space:]
    first_char = first_name[0]
    if first_char.islower() or first_char == '.':
        first_char = 'V'
    abbrev = first_char + '.' + rest_of_name
    # print >> sys.stderr, name, 'became', abbrev
    return abbrev

pos_re_str = r"\s(QB|RB|WR|TE|K|DST)$"
player_data = defaultdict(list)  # (name, position, team) -> list of (site, rank, bye week, value)


def _helper(thing, f=int):
    thing = thing.strip().strip("#").strip("-")
    try:
        thing = f(thing)
    except ValueError:
        thing = ''
    return thing

# key = player position team
with open("cbs_all_2016.csv", 'rb') as cbs_file:
    cbs_reader = csv.reader(cbs_file)
    # headers: Rank, Player, Trends, Avg Pick, HI/LO, % Drafted
    cbs_reader.next()
    for row in cbs_reader:
        print "cbs row:", row
        cbs_rank = _helper(row[0])
        info = row[1].strip().strip("*").strip().split("|")
        # Bears DST | CHI  *
        name_pos = info[0].strip()
        team = info[1].strip()
        pos_match = re.search(pos_re_str, name_pos)
        position = pos_match.group(1)
        name = re.sub(pos_re_str, '', name_pos).strip()
        if position == 'TM':
            position = "DST"
        if position != 'DST':
            name = abbreviate_name(name)
        else:
            continue
        if team == 'ARZ':
            team = 'ARI'
        if team == 'LA':
            team = 'LAR'
        # key = name, position, team
        player_data[(name, position, team)].append(('cbs', cbs_rank, None))

with open("top200_rotoworld_dynasty.csv", "rb") as roto_file:
    roto_reader = csv.reader(roto_file)
    # headers: Rk,Player,Pos,Tm,Bye
    roto_reader.next()
    for row in roto_reader:
        print "roto row:", row
        roto_rank = _helper(row[0])
        name = row[1].strip()
        position = row[2].strip()
        if position == 'TM':
            position = "DST"
        if position != 'DST':
            name = abbreviate_name(name)
        else:
            continue
        team = row[3].strip()
        if team == 'ARZ':
            team = 'ARI'
        if team == 'LA':
            team = 'LAR'
        # key = name, position, team, bye
        bye = _helper(row[4])
        player_data[(name, position, team)].append(('rotoworld', roto_rank, bye))

outfile = 'dynasty_ranks.csv'
headers = ['name', 'position', 'team']
for i in xrange(2):
    headers.extend(['site%d' % i, 'rank%d' % i, 'bye%d' % i])
with open(outfile, 'wb') as out:
    d = csv.DictWriter(out, fieldnames=headers)
    d.writeheader()
    for player_key in sorted(player_data):
        player_val_list = player_data[player_key]
        row_dict = {'name': player_key[0],
                    'position': player_key[1],
                    'team': player_key[2],
                    }
        if player_val_list[0][0] == 'rotoworld':
            player_val_list = [('espn', 1000, None), player_val_list[0]]
        for i, player_val in enumerate(player_val_list):
            row_dict['site%d' % i] = player_val[0]
            row_dict['rank%s' % i] = player_val[1]
            row_dict['bye%d' % i] = player_val[2]
        d.writerow(row_dict)

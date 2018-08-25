__author__ = 'mcs'
from bs4 import BeautifulSoup
import re
import unicodedata
import urllib2
import sys
from collections import defaultdict
from csv import DictWriter, DictReader, reader
from os.path import isfile
from glob import glob


url = "http://www.espn.com/fantasy/football/story/_/page/18RanksPreseason300nonPPR/2018-fantasy-football-non-ppr-rankings-top-300"
pos_re_str = r"(QB|RB|WR|TE|K|DST)"
# three groups: rank, name, position
rank_name_re = re.compile(r"(\d+)\.\s(.+)")
# value_re = re.compile(r"\$(\d+)")
posrank_re = re.compile(pos_re_str + "\d+")
player_data = defaultdict(list)  # (name, position, team) -> list of (site, rank, bye week, value)
# extract first name, replace with first initial


def decode(st):
    return str(st)


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

espn_file = "espn.html"
# get espn
if not isfile(espn_file):
    print >> sys.stderr, 'getting espn!'
    response = urllib2.urlopen(url)
    html = response.read()  # throws URLError if fail
    with open(espn_file, 'wb') as out:
        out.write(html)

with open(espn_file, 'rb') as inf:
    html = inf.read()
    table_class = 'inline inline-table'
    soup = BeautifulSoup(html, 'html5lib')
    tables = soup.find_all('aside', class_=table_class)
    for t in tables:
        # print t
        if t.h2.text == "Top-300 non-PPR rankings for 2018":
            print >> sys.stderr, "found ranking table"
            # in the tbody
            for tr in t.tbody.children:
                # sanity checks...
                assert(tr.name == 'tr')
                # print tr.contents
                assert len(tr.contents) == 4
                for td in tr.children:
                    assert(td.name == 'td')
                # first td, get text, it's rank name position
                rank_name_info = tr.contents[0].text
                m = rank_name_re.match(rank_name_info)
                assert(m is not None)
                # print(m.groups())
                rank = decode(m.group(1).strip())
                try:
                    rank = int(rank)
                except ValueError:
                    rank = ''
                name = decode(m.group(2).strip())
                position = decode(tr.contents[1].text.strip())
                # position = decode(m.group(3).strip())
                if position != "DST":
                    name = decode(abbreviate_name(name))
                else:
                    continue
                # second td, get text, it's team abbreviation
                team_info = decode(tr.contents[2].text.strip())
                if team_info == 'ARZ':
                    team_info = 'ARI'
                if team_info == 'LA':
                    team_info = 'LAR'
                # third td, get text, it's bye week number
                bye_info = decode(tr.contents[3].text.strip())
                # last td, get text, it's posrank
                pos_rank_info = decode(tr.contents[-1].text.strip())
                # print(pos_rank_info)
                # m = pos_re_str.match(pos_rank_info)
                # if m:
                #     auction_value = int(m.group(1))
                # elif pos_rank_info == '--':
                #     # print("have %s, making zero" % auction_value_info, file=sys.stderr)
                #     auction_value = 0
                # else:
                #     raise ValueError("invalid auction value string")
                # print("rank:%s name:%s position:%s bye:%s value:%s" %
                #      (rank, name, position, bye_info, auction_value))
                player_key = (name, position, team_info, bye_info)
                print >> sys.stderr, 'espn has', player_key
                player_value = ('espn', rank, pos_rank_info, None)
                player_data[player_key].append(player_value)

print >> sys.stderr, '\n\nrotoworld\n'
for infile in glob("2018/tiers*_rotoworld.csv"):
    with open(infile, 'rb') as inf:
        # print infile
        # r = DictReader(inf)
        r = reader(inf)
        r.next()

        def _helper(thing, f=int):
            print thing
            thing = thing.strip().strip("#").strip("-")
            try:
                thing = f(thing)
            except ValueError:
                thing = ''
            print thing
            return thing

        for row in r:
            # assemble player key: name, position, team info, bye
            # player value: 'rotoworld', rank, auction value
            # headers: Rank,Overall,Tier,Player,Tm,AGE,Pos,BYE,ADP
            rank = _helper(row[0])
            overall_rank = _helper(row[1])
            tier = _helper(row[2])
            name = row[3].strip()
            team = row[4].strip()
            # age
            position = row[6].strip()
            bye = row[7].strip()
            adp = _helper(row[8], f=float)
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
            player_key = (name, position, team, bye)
            # print >> sys.stderr, 'rotoworld has', player_key
            pos_rank_info = "%s%s" % (position.lower(), rank)
            if rank == '--':
                rank = ""
            if overall_rank == '--':
                overall_rank = ""
            player_value = ('rotoworld', overall_rank, pos_rank_info, tier)
            if player_key not in player_data:
                print >> sys.stderr, 'player not in espn player data:', player_key
            player_data[player_key].append(player_value)


outfile = 'ranks.csv'
headers = ['name', 'position', 'team', 'bye']
for i in xrange(2):
    headers.extend(['site%d' % i, 'rank%d' % i, 'posrank%s' % i, "tier%s" % i])
with open(outfile, 'wb') as out:
    d = DictWriter(out, fieldnames=headers)
    d.writeheader()
    for player_key in sorted(player_data):
        player_val_list = player_data[player_key]
        row_dict = {'name': player_key[0],
                    'position': player_key[1],
                    'team': player_key[2],
                    'bye': player_key[3]}
        if player_val_list[0][0] == 'rotoworld':
            player_val_list = [('espn', 1000, '', ''), player_val_list[0]]
        for i, player_val in enumerate(player_val_list):
            row_dict['site%d' % i] = player_val[0]
            row_dict['rank%s' % i] = player_val[1]
            row_dict['posrank%s' % i] = player_val[2]
            row_dict['tier%s' % i] = player_val[3]
        d.writerow(row_dict)

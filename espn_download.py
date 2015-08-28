__author__ = 'mcs'
from bs4 import BeautifulSoup
import re
import unicodedata
import urllib2
import sys
from collections import defaultdict
from csv import DictWriter, DictReader, reader
from os.path import isfile

url = "http://espn.go.com/fantasy/football/story/_/id/12866396/top-300-rankings-2015"
pos_re_str = r"(QB|RB|WR|TE|K|DST)"
# three groups: rank, name, position
rank_re = re.compile(r"(\d+)\.(.+),\s+" + pos_re_str)
value_re = re.compile(r"\$(\d+)")
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
    table_class = 'inline-table'
    soup = BeautifulSoup(html, 'html5lib')
    tables = soup.find_all('table', class_=table_class)
    for t in tables:
        if t.caption.text == "Top 300 for 2015":
            #print("found ranking table", file=sys.stderr)
            # in the tbody
            for tr in t.tbody.children:
                # sanity checks...
                assert(tr.name == 'tr')
                assert len(tr.contents) == 5
                for td in tr.children:
                    assert(td.name == 'td')
                # first td, get text, it's rank name position
                rank_name_position_info = tr.contents[0].text
                m = rank_re.match(rank_name_position_info)
                assert(m is not None)
                # print(m.groups())
                rank = decode(m.group(1).strip())
                try:
                    rank = int(rank)
                except ValueError:
                    rank = '--'
                name = decode(m.group(2).strip())
                position = decode(m.group(3).strip())
                if position != "DST":
                    name = decode(abbreviate_name(name))
                else:
                    continue
                # second td, get text, it's team abbreviation
                team_info = decode(tr.contents[1].text.strip())
                # third td, get text, it's bye week number
                bye_info = decode(tr.contents[2].text.strip())
                # last td, get text, it's auction value
                auction_value_info = decode(tr.contents[-1].text.strip())
                # print(auction_value_info)
                m = value_re.match(auction_value_info)
                if m:
                    auction_value = int(m.group(1))
                elif auction_value_info == '--':
                    # print("have %s, making zero" % auction_value_info, file=sys.stderr)
                    auction_value = 0
                else:
                    raise ValueError("invalid auction value string")
                #print("rank:%s name:%s position:%s bye:%s value:%s" %
                #      (rank, name, position, bye_info, auction_value))
                player_key = (name, position, team_info, bye_info)
                # print >> sys.stderr, 'espn has', player_key
                player_value = ('espn', rank, auction_value)
                player_data[player_key].append(player_value)

print >> sys.stderr, '\n\nrotoworld\n'
infile = 'rotoworld.csv'
with open(infile, 'rb') as inf:
    #r = DictReader(inf)
    r = reader(inf)
    next(r)
    for row in r:
        # assemble player key: name, position, team info, bye
        # player value: 'rotoworld', rank, auction value
        # headers: Rk,Player,Pos,Tm,Bye
        rank = row[0].strip()
        try:
            rank = int(rank)
        except ValueError:
            rank = '--'
        name = row[1].strip()
        position = row[2].strip()
        team = row[3].strip()
        bye = row[4].strip()
        # rank = row['Rk']
        # name = row['Player']
        # position = row['Pos']
        # team = row['Tm']
        # bye = row['Bye']
        if position == 'TM':
            position = "DST"
        if position != 'DST':
            name = abbreviate_name(name)
        else:
            continue
        if team == 'ARZ':
            team = 'ARI'
        player_key = (name, position, team, bye)
        # print >> sys.stderr, 'rotoworld has', player_key
        player_value = ('rotoworld', rank, None)
        if player_key not in player_data:
            print >> sys.stderr, 'crap. ', player_key
        player_data[player_key].append(player_value)



outfile = 'ranks.csv'
headers = ['name', 'position', 'team', 'bye']
for i in xrange(2):
    headers.extend(['site%d'%i, 'rank%d'%i, 'value%d'%i])
with open(outfile, 'wb') as out:
    d = DictWriter(out, fieldnames=headers)
    d.writeheader()
    for player_key in sorted(player_data):
        player_val_list = player_data[player_key]
        rowdict = {'name': player_key[0],
                   'position': player_key[1],
                   'team': player_key[2],
                   'bye': player_key[3]}
        for i, player_val in enumerate(player_val_list):
            rowdict['site%d'%i] = player_val[0]
            rowdict['rank%d'%i] = player_val[1]
            rowdict['value%d'%i] = player_val[2]
        d.writerow(rowdict)

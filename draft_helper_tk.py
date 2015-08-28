import sqlite3 as sql
import csv
import re
from collections import OrderedDict
import sys

conn = sql.connect('ranks.db')
c = conn.cursor()

player_table_columns = OrderedDict(
        [
        ('name', 'text collate nocase'),
        ('position', 'text'),
        ('rank diff', 'int'),
        ('espn_rank', 'int'),
        ('bye', 'real'),
        ('rw_rank', 'int'),
        ('team', 'text'),
        ('rw_posrank', 'int'),
        ('rw_tier', 'text'),
        ('drafted', 'int')
        ])

position_list = ['QB', 'RB', 'WR', 'TE']

colors = ['red', 'green', 'yellow', 'magenta', 'cyan', 'blue']

col_list = []
col_list.extend(player_table_columns.keys())
col_list.append('id')
player_cols_to_print = ['name', 'team', 'rw_rank', 'rw_tier', 'diff']

def create_player_table(cursor):
    s = "CREATE TABLE if not exists players (%s id INTEGER PRIMARY KEY not null)" % ''.join(map(lambda item: '%s %s ,' % (item[0],item[1]), player_table_columns.items()))
    print s
    cursor.execute(s)

def get_datatype_by_colname(colname):
    return player_table_columns[colname]

def load_data(connection, cursor):
    cursor.execute("drop table if exists players")
    create_player_table(cursor)
    # load in csv data
    with open("ranks.csv", 'rb') as infile:
        r = csv.reader(infile)
        headers = ['name', 'position', 'team', 'bye']
        for i in xrange(2):
            headers.extend(['site%d'%i, 'rank%d'%i, 'value%d'%i])
        next(r)
        for row in r:
            name = row[0]
            position = row[1]
            team = row[2]
            try:
                bye = int(row[3])
            except ValueError:
                bye = 'NULL'
            # site0 = row[4]
            espn_rank = int(row[5])
            # espn value = row[6]
            # site1 = row[7]
            try:
                rotoworld_rank = int(row[8])
            except ValueError:
                rotoworld_rank = 'NULL'
            rotoworld_tier = row[9]
            rotoworld_posrank = row[10]
            to_remove = r"%sT?" % position.lower()
            #try:
            #    rotoworld_tier = int(re.sub(to_remove, '', rotoworld_tier))
            #except ValueError:
            #    rotoworld_tier = 'NULL'
            try:
                rotoworld_posrank = int(re.sub(to_remove, '', rotoworld_posrank))
            except ValueError:
                rotoworld_posrank = 'NULL'
            # rotoworld value = row[11]
            diff = int(row[12])
            if diff == 1000:
                diff = 'NULL'
            s = "INSERT INTO players VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
            t = (name, position, diff, espn_rank, bye, rotoworld_rank, team, rotoworld_posrank, rotoworld_tier, 0, None)
            print t
            cursor.execute(s, t)
            connection.commit()

def get_drafted_subquery(drafted, has_previous_clauses):
    if has_previous_clauses:
        s = " and "
    else:
        s = ""
    s += " drafted = %d" % int(drafted)
    return s

def assemble_select_query(query_args, drafted=False, orderby=None):
    q = "select * from players where "
    i = 0
    for colname, value in query_args.items():
        if i > 0:
            q += ' and '
        datatype = player_table_columns[colname]
        if datatype.startswith('text'):
            q += " " + colname + " like '%" + value + "%'"
        else:
            q += " %s=%s"% (colname, value)
        i += 1
    q += get_drafted_subquery(drafted, i)
    if orderby:
        q += ' order by %s' % orderby
    print q
    return q

def get_players(cursor, query_args, drafted=False, orderby=None):
    cursor.execute(assemble_select_query(query_args, drafted=drafted, orderby=orderby))
    return cursor.fetchall()

def get_players_by_position(cursor, position, drafted=False, orderby=None):
    return get_players(cursor, {"position":position}, drafted=drafted, orderby=orderby)

def set_draft_status(connection, cursor, player_id, drafted):
    s = "update players set drafted = %s where id = %s" % (drafted, player_id)
    print s
    cursor.execute("update players set drafted = ? where id = ?", (drafted, player_id))
    connection.commit()

def set_drafted(connection, cursor, player_id):
    set_draft_status(connection, cursor, player_id, True)
    get_number_players_drafted(cursor)

def set_undrafted(connection, cursor, player_id):
    set_draft_status(connection, cursor, player_id, False)

def get_color_from_tier(position, rotoworld_tier):
    to_remove = r"%sT?" % position.lower()
    try:
        tier_num = int(re.sub(to_remove, '', rotoworld_tier))
        i = tier_num % len(colors)
        return colors[i]
    except ValueError:
        rotoworld_tier = 'NULL'
        return "white"

def get_number_players_drafted(cursor):
    # count number drafted players
    try:
        t = cursor.execute("select count(*) from players where drafted = 1")
        n = cursor.fetchone()[0]
        print n
        return n
    except (AttributeError, IndexError) as e:
        print >> sys.stderr, e
        return -1

load_data(conn, c)




#############################################################
#             UI
#############################################################



import Tkinter as tk
import ttk
import tkMessageBox

# get text input
def get_text_input(msg):
    return enterbox(msg,"Enter text")
# text box mark as drafted
def get_text_mark_drafted():
    return get_text_input("Mark who as drafted?")
# text box mark as undrafted
def get_text_mark_undrafted():
    return get_text_input("Mark who as undrafted?")
next_choices = ["Mark Drafted", "Mark UN-drafted"]
def get_marking_choice():
    c = choicebox("What next?", 'What next?', next_choices)
    if "UN-" in c:
        return get_text_mark_undrafted(), False
    else:
        return get_text_mark_drafted(), True
# box pops up list of possible matches by name, choose one to mark as drafted / undrafted
def get_user_choice(choices_list):
    return choicebox("Multiple matches. Choose one:", "choose one", choices_list)
# get id from choice
def get_id_from_player_data(player_data):
    return get_data_from_player_row(player_data, 'id')
def get_data_from_player_row(player_row, col_name):
    return player_row[col_list.index(col_name)]
# confirm yes no
def confirm(action_msg):
    return ccbox("About to %s. Confirm?" % action_msg, 'Confirm')

def print_table(table):
    col_width = [max(len(x) for x in col) for col in zip(*table)]
    col_width = max(col_width)
    f = ""
    s = ""
    for line in table:
        print line
        if line[0] in player_cols_to_print:
            print 'wahoo found ' + line[0]
            f += " | " + "{0:{1}}".format(line[0], col_width)
            s += " | " + "{0:{1}}".format(line[1], col_width)
    return f + "\n" + s
    #return s

def to_player_str(player_row):
    table = zip(col_list, map(str, player_row))
    return print_table(table)

def get_top_by_position(position, num=20):
    l = get_players_by_position(c, position, orderby='rw_posrank')
    if num < len(l):
        return l[0:num]
    else:
        return l

def display_positional_data():
    for pos in position_list:
        msgbox('\n'.join(map(to_player_str, get_top_by_position(pos))), "Top available players at %s:" % pos)

def display_top_data(num=10):
    l = get_players(c, {}, orderby='rw_rank')
    if num < len(l):
        l = l[0:num]
    msgbox('\n'.join(map(to_player_str, l)), "Top available players:")

def augment_values_pick_diff(player_data, col_list, num_players_drafted=None, cursor=None):
    # augmented_cols, augmented_vals = augment_values_pick_diff(p)
    pl_col_list = list(col_list)
    i = pl_col_list.index("espn_rank")
    pl_col_list.insert(i, "espn pick diff")
    pl_data_list = None
    if player_data:
        espn_rank = get_data_from_player_row(player_data, 'espn_rank')
        espn_pick_diff = num_players_drafted - espn_rank
        pl_data_list = list(player_data) #  ensure list
        i = pl_data_list.index(espn_rank)
        pl_data_list.insert(i, espn_pick_diff)
    return pl_col_list, pl_data_list

def get_augmented_col_list(col_list, cursor=None):
    c, _ = augment_values_pick_diff([], col_list, cursor=None)
    return c

# 4 sections, one each for QB, RB, WR, TE
# section:
# select all where position matches and undrafted
# display a list of players, highlighting background color by tier
# control flow
# display the 4 sections
# offer cahnce to 'draft' or 'undraft' someone
# draft or undraft, modifying list
# repopulate lists
# quit button

class BaseDialog(tk.Toplevel):
    def __init__(self, parent, title = None, list_things=None):
        tk.Toplevel.__init__(self, parent)
        self.transient(parent)
        if title:
            self.title(title)
        self.parent = parent
        self.result = None
        body = tk.Frame(self)
        self.initial_focus = self.body(body)
        self.populate(list_things)
        body.pack(padx=5, pady=5)
        self.buttonbox()
        self.grab_set()
        if not self.initial_focus:
            self.initial_focus = self
        self.protocol("WM_DELETE_WINDOW", self.cancel)
        self.geometry("+%d+%d" % (parent.winfo_rootx()+50,
                                  parent.winfo_rooty()+50))
        self.initial_focus.focus_set()
        self.wait_window(self)
    #
    # construction hooks

    def body(self, master):
        # create dialog body.  return widget that should have
        # initial focus.  this method should be overridden
        pass

    def buttonbox(self):
        # add standard button box. override if you don't want the
        # standard buttons
        box = tk.Frame(self)
        w = tk.Button(box, text="OK", width=10, command=self.ok, default=tk.ACTIVE)
        w.pack(side=tk.LEFT, padx=5, pady=5)
        self.bind("<Return>", self.ok)
        self.bind("<Escape>", self.cancel)
        self.bind("<Double-Button-1>", self.ok)
        box.pack()
    #
    # standard button semantics
    def ok(self, event=None):
        if not self.validate():
            self.initial_focus.focus_set() # put focus back
            return
        self.withdraw()
        self.update_idletasks()
        self.apply()
        self.cancel()
    def cancel(self, event=None):
        # put focus back to the parent window
        self.parent.focus_set()
        self.destroy()
    #
    # command hooks
    def validate(self):
        return 1 # override
    def apply(self):
        pass # override
    def populate(self, list_things=None):
        pass

class ListDialog(BaseDialog):
    def body(self, master):
        tk.Label(master, text="Choose match:").grid(row=0)
        self.l1 = tk.Listbox(master)
        self.l1.pack()
        self.l1.grid(row=0, column=1)
        self.l1.bind("<Double-Button-1>", self.ok)
        return self.l1 # initial focus
    def apply(self):
        items = map(int, self.l1.curselection())
        try:
            self.result = items[0]
        except IndexError:
            pass
    def populate(self, list_things=None):
        if list_things is not None:
            for thing in list_things:
                self.l1.insert(tk.END, thing)

class Drafter(ttk.Frame):
    def __init__(self, parent):
        ttk.Frame.__init__(self, parent)
        self.canvas = tk.Canvas(root, borderwidth=0, background="#ffffff")
        self.frame = tk.Frame(self.canvas, background="#ffffff")
        self.vsb = tk.Scrollbar(root, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.vsb.set)
        self.hsb = tk.Scrollbar(root, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(xscrollcommand=self.hsb.set)

        self.vsb.pack(side="right", fill="y")
        self.hsb.pack(side="bottom", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.canvas.create_window((4,4), window=self.frame, anchor="nw",
                                  tags="self.frame")

        self.frame.bind("<Configure>", self.onFrameConfigure)
        self.parent = parent
        self.initUI()

    def onFrameConfigure(self, event):
        '''Reset the scroll region to encompass the inner frame'''
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def set_name_entry_text(self, text):
        self.name_var.set(text)

    def initUI(self):
        self.parent.title("Draft Helper")
        self.style = ttk.Style()
        self.style.theme_use("default")
        self.pack(fill=tk.BOTH, expand=1)
        # text input, mark players as drafted or undrafted
        self.name_var = tk.StringVar()
        self.name_entry = tk.Entry(self.canvas, text="Enter player whose draft status to edit", textvar=self.name_var)
        self.name_entry.grid()
        self.draft_button = ttk.Button(self.canvas, text="Mark Drafted", command=lambda: self.player_mark_logic(self.name_entry.get(), True))
        self.draft_button.grid()
        self.undraft_button = ttk.Button(self.canvas, text="Mark Undrafted", command=lambda: self.player_mark_logic(self.name_entry.get(), False))
        self.undraft_button.grid()
        # quit
        quit_button = ttk.Button(self.canvas, text="quit", command=self.quit)
        quit_button.grid()
        # all player list
        augmented_col_list = get_augmented_col_list(col_list, cursor=c)
        self.all_players_pane = ttk.Treeview(self.frame, columns=augmented_col_list, selectmode="browse")
        self.all_players_pane.grid()
        # top positional list
        self.top_qbs_pane = ttk.Treeview(self.frame, columns=augmented_col_list, selectmode="browse")
        self.top_qbs_pane.grid()
        self.top_rbs_pane = ttk.Treeview(self.frame, columns=augmented_col_list, selectmode="browse")
        self.top_rbs_pane.grid()
        self.top_wrs_pane = ttk.Treeview(self.frame, columns=augmented_col_list, selectmode="browse")
        self.top_wrs_pane.grid()
        self.top_tes_pane = ttk.Treeview(self.frame, columns=augmented_col_list, selectmode="browse")
        #self.top_tes_pane.tag_bind("<<TreeviewSelect>>", callback=lambda: self.set_name_entry_text(self.top_tes_pane.selection()))
        self.top_tes_pane.grid()
        self.populate_data_panes()
    def populate_data_panes(self):
        self.all_players_pane.delete(*self.all_players_pane.get_children())
        self.top_qbs_pane.delete(*self.top_qbs_pane.get_children())
        self.top_rbs_pane.delete(*self.top_rbs_pane.get_children())
        self.top_wrs_pane.delete(*self.top_wrs_pane.get_children())
        self.top_tes_pane.delete(*self.top_tes_pane.get_children())
        all_top_players = get_players(c, {}, orderby='rw_rank')
        num_players_drafted = get_number_players_drafted(c)
        for i, p in enumerate(all_top_players):
            if i > 15:
                break
            t = get_data_from_player_row(p, 'rw_tier')
            pos = get_data_from_player_row(p, 'position')
            augmented_cols, augmented_vals = augment_values_pick_diff(p, col_list, num_players_drafted=num_players_drafted, cursor=c)
            self.all_players_pane.insert("", tk.END, values=zip(augmented_cols, augmented_vals), tags=(get_color_from_tier(pos, t)))
        top_qbs = get_top_by_position('QB')
        for p in top_qbs:
            t = get_data_from_player_row(p, 'rw_tier')
            pos = get_data_from_player_row(p, 'position')
            augmented_cols, augmented_vals = augment_values_pick_diff(p, col_list, num_players_drafted=num_players_drafted, cursor=c)
            self.top_qbs_pane.insert("", tk.END, values=zip(augmented_cols, augmented_vals), tags=(get_color_from_tier(pos, t)))
        top_rbs = get_top_by_position('RB')
        for p in top_rbs:
            t = get_data_from_player_row(p, 'rw_tier')
            pos = get_data_from_player_row(p, 'position')
            augmented_cols, augmented_vals = augment_values_pick_diff(p, col_list, num_players_drafted=num_players_drafted, cursor=c)
            self.top_rbs_pane.insert("", tk.END, values=zip(augmented_cols, augmented_vals), tags=(get_color_from_tier(pos, t)))
        top_wrs = get_top_by_position('WR')
        for p in top_wrs:
            t = get_data_from_player_row(p, 'rw_tier')
            pos = get_data_from_player_row(p, 'position')
            augmented_cols, augmented_vals = augment_values_pick_diff(p, col_list, num_players_drafted=num_players_drafted, cursor=c)
            self.top_wrs_pane.insert("", tk.END, values=zip(augmented_cols, augmented_vals), tags=(get_color_from_tier(pos, t)))
        top_tes = get_top_by_position('TE')
        for p in top_tes:
            t = get_data_from_player_row(p, 'rw_tier')
            pos = get_data_from_player_row(p, 'position')
            augmented_cols, augmented_vals = augment_values_pick_diff(p, col_list, num_players_drafted=num_players_drafted, cursor=c)
            self.top_tes_pane.insert("", tk.END, values=zip(augmented_cols, augmented_vals), tags=(get_color_from_tier(pos, t)))
        trees = [self.all_players_pane, self.top_qbs_pane, self.top_rbs_pane, self.top_wrs_pane, self.top_tes_pane]
        for t in trees:
            for color in colors:
                t.tag_configure(color, background=color)

    def player_mark_logic(self, player_name, to_set_drafted):
        if not player_name:
            return
        print "player:%s to set drafted? %s" % (player_name, to_set_drafted)
        possible_players = get_players(c, {"name":player_name}, drafted=(not to_set_drafted), orderby='name')
        print "possible matches:",possible_players
        if len(possible_players) > 1:
            chooser = ListDialog(self, list_things=possible_players)
            if chooser.result is not  None:
                player_choice = possible_players[chooser.result]
                s = "drafted"
                if not to_set_drafted:
                    s = "UNdrafted"
                if not tkMessageBox.askyesno("Confirm?", "Mark as %s ? %s" % (s, repr(player_choice))):
                    self.name_entry.delete(0, tk.END)
                    return
            else:
                return
        elif len(possible_players) == 1:
            player_choice = possible_players[0]
            s = "drafted"
            if not to_set_drafted:
                s = "UNdrafted"
            if not tkMessageBox.askyesno("Confirm?", "Mark as %s ? %s" % (s, repr(player_choice))):
                self.name_entry.delete(0, tk.END)
                return
        else:
            s = "drafted"
            if to_set_drafted:
                s = "UNdrafted"
            tkMessageBox.showwarning("No results", "No %s results found for name:%s" % (s, player_name))
            self.name_entry.delete(0, tk.END)
            return
        # assert drafted status differs from set drafted variable
        print >> sys.stderr, 'player:' + repr(player_choice)
        print >> sys.stderr, 'player:%s is %sdrafted'\
            % (get_data_from_player_row(player_choice, 'name'), get_data_from_player_row(player_choice, 'drafted'))
        if to_set_drafted:
            set_drafted(conn, c, get_data_from_player_row(player_choice, 'id'))
        else:
            set_undrafted(conn, c, get_data_from_player_row(player_choice, 'id'))
        self.name_entry.delete(0, tk.END)
        self.populate_data_panes()

root = tk.Tk()
root.geometry("250x150+300+300")
app = Drafter(root)
#root.bind("<<Populate>>", app.populate_data_panes)
root.mainloop()

## /usr/bin/env python2.2

import diffutil
import errno
import gnomeglade
import gobject
import gtk
import math
import misc
import os
import undo

gdk = gtk.gdk

################################################################################
#
# Local Functions
#
################################################################################

def _clamp(val, lower, upper):
    assert lower <= upper
    return min( max(val, lower), upper)

join = os.path.join

NAME, TYPE, TEXT, FOREGROUND, LAST = 0,1,2,5,8

################################################################################
#
# DirDiff
#
################################################################################

MASK_SHIFT, MASK_CTRL, MASK_ALT = 1, 2, 3

class DirDiff(gnomeglade.Component):
    """Two or three way diff of directories"""

    __gsignals__ = {
        'label-changed': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (gobject.TYPE_STRING,)),
        'working-hard': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (gobject.TYPE_INT,)),
        'create-diff': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,))
    }

    keylookup = {65505 : MASK_SHIFT, 65507 : MASK_CTRL, 65513: MASK_ALT}


    def __init__(self, num_panes, statusbar):
        gnomeglade.Component.__init__(self, misc.appdir("glade2/dirdiff.glade"), "dirdiff")
        self._map_widgets_into_lists( ["treeview", "fileentry", "diffmap", "scrolledwindow", "linkmap"] )
        self.num_panes = 0
        self.set_num_panes(num_panes)
        self.statusbar = statusbar
        self.undosequence = undo.UndoSequence()
        self.lock = 0
        self.cache = {}
        types = map(lambda x: type(""), range(LAST))
        self.model = apply(gtk.TreeStore, types )

        for i in range(3):
            rentext = gtk.CellRendererText()
            column = gtk.TreeViewColumn("", rentext, text=i+TEXT, foreground=i+FOREGROUND)
            self.treeview[i].append_column(column)
            self.treeview[i].set_model(self.model)
            self.scrolledwindow[i].get_vadjustment().connect("value-changed", self._sync_vscroll )
            self.scrolledwindow[i].get_hadjustment().connect("value-changed", self._sync_hscroll )

    def _do_to_others(self, master, objects, method, args):
        for o in filter(lambda x:x!=master, objects):
            m = getattr(o,method)
            apply(m, args)

    def _sync_vscroll(self, adjustment):
        if self.lock==0:
            self.lock = 1
            adjs = map(lambda x: x.get_vadjustment(), self.scrolledwindow)
            self._do_to_others( adjustment, adjs, "set_value", (adjustment.value,) )
            self.lock = 0
    def _sync_hscroll(self, adjustment):
        if self.lock==0:
            self.lock = 1
            adjs = map(lambda x: x.get_hadjustment(), self.scrolledwindow)
            self._do_to_others( adjustment, adjs, "set_value", (adjustment.value,) )
            self.lock = 0

    def on_fileentry_activate(self, entry):
        pane = self.fileentry.index(entry)
        loc = entry.get_full_path(0)
        self.set_location(loc, pane)

    def set_location(self, loc, pane):
        loc = os.path.abspath(loc or ".")
        self.fileentry[pane].set_filename(loc)
        self.statusbar.add_status( "Set location %i %s" % (pane, loc) )
        self.label_changed()
        self.model.clear()
        root = self.model.append(None)
        child = self.model.append(root)
        self.model.set_value( root, NAME, "")
        self.model.set_value(child, NAME, "")
        for i in range(self.num_panes):
            l = self.fileentry[i].get_full_path(0) or ""
            self.model.set_value( root, i+TEXT, os.path.basename(l))
            self.model.set_value(child, i+TEXT, "")
        self.treeview[pane].expand_row(self.model.get_path(root), 0)

    def on_treeview_row_activated(self, view, path, column):
        iter = self.model.get_iter(path)
        files = []
        for i in range(self.num_panes):
            file = []
            up = iter.copy()
            while up:
                f = self.model.get_value( up, i+TEXT)
                if f:
                    file.insert( 0, f )
                    up = self.model.iter_parent(up)
                else:
                    file = None
                    break
            if file:
                file = "/".join( filter(lambda x: x!=None, file[1:] ) )
                r = self.fileentry[i].get_full_path(0)
                files.append( join(r,file) )
        if len(files):
            if os.path.isfile( files[0] ):
                self.emit("create-diff", files)
            else:
                if view.row_expanded(path):
                    view.collapse_row(path)
                else:
                    view.expand_row(path,0)

    def on_treeview_row_expanded(self, view, iter, path):
        if self.lock == 0:
            self.lock = 1
            p = self.model.get_value(iter,NAME)
            dirs = []
            files = []
            alldirs = []
            allfiles = []
            for i in range(self.num_panes):
                r = self.fileentry[i].get_full_path(0)
                if r and os.path.isdir( join(r,p) ):
                    try:
                        e = os.listdir( join(r,p) )
                    except OSError, err:
                        if err.errno == errno.ENOENT:
                            e = ["(No such directory)" + str(err)]
                        else:
                            e = ["(Permission Denied)" + str(err)]
                    e.sort()
                    dirs.append( filter(lambda x: os.path.isdir( join(r, p, x) ), e) )
                    files.append( filter(lambda x: x not in dirs[-1], e) )
                else:
                    dirs.append( [] )
                    files.append( [] )
                alldirs += dirs[i]
                allfiles+= files[i]
            def uniq(l):
                l.sort()
                r = []
                c = None
                for i in l:
                    if i != c:
                        r.append(i)
                        c = i
                return r
            alldirs = uniq(alldirs)
            allfiles = uniq(allfiles)
            for d in alldirs:
                i = self.model.append(iter)
                child = self.model.append(i)
                self.model.set_value(i, NAME, d)
                for j in range(self.num_panes):
                    self.model.set_value(child, j+TEXT, "")
                    if d in dirs[j]:
                        self.model.set_value(i, j+TEXT, d)
            for d in allfiles:
                i = self.model.append(iter)
                self.model.set_value(i, 0, d)
                for j in range(self.num_panes):
                    if d in files[j]:
                        self.model.set_value(i, j+TEXT, d)
            if 1:#len(alldirs) + len(allfiles):
                child = self.model.iter_children(iter)
                self.model.remove(child)
            self._do_to_others(view, self.treeview, "expand_row", (path,0) )
            self.lock = 0

    def on_treeview_row_collapsed(self, view, me, path):
        if self.lock == 0:
            self.lock = 1
            child = self.model.iter_children(me)
            while child:
                self.model.remove(child)
                child = self.model.iter_children(me)
            child = self.model.append(me)
            self.model.set_value(child, TEXT, "" )
            self._do_to_others(view, self.treeview, "collapse_row", (path,) )
            self.lock = 0

    def set_num_panes(self, n):
        if n != self.num_panes and n in (1,2,3):
            self.num_panes = n
            toshow =  self.scrolledwindow[:n] + self.fileentry[:n]
            toshow += self.linkmap[:n-1] + self.diffmap[:n]
            map( lambda x: x.show(), toshow )

            tohide =  self.scrolledwindow[n:] + self.fileentry[n:]
            tohide += self.linkmap[n-1:] + self.diffmap[n:]
            map( lambda x: x.hide(), tohide )
            self.label_changed()

    def refresh(self):
        pass

    def label_changed(self):
        filenames = []
        for i in range(self.num_panes):
            f = self.fileentry[i].get_full_path(0) or ""
            filenames.append( f )
        shortnames = misc.shorten_names(*filenames)
        labeltext = " : ".join(shortnames) + " "
        self.emit("label-changed", labeltext)

gobject.type_register(DirDiff)








def foo():

    def _update_differences_filestates(self, path, d0, d1, files):
        join = os.path.join
        fullpath0 = join(self.model[0].root, path)
        fullpath1 = join(self.model[1].root, path)
        i0 = 0
        i1 = 0
        while i0 < len(d0) and i1 < len(d1):
            cur0 = d0[i0]
            cur1 = d1[i1]
            if   cur0 > cur1:
                self.model[1].state[join(path,cur1)] = "only"
                i1 += 1
            elif cur0 < cur1:
                self.model[0].state[join(path,cur0)] = "only"
                i0 += 1
            else:
                if files:
                    t0 = open( join(fullpath0,cur0) ).read()
                    t1 = open( join(fullpath1,cur1) ).read()
                    if t0 != t1:
                        self.model[0].state[join(path,cur0)] = "changed"
                        self.model[1].state[join(path,cur1)] = "changed"
                i0 += 1
                i1 += 1
        while i0 < len(d0):
            self.model[0].state[join(path,d0[i0])] = "only"
            i0 += 1
        while i1 < len(d1):
            self.model[1].state[join(path,d1[i1])] = "only"
            i1 += 1
import gtk
import gtk.gdk
import pango

# TODO
# * RTL/LTR Support
# * Fixed size preview entry
# * Tooltip for marks
# * Create a value conversion function for the slider

DEFAULT_SIZE = 24.
SIZES = [6.,8.,9.,10.,11.,12.,13.,14.,16.,20.,24.,36.,48.,72.]

class widgets(object):
	def __init__ (self):
		self.last_selected_face = None
		self.current_face = None
		self.face_list = None
		self.font_filter = None
		self.last_search = None
		
		interface = gtk.Builder ()
		interface.add_from_file ("fontselector.ui")

		self.face_list = interface.get_object ("facelist")
		self.font_dialog = interface.get_object ("fontdialog")
		self.font_list_view = interface.get_object ("fontlist")
		self.font_preview = interface.get_object ("preview")
		self.font_size = interface.get_object ("fontsize")
		self.font_size_scale = interface.get_object ("sizescale")
		self.font_weight = interface.get_object ("fontweight")
		self.font_face = interface.get_object ("fontface")
		self.font_search = interface.get_object ("fontsearch")
		
		self.font_preview.add_events (gtk.gdk.SCROLL_MASK)

		self.font_preview.connect ("scroll-event", preview_scrolled_cb, self)
		self.font_list_view.connect ("cursor-changed", family_changed_cb, self)
		self.font_size.connect ("value-changed", size_changed_cb, self)
		self.font_size_scale.connect ("value-changed", size_changed_cb, self)
		#self.font_size_scale.connect ("value-changed", scale_tooltip_cb, self)
		self.font_face.connect ("changed", face_changed_cb, self)
		self.font_search.connect ("key-press-event", key_pressed_cb, self)
		self.font_search.connect ("backspace", backspace_cb, self)
		self.font_search.connect ("icon-press", icon_press_cb, self)
		
		self.scale_adjustment = gtk.Adjustment (DEFAULT_SIZE, SIZES[0], SIZES[-1], 0.5, 0., 0.)
		self.adjustment = gtk.Adjustment (DEFAULT_SIZE, 0.01, 1000, 0.5, 0., 0.)
		self.font_size_scale.set_adjustment (self.scale_adjustment)
		self.font_size.set_adjustment (self.adjustment)
		
		self.completion = gtk.EntryCompletion ()
		self.font_search.set_completion (self.completion)
		
		self.set_size (24.0)
		
		self.bootstrap_treeview ()
		
	def bootstrap_treeview (self):
		cell = gtk.CellRendererText ()
		column = gtk.TreeViewColumn ("Font name", cell, markup=2)
		self.font_list_view.append_column (column)

		cell.set_property  ("ellipsize", pango.ELLIPSIZE_END)
		column.set_resizable (True)
		column.set_min_width (230)
		
		cell = gtk.CellRendererText ()
		column = gtk.TreeViewColumn ("Font family", cell, markup=3)
		self.font_list_view.append_column (column)
		
		cell.set_property("ellipsize", pango.ELLIPSIZE_END)
	
	def set_face (self, face):
		self.current_face = face
		description = face.describe ()
		size = self.font_size.get_value () * pango.SCALE
		description.set_size (int(size))
		self.font_preview.modify_font (description)
		
		self.sizes = face.list_sizes ()
		
		if not self.sizes:
			self.sizes = SIZES

		self.font_size_scale.clear_marks ()

		for size in self.sizes:
			self.font_size_scale.add_mark (float (size), gtk.POS_BOTTOM, None)
		
	def set_size (self, size):
		size = size * pango.SCALE
		pc = self.font_preview.get_pango_context ()
		fd = pc.get_font_description ()
		fd.set_size (int(size))
		self.font_preview.modify_font (fd)
		
	def get_face_for_family (self, family):
		list_faces = family.list_faces ()
		if not self.last_selected_face:
			return list_faces[0]
		
		face_name = self.last_selected_face.get_face_name ()
		possible_faces = face_name.split (" ")
		if len(possible_faces) < 2:
			possible_faces = []
		
		#search for most similar face to the selected one
		result = []
		for face in list_faces:
			if face.get_face_name() == face_name:
				return face
			if face.get_face_name() in possible_faces:
				result.append (face)
				
		if len(result) < 1:
			return list_faces [0]
		
		return result[0]
		
	def set_model (self, model):
		self.font_filter = model.filter_new ()
		self.font_filter.set_visible_func (font_visible_func, self)
		self.font_list_view.set_model (self.font_filter)
		
		pc = self.font_dialog.get_pango_context ()
		font = pc.get_font_description ()
		family = font.get_family ()
		
		for row in model:
			if family == row[1]:
				self.font_list_view.set_cursor (row.path, None, False)
				break

#Filter function
def font_visible_func (model, treeiter, ui):
	text = ui.font_search.get_text ()
	if not text:
		return True
		
	if text.lower () in model[treeiter][1].lower ():
		return True
	
	return False

#Callbacks
def family_changed_cb (tv, ui):
	index = tv.get_cursor()[0][0]
	font_family = tv.get_model()[index][0]
	
	pc = tv.get_pango_context()
	fd = pc.get_font_description()
	fd.set_family (font_family.get_name ())
	ui.font_preview.modify_font (fd)
	
	ui.face_list = gtk.ListStore (str, pango.FontFace)
	for face in font_family.list_faces ():
		ui.face_list.append ([face.get_face_name (), face])
	ui.font_face.set_model (ui.face_list)
	
	size_changed_cb (ui.font_size, ui)
	face = ui.get_face_for_family (font_family)
	ui.current_face = face
	ui.set_face (face)
	
	for row in ui.face_list:
		if row[1] == face:
			ui.font_face.set_active_iter(row.iter)
		
def size_changed_cb (font_size, ui):
	size = font_size.get_value ()
	ui.font_size.set_value (size)
	if font_size <= SIZES[-1]:
		ui.font_size_scale.set_value (size)
	ui.set_size (size)

def scale_tooltip_cb (scale, ui):
	value = scale.get_value ()
	
	if not value in SIZES:
		if scale.get_has_tooltip ():
			scale.set_has_tooltip (False)
		return

def face_changed_cb (font_style, ui):
	i = font_style.get_active()
	ui.last_selected_face = font_style.get_model()[i][1]
	ui.current_face = ui.last_selected_face
	ui.set_face (ui.current_face)
	
def preview_scrolled_cb (widget, event, ui):
	adj = ui.font_size.get_adjustment ()
	if event.direction == gtk.gdk.SCROLL_UP or \
	   event.direction == gtk.gdk.SCROLL_RIGHT:
		adj.set_value (adj.get_value () + adj.get_step_increment ())
	else:
		adj.set_value (adj.get_value () - adj.get_step_increment ())
		
def icon_press_cb (font_search, position, event, ui):
	font_search.set_text ("")
	key_pressed_cb (font_search, None, ui)

#Workaround for the lack of gtk.EntryBuffer
def key_pressed_cb (font_search, event, ui):
	text = font_search.get_text ()
	if text == ui.last_search:
		return
		
	ui.last_search = text
	ui.font_filter.refilter ()
	
def backspace_cb(font_search, ui):
	key_pressed_cb(font_search, None, ui)
	

#Family sorting fuction
def compare_family_names (f1, f2):
	if f1.get_name () > f2.get_name ():
		return 1
	if f1.get_name () == f2.get_name ():
		return 0
	return -1

def main():
	ui = widgets ()
	
	fonts = gtk.ListStore (pango.FontFamily, str, str, str)
	pc = ui.font_dialog.get_pango_context ()
	families = list(pc.list_families())
	families.sort (compare_family_names)
	for family in families:
		name = "<span foreground=\"darkgrey\">%s</span>" % (family.get_name (),)
		preview = "<span font_family=\"%s\">Aa Bb Cc Dd Ee Ff Gg Hh Ii Jj Kk Ll Mm</span>" % (family.get_name (),)
		
		fonts.append([family, family.get_name (), name, preview])
	
	ui.set_model (fonts)
	print ui.font_list_view.get_cell_area (fonts[0].path, ui.font_list_view.get_column (0))
	print ui.font_list_view.get_cell_area (fonts[5].path, ui.font_list_view.get_column (0))
	
	ui.font_dialog.run()
	
if __name__ == '__main__':
	main()

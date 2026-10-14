#!/usr/bin/env python


#DNApy is a DNA editor written purely in python.
#The program is intended to be an intuitive and fully featured 
#editor for molecular and synthetic biology.
#Enjoy!
#
#copyright (C) 2014-2015  Martin Engqvist |
#
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#LICENSE:
#
#DNApy is free software; you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation; either version 3 of the License, or
#(at your option) any later version.
#
#DNApy is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU Library General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with this program; if not, write to the Free Software Foundation,
#Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301  USA
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#Get source code at: https://github.com/mengqvist/DNApy
#


#TODO
#nothing at the moment


import ast
from wx.lib.agw import ultimatelistctrl as ULC
import wx
 	                                  #See documentation for more detail
from .compat import pub
from .. import settings

import sys, os
import string


import copy

from . import colcol
from .. import genbank
from .base_class import DNApyBaseClass
from . import featureedit_GUI





class FeatureList(DNApyBaseClass):
	"""
	Class for viewing features as a list and buttons for editing the features.
	"""
	def __init__(self, parent, id, state):
		wx.Panel.__init__(self, parent)
		self.state = state # the shared state of the window (see state.py)
		self.feature_list = ULC.UltimateListCtrl(self, id=3001, agwStyle=ULC.ULC_REPORT|ULC.ULC_SINGLE_SEL)

		self.feature_list.InsertColumn(0, "Feature", format=wx.LIST_FORMAT_LEFT, width=200)
		self.feature_list.InsertColumn(1, "Type", format=wx.LIST_FORMAT_LEFT, width=100)
		self.feature_list.InsertColumn(2, "Location on DNA", format=wx.LIST_FORMAT_LEFT, width=200)
		self.feature_list.InsertColumn(3, "Strand", format=wx.LIST_FORMAT_LEFT, width=120)

		font = wx.Font(pointSize=10, family=wx.FONTFAMILY_DEFAULT, style=wx.FONTSTYLE_NORMAL, weight=wx.FONTWEIGHT_NORMAL, underline=False, faceName='Monospace', encoding=wx.FONTENCODING_DEFAULT)
		self.feature_list.SetFont(font)
		self.feature_list.Bind(wx.EVT_LIST_ITEM_SELECTED, self.ListOnSelect)
		self.feature_list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.ListOnActivate)
		
		#buttons
		padding = 10 #how much to add around the picture
		imageFile = settings.get().icon('new_small.png')
		image1 = wx.Image(imageFile, wx.BITMAP_TYPE_ANY).ConvertToBitmap()
		newfeature = wx.BitmapButton(self, id=1, bitmap=image1, size = (image1.GetWidth()+padding, image1.GetHeight()+padding), name = "share")

		imageFile = settings.get().icon('remove_small.png')
		image1 = wx.Image(imageFile, wx.BITMAP_TYPE_ANY).ConvertToBitmap()
		deletefeature = wx.BitmapButton(self, id=2, bitmap=image1, size = (image1.GetWidth()+padding, image1.GetHeight()+padding), name = "share")

		imageFile = settings.get().icon('move_up.png')
		image1 = wx.Image(imageFile, wx.BITMAP_TYPE_ANY).ConvertToBitmap()
		moveup = wx.BitmapButton(self, id=4, bitmap=image1, size = (image1.GetWidth()+padding, image1.GetHeight()+padding), name = "share")

		imageFile = settings.get().icon('move_down.png')
		image1 = wx.Image(imageFile, wx.BITMAP_TYPE_ANY).ConvertToBitmap()
		movedown = wx.BitmapButton(self, id=5, bitmap=image1, size = (image1.GetWidth()+padding, image1.GetHeight()+padding), name = "share")

		imageFile = settings.get().icon('edit.png')
		image1 = wx.Image(imageFile, wx.BITMAP_TYPE_ANY).ConvertToBitmap()
		edit = wx.BitmapButton(self, id=6, bitmap=image1, size = (image1.GetWidth()+padding, image1.GetHeight()+padding), name = "edit")
		
		#bind feature list buttons
		self.Bind(wx.EVT_BUTTON, self.OnNew, id=1)
		self.Bind(wx.EVT_BUTTON, self.OnDelete, id=2)
		self.Bind(wx.EVT_BUTTON, self.OnMoveFeatureUp, id=4)
		self.Bind(wx.EVT_BUTTON, self.OnMoveFeatureDown, id=5)
		self.Bind(wx.EVT_BUTTON, self.OnEditFeature, id=6)


		#arrange buttons vertically		
		sizer = wx.BoxSizer(wx.VERTICAL)
		sizer.Add(newfeature)
		sizer.Add(deletefeature)
		sizer.Add(edit)
		sizer.Add(moveup)
		sizer.Add(movedown)


		#add feature list and buttons horisontally	
		sizer2 = wx.BoxSizer(wx.HORIZONTAL)
		sizer2.Add(sizer, proportion=0, flag=wx.EXPAND)
		sizer2.Add(self.feature_list, proportion=3, flag=wx.EXPAND)

		self.SetSizer(sizer2)


####### Modify methods from base calss to fit current needs #########

	def update_globalUI(self):
		'''
		Method should be modified as to update other panels in response to changes in own panel.
		'''
		MSG_CHANGE_TEXT = "change.text"
		pub.sendMessage(MSG_CHANGE_TEXT, text="Feature list says update!")
		

	def update_ownUI(self):
		'''
		Refreshes only the UI of this panel by re-filling the table from features stored in the genbank object
		'''
		#need to figure out how to do this without changing the selection....
		self.feature_list.DeleteAllItems()
		item = 0 #for feautrecolor
		features = self.state.gb.get_all_features()
		if features != None:
			for entry in features:
	#			print(entry)
				if len(entry['qualifiers']) == 0:
					col0 = entry['key']	
				else:
					col0 = entry['qualifiers'][0].split('=')[1]
				col1 = entry['key']
				locationstring = ''
				for location in entry['location']:
					if locationstring != '':
						locationstring += ', '
					locationstring += str(location)
				col2 = locationstring
				if entry['complement'] == True:
					col3 = 'complement'
				else:
					col3 = 'leading'
	#			col4 = entry['qualifiers']
			
				self.feature_list.Append([col0, col1, col2, col3])	
		
				#coloring
				self.get_feature_color(entry)
				hexcolor = self.current_highlight_color #get hex color
				r, g, b = colcol.hex_to_rgb(hexcolor) #convert to RGB
				color = wx.Colour(r, g, b) #make color object
				self.feature_list.SetItemBackgroundColour(item, color)	
				item += 1
		try:
			if self.state.feature_selection != None: #focus on the selected feature
				self.focus_feature_selection()
		except:
			pass


######################################################


	def ListOnSelect(self, event):	
		'''Updates selection depending on which feature is chosen'''
		index = self.feature_list.GetFirstSelected()
		self.state.feature_selection = copy.copy(index)


	def ListOnActivate(self, event):
		'''Updates feature AND DNA selection based on which feature is chosen'''
		index = self.feature_list.GetFirstSelected()
		self.state.feature_selection = copy.copy(index)

		locations = self.state.gb.get_feature_location(index)
		start = self.state.gb.get_location(locations[0])[0]
		finish = self.state.gb.get_location(locations[-1])[1]
		self.state.dna_selection = copy.copy((start, finish))
		self.update_globalUI()

######
######
######
######
	def OnNew(self, event):
		'''Make new feature'''
		#make feature and update interface
		start, finish = self.get_dna_selection()
		
		self.state.gb.add_feature(key='misc_feature', qualifiers=['/note=New feature'], location=['%s..%s' % (start, finish)], complement=False, join=False, order=False)
		self.state.feature_selection = copy.copy(len(self.state.gb.get_all_features())-1)

		dlg = featureedit_GUI.FeatureEditDialog(None, 'New Feature', self.state) # creation of a dialog with a title
		dlg.Center()
		dlg.ShowModal()
		self.update_ownUI() #update the feature view
		self.update_globalUI() 
		

	def OnDelete(self, event):
		'''Delete selected feature'''
		index = self.feature_list.GetFirstSelected()
		feature = self.state.gb.get_feature(index)
		self.state.gb.remove_feature(feature)
		self.update_ownUI() #update the feature view
		self.update_globalUI() 
	
		#set highlight, focus and selection
		if index == self.feature_list.GetItemCount():
			index = index-1
		if index < 0:
			self.update_feature_selection(None)	
		else:
			self.update_feature_selection(index)


	def OnMoveFeatureUp(self, event):
		'''Move feature up one step'''
		index = self.feature_list.GetFirstSelected()
		feature = self.state.gb.get_feature(index)
		self.state.gb.move_feature(feature, 'u')	
		self.update_ownUI()

		#set highlight, focus and selection
		if index != 0:
			index = index-1
		self.update_feature_selection(index)
		

	def OnMoveFeatureDown(self, event):
		'''Move feature up down step'''
		index = self.feature_list.GetFirstSelected()
		feature = self.state.gb.get_feature(index)
		self.state.gb.move_feature(feature, 'd')
		self.update_ownUI()

		#set highlight, focus and selection	
		if index != self.feature_list.GetItemCount()-1:
			index = index+1
		self.update_feature_selection(index)

	def OnEditFeature(self, event):
		'''Edit a feature that is already present'''
		dlg = featureedit_GUI.FeatureEditDialog(None, 'Edit Feature', self.state) # creation of a dialog with a title
		dlg.Center()
		dlg.ShowModal()
		self.update_ownUI() #update the feature view
		self.update_globalUI() 

	def focus_feature_selection(self):
		index = copy.copy(self.state.feature_selection)

		self.feature_list.SetItemState(item=index, state=ULC.ULC_STATE_SELECTED, stateMask=wx.LIST_STATE_SELECTED) #for the highlight
		self.feature_list.Select(index, True) #to select it
		self.feature_list.Focus(index) #to focus it


	def update_feature_selection(self, index):
		'''Updates which feature is selected'''
		self.state.feature_selection = copy.copy(index)
		if index == None:
			pass
		else:
			self.focus_feature_selection()



	def OnCopyFASTA(self, event):
		pass

	def OnCopyDNA(self, event):
		pass
		
	def OnCopyTranslation(self, event):
		pass

	def get_feature_color(self, feature):
		'''Takes single feature and finds its color, if any'''
		#piece of code to check if there are assigned colors to the features
		
		Key = settings.get().feature_colour(feature['key'])
		
		complement = feature['complement']
		if complement == True: self.current_highlight_color = Key['rv']
		else: self.current_highlight_color = Key['fw']


	def get_dna_selection(self):
		'''This method is needed to get the dna selection for creating new features.'''
		return self.state.dna_selection




######################################
######################################



##### main loop

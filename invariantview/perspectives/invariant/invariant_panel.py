"""
    This module provide GUI for the neutron scattering length density calculator
    @author: Gervaise B. Alina
"""

import wx
import sys

from sans.invariant import invariant
from sans.guiframe.utils import format_number, check_float
from sans.guicomm.events import NewPlotEvent, StatusEvent
from invariant_details import InvariantDetailsPanel
from invariant_widgets import OutputTextCtrl, InvTextCtrl
# The minimum q-value to be used when extrapolating
Q_MINIMUM  = 1e-5
# The maximum q-value to be used when extrapolating
Q_MAXIMUM  = 10
# the maximum value to plot the theory data
Q_MAXIMUM_PLOT = 2
# the number of points to consider during fit
NPTS = 10
#Default value for background
BACKGROUND = 0.0
#default value for the scale
SCALE = 1.0
#default value of the contrast
CONTRAST = 1.0
#Invariant panel size 
_BOX_WIDTH = 76
#scale to use for a bar of value zero
RECTANGLE_SCALE  = 0.0001

if sys.platform.count("win32")>0:
    _STATICBOX_WIDTH = 450
    PANEL_WIDTH = 500
    PANEL_HEIGHT = 700
    FONT_VARIANT = 0
else:
    _STATICBOX_WIDTH = 480
    PANEL_WIDTH = 530
    PANEL_HEIGHT = 700
    FONT_VARIANT = 1
    
class InvariantContainer(wx.Object):
    def __init__(self):
        #invariant at low range
        self.qstar_low = None
        #invariant at low range error
        self.qstar_low_err = None
        #invariant 
        self.qstar = None
        #invariant error
        self.qstar_err = None
        #invariant at high range
        self.qstar_high = None
        #invariant at high range error
        self.qstar_high_err = None
        #invariant total
        self.qstar_total = None
        #invariant error
        self.qstar_total_err = None
        #scale
        self.qstar_low_scale = RECTANGLE_SCALE
        self.qstar_scale = RECTANGLE_SCALE
        self.qstar_high_scale = RECTANGLE_SCALE
 
class InvariantPanel(wx.ScrolledWindow):
    """
        Provides the Invariant GUI.
    """
    ## Internal nickname for the window, used by the AUI manager
    window_name = "Invariant"
    ## Name to appear on the window title bar
    window_caption = "Invariant"
    ## Flag to tell the AUI manager to put this panel in the center pane
    CENTER_PANE = True
    def __init__(self, parent, data=None, manager=None):
        wx.ScrolledWindow.__init__(self, parent, style= wx.FULL_REPAINT_ON_RESIZE )
        #Font size 
        self.SetWindowVariant(variant=FONT_VARIANT)
        #Object that receive status event
        self.parent = parent
        #plug-in using this panel
        self._manager = manager 
        #Default power value
        self.power_law_exponant = 4 
        #Data uses for computation
        self._data = data
        #container of invariant value
        self.inv_container = None
        #Draw the panel
        self._do_layout()
        if self.parent is not None:
            msg = ""
            wx.PostEvent(self.parent, StatusEvent(status= msg))
       
    def err_check_on_data(self):
        """
            Check if data is valid for further computation
        """
        flag = False
        #edit the panel
        if self._data is not None:
            if len(self._data.x[self._data.x==0]) > 0:
                flag = True
                msg = "Invariant: one of your q-values is zero. Delete that entry before proceeding"
                wx.PostEvent(self.parent, StatusEvent(status= msg, type="stop")) 
        return flag
    
    def set_data(self, data):
        """
            Set the data
        """
        self._data = data
        #edit the panel
        if self._data is not None:
            self.err_check_on_data()
            data_name = self._data.name
            data_qmin = min (self._data.x)
            data_qmax = max (self._data.x)
            self.data_name_tcl.SetValue(str(data_name))
            self.data_min_tcl.SetLabel(str(data_qmin))
            self.data_max_tcl.SetLabel(str(data_qmax))
        
    def set_manager(self, manager):
        """
            set value for the manager
        """
        self._manager = manager 
    
    def get_background(self):
        """
            @return the background textcrtl value as a float
        """
        background = self.background_tcl.GetValue().lstrip().rstrip()
        if background == "":
            raise ValueError, "Need a background"
        if check_float(self.background_tcl):
            return float(background)
        else:
            raise ValueError, "Receive invalid value for background : %s"%(background)
    
    def get_scale(self):
        """
            @return the scale textcrtl value as a float
        """
        scale = self.scale_tcl.GetValue().lstrip().rstrip()
        if scale == "":
            raise ValueError, "Need a background"
        if check_float(self.scale_tcl):
            return float(scale)
        else:
            raise ValueError, "Receive invalid value for background : %s"%(scale)
        
    def get_contrast(self):
        """
            @return the contrast textcrtl value as a float
        """
        par_str = self.contrast_tcl.GetValue().strip()
        contrast = None
        if par_str !="" and check_float(self.contrast_tcl):
            contrast = float(par_str)
        return contrast
    
    def get_extrapolation_type(self, low_q, high_q):
        """
        """
        extrapolation = None
        if low_q  and not high_q:
            extrapolation = "low"
        elif not low_q  and high_q:
            extrapolation = "high"
        elif low_q and high_q:
            extrapolation = "both"
        return extrapolation
            
    def get_porod_const(self):
        """
            @return the porod constant textcrtl value as a float
        """
        par_str = self.porod_constant_tcl.GetValue().strip()
        porod_const = None
        if par_str !="" and check_float(self.porod_constant_tcl):
            porod_const = float(par_str)
        return porod_const
    
    def get_volume(self, inv, contrast, extrapolation):
        """
        """
        if contrast is not None:
            try:
                v, dv = inv.get_volume_fraction_with_error(contrast=contrast, 
                                                           extrapolation=extrapolation)
                self.volume_tcl.SetValue(format_number(v))
                self.volume_err_tcl.SetValue(format_number(dv))
            except:
                raise
                msg= "Error occurred computing volume fraction: %s"%sys.exc_value
                wx.PostEvent(self.parent, StatusEvent(status= msg, type="stop"))
               
    def get_surface(self, inv, contrast, porod_const, extrapolation):
        """
        """
        if contrast is not None and porod_const is not None:
            try:
                s, ds = inv.get_surface_with_error(contrast=contrast,
                                        porod_const=porod_const,
                                        extrapolation=extrapolation)
                self.surface_tcl.SetValue(format_number(s))
                self.surface_err_tcl.SetValue(format_number(ds))
            except:
                msg= "Error occurred computing specific surface: %s"%sys.exc_value
                wx.PostEvent(self.parent, StatusEvent(status= msg, type="stop"))
                
    def get_total_qstar(self, inv, extrapolation):
        """
        """
        try:
            qstar_total, qstar_total_err = inv.get_qstar_with_error(extrapolation)
            self.invariant_total_tcl.SetValue(format_number(qstar_total))
            self.invariant_total_err_tcl.SetValue(format_number(qstar_total_err))
            self.inv_container.qstar_total = qstar_total
            self.inv_container.qstar_total_err = qstar_total_err
         
        except:
            msg= "Error occurred computing invariant using extrapolation: %s"%sys.exc_value
            wx.PostEvent(self.parent, StatusEvent(status= msg, type="stop"))  
            
    def get_low_qstar(self, inv, npts_low, low_q=False):
        """
        """
        if low_q:
            try: 
                qstar_low, qstar_low_err = inv.get_qstar_low()
                self.inv_container.qstar_low = qstar_low
                self.inv_container.qstar_low_err = qstar_low_err
                extrapolated_data = inv.get_extra_data_low(npts_in=npts_low) 
                power_low = inv.get_extrapolation_power(range='low')  
                if self.power_law_low.GetValue():
                    self.power_low_tcl.SetValue(str(power_low))
                self._manager.plot_theory(data=extrapolated_data,
                                           name="Low-Q extrapolation")
            except:
                msg= "Error occurred computing low-Q invariant: %s"%sys.exc_value
                wx.PostEvent(self.parent, StatusEvent(status= msg, type="stop"))
        else:
            self._manager.plot_theory(name="Low-Q extrapolation")
            
    def get_high_qstar(self, inv, high_q=False):
        """
        """
        if high_q:
            try: 
                qstar_high, qstar_high_err = inv.get_qstar_high()
                self.inv_container.qstar_high = qstar_high
                self.inv_container.qstar_high_err = qstar_high_err
                power_high = inv.get_extrapolation_power(range='high') 
                self.power_high_tcl.SetValue(str(power_high))
                high_out_data = inv.get_extra_data_high(q_end=Q_MAXIMUM_PLOT)
                self._manager.plot_theory(data=high_out_data,
                                           name="High-Q extrapolation")
            except:
                msg= "Error occurred computing high-Q invariant: %s"%sys.exc_value
                wx.PostEvent(self.parent, StatusEvent(status= msg, type="stop"))
        else:
            self._manager.plot_theory(name="High-Q extrapolation")
            
    def get_qstar(self, inv):
        """
        """
        qstar, qstar_err = inv.get_qstar_with_error()
        self.inv_container.qstar = qstar
        self.inv_container.qstar_err = qstar_err
             
    def set_extrapolation_low(self, inv, low_q=False):
        """
            @return float value necessary to compute invariant a low q
        """
        #get funtion
        if self.guinier.GetValue():
            function_low = "guinier"
        # get the function
        power_low = None #2.0/3.0
        if self.power_law_low.GetValue():
            function_low = "power_law"
            if self.fit_enable_low.GetValue():
                #set value of power_low to none to allow fitting
                power_low = None
            else:
                power_low = self.power_low_tcl.GetValue().lstrip().rstrip()
                if check_float(self.power_low_tcl):
                    power_low = float(power_low)
                else:
                    if low_q :
                        #Raise error only when qstar at low q is requested
                        msg = "Expect float for power at low q , got %s"%(power_low)
                        raise ValueError, msg
       
        #Get the number of points to extrapolated
        npts_low = self.npts_low_tcl.GetValue().lstrip().rstrip()   
        if check_float(self.npts_low_tcl):
            npts_low = float(npts_low)
        else:
            if low_q:
                msg = "Expect float for number of points at low q , got %s"%(npts_low)
                raise ValueError, msg
        #Set the invariant calculator
        inv.set_extrapolation(range="low", npts=npts_low,
                                   function=function_low, power=power_low)    
        return inv, npts_low  
        
    def set_extrapolation_high(self, inv, high_q=False):
        """
            @return float value necessary to compute invariant a high q
        """
        function_high = "power_law"
        power_high = None
        if self.power_law_high.GetValue():
            function_high = "power_law"
            if self.fit_enable_high.GetValue():
                #set value of power_high to none to allow fitting
                power_high = None
            else:
                power_high = self.power_high_tcl.GetValue().lstrip().rstrip()
                if check_float(self.power_high_tcl):
                    power_high = float(power_high)
                else:
                    if high_q :
                        #Raise error only when qstar at high q is requested
                        msg = "Expect float for power at high q , got %s"%(power_high)
                        raise ValueError, msg
                          
        npts_high = self.npts_high_tcl.GetValue().lstrip().rstrip()   
        if check_float(self.npts_high_tcl):
            npts_high = float(npts_high)
        else:
            if high_q:
                msg = "Expect float for number of points at high q , got %s"%(npts_high)
                raise ValueError, msg
        inv.set_extrapolation(range="high", npts=npts_high,
                                   function=function_high, power=power_high)
        return inv, npts_high
    
    def display_details(self, event):
        """
            open another panel for more details on invariant calculation
        """
        #panel = InvariantDetailsWindow(parent=self.parent,
        #                               qstar_container=self.inv_container)
        panel = InvariantDetailsPanel(parent=self, 
                                           qstar_container=self.inv_container)
        panel.ShowModal()
        panel.Destroy()
        
    def compute_invariant(self, event):
        """
            compute invariant 
        """
        msg= ""
        wx.PostEvent(self.parent, StatusEvent(status= msg))
        if self._data is None or self.err_check_on_data():
            return
    
        #clear outputs textctrl 
        self._reset_output()
        try:
            background = self.get_background()
            scale = self.get_scale()
        except:
            msg= "Invariant Error: %s"%(sys.exc_value)
            wx.PostEvent(self.parent, StatusEvent(status= msg, type="stop"))
            return
        
        low_q = self.enable_low_cbox.GetValue()
        high_q = self.enable_high_cbox.GetValue()  
        #set invariant calculator 
        inv = invariant.InvariantCalculator(data=self._data,
                                            background=background,
                                            scale=scale)
        try:
            inv, npts_low = self.set_extrapolation_low(inv=inv, low_q=low_q)
            inv, npts_high = self.set_extrapolation_high(inv=inv, high_q=high_q)
        except:
            raise
            #msg= "Error occurred computing invariant: %s"%sys.exc_value
            #wx.PostEvent(self.parent, StatusEvent(status= msg, type="stop"))
            return
        #check the type of extrapolation
        extrapolation = self.get_extrapolation_type(low_q=low_q, high_q=high_q)
       
        #Compute invariant
        try:
            self.get_qstar(inv=inv)
        except:
            msg= "Error occurred computing invariant: %s"%sys.exc_value
            wx.PostEvent(self.parent, StatusEvent(status= msg, type="stop"))
            return
        #Compute qstar extrapolated to low q range 
        self.get_low_qstar(inv=inv, npts_low=npts_low, low_q=low_q)
        #Compute qstar extrapolated to high q range 
        self.get_high_qstar(inv=inv, high_q=high_q)
        #Compute qstar extrapolated to total q range and set value to txtcrtl
        self.get_total_qstar(inv=inv, extrapolation=extrapolation)
        # Parse additional parameters
        porod_const = self.get_porod_const()        
        contrast = self.get_contrast()
        try:
            #Compute volume and set value to txtcrtl
            self.get_volume(inv=inv, contrast=contrast, extrapolation=extrapolation)
            #compute surface and set value to txtcrtl
        except:
            msg= "Error occurred computing invariant: %s"%sys.exc_value
            wx.PostEvent(self.parent, StatusEvent(status= msg))
        try:
            self.get_surface(inv=inv, contrast=contrast, porod_const=porod_const, 
                                    extrapolation=extrapolation)
        except:
            msg= "Error occurred computing invariant: %s"%sys.exc_value
            wx.PostEvent(self.parent, StatusEvent(status= msg))
      
        #enable the button_ok for more details
        self.button_ok.Enable()
        
    def _reset_output(self):
        """
            clear outputs textcrtl
        """
        self.invariant_total_tcl.Clear()
        self.invariant_total_err_tcl.Clear()
        self.volume_tcl.Clear()
        self.volume_err_tcl.Clear()
        self.surface_tcl.Clear()
        self.surface_err_tcl.Clear()
        #prepare a new container to put result of invariant
        self.inv_container = InvariantContainer()
        
    def _define_structure(self):
        """
            Define main sizers needed for this panel
        """
        ## Box sizers must be defined first before defining buttons/textctrls (MAC).
        self.main_sizer = wx.BoxSizer(wx.VERTICAL)
        #Sizer related to outputs
        outputs_box = wx.StaticBox(self, -1, "Outputs")
        self.outputs_sizer = wx.StaticBoxSizer(outputs_box, wx.VERTICAL)
        self.outputs_sizer.SetMinSize((PANEL_WIDTH,-1))
        #Sizer related to data
        data_name_box = wx.StaticBox(self, -1, "I(q) Data Source")
        self.data_name_boxsizer = wx.StaticBoxSizer(data_name_box, wx.VERTICAL)
        self.data_name_boxsizer.SetMinSize((PANEL_WIDTH,-1))
        self.hint_msg_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.data_name_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.data_range_sizer = wx.BoxSizer(wx.HORIZONTAL)
        #Sizer related to background
        self.background_sizer = wx.BoxSizer(wx.HORIZONTAL) 
        #Sizer related to scale
        self.scale_sizer = wx.BoxSizer(wx.HORIZONTAL) 
        #Sizer related to contrast
        self.contrast_sizer = wx.BoxSizer(wx.HORIZONTAL) 
        #Sizer related to Porod Constant
        self.porod_constant_sizer = wx.BoxSizer(wx.HORIZONTAL) 
        extrapolation_box = wx.StaticBox(self, -1, "Extrapolation")
        self.extrapolation_sizer = wx.StaticBoxSizer(extrapolation_box,
                                                        wx.VERTICAL)
        self.extrapolation_sizer.SetMinSize((PANEL_WIDTH,-1))
        self.extrapolation_hint_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.extrapolation_range_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.extrapolation_low_high_sizer = wx.BoxSizer(wx.HORIZONTAL)
        #Sizer related to extrapolation at low q range
        low_q_box = wx.StaticBox(self, -1, "Low Q")
        self.low_extrapolation_sizer = wx.StaticBoxSizer(low_q_box, wx.VERTICAL)
        self.low_q_sizer = wx.GridBagSizer(5,5)
        #Sizer related to extrapolation at low q range
        high_q_box = wx.StaticBox(self, -1, "High Q")
        self.high_extrapolation_sizer = wx.StaticBoxSizer(high_q_box, wx.VERTICAL)
        self.high_q_sizer = wx.GridBagSizer(5,5)
        #sizer to define outputs
        self.volume_surface_sizer = wx.GridBagSizer(5,5)
        #Sizer related to invariant output
        self.invariant_sizer = wx.GridBagSizer(4, 4)
        #Sizer related to button
        self.button_sizer = wx.BoxSizer(wx.HORIZONTAL)
       
    def _layout_data_name(self):
        """
            Draw widgets related to data's name
        """
        #Sizer hint 
        hint_msg = "Load Data then right click to add the data on this panel! "
        hint_msg_txt = wx.StaticText(self, -1, hint_msg)  
        hint_msg_txt.SetForegroundColour("red")
        self.hint_msg_sizer.Add(hint_msg_txt)
        #Data name [string]
        data_name_txt = wx.StaticText(self, -1, 'Data : ')  
       
        self.data_name_tcl = OutputTextCtrl(self, -1, size=(_BOX_WIDTH*5, 20), style=0) 
        self.data_name_tcl.SetToolTipString("Data's name.")
        self.data_name_sizer.AddMany([(data_name_txt, 0, wx.LEFT|wx.RIGHT, 10),
                                       (self.data_name_tcl, 0, wx.EXPAND)])
        #Data range [string]
        data_range_txt = wx.StaticText(self, -1, 'Total Q Range (1/A): ') 
        data_min_txt = wx.StaticText(self, -1, 'Min : ')  
        self.data_min_tcl = OutputTextCtrl(self, -1, size=(_BOX_WIDTH, 20), style=0)
        self.data_min_tcl.SetToolTipString("The minimum value of q range.")
        data_max_txt = wx.StaticText(self, -1, 'Max : ') 
        self.data_max_tcl = OutputTextCtrl(self, -1, size=(_BOX_WIDTH, 20), style=0) 
        self.data_max_tcl.SetToolTipString("The maximum value of q range.")
        self.data_range_sizer.AddMany([(data_range_txt, 0, wx.RIGHT, 10),
                                       (data_min_txt, 0, wx.RIGHT, 10),
                                       (self.data_min_tcl, 0, wx.RIGHT, 10),
                                       (data_max_txt, 0, wx.RIGHT, 10),
                                       (self.data_max_tcl, 0, wx.RIGHT, 10)])
        self.data_name_boxsizer.AddMany([(self.hint_msg_sizer, 0 , wx.ALL, 10),
                                         (self.data_name_sizer, 0 , wx.RIGHT, 10),
                                         (self.data_range_sizer, 0 , wx.ALL, 10)])
    
    def _layout_background(self):
        """
            Draw widgets related to background
        """
        background_txt = wx.StaticText(self, -1, 'Background : ')  
        self.background_tcl = InvTextCtrl(self, -1, size=(_BOX_WIDTH, 20), style=0) 
        self.background_tcl.SetValue(str(BACKGROUND))
        background_hint_txt = "background"
        self.background_tcl.SetToolTipString(background_hint_txt)
        background_unit_txt = wx.StaticText(self, -1, '[1/cm]')  
        self.background_sizer.AddMany([(background_txt, 0, wx.LEFT|wx.RIGHT, 10),
                                       (self.background_tcl, 0, wx.RIGHT, 10),
                                       (background_unit_txt)])
    def _layout_scale(self):
        """
            Draw widgets related to scale
        """
        scale_txt = wx.StaticText(self, -1, 'Scale : ')  
        self.scale_tcl = InvTextCtrl(self, -1, size=(_BOX_WIDTH, 20), style=0)
        scale_hint_txt = "Scale"
        self.scale_tcl.SetToolTipString(scale_hint_txt)
        self.scale_tcl.SetValue(str(SCALE)) 
        self.scale_sizer.AddMany([(scale_txt, 0, wx.LEFT|wx.RIGHT, 10),
                                       (self.scale_tcl, 0, wx.LEFT, 30)])
        
    def _layout_contrast(self):
        """
            Draw widgets related to contrast
        """
        contrast_txt = wx.StaticText(self, -1, 'Contrast : ')  
        self.contrast_tcl = InvTextCtrl(self, -1, size=(_BOX_WIDTH, 20), style=0)
        self.contrast_tcl.SetValue(str(CONTRAST)) 
        contrast_hint_txt = "Contrast"
        self.contrast_tcl.SetToolTipString(contrast_hint_txt)
        contrast_unit_txt = wx.StaticText(self, -1, '[1/A^(2)]')  
        self.contrast_sizer.AddMany([(contrast_txt, 0, wx.LEFT|wx.RIGHT, 10),
                                       (self.contrast_tcl, 0, wx.LEFT, 15),
                                       (contrast_unit_txt, 0, wx.LEFT, 10)])
    
    def _layout_porod_constant(self):
        """
            Draw widgets related to porod constant
        """
        porod_const_txt = wx.StaticText(self, -1, 'Porod Constant:')  
        self.porod_constant_tcl = InvTextCtrl(self, -1, 
                                              size=(_BOX_WIDTH, 20), style=0) 
        porod_const_hint_txt = "Porod Constant"
        self.porod_constant_tcl.SetToolTipString(porod_const_hint_txt)
        optional_txt = wx.StaticText(self, -1, '(Optional)')  
        self.porod_constant_sizer.AddMany([(porod_const_txt, 0, wx.LEFT, 10),
                                       (self.porod_constant_tcl, 0, wx.LEFT, 0),
                                       (optional_txt, 0, wx.LEFT, 10)])
        
    def _enable_fit_power_law_low(self, event=None):
        """
            Enable and disable the power value editing
        """
        if self.fix_enable_low.IsEnabled():
            if self.fix_enable_low.GetValue():
                self.power_low_tcl.Enable()
            else:
                self.power_low_tcl.Disable()
            
    def _enable_low_q_section(self, event=None):
        """
            Disable or enable some button if the user enable low q extrapolation
        """
        if self.enable_low_cbox.GetValue():
            self.npts_low_tcl.Enable()
            self.fix_enable_low.Enable()
            self.fit_enable_low.Enable()
            self.guinier.Enable()
            self.power_law_low.Enable()

        else:
            self.npts_low_tcl.Disable()
            self.fix_enable_low.Disable()
            self.fit_enable_low.Disable()
            self.guinier.Disable()
            self.power_law_low.Disable()
        self._enable_power_law_low()
        self._enable_fit_power_law_low()
    
    def _enable_power_law_low(self, event=None):
        """
            Enable editing power law section at low q range
        """
        if self.guinier.GetValue():
            self.fix_enable_low.Disable()
            self.fit_enable_low.Disable()
            self.power_low_tcl.Disable()
        else:
            self.fix_enable_low.Enable()
            self.fit_enable_low.Enable()
            self.power_low_tcl.Enable()
        self._enable_fit_power_law_low()
            
    def _layout_extrapolation_low(self):
        """
            Draw widgets related to extrapolation at low q range
        """
        self.enable_low_cbox = wx.CheckBox(self, -1, "Enable Extrapolate Low Q")
        self.enable_low_cbox.SetForegroundColour('red')
        self.enable_low_cbox.SetValue(False)
        wx.EVT_CHECKBOX(self, self.enable_low_cbox.GetId(),
                                         self._enable_low_q_section)
        self.fix_enable_low = wx.RadioButton(self, -1, 'Fix',
                                         (10, 10),style=wx.RB_GROUP)
        self.fix_enable_low.SetValue(True)
        self.fit_enable_low = wx.RadioButton(self, -1, 'Fit', (10, 10))
        self.Bind(wx.EVT_RADIOBUTTON, self._enable_fit_power_law_low,
                                     id=self.fix_enable_low.GetId())
        self.Bind(wx.EVT_RADIOBUTTON, self._enable_fit_power_law_low, 
                                        id=self.fit_enable_low.GetId())
        self.guinier = wx.RadioButton(self, -1, 'Guinier',
                                         (10, 10),style=wx.RB_GROUP)
        self.guinier.SetValue(True)
        self.power_law_low = wx.RadioButton(self, -1, 'Power Law', (10, 10))
        self.Bind(wx.EVT_RADIOBUTTON, self._enable_power_law_low,
                                     id=self.guinier.GetId())
        self.Bind(wx.EVT_RADIOBUTTON, self._enable_power_law_low, 
                                        id=self.power_law_low.GetId())
        
        npts_low_txt = wx.StaticText(self, -1, 'Npts')
        self.npts_low_tcl = InvTextCtrl(self, -1, size=(_BOX_WIDTH*2/3, -1))
        self.npts_low_tcl.SetValue(str(NPTS))
        msg_hint = "Number of Q points to consider"
        msg_hint +="while extrapolating the low-Q region"
        self.npts_low_tcl.SetToolTipString(msg_hint)
        power_txt = wx.StaticText(self, -1, 'Power')
        self.power_low_tcl = InvTextCtrl(self, -1, size=(_BOX_WIDTH*2/3, -1))
        self.power_low_tcl.SetValue(str(self.power_law_exponant))
        self.power_low_tcl.Disable()
        power_hint_txt = "Exponent to apply to the Power_law function."
        self.power_low_tcl.SetToolTipString(power_hint_txt)
        iy = 0
        ix = 0
        self.low_q_sizer.Add(self.enable_low_cbox,(iy, ix),(1,5),
                            wx.TOP|wx.LEFT|wx.EXPAND|wx.ADJUST_MINSIZE, 15)
        iy += 1
        ix = 0
        self.low_q_sizer.Add(npts_low_txt,(iy, ix),(1,1),
                            wx.LEFT|wx.EXPAND|wx.ADJUST_MINSIZE, 15)
        ix += 1
        self.low_q_sizer.Add(self.npts_low_tcl, (iy, ix), (1,1),
                            wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        iy += 1
        ix = 0
        self.low_q_sizer.Add(self.guinier,(iy, ix),(1,2),
                             wx.LEFT|wx.EXPAND|wx.ADJUST_MINSIZE, 15)
        iy += 1
        ix = 0
        self.low_q_sizer.Add(self.power_law_low,(iy, ix),(1,2),
                            wx.LEFT|wx.EXPAND|wx.ADJUST_MINSIZE, 15)
       
        # Parameter controls for power law
        ix = 1
        iy += 1
        self.low_q_sizer.Add(self.fix_enable_low,(iy, ix),(1,1),
                            wx.LEFT|wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        ix += 1
        self.low_q_sizer.Add(self.fit_enable_low,(iy, ix),(1,1),
                           wx.LEFT|wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        ix = 1
        iy += 1
        self.low_q_sizer.Add(power_txt,(iy, ix),(1,1),
                            wx.LEFT|wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        ix += 1
        self.low_q_sizer.Add(self.power_low_tcl, (iy, ix), (1,1),
                            wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        #Change the state of txtcrtl to enable/disable
        self._enable_low_q_section()
        self.low_extrapolation_sizer.AddMany([(self.low_q_sizer, 0,
                                                wx.BOTTOM|wx.RIGHT, 10)])
    def _enable_fit_power_law_high(self, event=None):
        """
            Enable and disable the power value editing
        """
        if self.fix_enable_high.IsEnabled():
            if self.fix_enable_high.GetValue():
                self.power_high_tcl.Enable()
            else:
                self.power_high_tcl.Disable()
        
    def _enable_high_q_section(self, event=None):
        """
            Disable or enable some button if the user enable high q extrapolation
        """
        if self.enable_high_cbox.GetValue():
            self.npts_high_tcl.Enable()
            self.power_law_high.Enable()
            self.power_high_tcl.Enable()
            self.fix_enable_high.Enable()
            self.fit_enable_high.Enable()
        else:
            self.npts_high_tcl.Disable()
            self.power_law_high.Disable()
            self.power_high_tcl.Disable()
            self.fix_enable_high.Disable()
            self.fit_enable_high.Disable()
        self._enable_fit_power_law_high()
  
    def _layout_extrapolation_high(self):
        """
            Draw widgets related to extrapolation at high q range
        """
        self.enable_high_cbox = wx.CheckBox(self, -1, "Enable Extrapolate high-Q")
        self.enable_high_cbox.SetForegroundColour('red')
        self.enable_high_cbox.SetValue(False)
        wx.EVT_CHECKBOX(self, self.enable_high_cbox.GetId(),
                                         self._enable_high_q_section)
      
        self.fix_enable_high = wx.RadioButton(self, -1, 'Fix',
                                         (10, 10),style=wx.RB_GROUP)
        self.fix_enable_high.SetValue(True)
        self.fit_enable_high = wx.RadioButton(self, -1, 'Fit', (10, 10))
        self.Bind(wx.EVT_RADIOBUTTON, self._enable_fit_power_law_high,
                                     id=self.fix_enable_high.GetId())
        self.Bind(wx.EVT_RADIOBUTTON, self._enable_fit_power_law_high, 
                                        id=self.fit_enable_high.GetId())
        
        self.power_law_high = wx.RadioButton(self, -1, 'Power Law',
                                              (10, 10), style=wx.RB_GROUP)
        msg_hint ="Check to extrapolate data at high-Q"
        self.power_law_high.SetToolTipString(msg_hint)
        self.power_law_high.SetValue(True)
        npts_high_txt = wx.StaticText(self, -1, 'Npts')
        self.npts_high_tcl = InvTextCtrl(self, -1, size=(_BOX_WIDTH*2/3, -1))
        msg_hint = "Number of Q points to consider"
        msg_hint += "while extrapolating the high-Q region"
        self.npts_high_tcl.SetToolTipString(msg_hint)
        self.npts_high_tcl.SetValue(str(NPTS))
        power_txt = wx.StaticText(self, -1, 'Power')
        self.power_high_tcl = InvTextCtrl(self, -1, size=(_BOX_WIDTH*2/3, -1))
        self.power_high_tcl.SetValue(str(self.power_law_exponant))
        power_hint_txt = "Exponent to apply to the Power_law function."
        self.power_high_tcl.SetToolTipString(power_hint_txt)
        iy = 0
        ix = 0
        self.high_q_sizer.Add(self.enable_high_cbox,(iy, ix),(1,5),
                            wx.TOP|wx.LEFT|wx.EXPAND|wx.ADJUST_MINSIZE, 15)
        iy += 1
        ix = 0
        self.high_q_sizer.Add(npts_high_txt,(iy, ix),(1,1),
                            wx.LEFT|wx.EXPAND|wx.ADJUST_MINSIZE, 15)
        ix += 1
        self.high_q_sizer.Add(self.npts_high_tcl, (iy, ix), (1,1),
                            wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        iy += 2
        ix = 0
        self.high_q_sizer.Add(self.power_law_high,(iy, ix),(1,2),
                            wx.LEFT|wx.EXPAND|wx.ADJUST_MINSIZE, 15)
       
        # Parameter controls for power law
        ix = 1
        iy += 1
        self.high_q_sizer.Add(self.fix_enable_high,(iy, ix),(1,1),
                            wx.LEFT|wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        ix += 1
        self.high_q_sizer.Add(self.fit_enable_high,(iy, ix),(1,1),
                           wx.LEFT|wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        ix = 1
        iy += 1
        self.high_q_sizer.Add(power_txt,(iy, ix),(1,1),
                            wx.LEFT|wx.EXPAND|wx.ADJUST_MINSIZE, 15)
        ix += 1
        self.high_q_sizer.Add(self.power_high_tcl, (iy, ix), (1,1),
                            wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        #Change the state of txtcrtl to enable/disable
        self._enable_high_q_section()
        self.high_extrapolation_sizer.AddMany([(self.high_q_sizer, 0, wx.RIGHT, 10)])
        
    def _layout_extrapolation(self):
        """
            Draw widgets related to extrapolation
        """
        extra_hint = "Extrapolation Maximum Q Range [1/A]: "
        extra_hint_txt = wx.StaticText(self, -1, extra_hint)
        #Extrapolation range [string]
        extrapolation_min_txt = wx.StaticText(self, -1, 'Min : ')  
        self.extrapolation_min_tcl = OutputTextCtrl(self, -1, 
                                                size=(_BOX_WIDTH, 20), style=0)
        self.extrapolation_min_tcl.SetValue(str(Q_MINIMUM))
        self.extrapolation_min_tcl.SetToolTipString("The minimum extrapolated q value.")
        extrapolation_max_txt = wx.StaticText(self, -1, 'Max : ') 
        self.extrapolation_max_tcl = OutputTextCtrl(self, -1,
                                                  size=(_BOX_WIDTH, 20), style=0) 
        self.extrapolation_max_tcl.SetValue(str(Q_MAXIMUM))
        self.extrapolation_max_tcl.SetToolTipString("The maximum extrapolated q value.")
        self.extrapolation_range_sizer.AddMany([(extra_hint_txt, 0, wx.LEFT, 10),
                                                (extrapolation_min_txt, 0, wx.LEFT, 10),
                                                (self.extrapolation_min_tcl,
                                                            0, wx.LEFT, 10),
                                                (extrapolation_max_txt, 0, wx.LEFT, 10),
                                                (self.extrapolation_max_tcl,
                                                            0, wx.LEFT, 10),
                                                ])
        extra_enable_hint = "Hint: Check any box to enable a specific extrapolation !"
        extra_enable_hint_txt = wx.StaticText(self, -1, extra_enable_hint )
        self.extrapolation_hint_sizer.AddMany([(extra_enable_hint_txt, 0, wx.LEFT, 0)
                                               ])
        self._layout_extrapolation_low()
        self._layout_extrapolation_high()
        self.extrapolation_low_high_sizer.AddMany([(self.low_extrapolation_sizer,
                                                     0, wx.ALL, 10),
                                                   (self.high_extrapolation_sizer,
                                                    0, wx.ALL, 10)])
        self.extrapolation_sizer.AddMany([(self.extrapolation_range_sizer, 0,
                                            wx.RIGHT, 10),
                                         (self.extrapolation_hint_sizer, 0,
                                           wx.ALL, 10),
                                        (self.extrapolation_low_high_sizer, 0,
                                           wx.ALL, 10)])
        
    def _layout_volume_surface_sizer(self):
        """
            Draw widgets related to volume and surface
        """
        unit_volume = ''
        unit_surface = ''
        uncertainty = "+/-" 
        volume_txt = wx.StaticText(self, -1, 'Volume Fraction')
        self.volume_tcl = OutputTextCtrl(self, -1, size=(_BOX_WIDTH,-1))
        self.volume_tcl.SetToolTipString("Volume fraction.")
        self.volume_err_tcl = OutputTextCtrl(self, -1, size=(_BOX_WIDTH,-1))
        self.volume_err_tcl.SetToolTipString("Uncertainty on the volume fraction.")
        volume_units_txt = wx.StaticText(self, -1, unit_volume)
        
        surface_txt = wx.StaticText(self, -1, 'Specific surface')
        self.surface_tcl = OutputTextCtrl(self, -1, size=(_BOX_WIDTH,-1))
        self.surface_tcl.SetToolTipString("Specific surface value.")
        self.surface_err_tcl = OutputTextCtrl(self, -1, size=(_BOX_WIDTH,-1))
        self.surface_err_tcl.SetToolTipString("Uncertainty on the specific surface.")
        surface_units_txt = wx.StaticText(self, -1, unit_surface)
        iy = 0
        ix = 0
        self.volume_surface_sizer.Add(volume_txt, (iy, ix), (1,1),
                             wx.LEFT|wx.EXPAND|wx.ADJUST_MINSIZE, 15)
        ix += 1
        self.volume_surface_sizer.Add(self.volume_tcl, (iy, ix), (1,1),
                            wx.EXPAND|wx.ADJUST_MINSIZE, 10)
        ix += 1
        self.volume_surface_sizer.Add(wx.StaticText(self, -1, uncertainty),
                         (iy, ix),(1,1),wx.EXPAND|wx.ADJUST_MINSIZE, 10) 
        ix += 1
        self.volume_surface_sizer.Add(self.volume_err_tcl, (iy, ix), (1,1),
                            wx.EXPAND|wx.ADJUST_MINSIZE, 10) 
        ix += 1
        self.volume_surface_sizer.Add(volume_units_txt, (iy, ix), (1,1),
                             wx.EXPAND|wx.ADJUST_MINSIZE, 10)
        iy += 1
        ix = 0
        self.volume_surface_sizer.Add(surface_txt, (iy, ix), (1,1),
                             wx.LEFT|wx.EXPAND|wx.ADJUST_MINSIZE, 15)
        ix += 1
        self.volume_surface_sizer.Add(self.surface_tcl, (iy, ix), (1,1),
                            wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        ix += 1
        self.volume_surface_sizer.Add(wx.StaticText(self, -1, uncertainty),
                         (iy, ix),(1,1),wx.EXPAND|wx.ADJUST_MINSIZE, 0) 
        ix += 1
        self.volume_surface_sizer.Add(self.surface_err_tcl, (iy, ix), (1,1),
                            wx.EXPAND|wx.ADJUST_MINSIZE, 0) 
        ix += 1
        self.volume_surface_sizer.Add(surface_units_txt, (iy, ix), (1,1),
                            wx.EXPAND|wx.ADJUST_MINSIZE, 10)
        
    def _layout_invariant_sizer(self):
        """
            Draw widgets related to invariant
        """
        uncertainty = "+/-" 
        unit_invariant = '[1/cm][1/A]'
        invariant_total_txt = wx.StaticText(self, -1, 'Invariant Total')
        self.invariant_total_tcl = OutputTextCtrl(self, -1, size=(_BOX_WIDTH,-1))
        msg_hint = "Total invariant, including extrapolated regions."
        self.invariant_total_tcl.SetToolTipString(msg_hint)
        self.invariant_total_err_tcl = OutputTextCtrl(self, -1, size=(_BOX_WIDTH,-1))
        self.invariant_total_err_tcl.SetToolTipString("Uncertainty on invariant.")
        invariant_total_units_txt = wx.StaticText(self, -1, unit_invariant)
    
        #Invariant total
        iy = 0
        ix = 0
        self.invariant_sizer.Add(invariant_total_txt, (iy, ix), (1,1),
                             wx.LEFT|wx.EXPAND|wx.ADJUST_MINSIZE, 15)
        ix += 1
        self.invariant_sizer.Add(self.invariant_total_tcl, (iy, ix), (1,1),
                            wx.EXPAND|wx.ADJUST_MINSIZE, 0) 
        ix += 1
        self.invariant_sizer.Add( wx.StaticText(self, -1, uncertainty),
                         (iy, ix),(1,1),wx.EXPAND|wx.ADJUST_MINSIZE, 0) 
        ix += 1
        self.invariant_sizer.Add(self.invariant_total_err_tcl, (iy, ix), (1,1),
                            wx.EXPAND|wx.ADJUST_MINSIZE, 0) 
        ix += 1
        self.invariant_sizer.Add(invariant_total_units_txt
                         ,(iy, ix),(1,1),wx.EXPAND|wx.ADJUST_MINSIZE, 0) 
 
    def _layout_outputs_sizer(self):
        """
            Draw widgets related to outputs
        """
        self._layout_volume_surface_sizer()
        self._layout_invariant_sizer()
        static_line = wx.StaticLine(self, -1)
        self.outputs_sizer.AddMany([(self.volume_surface_sizer, 0, wx.ALL, 10),
                                    (static_line, 0, wx.EXPAND, 0),
                                    (self.invariant_sizer, 0, wx.ALL, 10)])
    def _layout_button(self):  
        """
            Do the layout for the button widgets
        """ 
        #compute button
        id = wx.NewId()
        button_calculate = wx.Button(self, id, "Compute")
        button_calculate.SetToolTipString("Compute invariant")
        self.Bind(wx.EVT_BUTTON, self.compute_invariant, id=id)   
        #detail button
        id = wx.NewId()
        self.button_ok = wx.Button(self, id, "Details?")
        self.button_ok.SetToolTipString("Give Details on Computation")
        self.Bind(wx.EVT_BUTTON, self.display_details, id=id)
        self.button_ok.Disable()
        details = "Details on Invariant Total Calculations"
        details_txt = wx.StaticText(self, -1, details)
        self.button_sizer.AddMany([((20,20), 0 , wx.LEFT, 100),
                                   (details_txt, 0 , wx.ALL, 10),
                                   (self.button_ok, 0 , wx.ALL, 10),
                        (button_calculate, 0 , wx.RIGHT|wx.TOP|wx.BOTTOM, 10)])
        
    def _do_layout(self):
        """
            Draw window content
        """
        self._define_structure()
        self._layout_data_name()
        self._layout_background()
        self._layout_scale()
        self._layout_contrast()
        self._layout_porod_constant()
        self._layout_extrapolation()
        self._layout_outputs_sizer()
        self._layout_button()
        self.main_sizer.AddMany([(self.data_name_boxsizer, 0, wx.ALL, 10),
                                 (self.background_sizer, 0,
                                   wx.LEFT|wx.RIGHT|wx.BOTTOM, 10),
                                 (self.scale_sizer, 0,
                                   wx.LEFT|wx.RIGHT|wx.BOTTOM, 10),
                                 (self.contrast_sizer, 0,
                                  wx.LEFT|wx.RIGHT|wx.BOTTOM, 10),
                                  (self.porod_constant_sizer, 0,
                                  wx.LEFT|wx.RIGHT|wx.BOTTOM, 10),
                                  (self.extrapolation_sizer, 0,
                                  wx.LEFT|wx.RIGHT|wx.BOTTOM, 10),
                                  (self.outputs_sizer, 0,
                                  wx.LEFT|wx.RIGHT|wx.BOTTOM, 10),
                                  (self.button_sizer, 0,
                                  wx.LEFT|wx.RIGHT|wx.BOTTOM, 10)])
        self.SetSizer(self.main_sizer)
        self.SetScrollbars(20,20,25,65)
        self.SetAutoLayout(True)
    
class InvariantDialog(wx.Dialog):
    def __init__(self, parent=None, id=1,graph=None,
                 data=None, title="Invariant",base=None):
        wx.Dialog.__init__(self, parent, id, title, size=(PANEL_WIDTH,
                                                             PANEL_HEIGHT))
        self.panel = InvariantPanel(self)
        self.Centre()
        self.Show(True)
        
class InvariantWindow(wx.Frame):
    def __init__(self, parent=None, id=1,graph=None, 
                 data=None, title="Invariant",base=None):
        
        wx.Frame.__init__(self, parent, id, title, size=(PANEL_WIDTH +100,
                                                             PANEL_HEIGHT+100))
        
        self.panel = InvariantPanel(self)
        self.Centre()
        self.Show(True)
        
class MyApp(wx.App):
    def OnInit(self):
        wx.InitAllImageHandlers()
        frame = InvariantWindow()
        frame.Show(True)
        self.SetTopWindow(frame)
        
        return True
      
# end of class MyApp

if __name__ == "__main__":
    app = MyApp(0)
    app.MainLoop()
"""
SANS generic computation and sld file readers
"""
from sans.models.BaseComponent import BaseComponent
import sans.models.sans_extension.sld2i as mod
import numpy
import os

MFactor_AM = 2.853E-12
MFactor_mT = 2.3164E-9
METER2ANG = 1.0E+10

def mag2sld(mag, v_unit=None):
    """
    Convert magnetization to magnatic SLD
    sldm = Dm * mag where Dm = gamma * classical elec. radius/(2*Bohr magneton)
    Dm ~ 2.853E-12 [A^(-2)] ==> Shouldn't be 2.90636E-12 [A^(-2)]???
    """ 
    if v_unit == "A/m":
        factor = MFactor_AM
    elif v_unit == "mT":
        factor = MFactor_mT
    else:
        raise ValueError, "Invalid valueunit"
    sld_m = factor * mag
    return sld_m

class GenSAS(BaseComponent):
    """
    Generic SAS computation Model based on sld (n & m) arrays
    """
    def __init__(self):
        """
        Init
        
        :Params sld_data: MagSLD object
        """
        # Initialize BaseComponent
        BaseComponent.__init__(self)
        self.sld_data = None
        self.data_pos_unit = None
        self.data_x = None
        self.data_y = None
        self.data_z = None
        self.data_sldn = None
        self.data_mx = None
        self.data_my = None
        self.data_mz = None
        self.volume = 1000 #[A^3]
        ## Name of the model
        self.name = "GenSAS"
        ## Define parameters
        self.params = {}
        self.params['scale']       = 1.0
        self.params['background']  = 0.0
        self.params['Up_frac_i']     = 1.0
        self.params['Up_frac_f']    = 1.0
        self.params['Up_theta']  = 0.0
        self.description='GenSAS'
        ## Parameter details [units, min, max]
        self.details = {}
        self.details['scale']      = ['', None, None]
        self.details['background'] = ['[1/cm]', None, None]
        self.details['Up_frac_i']    = ['[u/(u+d)]', None, None]
        self.details['Up_frac_f']   = ['[u/(u+d)]', None, None]
        self.details['Up_theta'] = ['[deg]', None, None]
        # fixed parameters
        self.fixed=[]
        
    def set_pixel_volume(self, volume):     
        """
        Set the volume of a pixel in (A^3) unit
        """
        self.volume = volume
        
    def _gen(self, x, y, i):
        """
        Evaluate the function
        :Param x: x-value
        :return: function value
        """
        len_x = len(self.data_x)
        len_q = len(x)
        model = mod.new_GenI(len_x, self.data_x, self.data_y, self.data_z, 
                             self.data_sldn, self.data_mx, self.data_my, 
                             self.data_mz, self.params['Up_frac_i'], 
                             self.params['Up_frac_f'], self.params['Up_theta'])
        mod.genicom(model, len_q, x, y, i)
        return  self.params['scale'] * i * self.volume \
                + self.params['background']
        
    def set_sld_data(self, sld_data=None):   
        """
        Sets sld_data
        """
        self.sld_data = sld_data
        self.data_pos_unit = sld_data.pos_unit
        self.data_x = sld_data.pos_x
        self.data_y = sld_data.pos_y
        self.data_z = sld_data.pos_z
        self.data_sldn = sld_data.sld_n
        self.data_mx = sld_data.sld_mx
        self.data_my = sld_data.sld_my
        self.data_mz = sld_data.sld_mz
        
    def getProfile(self):
        """
        Get SLD profile 
        
        : return: sld_data
        """
        return self.sld_data
     
    def run(self, x = 0.0):
        """ 
        Evaluate the model
        :param x: simple value
        :return: (I value)
        """
        if x.__class__.__name__ == 'list':
            i_out = numpy.zeros_like(x[0])
            y_in = numpy.zero_like(x[0])
            # 1D I is found at y =0 in the 2D pattern
            return self._gen(x[0],y_in, i_out )
        else:
            msg = "Q must be given as list of qx's and qy's"
            raise ValueError, msg
   
    def runXY(self, x = 0.0):
        """ 
        Evaluate the model
        :param x: simple value
        :return: I value
        :Use this runXY() for the computation
        """
        if x.__class__.__name__ == 'list':
            i_out = numpy.zeros_like(x[0])
            import time
            s=time.time()
            out = self._gen(x[0], x[1], i_out)
            print "i_out_time",time.time()-s
            return out
        else:
            msg = "Q must be given as list of qx's and qy's"
            raise ValueError, msg
        
    def evalDistribution(self, qdist):
        """
        Evaluate a distribution of q-values.
        * For 1D, a numpy array is expected as input:
            evalDistribution(q)   
        where q is a numpy array.
        * For 2D, a list of numpy arrays are expected: [qx_prime,qy_prime],
          where 1D arrays,  
        :param qdist: ndarray of scalar q-values or list [qx,qy] 
                    where qx,qy are 1D ndarrays 
        """
        if qdist.__class__.__name__ == 'list':
            out = self.runXY(qdist)
            return out
        else:
            mesg = "evalDistribution is expecting an ndarray of "
            mesg += "a list [qx,qy] where qx,qy are arrays."
            raise RuntimeError, mesg
      
class OMF2SLD:
    """
    Convert OMFData to MAgData
    """
    def __init__(self): 
        """
        Init
        """
        self.pos_x = None
        self.pos_y = None
        self.pos_z = None
        self.mx = None
        self.my = None
        self.mz = None
        self.sld_n = None
        self.output = None
        self.omfdata = None
    
    def set_data(self, omfdata, shape='rectangular'):
        """
        Set all data
        """
        self.omfdata = omfdata
        length = int(omfdata.xnodes * omfdata.ynodes * omfdata.znodes)
        pos_x = numpy.arange(omfdata.xmin, 
                             omfdata.xnodes*omfdata.xstepsize + omfdata.xmin, 
                             omfdata.xstepsize)
        pos_y = numpy.arange(omfdata.ymin,  
                             omfdata.ynodes*omfdata.ystepsize + omfdata.ymin, 
                             omfdata.ystepsize)
        pos_z = numpy.arange(omfdata.zmin, 
                             omfdata.znodes*omfdata.zstepsize + omfdata.zmin, 
                             omfdata.zstepsize)
        self.pos_x = numpy.tile(pos_x, int(omfdata.ynodes * omfdata.znodes))
        self.pos_y = pos_y.repeat(int(omfdata.xnodes))
        self.pos_y = numpy.tile(self.pos_y, int(omfdata.znodes))
        self.pos_z = pos_z.repeat(int(omfdata.xnodes * omfdata.ynodes))
        self.mx = omfdata.mx
        self.my = omfdata.my
        self.mz = omfdata.mz
        self.sld_n = numpy.zeros(length)
            
        if omfdata.mx == None:
            self.mx = numpy.zeros(length)
        if omfdata.my == None:
            self.my = numpy.zeros(length)
        if omfdata.mz == None:
            self.mz = numpy.zeros(length)
        
        self._check_data_length(length)
        self.remove_null_points()
        mask = numpy.ones(len(self.sld_n), dtype=bool)
        if shape == 'ellipsoid':
            try:
                # Pixel (step) size included
                x_r = (max(self.pos_x) - min(self.pos_x) + \
                       omfdata.xstepsize) / 2.0
                y_r = (max(self.pos_y) - min(self.pos_y) + \
                       omfdata.ystepsize) / 2.0
                z_r = (max(self.pos_z) - min(self.pos_z) + \
                       omfdata.zstepsize) / 2.0
                x_dir2 = (self.pos_x / x_r) * (self.pos_x / x_r)
                y_dir2 = (self.pos_y / y_r) * (self.pos_y / y_r)
                z_dir2 = (self.pos_z / z_r) * (self.pos_z / z_r)
                mask = (x_dir2 + y_dir2 + z_dir2) <= 1
            except:
                pass
        self.output = MagSLD(self.pos_x[mask], self.pos_y[mask], 
                             self.pos_z[mask], self.sld_n[mask], 
                             self.mx[mask], self.my[mask], self.mz[mask])
        self.output.set_pix_type('pixel')
        self.output.set_pixel_symbols('pixel')
        
    def get_omfdata(self):
        """
        Return all data
        """
        return self.omfdata
    
    def get_output(self):
        """
        Return output
        """
        return self.output
    
    def _check_data_length(self, length):
        """
        Check if the data lengths are consistent
        :Params length: data length
        """
        msg = "Error: Inconsistent data length."
        if len(self.pos_x) != length:
            raise ValueError, msg
        if len(self.pos_y) != length:
            raise ValueError, msg
        if len(self.pos_z) != length:
            raise ValueError, msg
        if len(self.mx) != length:
            raise ValueError, msg
        if len(self.my) != length:
            raise ValueError, msg
        if len(self.mz) != length:
            raise ValueError, msg
        
    def remove_null_points(self, remove=False):
        """
        Removes any mx, my, and mz = 0 points
        """
        if remove:
            is_nonzero = (numpy.fabs(self.mx) + numpy.fabs(self.my) + 
                          numpy.fabs(self.mz)).nonzero()  
            if len(is_nonzero[0]) > 0: 
                self.pos_x = self.pos_x[is_nonzero]
                self.pos_y = self.pos_y[is_nonzero]
                self.pos_z = self.pos_z[is_nonzero]
                self.sld_n = self.sld_n[is_nonzero]
                self.mx = self.mx[is_nonzero]
                self.my = self.my[is_nonzero]
                self.mz = self.mz[is_nonzero]
        self.pos_x -= (min(self.pos_x) + max(self.pos_x)) / 2.0
        self.pos_y -= (min(self.pos_y) + max(self.pos_y)) / 2.0
        self.pos_z -= (min(self.pos_z) + max(self.pos_z)) / 2.0
 
    def get_magsld(self):
        """
        return MagSLD
        """
        return self.output
    
        
class OMFReader:
    """
    Class to load omf/ascii files (3 columns w/header).
    """
    ## File type
    type_name = "OMF ASCII"
    
    ## Wildcards
    type = ["OMF files (*.OMF, *.omf)|*.omf"]
    ## List of allowed extensions
    ext = ['.omf', '.OMF']
        
    def read(self, path):
        """
        Load data file
        :param path: file path
        :return: x, y, z, sld_n, sld_mx, sld_my, sld_mz
        """
        data_conv_m = None
        desc = ""
        mx = numpy.zeros(0)
        my = numpy.zeros(0)
        mz = numpy.zeros(0)
        try:
            data_conv_val = None
            data_conv_mesh = None
            input_f = open(path, 'rb')
            buff = input_f.read()
            lines = buff.split('\n')
            input_f.close()
            output = OMFData()
            valueunit = None
            for line in lines:
                toks = line.split()
                # Read data
                try:
                    _mx = float(toks[0])
                    _my = float(toks[1])
                    _mz = float(toks[2])
                    _mx = mag2sld(_mx, valueunit)
                    _my = mag2sld(_my, valueunit)
                    _mz = mag2sld(_mz, valueunit)
                    mx = numpy.append(mx, _mx)
                    my = numpy.append(my, _my)
                    mz = numpy.append(mz, _mz)
                except:
                    # Skip non-data lines
                    pass
                #Reading Header; Segment count ignored
                s_line = line.split(":", 1)
                if s_line[0].lower().count("oommf") > 0:
                    oommf = s_line[1].lstrip()
                if s_line[0].lower().count("title") > 0:
                    title = s_line[1].lstrip()
                if s_line[0].lower().count("desc") > 0:
                    desc += s_line[1].lstrip()
                    desc += '\n'
                if s_line[0].lower().count("meshtype") > 0:
                    meshtype = s_line[1].lstrip()
                if s_line[0].lower().count("meshunit") > 0:
                    meshunit = s_line[1].lstrip()
                    if meshunit.count("m") < 1:
                        msg = "Error: \n"
                        msg += "We accept only m as meshunit"
                        raise ValueError, msg
                if s_line[0].lower().count("xbase") > 0:
                    xbase = s_line[1].lstrip()
                if s_line[0].lower().count("ybase") > 0:
                    ybase = s_line[1].lstrip()
                if s_line[0].lower().count("zbase") > 0:
                    zbase = s_line[1].lstrip()
                if s_line[0].lower().count("xstepsize") > 0:
                    xstepsize = s_line[1].lstrip()
                if s_line[0].lower().count("ystepsize") > 0:
                    ystepsize = s_line[1].lstrip()
                if s_line[0].lower().count("zstepsize") > 0:
                    zstepsize = s_line[1].lstrip()
                if s_line[0].lower().count("xnodes") > 0:
                    xnodes = s_line[1].lstrip()
                if s_line[0].lower().count("ynodes") > 0:
                    ynodes = s_line[1].lstrip()
                if s_line[0].lower().count("znodes") > 0:
                    znodes = s_line[1].lstrip()
                if s_line[0].lower().count("xmin") > 0:
                    xmin = s_line[1].lstrip()
                if s_line[0].lower().count("ymin") > 0:
                    ymin = s_line[1].lstrip()
                if s_line[0].lower().count("zmin") > 0:
                    zmin = s_line[1].lstrip()
                if s_line[0].lower().count("xmax") > 0:
                    xmax = s_line[1].lstrip()
                if s_line[0].lower().count("ymax") > 0:
                    ymax = s_line[1].lstrip()
                if s_line[0].lower().count("zmax") > 0:
                    zmax = s_line[1].lstrip()
                if s_line[0].lower().count("valueunit") > 0:
                    valueunit = s_line[1].lstrip().rstrip()
                if s_line[0].lower().count("valuemultiplier") > 0:
                    valuemultiplier = s_line[1].lstrip()
                if s_line[0].lower().count("valuerangeminmag") > 0:
                    valuerangeminmag = s_line[1].lstrip()
                if s_line[0].lower().count("valuerangemaxmag") > 0:
                    valuerangemaxmag = s_line[1].lstrip()
                if s_line[0].lower().count("end") > 0:
                    #output.set_sldms(mx, my, mz)    
                    output.filename = os.path.basename(path)
                    output.oommf = oommf
                    output.title = title
                    output.desc = desc
                    output.meshtype = meshtype
                    output.xbase = float(xbase) * METER2ANG
                    output.ybase = float(ybase) * METER2ANG
                    output.zbase = float(zbase) * METER2ANG
                    output.xstepsize = float(xstepsize) * METER2ANG
                    output.ystepsize = float(ystepsize) * METER2ANG
                    output.zstepsize = float(zstepsize) * METER2ANG
                    output.xnodes = float(xnodes)
                    output.ynodes = float(ynodes)
                    output.znodes = float(znodes)
                    output.xmin = float(xmin) * METER2ANG
                    output.ymin = float(ymin) * METER2ANG
                    output.zmin = float(zmin) * METER2ANG
                    output.xmax = float(xmax) * METER2ANG
                    output.ymax = float(ymax) * METER2ANG
                    output.zmax = float(zmax) * METER2ANG
                    output.valuemultiplier = valuemultiplier
                    output.valuerangeminmag = mag2sld(float(valuerangeminmag),\
                                                      valueunit)
                    output.valuerangemaxmag = mag2sld(float(valuerangemaxmag),\
                                                      valueunit)
            output.set_m(mx, my, mz)
            return output
        except:
            msg = "%s is not supported: \n" % path
            msg += "We accept only Text format OMF file."
            raise RuntimeError, msg

class PDBReader:
    """
    PDB reader class: limited for reading the lines starting with 'ATOM'
    """
    type_name = "PDB"
    ## Wildcards
    type = ["pdb files (*.PDB, *.pdb)|*.pdb"]
    ## List of allowed extensions
    ext = ['.pdb', '.PDB']

    def read(self, path):
        """
        Load data file
        
        :param path: file path
        
        :return: MagSLD
        
        :raise RuntimeError: when the file can't be opened
        """
        pos_x = numpy.zeros(0)
        pos_y = numpy.zeros(0)
        pos_z = numpy.zeros(0)
        sld_n = numpy.zeros(0)
        sld_mx = numpy.zeros(0)
        sld_my = numpy.zeros(0)
        sld_mz = numpy.zeros(0)
        pix_symbol = numpy.zeros(0)#numpy.array([])
        try:
            input_f = open(path, 'rb')
            buff = input_f.read()
            #buff.replace(' ', '')
            lines = buff.split('\n')
            input_f.close()
            for line in lines:
                try:
                    toks = line.split()
                    # check if line starts with "ATOM"
                    if toks[0].count('ATM') > 0 or toks[0] == 'ATOM':
                        # define fields of interest
                        atom_id = toks[1]
                        atom_name = toks[2]
                        atom_name = atom_name[0].upper() + atom_name[1:].lower()
                        try:
                            float(toks[3])
                            ind = 3
                        except:
                            ind = 4
                        res_name = toks[ind]
                        #chain_name = toks[3].strip()
                        #residue_id = toks[4].strip()
                        try:
                            float(toks[4])
                        except:
                            ind += 1
                        ind += 1
                        _pos_x = float(toks[ind])
                        ind += 1
                        _pos_y = float(toks[ind])
                        ind += 1
                        _pos_z = float(toks[ind])
                        pos_x = numpy.append(pos_x, _pos_x)
                        pos_y = numpy.append(pos_y, _pos_y)
                        pos_z = numpy.append(pos_z, _pos_z)
                        sld_n = numpy.append(sld_n, 7e-06)
                        sld_mx = numpy.append(sld_mx, 0)
                        sld_my = numpy.append(sld_my, 0)
                        sld_mz = numpy.append(sld_mz, 0)
                        pix_symbol = numpy.append(pix_symbol, atom_name)
                except:
                    pass
            #print pix_symbol, pos_x
            pos_x -= (min(pos_x) + max(pos_x)) / 2.0
            pos_y -= (min(pos_y) + max(pos_y)) / 2.0
            pos_z -= (min(pos_z) + max(pos_z)) / 2.0

            output = MagSLD(pos_x, pos_y, pos_z, sld_n, sld_mx, sld_my, sld_mz)
            #output.set_sldms(0, 0, 0)
            output.filename = os.path.basename(path)
            output.set_pix_type('atom')
            output.set_pixel_symbols(pix_symbol)
            output.set_nodes()
            output.sld_unit = 'A'
            return output
        except:
            RuntimeError, "%s is not a sld file" % path

    def write(self, path, data):
        """
        Write
        """
        #Not implemented 
        print "Not implemented... "

class SLDReader:
    """
    Class to load ascii files (7 columns).
    """
    ## File type
    type_name = "SLD ASCII"
    
    ## Wildcards
    type = ["sld files (*.SLD, *.sld)|*.sld",
            "txt files (*.TXT, *.txt)|*.txt"]
    ## List of allowed extensions
    ext = ['.txt', '.TXT', '.sld', 'SLD', '.*']
    
    def read(self, path):
        """
        Load data file
        
        :param path: file path
        
        :return MagSLD: x, y, z, sld_n, sld_mx, sld_my, sld_mz
        
        :raise RuntimeError: when the file can't be opened
        :raise ValueError: when the length of the data vectors are inconsistent
        """
        pos_x = numpy.zeros(0)
        pos_y = numpy.zeros(0)
        pos_z = numpy.zeros(0)
        sld_n = numpy.zeros(0)
        sld_mx = numpy.zeros(0)
        sld_my = numpy.zeros(0)
        sld_mz = numpy.zeros(0)
        try:
            input_f = open(path, 'rb')
            buff = input_f.read()
            lines = buff.split('\n')
            input_f.close()
            for line in lines:
                toks = line.split()
                try:
                    _pos_x = float(toks[0])
                    _pos_y = float(toks[1])
                    _pos_z = float(toks[2])
                    _sld_n = float(toks[3])
                    _sld_mx = float(toks[4])
                    _sld_my = float(toks[5])
                    _sld_mz = float(toks[6])

                    pos_x = numpy.append(pos_x, _pos_x)
                    pos_y = numpy.append(pos_y, _pos_y)
                    pos_z = numpy.append(pos_z, _pos_z)
                    sld_n = numpy.append(sld_n, _sld_n)
                    sld_mx = numpy.append(sld_mx, _sld_mx)
                    sld_my = numpy.append(sld_my, _sld_my)
                    sld_mz = numpy.append(sld_mz, _sld_mz)
                except:
                    # Skip non-data lines
                    pass
            pos_x -= (min(pos_x) + max(pos_x)) / 2.0
            pos_y -= (min(pos_y) + max(pos_y)) / 2.0
            pos_z -= (min(pos_z) + max(pos_z)) / 2.0

            output = MagSLD(pos_x, pos_y, pos_z, sld_n, sld_mx, sld_my, sld_mz)
            output.filename = os.path.basename(path)
            output.set_pix_type('pixel')
            output.set_pixel_symbols('pixel')
            return output
        except:
            RuntimeError, "%s is not a sld file" % path
        
    def write(self, path, data):
        """
        Write sld file
        
        :Param path: file path 
        :Param data: MagSLD data object
        """
        if path == None:
            raise ValueError, "Missing the file path."
        if data == None:
            raise ValueError, "Missing the data to save."
        
        x_val = data.pos_x
        y_val = data.pos_y
        z_val = data.pos_z
        
        length = len(x_val)
        
        sld_n = data.sld_n
        if sld_n == None:
            sld_n = numpy.zerros(length)
            
        sld_mx = data.sld_mx
        if sld_mx == None:
            sld_mx = numpy.zerros(length)
            sld_my = numpy.zerros(length)
            sld_mz = numpy.zerros(length)
        else:
            sld_my = data.sld_my
            sld_mz = data.sld_mz
            
        out = open(path, 'w')
        # First Line: Column names
        out.write("X  Y  Z  SLDN  SLDMx  SLDMy  SLDMz")
        for ind in range(length):
            out.write("\n%g  %g  %g  %g  %g  %g  %g" % (x_val[ind], y_val[ind], 
                                                    z_val[ind], sld_n[ind], 
                                                    sld_mx[ind], sld_my[ind], 
                                                    sld_mz[ind]))  
        out.close()       
            
            
class OMFData:
    """
    OMF Data.
    """
    _meshunit = "A"
    _valueunit = "A^(-2)"
    def __init__(self):
        """
        Init for mag SLD
        """
        self.filename = 'default'
        self.oommf = ''
        self.title = ''
        self.desc = ''
        self.meshtype = ''
        self.meshunit = self._meshunit
        self.valueunit = self._valueunit
        self.xbase = 0.0
        self.ybase = 0.0
        self.zbase = 0.0
        self.xstepsize = 6.0
        self.ystepsize = 6.0
        self.zstepsize = 6.0
        self.xnodes = 10.0
        self.ynodes = 10.0
        self.znodes = 10.0
        self.xmin = 0.0
        self.ymin = 0.0
        self.zmin = 0.0
        self.xmax = 60.0
        self.ymax = 60.0
        self.zmax = 60.0
        self.mx = None
        self.my = None
        self.mz = None
        self.valuemultiplier = 1.
        self.valuerangeminmag = 0
        self.valuerangemaxmag = 0
        
    def __str__(self):
        """
        doc strings
        """
        _str =  "Type:            %s\n" % self.__class__.__name__
        _str += "File:            %s\n" % self.filename
        _str += "OOMMF:           %s\n" % self.oommf
        _str += "Title:           %s\n" % self.title
        _str += "Desc:            %s\n" % self.desc
        _str += "meshtype:        %s\n" % self.meshtype
        _str += "meshunit:        %s\n" % str(self.meshunit)
        _str += "xbase:           %s [%s]\n" % (str(self.xbase), self.meshunit)
        _str += "ybase:           %s [%s]\n" % (str(self.ybase), self.meshunit)
        _str += "zbase:           %s [%s]\n" % (str(self.zbase), self.meshunit)
        _str += "xstepsize:       %s [%s]\n" % (str(self.xstepsize), 
                                                self.meshunit)
        _str += "ystepsize:       %s [%s]\n" % (str(self.ystepsize), 
                                                self.meshunit)
        _str += "zstepsize:       %s [%s]\n" % (str(self.zstepsize), 
                                                self.meshunit)
        _str += "xnodes:          %s\n" % str(self.xnodes)
        _str += "ynodes:          %s\n" % str(self.ynodes)
        _str += "znodes:          %s\n" % str(self.znodes)
        _str += "xmin:            %s [%s]\n" % (str(self.xmin), self.meshunit)
        _str += "ymin:            %s [%s]\n" % (str(self.ymin), self.meshunit)
        _str += "zmin:            %s [%s]\n" % (str(self.zmin), self.meshunit)
        _str += "xmax:            %s [%s]\n" % (str(self.xmax), self.meshunit)
        _str += "ymax:            %s [%s]\n" % (str(self.ymax), self.meshunit)
        _str += "zmax:            %s [%s]\n" % (str(self.zmax), self.meshunit)
        _str += "valueunit:       %s\n" % self.valueunit
        _str += "valuemultiplier: %s\n" % str(self.valuemultiplier)
        _str += "ValueRangeMinMag:%s [%s]\n" % (str(self.valuerangeminmag), 
                                                 self.valueunit)
        _str += "ValueRangeMaxMag:%s [%s]\n" % (str(self.valuerangemaxmag), 
                                                 self.valueunit)
        return _str
    
    def set_m(self, mx, my, mz):
        """
        Set the Mx, My, Mz values
        """
        self.mx = mx
        self.my = my
        self.mz = mz
               
class MagSLD:
    """
    Magnetic SLD.
    """
    pos_x = None
    pos_y = None
    pos_z = None
    sld_n = None
    sld_mx = None
    sld_my = None
    sld_mz = None
    # Units
    _pos_unit = 'A'
    _sld_unit = '1/A^(2)'
    _pix_type = 'pixel'
    
    def __init__(self, pos_x, pos_y, pos_z, sld_n=None, 
                 sld_mx=None, sld_my=None, sld_mz=None):
        """
        Init for mag SLD
        :params : All should be numpy 1D array
        """
        self.is_data = True
        self.filename = ''
        self.xstepsize = 6.0
        self.ystepsize = 6.0
        self.zstepsize = 6.0
        self.xnodes = 10.0
        self.ynodes = 10.0
        self.znodes = 10.0
        self.has_stepsize = False
        self.pos_unit = self._pos_unit
        self.sld_unit = self._sld_unit
        self.pix_type = 'pixel'
        self.pos_x = pos_x
        self.pos_y = pos_y
        self.pos_z = pos_z
        self.sld_n = sld_n
        self.sld_mx = sld_mx
        self.sld_my = sld_my
        self.sld_mz = sld_mz
        self.sld_m = None
        self.sld_phi = None
        self.sld_theta = None
        self.pix_symbol = None
        if sld_mx != None and sld_my != None and sld_mz != None:
            self.set_sldms(sld_mx, sld_my, sld_mz)
        self.set_nodes()
                   
    def __str__(self):
        """
        doc strings
        """
        _str =  "Type:       %s\n" % self.__class__.__name__
        _str += "File:       %s\n" % self.filename
        _str += "Axis_unit:  %s\n" % self.pos_unit
        _str += "SLD_unit:   %s\n" % self.sld_unit
        return _str
    
    def set_pix_type(self, pix_type):
        """
        Set pixel type
        :Param pix_type: string, 'pixel' or 'atom'
        """
        self.pix_type = pix_type
        
    def set_sldn(self, sld_n):
        """
        Sets neutron SLD
        """
        if sld_n.__class__.__name__ == 'float':
            if self.is_data:
                # For data, put the value to only the pixels w non-zero M 
                is_nonzero = (numpy.fabs(self.sld_mx) + 
                                  numpy.fabs(self.sld_my) + 
                                  numpy.fabs(self.sld_mz)).nonzero() 
                self.sld_n = numpy.zeros(len(self.pos_x))
                if len(self.sld_n[is_nonzero]) > 0:
                    self.sld_n[is_nonzero] = sld_n
                else:
                    self.sld_n.fill(sld_n)
            else:
                # For non-data, put the value to all the pixels
                self.sld_n = numpy.ones(len(self.pos_x)) * sld_n
        else:
            self.sld_n = sld_n
           
    def set_sldms(self, sld_mx, sld_my, sld_mz):
        """
        Sets (|m|, m_theta, m_phi)
        """
        if sld_mx.__class__.__name__ == 'float':
            self.sld_mx = numpy.ones(len(self.pos_x)) * sld_mx
        else:
            self.sld_mx = sld_mx
        if sld_my.__class__.__name__ == 'float':
            self.sld_my = numpy.ones(len(self.pos_x)) * sld_my
        else:
            self.sld_my = sld_my
        if sld_mz.__class__.__name__ == 'float':
            self.sld_mz = numpy.ones(len(self.pos_x)) * sld_mz
        else:
            self.sld_mz = sld_mz

        sld_m = numpy.sqrt(sld_mx * sld_mx + sld_my * sld_my + \
                                sld_mz * sld_mz)  
        self.sld_m = sld_m
    
    def set_pixel_symbols(self, symbol='pixel'):  
        """
        Set pixel
        :Params pixel: str; pixel or atomic symbol, or array of strings
        """
        if self.sld_n == None:
            return
        if symbol.__class__.__name__ == 'str':
            self.pix_symbol = numpy.repeat(symbol, len(self.sld_n))
        else:
            self.pix_symbol = symbol

    def get_sldn(self):
        """
        Returns nuclear sld
        """
        return self.sld_n
    
    def get_sld_mxyz(self):
        """
        Returns (sld_mx, sldmy, sld_mz)
        """
        return (self.sld_mx, self.sldmy, self.sld_mz)
    
    def get_sld_m(self):
        """
        Returns (sldm, sld_theta, sld_phi)
        """
        return (self.sldm, self.sld_theta, self.sld_phi)
    
    def set_nodes(self):
        """
        Set xnodes, ynodes, and znodes
        """
        self.set_stepsize()
        if self.pix_type == 'pixel':
            try:
                xdist = (max(self.pos_x) - min(self.pos_x)) / self.xstepsize
                ydist = (max(self.pos_y) - min(self.pos_y)) / self.ystepsize
                zdist = (max(self.pos_z) - min(self.pos_z)) / self.zstepsize
                self.xnodes = int(xdist) + 1
                self.ynodes = int(ydist) + 1
                self.znodes = int(zdist) + 1
            except:
                self.xnodes = None
                self.ynodes = None
                self.znodes = None
        else:
            self.xnodes = None
            self.ynodes = None
            self.znodes = None
        
    def set_stepsize(self):
        """
        Set xtepsize, ystepsize, and zstepsize
        """
        if self.pix_type == 'pixel':
            try:
                xpos_pre = self.pos_x[0]
                ypos_pre = self.pos_y[0]
                zpos_pre = self.pos_z[0]
                for x_pos in self.pos_x:
                    if xpos_pre != x_pos:
                        self.xstepsize = numpy.fabs(x_pos - xpos_pre)
                        break
                for y_pos in self.pos_y:
                    if ypos_pre != y_pos:
                        self.ystepsize = numpy.fabs(y_pos - ypos_pre)
                        break
                for z_pos in self.pos_z:
                    if zpos_pre != z_pos:
                        self.zstepsize = numpy.fabs(z_pos - zpos_pre)
                        break
                self.has_stepsize = True
            except:
                self.xstepsize = None
                self.ystepsize = None
                self.zstepsize = None
                self.has_stepsize = False
        else:
            self.xstepsize = None
            self.ystepsize = None
            self.zstepsize = None
            self.has_stepsize = True
        return self.xstepsize, self.ystepsize, self.zstepsize

    
def test_load():
    from danse.common.plottools.arrow3d import Arrow3D
    import os
    dir = os.path.abspath(os.path.curdir)
    print dir
    for i in range(6):
        dir, _ = os.path.split(dir)
        tfile = os.path.join(dir, "test", "CoreXY_ShellZ.txt")
        ofile = os.path.join(dir, "test", "A_Raw_Example-1.omf")
        if os.path.isfile(tfile):
            tfpath = tfile
            ofpath = ofile
            break
    reader = SLDReader()
    oreader = OMFReader()
    output = reader.read(tfpath)
    ooutput = oreader.read(ofpath)
    foutput = OMF2SLD()
    foutput.set_data(ooutput)

    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d import Axes3D
    fig = plt.figure()
    ax = fig.gca(projection='3d')
    ax.plot(output.pos_x, output.pos_y, output.pos_z, '.', c="g", 
            alpha = 0.7, markeredgecolor='gray',rasterized=True)
    gap = 7
    max_mx = max(output.sld_mx)
    max_my = max(output.sld_my)
    max_mz = max(output.sld_mz)
    max_m = max(max_mx,max_my,max_mz)
    x2 = output.pos_x+output.sld_mx/max_m * gap
    y2 = output.pos_y+output.sld_my/max_m * gap
    z2 = output.pos_z+output.sld_mz/max_m * gap
    x_arrow = numpy.column_stack((output.pos_x,x2))
    y_arrow = numpy.column_stack((output.pos_y,y2))
    z_arrow = numpy.column_stack((output.pos_z,z2))
    unit_x2 = output.sld_mx / max_m
    unit_y2 = output.sld_my / max_m
    unit_z2 = output.sld_mz / max_m
    color_x = numpy.fabs(unit_x2 * 0.8)
    color_y = numpy.fabs(unit_y2 * 0.8)
    color_z = numpy.fabs(unit_z2 * 0.8)
    colors =  numpy.column_stack((color_x, color_y, color_z))
    a = Arrow3D(None, x_arrow,y_arrow,z_arrow, colors, mutation_scale=10, lw=1, 
                arrowstyle="->", color="y", alpha = 0.5)

    ax.add_artist(a)
    plt.show()
    
def test():
    import os
    dir = os.path.abspath(os.path.curdir)
    for i in range(3):
        dir, _ = os.path.split(dir)
        #tfile = os.path.join(dir, "test", "C_Example_Converted.txt")
        ofile = os.path.join(dir, "test", "A_Raw_Example-1.omf")
        if os.path.isfile(ofile):
            #tfpath = tfile
            ofpath = ofile
            break
    #reader = SLDReader()
    oreader = OMFReader()
    #output = reader.read(tfpath)
    ooutput = oreader.read(ofpath)
    foutput = OMF2SLD() 
    foutput.set_data(ooutput)  
    writer =  SLDReader() 
    writer.write(os.path.join(os.path.dirname(ofpath), "out.txt"), 
                 foutput.output)
    model = GenSAS()
    model.set_sld_data(foutput.output) 
    x = numpy.arange(1000)/10000. + 1e-5
    y = numpy.arange(1000)/10000. + 1e-5
    z = numpy.arange(1000)/10000. + 1e-5
    i = numpy.zeros(1000)
    out = model.runXY([x,y,i])
        
if __name__ == "__main__": 
    #test()
    test_load()
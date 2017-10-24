# global
import os
import sys
import sasmodels

from PyQt4 import QtGui, QtCore
from sas.qtgui.Perspectives.Fitting.UI.GPUOptionsUI import Ui_GPUOptions

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s

try:
    _encoding = QtGui.QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig)


class GPUOptions(QtGui.QDialog, Ui_GPUOptions):
    """
    OpenCL Dialog to modify the OpenCL options
    """

    clicked = False
    checkBoxes = None
    sas_open_cl = None

    def __init__(self, parent=None):
        super(GPUOptions, self).__init__(parent)
        self.parent = parent
        self.setupUi(self)
        self.addOpenCLOptions()
        self.createLinks()

    def addOpenCLOptions(self):
        """
        Populate the window with a list of OpenCL options
        """
        # Get list of openCL options and add to GUI
        cl_tuple = _get_clinfo()
        i = 0
        self.sas_open_cl = os.environ.get("SAS_OPENCL", "")
        self.checkBoxes = []
        for title, descr in cl_tuple:
            checkBox = QtGui.QCheckBox(self.openCLCheckBoxGroup)
            checkBox.setGeometry(20, 20 + i, 351, 30)
            checkBox.setObjectName(_fromUtf8(descr))
            checkBox.setText(_translate("GPUOptions", descr, None))
            if (descr == self.sas_open_cl) or (title == "None" and not self.clicked):
                checkBox.click()
                self.clicked = True
            self.checkBoxes.append(checkBox)
            # Expand group and shift items down as more are added
            self.openCLCheckBoxGroup.resize(391, 60 + i)
            self.okButton.setGeometry(QtCore.QRect(20, 90 + i, 93, 28))
            self.resetButton.setGeometry(QtCore.QRect(120, 90 + i, 93, 28))
            self.testButton.setGeometry(QtCore.QRect(220, 90 + i, 93, 28))
            self.helpButton.setGeometry(QtCore.QRect(320, 90 + i, 93, 28))
            self.resize(440, 130 + i)
            i += 30

    def createLinks(self):
        """
        Link actions to function calls
        """
        self.testButton.clicked.connect(lambda: self.testButtonClicked())
        self.helpButton.clicked.connect(lambda: self.helpButtonClicked())
        self.openCLCheckBoxGroup.clicked.connect(lambda: self.checked())

    def checked(self):
        """
        Action triggered when box is selected
        """
        selected_box = None
        for box in self.checkBoxes:
            if box.isChecked() and box.getText() != self.sas_open_cl:
                selected_box = box
            else:
                box.setChecked(False)
        if selected_box.getText():
            self.sas_open_cl = self.option_button[selected_box.title]
        else:
            self.sas_open_cl = None

    def testButtonClicked(self):
        """
        Run the model tests when the test button is clicked
        """
        pass

    def helpButtonClicked(self):
        """
        Open the help menu when the help button is clicked
        """
        pass

    def reject(self):
        """
        Close the window without modifying SAS_OPENCL
        """
        self.close()
        self.parent.gpu_options_widget = GPUOptions(self)
        self.open()

    def accept(self):
        """
        Close the window after modifying the SAS_OPENCL value
        """
        # If statement added to handle Reset
        if self.sas_open_cl:
            os.environ["SAS_OPENCL"] = self.sas_open_cl
        else:
            if "SAS_OPENCL" in os.environ:
                del os.environ["SAS_OPENCL"]

        # Sasmodels kernelcl doesn't exist when initiated with None
        if 'sasmodels.kernelcl' in sys.modules:
            sasmodels.kernelcl.ENV = None

        reload(sasmodels.core)
        super(GPUOptions, self).accept()

    def closeEvent(self, event):
        """
        Overwrite QDialog close method to allow for custom widget close
        """
        self.reject()


def _get_clinfo():
    """
    Reading in information about available OpenCL infrastructure
    :return:
    """
    clinfo = []
    platforms = []
    try:
        import pyopencl as cl
        platforms = cl.get_platforms()
    except ImportError:
        print("pyopencl import failed. Using only CPU computations")

    p_index = 0
    for platform in platforms:
        d_index = 0
        devices = platform.get_devices()
        for device in devices:
            if len(devices) > 1 and len(platforms) > 1:
                combined_index = ":".join([str(p_index), str(d_index)])
            elif len(platforms) > 1:
                combined_index = str(p_index)
            else:
                combined_index = str(d_index)
            clinfo.append((combined_index, ":".join([platform.name, device.name])))
            d_index += 1
        p_index += 1

    clinfo.append(("None", "No OpenCL"))
    return clinfo

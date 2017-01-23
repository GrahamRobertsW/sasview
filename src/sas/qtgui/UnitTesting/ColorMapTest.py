import sys
import unittest
import numpy

from PyQt4 import QtGui
from mock import MagicMock
import matplotlib as mpl

# set up import paths
import path_prepare

from sas.sasgui.guiframe.dataFitting import Data2D
import sas.qtgui.Plotter2D as Plotter2D
from UnitTesting.TestUtils import WarningTestNotImplemented

# Local
from sas.qtgui.ColorMap import ColorMap

app = QtGui.QApplication(sys.argv)

class ColorMapTest(unittest.TestCase):
    '''Test the ColorMap'''
    def setUp(self):
        '''Create the ColorMap'''
        self.plotter = Plotter2D.Plotter2D(None, quickplot=True)

        self.data = Data2D(image=[0.1]*4,
                           qx_data=[1.0, 2.0, 3.0, 4.0],
                           qy_data=[10.0, 11.0, 12.0, 13.0],
                           dqx_data=[0.1, 0.2, 0.3, 0.4],
                           dqy_data=[0.1, 0.2, 0.3, 0.4],
                           q_data=[1,2,3,4],
                           xmin=-1.0, xmax=5.0,
                           ymin=-1.0, ymax=15.0,
                           zmin=-1.0, zmax=20.0)

        self.data.title="Test data"
        self.data.id = 1
        self.widget = ColorMap(parent=self.plotter, data=self.data)

    def tearDown(self):
        '''Destroy the GUI'''
        self.widget.close()
        self.widget = None

    def testDefaults(self):
        '''Test the GUI in its default state'''
        self.assertIsInstance(self.widget, QtGui.QDialog)

        self.assertEqual(self.widget._cmap_orig, "jet")
        self.assertEqual(len(self.widget.all_maps), 144)
        self.assertEqual(len(self.widget.maps), 72)
        self.assertEqual(len(self.widget.rmaps), 72)

        self.assertEqual(self.widget.lblWidth.text(), "0")
        self.assertEqual(self.widget.lblHeight.text(), "0")
        self.assertEqual(self.widget.lblQmax.text(), "15.8")
        self.assertEqual(self.widget.lblStopRadius.text(), "-1")
        self.assertFalse(self.widget.chkReverse.isChecked())
        self.assertEqual(self.widget.cbColorMap.count(), 72)
        self.assertEqual(self.widget.cbColorMap.currentIndex(), 60)

        # validators
        self.assertIsInstance(self.widget.txtMinAmplitude.validator(), QtGui.QDoubleValidator)
        self.assertIsInstance(self.widget.txtMaxAmplitude.validator(), QtGui.QDoubleValidator)

    def testOnReset(self):
        '''Check the dialog reset function'''
        # Set some controls to non-default state
        self.widget.cbColorMap.setCurrentIndex(20)
        self.widget.chkReverse.setChecked(True)
        self.widget.txtMinAmplitude.setText("20.0")

        # Reset the widget state
        self.widget.onReset()

        # Assure things went back to default
        self.assertEqual(self.widget.cbColorMap.currentIndex(), 20)
        self.assertFalse(self.widget.chkReverse.isChecked())
        self.assertEqual(self.widget.txtMinAmplitude.text(), "")

    def testInitMapCombobox(self):
        '''Test the combo box initializer'''
        # Set a color map from the direct list
        self.widget._cmap = "gnuplot"
        self.widget.initMapCombobox()

        # Check the combobox
        self.assertEqual(self.widget.cbColorMap.currentIndex(), 55)
        self.assertFalse(self.widget.chkReverse.isChecked())

        # Set a reversed value
        self.widget._cmap = "hot_r"
        self.widget.initMapCombobox()
        # Check the combobox
        self.assertEqual(self.widget.cbColorMap.currentIndex(), 56)
        self.assertTrue(self.widget.chkReverse.isChecked())


    def testOnMapIndexChange(self):
        '''Test the response to the combo box index change'''

        self.widget.canvas.draw = MagicMock()
        mpl.colorbar.ColorbarBase = MagicMock()

        # simulate index change
        self.widget.cbColorMap.setCurrentIndex(1)

        # Check that draw() got called
        self.assertTrue(self.widget.canvas.draw.called)
        self.assertTrue(mpl.colorbar.ColorbarBase.called)

    def testOnColorMapReversed(self):
        '''Test reversing the color map functionality'''
        # Check the defaults
        self.assertEqual(self.widget._cmap, "jet")
        self.widget.cbColorMap.addItems = MagicMock()

        # Reverse the choice
        self.widget.onColorMapReversed(True)

        # check the behaviour
        self.assertEqual(self.widget._cmap, "jet_r")
        self.assertTrue(self.widget.cbColorMap.addItems.called)

    def testOnAmplitudeChange(self):
        '''Check the callback method for responding to changes in textboxes'''
        self.widget.canvas.draw = MagicMock()
        mpl.colors.Normalize = MagicMock()
        mpl.colorbar.ColorbarBase = MagicMock()

        self.widget.vmin = 0.0
        self.widget.vmax = 100.0

        # good values in fields
        self.widget.txtMinAmplitude.setText("1.0")
        self.widget.txtMaxAmplitude.setText("10.0")

        self.widget.onAmplitudeChange()

        # Check the arguments to Normalize
        mpl.colors.Normalize.assert_called_with(vmin=1.0, vmax=10.0)
        self.assertTrue(self.widget.canvas.draw.called)

        # Bad values in fields
        self.widget.txtMinAmplitude.setText("cake")
        self.widget.txtMaxAmplitude.setText("more cake")

        self.widget.onAmplitudeChange()

        # Check the arguments to Normalize - should be defaults
        mpl.colors.Normalize.assert_called_with(vmin=0.0, vmax=100.0)
        self.assertTrue(self.widget.canvas.draw.called)


if __name__ == "__main__":
    unittest.main()

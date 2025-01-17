# Copyright 2019 TerraPower, LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
Test the fission product module to ensure all FP are available.
"""
import unittest

from armi import nuclideBases
from armi.reactor.flags import Flags

from armi.physics.neutronics.fissionProductModel import fissionProductModel
from armi.reactor.tests.test_reactors import (
    buildOperatorOfEmptyHexBlocks,
    loadTestReactor,
)
from armi.physics.neutronics.fissionProductModel.tests import test_lumpedFissionProduct
from armi.physics.neutronics.isotopicDepletion.isotopicDepletionInterface import (
    isDepletable,
)


class TestFissionProductModelLumpedFissionProducts(unittest.TestCase):
    """
    Tests the fission product model interface behavior when lumped fission products are enabled.

    Notes
    -----
    This loads the global fission products from a file stream.
    """

    def setUp(self):
        o = buildOperatorOfEmptyHexBlocks()
        o.removeAllInterfaces()
        self.fpModel = fissionProductModel.FissionProductModel(o.r, o.cs)
        o.addInterface(self.fpModel)

        # Load the fission products from a file stream.
        dummyLFPs = test_lumpedFissionProduct.getDummyLFPFile()
        self.fpModel.setGlobalLumpedFissionProducts(dummyLFPs.createLFPsFromFile())

        # Set up the global LFPs and check that they are setup.
        self.fpModel.interactBOL()
        self.assertTrue(self.fpModel._useGlobalLFPs)

    def test_loadGlobalLFPsFromFile(self):
        """Tests that loading lumped fission products from a file."""
        self.assertEqual(len(self.fpModel._globalLFPs), 3)
        lfps = self.fpModel.getGlobalLumpedFissionProducts()
        self.assertIn("LFP39", lfps)

    def test_getAllFissionProductNames(self):
        """Tests retrieval of the fission product names within all the lumped fission products of the core."""
        fissionProductNames = self.fpModel.getAllFissionProductNames()
        self.assertGreater(len(fissionProductNames), 5)
        self.assertIn("XE135", fissionProductNames)


class TestFissionProductModelExplicitMC2Library(unittest.TestCase):
    """
    Tests the fission product model interface behavior when explicit fission products are enabled.
    """

    def setUp(self):
        o, r = loadTestReactor(
            customSettings={
                "fpModel": "explicitFissionProducts",
                "fpModelLibrary": "MC2-3",
            }
        )
        self.r = r
        self.fpModel = fissionProductModel.FissionProductModel(o.r, o.cs)
        # Set up the global LFPs and check that they are setup.
        self.assertFalse(self.fpModel._useGlobalLFPs)

    def test_nuclideFlags(self):
        """Test that the nuclide flags contain the set of MC2-3 modeled nuclides."""
        # Run the ``interactBOL`` here to trigger setting up the fission
        # products in the reactor data model.
        self.fpModel.interactBOL()

        for nb in nuclideBases.byMcc3Id.values():
            self.assertIn(nb.name, self.r.blueprints.nuclideFlags.keys())

    def test_nuclidesInModelFuel(self):
        """Test that the fuel blocks contain all the MC2-3 modeled nuclides."""
        # Run the ``interactBOL`` here to trigger setting up the fission
        # products in the reactor data model.
        self.fpModel.interactBOL()

        b = self.r.core.getFirstBlock(Flags.FUEL)
        nuclideList = b.getNuclides()
        for nb in nuclideBases.byMcc3Id.values():
            self.assertIn(nb.name, nuclideList)

    def test_nuclidesInModelAllDepletableBlocks(self):
        """Test that the depletable blocks contain all the MC2-3 modeled nuclides."""

        # Check that there are some fuel and control blocks in the core model.
        fuelBlocks = self.r.core.getBlocks(Flags.FUEL)
        controlBlocks = self.r.core.getBlocks(Flags.CONTROL)
        self.assertGreater(len(fuelBlocks), 0)
        self.assertGreater(len(controlBlocks), 0)

        # Force the the first component in the control blocks
        # to be labeled as depletable for checking that explicit
        # fission products can be assigned.
        for b in controlBlocks:
            c = b.getComponents()[0]
            c.p.flags |= Flags.DEPLETABLE

        # Run the ``interactBOL`` here to trigger setting up the fission
        # products in the reactor data model.
        self.fpModel.interactBOL()

        # Check that the depletable blocks have all explicit
        # fission products in them.
        for b in self.r.core.getBlocks():
            nuclideList = b.getNuclides()
            if isDepletable(b):
                for nb in nuclideBases.byMcc3Id.values():
                    self.assertIn(nb.name, nuclideList)
            else:
                self.assertLess(len(b.getNuclides()), len(nuclideBases.byMcc3Id))


if __name__ == "__main__":
    # import sys;sys.argv = ['', 'Test.testName']
    unittest.main()

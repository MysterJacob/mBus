#!/bin/env python3
from logging import exception
import unittest
from mbus import InvalidRailNameException, RailAlreadyBoundException, RailExistsException, RailNotFoundExceptionException
from mbus import mbus

class mBusSingleton(unittest.TestCase):
    def test_getBus(self):
        self.assertIsNot(mbus, None)

    def test_tryImport(self):
        try: 
            from mbus import __mBusSingleton
        except ImportError:
            failed = True
        else:
            failed = False

        self.assertTrue(failed)

class mBusRail(unittest.TestCase):
    def test_registerRailNameFail(self):
        cases = ["!", "0name", "name!", "name.test", "test rail"]
        for case in cases:
            try:
                mbus.registerRail(case)
            except InvalidRailNameException:
                failed = True
            else:
                failed = False

            self.assertTrue(failed)

    def test_registerRailNameSuccess(self):
        cases = ["validname1", "anothervaildname", "testrail0", "vaild_rail"]
        for case in cases:
            try:
                mbus.registerRail(case)
            except InvalidRailNameException:
                failed = True
            else:
                failed = False

            self.assertFalse(failed)
            self.assertIn(case, mbus.getRails())

    def test_doubleRail(self):
        try:
            mbus.registerRail("rail1")
            mbus.registerRail("rail1")
        except RailExistsException:
            failed = True
        else:
            failed = False

        self.assertTrue(failed)

    def test_bindingRail(self):
        try:
            mbus.registerRail("rail2", bindToModule = True)
            mbus.registerRail("rail3", bindToModule = True)
        except RailAlreadyBoundException:
            failed = True
        else:
            failed = False

        self.assertFalse(failed)

        try:
            mbus.registerRail("rail4")
            mbus.registerRail("rail5")
        except RailAlreadyBoundException:
            failed = True
        else:
            failed = False

        self.assertFalse(failed)

        try:
            mbus.registerRail("rail6", bindToModule = True)
            mbus.bindModuleToRail("rail6")
        except RailAlreadyBoundException:
            failed = True
        else:
            failed = False

        self.assertTrue(failed)

        try:
            mbus.bindModuleToRail("sdjlganj")
        except RailNotFoundExceptionException:
            failed = True
        else:
            failed = False

        self.assertTrue(failed)

if __name__ == "__main__":
    unittest.main()

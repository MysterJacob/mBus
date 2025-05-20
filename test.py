#!/bin/env python3
import unittest
from mbus import (
    ModuleLoadingError,
)
from mbus import mbus, mbusModule

# import logging
# import sys
# logging.basicConfig(
#     level=logging.INFO,
#     format="%(asctime)s [%(levelname)s] %(message)s",
#     handlers=[logging.StreamHandler(sys.stdout)],
# )


class TestModule(mbusModule):
    name = "testModule"


class TestModule2(mbusModule):
    name = "testModule2"
    dependencies = {"testModule"}


class InvalidNameModule(mbusModule):
    name = "!!!!910232"


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


class mbusModules(unittest.TestCase):
    def test_simpleloading(self):
        mbus.loadModule(TestModule)
        self.assertTrue(mbus.isModuleLoaded("testModule"))
        mbus.unloadModule("testModule")

    def test_loadingqueue(self):
        mbus.loadModule(TestModule2)
        self.assertFalse(mbus.isModuleLoaded("testModule2"))
        mbus.loadModule(TestModule)
        self.assertTrue(mbus.isModuleLoaded("testModule"))
        self.assertTrue(mbus.isModuleLoaded("testModule2"))
        mbus.unloadModule("testModule")
        mbus.unloadModule("testModule2")

    def test_collision(self):
        exception = False
        try:
            mbus.loadModule(TestModule)
            mbus.loadModule(TestModule)
        except ModuleLoadingError:
            exception = True
        finally:
            mbus.unloadModule("testModule")

            self.assertTrue(exception)

    def testInvalidName(self):
        exception = False
        try:
            mbus.loadModule(InvalidNameModule)
        except ModuleLoadingError:
            exception = True

        self.assertTrue(exception)

class mbusGroups(unittest.TestCase):
    def test_creatingGroups(self):
        pass

    def test_creatingNestedGroups(self):
        pass

class mbusEndpoints(unittest.TestCase):
    def test_trigger(self):
        pass
    def test_event(self):
        pass
    def test_field(self):
        pass
    def test_action(self):
        pass


if __name__ == "__main__":
    unittest.main()

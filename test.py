#!/bin/env python3
import unittest
from mbus import (
    EndpointCreationError,
    GroupCreationError,
    ModuleLoadingError,
)
from mbus import mBus, mbusModule

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
        mbus = mBus()
        self.assertIsNot(mbus, None)

    def test_tryImport(self):
        m1 = mBus()
        m2 = mBus()

        self.assertIs(m1, m2)


class mbusModules(unittest.TestCase):
    def test_simpleloading(self):
        mbus = mBus()
        mbus.loadModule(TestModule)
        self.assertTrue(mbus.isModuleLoaded("testModule"))
        mbus.unloadModule("testModule")

    def test_loadingqueue(self):
        mbus = mBus()
        mbus.loadModule(TestModule2)
        self.assertFalse(mbus.isModuleLoaded("testModule2"))
        mbus.loadModule(TestModule)
        self.assertTrue(mbus.isModuleLoaded("testModule"))
        self.assertTrue(mbus.isModuleLoaded("testModule2"))
        mbus.unloadModule("testModule")
        mbus.unloadModule("testModule2")

    def test_collision(self):
        mbus = mBus()
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
            mbus = mBus()
            mbus.loadModule(InvalidNameModule)
        except ModuleLoadingError:
            exception = True

        self.assertTrue(exception)


class GroupTestModule(mbusModule):
    name = "groupTestModule"

    def load(self, mbus: mBus):
        group = self._createGroup("testGroup")
        group.createGroup("insider")


class GroupTestCollsionModule(mbusModule):
    name = "groupTestModule"

    def load(self, mbus: mBus):
        self._createGroup("collsion")
        self._createGroup("collsion")


class mbusGroups(unittest.TestCase):
    def test_addressExists(self):
        mbus = mBus()
        self.assertFalse(mbus.addressExisits(""))
        self.assertFalse(mbus.addressExisits("nonexistingModule"))

    def test_creatingGroups(self):
        mbus = mBus()
        mbus.loadModule(GroupTestModule)
        self.assertTrue(mbus.addressExisits("groupTestModule.testGroup"))
        self.assertTrue(
            mbus.addressExisits("groupTestModule.testGroup.insider")
        )

    def test_collision(self):
        mbus = mBus()
        exception = False
        try:
            mbus.loadModule(GroupTestCollsionModule)
        except GroupCreationError:
            exception = True
        finally:
            self.assertTrue(exception)


class TriggerCreatorModule(mbusModule):
    testTriggerValue = 0
    name = "tcm"

    def load(self, mbus: mBus):
        self._createEndpoint(
            endpointName="trigger",
            type="trigger",
            callback=self.callback,
        )
        self._createGroup("test").createEndpoint(
            endpointName="trigger",
            type="trigger",
            callback=self.callback,
        )

    def callback(self, x: int):
        TriggerCreatorModule.testTriggerValue += x
        return True


class EndpointCollisionModule(mbusModule):
    name = "ecm"

    def load(self, mbus: "mBus"):
        self._createEndpoint(
            endpointName="collsion",
            type="trigger",
            callback=lambda x: print(x),
        )
        self._createEndpoint(
            endpointName="collsion",
            type="trigger",
            callback=lambda x: print(x),
        )


# Trigger with multiple responders. Triggered with arguments. Arguments are loosely defined. Does not return any value.
class EventRegisterModule(mbusModule):
    name = "erm"
    dependencies = {"etm"}
    testValue = 1

    def load(self, mbus: "mBus"):
        mbus.addEventListener("etm.event", self.callback)

    def callback(self, *args, **kwargs):
        EventRegisterModule.testValue *= kwargs.get("mul", 2)


class EventTriggerModule(mbusModule):
    name = "etm"

    def load(self, mbus: "mBus"):
        self._createEndpoint(endpointName="event", type="event", responders=set())
        self._createEndpoint(endpointName="trigger", type="trigger", callback=self.callback)

    def callback(self, *args, **kwargs):
        self._callEvent("event")
        self._callEvent("event", mul=5)


class mbusEndpoints(unittest.TestCase):
    def test_collision(self):
        mbus = mBus()
        exception = False
        try:
            mbus.loadModule(EndpointCollisionModule)
        except EndpointCreationError:
            exception = True
        finally:
            self.assertTrue(exception)

    def test_trigger(self):
        mbus = mBus()
        mbus.loadModule(TriggerCreatorModule)
        self.assertTrue(mbus.addressExisits("tcm.trigger"))
        self.assertTrue(mbus.addressExisits("tcm.test.trigger"))

        self.assertTrue(mbus.fireTrigger("tcm.trigger", 1))
        self.assertEqual(TriggerCreatorModule.testTriggerValue, 1)
        self.assertTrue(mbus.fireTrigger("tcm.test.trigger", 10))
        self.assertEqual(TriggerCreatorModule.testTriggerValue, 11)

    def test_event(self):
        mbus = mBus()
        mbus.loadModule(EventRegisterModule)
        mbus.loadModule(EventTriggerModule)
        self.assertEqual(EventRegisterModule.testValue, 1)
        self.assertTrue(mbus.addressExisits("etm.event"))
        self.assertTrue(mbus.addressExisits("etm.trigger"))
        mbus.fireTrigger("etm.trigger")
        self.assertEqual(EventRegisterModule.testValue, 10)
        mbus.fireTrigger("etm.trigger")
        self.assertEqual(EventRegisterModule.testValue, 100)

    def test_field(self):
        pass

    def test_action(self):
        pass


if __name__ == "__main__":
    unittest.main()

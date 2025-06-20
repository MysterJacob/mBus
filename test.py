#!/bin/env python3
import asyncio
import unittest
from mbus import (
    EndpointCreationError,
    FieldValueTypeError,
    GroupCreationError,
    ModuleLoadingError,
)
from mbus import mBus, mbusModule

# import logging
# import sys
#
# logging.basicConfig(
#     level=logging.INFO,
#     format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
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

    def test_collision(self):
        mbus = mBus()
        mbus.loadModule(TestModule)
        self.assertRaises(
            ModuleLoadingError, lambda: mbus.loadModule(TestModule)
        )
        mbus.unloadModule("testModule")

    def testInvalidName(self):
        mbus = mBus()
        self.assertRaises(
            ModuleLoadingError, lambda: mbus.loadModule(InvalidNameModule)
        )


class GroupTestModule(mbusModule):
    name = "groupTestModule"

    def load(self):
        group = self._createGroup("testGroup")
        group.createGroup("insider")


class GroupTestCollsionModule(mbusModule):
    name = "groupCollisionModule"

    def load(self):
        self._createGroup("collision")
        self._createGroup("collision")


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
        self.assertRaises(
            GroupCreationError, lambda: mbus.loadModule(GroupTestCollsionModule)
        )


class TriggerCreatorModule(mbusModule):
    testTriggerValue = 0
    name = "tcm"

    def load(self):
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

    def load(self):
        self._createEndpoint(
            endpointName="collision",
            type="trigger",
            callback=lambda x: (x),
        )
        self._createEndpoint(
            endpointName="collision",
            type="trigger",
            callback=lambda x: (x),
        )


class EventRegisterModule(mbusModule):
    name = "erm"
    dependencies = {"etm"}
    testValue = 1

    def load(self):
        self.mbus.addEventListener("etm.event", self.callback)

    async def callback(self, *args, **kwargs):
        EventRegisterModule.testValue *= kwargs.get("mul", 2)


class EventTriggerModule(mbusModule):
    name = "etm"

    def load(self):
        self._createEndpoint(endpointName="event", type="event")
        self._createEndpoint(
            endpointName="trigger", type="trigger", callback=self.callback
        )

    def callback(self, *args, **kwargs):
        self._callEvent("event")
        self._callEvent("event", mul=5)
        self.safeWait(1)


class FieldTestModule(mbusModule):
    testValue = 0
    name = "ftm"

    def load(self):
        self._createEndpoint(
            endpointName="testField",
            type="field",
            fieldType=int,
            value=5,
            onChangeCallback=self.onChangeCallback,
        )
        self._createEndpoint(
            endpointName="tryset", type="trigger", callback=self.tryset
        )

    def tryset(self, x):
        self._setFieldValue("testField", x)

    def onChangeCallback(self, value):
        FieldTestModule.testValue = value


class mbusEndpoints(unittest.TestCase):
    def test_collision(self):
        mbus = mBus()
        self.assertRaises(
            EndpointCreationError,
            lambda: mbus.loadModule(EndpointCollisionModule),
        )

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
        mbus = mBus()
        mbus.loadModule(FieldTestModule)

        valueList = []
        mbus.addFieldChangeCallback("ftm.testField", valueList.append)

        self.assertTrue(mbus.addressExisits("ftm.testField"))

        mbus.fireTrigger("ftm.tryset", 20)

        self.assertEqual(mbus.getValue("ftm.testField"), 20)
        self.assertEqual(FieldTestModule.testValue, 20)
        self.assertEqual(valueList[-1], 20)

        self.assertRaises(
            FieldValueTypeError,
            lambda: mbus.fireTrigger("ftm.tryset", "tryset"),
        )


class TestLoadFromFile(unittest.TestCase):
    def test_loading(self):
        mbus = mBus()
        mbus.loadConfigFile("./testconfig.toml")
        mbus.loadModuleFromFile("testmodules.testmod")

        self.assertEqual(
            mbus.fireTrigger("testmod.testTrigger"), "value from test config"
        )


class dep1(mbusModule):
    name = "dep1"


class dep2(mbusModule):
    name = "dep2"
    dependencies = {"dep1"}


class TestUnloadingDependecies(unittest.TestCase):
    def test_unloading(self):
        mbus = mBus()
        mbus.loadModule(dep1)
        mbus.loadModule(dep2)
        self.assertTrue(mbus.isModuleLoaded("dep1"))
        self.assertTrue(mbus.isModuleLoaded("dep2"))
        mbus.unloadModule("dep1")
        self.assertFalse(mbus.isModuleLoaded("dep1"))
        self.assertFalse(mbus.isModuleLoaded("dep2"))


if __name__ == "__main__":
    unittest.main()

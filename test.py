#!/bin/env python3
import unittest
from mbus import BusException, GroupAlreadyExists, GroupNotFound, InvalidEnpointParameter, InvalidFieldValueType, InvalidGroupName, InvalidRailName, MissingArgumentException, MissingEndpointParameter, RailAlreadyBound, RailAlready, RailNotFound
from mbus import mbus
import random

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
            except InvalidRailName:
                failed = True
            else:
                failed = False

            self.assertTrue(failed)

    def test_registerRailNameSuccess(self):
        cases = ["validname1", "anothervaildname", "testrail0", "vaild_rail"]
        for case in cases:
            try:
                mbus.registerRail(case)
            except BusException:
                failed = True
            else:
                failed = False

            self.assertFalse(failed)
            self.assertIn(case, mbus.getRails())

    def test_doubleRail(self):
        try:
            mbus.registerRail("rail1")
            mbus.registerRail("rail1")
        except RailAlready:
            failed = True
        else:
            failed = False

        self.assertTrue(failed)

    def test_bindingRail(self):
        try:
            mbus.registerRail("rail2", bindToModule = True)
            mbus.registerRail("rail3", bindToModule = True)
        except BusException:
            failed = True
        else:
            failed = False

        self.assertFalse(failed)

        try:
            mbus.registerRail("rail4")
            mbus.registerRail("rail5")
        except BusException:
            failed = True
        else:
            failed = False

        self.assertFalse(failed)

        try:
            mbus.registerRail("rail6", bindToModule = True)
            mbus.bindModuleToRail("rail6")
        except RailAlreadyBound:
            failed = True
        else:
            failed = False

        self.assertTrue(failed)

        try:
            mbus.bindModuleToRail("sdjlganj")
        except RailNotFound:
            failed = True
        else:
            failed = False

        self.assertTrue(failed)

class mBusGroup(unittest.TestCase):
    def test_registerGroupNameFail(self):
        railName = "grouptestfail"
        mbus.registerRail(railName)
        cases = ["!", "0name", "name!", "name-test", "test group", "test_group"]
        for case in cases:
            try:
                mbus.createGroup(f"{railName}.{case}")
            except InvalidGroupName:
                failed = True
            else:
                failed = False

            self.assertTrue(failed, f"Failed on name {case}")

    def test_registerGroupNameSuccess(self):
        railName = "grouptestsuccess"
        mbus.registerRail(railName)
        cases = ["validname1", "anothervaildname", "testgroup0", "vaildgroup"]
        for case in cases:
            try:
                mbus.createGroup(f"{railName}.{case}")
                self.assertTrue(mbus.addressExists(f"{railName}.{case}"))
            except BusException:
                failed = True
            else:
                failed = False

            self.assertFalse(failed)

    def test_doubleGroup(self):
        railName = "grupDobule"
        mbus.registerRail(railName)
        try:
            mbus.createGroup(f"{railName}.double")
            mbus.createGroup(f"{railName}.double")
        except GroupAlreadyExists:
            failed = True
        else:
            failed = False

        self.assertTrue(failed)

    def test_groupNotFound(self):
        railName = "groupNotFound"
        mbus.registerRail(railName)
        try:
            mbus.createGroup(f"{railName}.notfound.test")
        except GroupNotFound:
            failed = True
        else:
            failed = False
        self.assertTrue(failed)

    def test_groupCascade(self):
        railName = "groupCascade"
        mbus.registerRail(railName)
        cascade = list("abcdefghijkl")
        try:
            for i in range(1, len(cascade)):
                mbus.createGroup(f"{railName}.{'.'.join(cascade[:i])}")
        except BusException:
            failed = True
        else:
            failed = False

        self.assertFalse(failed)

class TestGenericEndpoints(unittest.TestCase):
    def test_NonExistingAddress(self):
        railName = "nonexistingrail"
        address = f'{railName}'
        mbus.registerRail(railName)
        try:
            mbus.createEndpoint(address + '.nongroup', 'endpoint1', 'trigger')
        except GroupNotFound:
            failed = True
        else:
            failed = False

        self.assertTrue(failed)

    def test_InvalidEnpointTypes(self):
        railName = "genericFailEndpoints"
        groupName = "genericFailGroup"
        address = f'{railName}.{groupName}'
        mbus.registerRail(railName)
        mbus.createGroup(address)
        types = ['invalid1', 'test', 'Trigger']
        for endpointType in types:
            try:
                mbus.createEndpoint(address, 'endpoint1' + endpointType, endpointType)
            except BusException:
                failed = True
            else:
                failed = False

            self.assertTrue(failed)

# ------------------------------
#    Trigger
# ------------------------------
    def test_CreatingTrigger(self):
        railName = "creatingTrigger"
        groupName = "creatingTrigger"
        address = f'{railName}.{groupName}'
        mbus.registerRail(railName)
        mbus.createGroup(address)
        try:
            mbus.createEndpoint(
                address, 'testTrigger', 
                'trigger', responder = lambda x : x, arguments={"x" : int})
        except BusException:
            failed = True
        else:
            failed = False

        self.assertFalse(failed)

    def test_CreatingTriggerWithArgumentsInvalid(self):
        railName = "creatingTriggerWArgumentsI"
        groupName = "creatingTriggerWArgumentsI"
        address = f'{railName}.{groupName}'
        mbus.registerRail(railName)
        mbus.createGroup(address)
        try:
            mbus.createEndpoint(
                address, 'testTrigger', 
                'trigger', responder = lambda x : x, arguments={"x" : int}, invalid=1)
        except InvalidEnpointParameter:
            failed = True
        else:
            failed = False

        self.assertTrue(failed)

    def test_CreatingTriggerWithArgumentsMissing(self):
        railName = "creatingTriggerWArgumentsM"
        groupName = "creatingTriggerWArgumentsM"
        address = f'{railName}.{groupName}'
        mbus.registerRail(railName)
        mbus.createGroup(address)
        try:
            mbus.createEndpoint(address, 'testTrigger', 'trigger')
        except MissingEndpointParameter:
            failed = True
        else:
            failed = False

        self.assertTrue(failed)

# ------------------------------
#    Event
# ------------------------------
    def test_CreatingEvent(self):
        railName = "creatingEvent"
        groupName = "creatingEvent"
        address = f'{railName}.{groupName}'
        mbus.registerRail(railName)
        mbus.createGroup(address)
        try:
            mbus.createEndpoint(
                address, 'testEvent', 
                'event', responders = lambda x : x
            )
        except BusException:
            failed = True
        else:
            failed = False

        self.assertFalse(failed)

    def test_CreatingEventWithArgumentsInvalid(self):
        railName = "creatingEventWArgumentsI"
        groupName = "creatingEventWArgumentsI"
        address = f'{railName}.{groupName}'
        mbus.registerRail(railName)
        mbus.createGroup(address)
        try:
            mbus.createEndpoint(
                address, 'testEvent', 
                'event', responders = lambda x : x, invalid=1)
        except InvalidEnpointParameter:
            failed = True
        else:
            failed = False

        self.assertTrue(failed)

    def test_CreatingEventWithArgumentsMissing(self):
        railName = "creatingEventWArgumentsM"
        groupName = "creatingEventWArgumentsM"
        address = f'{railName}.{groupName}'
        mbus.registerRail(railName)
        mbus.createGroup(address)
        try:
            mbus.createEndpoint(address, 'testEvent', 'event')
        except MissingEndpointParameter:
            failed = True
        else:
            failed = False

        self.assertTrue(failed)

# ------------------------------
#    Field
# ------------------------------
    def test_CreatingField(self):
        railName = "creatingField"
        groupName = "creatingField"
        address = f'{railName}.{groupName}'
        mbus.registerRail(railName)
        mbus.createGroup(address)
        try:
            mbus.createEndpoint(
                address, 'testField', 
                'field',
                type=int, value=0
            )
        except BusException:
            failed = True
        else:
            failed = False

        self.assertFalse(failed)

    def test_CreatingFieldWithArgumentsInvalid(self):
        railName = "creatingFieldWArgumentsI"
        groupName = "creatingFieldWArgumentsI"
        address = f'{railName}.{groupName}'
        mbus.registerRail(railName)
        mbus.createGroup(address)
        try:
            mbus.createEndpoint(
                address, 'testField', 
                'field', 
                type=int, value=0, invalid=1
            )
        except InvalidEnpointParameter:
            failed = True
        else:
            failed = False

        self.assertTrue(failed)

    def test_CreatingFieldWithArgumentsTypeInvalid(self):
        railName = "creatingFieldWArgumentsTI"
        groupName = "creatingFieldWArgumentsTI"
        address = f'{railName}.{groupName}'
        mbus.registerRail(railName)
        mbus.createGroup(address)
        try:
            mbus.createEndpoint(
                address, 'testField', 
                'field', 
                type=int, value="invalidInt"
            )
        except InvalidFieldValueType:
            failed = True
        else:
            failed = False

        self.assertTrue(failed)

    def test_CreatingFieldWithArgumentsMissing(self):
        railName = "creatingFieldWArgumentsM"
        groupName = "creatingFieldWArgumentsM"
        address = f'{railName}.{groupName}'
        mbus.registerRail(railName)
        mbus.createGroup(address)
        try:
            mbus.createEndpoint(address, 'testField', 'field')
        except MissingEndpointParameter:
            failed = True
        else:
            failed = False

        self.assertTrue(failed)

# ------------------------------
#    Action
# ------------------------------
    def test_CreatingAction(self):
        railName = "creatingAction"
        groupName = "creatingAction"
        address = f'{railName}.{groupName}'
        mbus.registerRail(railName)
        mbus.createGroup(address)
        try:
            mbus.createEndpoint(
                address, 'testAction', 
                'action', 
                responder = lambda x : x,
                arguments = {"arg1": int, "arg2": str},
                rtype = int
            )
        except BusException:
            failed = True
        else:
            failed = False

        self.assertFalse(failed)

    def test_CreatingActionWithArgumentsInvalid(self):
        railName = "creatingActionWArgumentsI"
        groupName = "creatingActionWArgumentsI"
        address = f'{railName}.{groupName}'
        mbus.registerRail(railName)
        mbus.createGroup(address)
        try:
            mbus.createEndpoint(
                address, 'testAction', 
                'action', 
                responder = lambda x : x,
                arguments = {"arg1": int, "arg2": str},
                rtype = int,
                invalid = 1
            )
        except InvalidEnpointParameter:
            failed = True
        else:
            failed = False

        self.assertTrue(failed)

    def test_CreatingActionWithArgumentsMissing(self):
        railName = "creatingActionWArgumentsM"
        groupName = "creatingActionWArgumentsM"
        address = f'{railName}.{groupName}'
        mbus.registerRail(railName)
        mbus.createGroup(address)
        try:
            mbus.createEndpoint(address, 'testAction', 'action')
        except MissingEndpointParameter:
            failed = True
        else:
            failed = False

        self.assertTrue(failed)

# ------------------------------
#    Fire trigger Sync
# ------------------------------
    def test_failFireTriggerSync(self):
        railName = "failFireTriggerSync"
        groupName = "failFireTriggerSync"
        address = f'{railName}.{groupName}'
        mbus.registerRail(railName)
        mbus.createGroup(address)

        value = [0]
        def testResponder(x : int):
            value[0] = x
            return True

        try:
            mbus.createEndpoint(
                address,
                'testTrigger',
                'trigger',
                arguments={"x" : int},
                responder=testResponder
            )

            mbus.fireTrigger(address + '.testTrigger')
        except MissingArgumentException:
            failed = True
        else:
            failed = False

        self.assertTrue(failed)

    def test_fireTriggerSync(self):
        railName = "fireTriggerSync"
        groupName = "fireTriggerSync"
        address = f'{railName}.{groupName}'
        mbus.registerRail(railName)
        mbus.createGroup(address)

        value = [0]
        def testResponder(x : int):
            value[0] = x
            return True

        try:
            mbus.createEndpoint(
                address,
                'testTrigger',
                'trigger',
                arguments={"x" : int},
                responder=testResponder
            )

            newValue = random.randint(0, 1023)
            result = mbus.fireTrigger(address + '.testTrigger', x = newValue)
            self.assertTrue(result)
            self.assertEqual(value[0], newValue)
        except BusException:
            failed = True
        else:
            failed = False

        self.assertFalse(failed)

# ------------------------------
#    Call event Sync
# ------------------------------
    def test_callEventSync(self):
        railName = "callEventSync"
        groupName = "callEventSync"
        address = f'{railName}.{groupName}'
        mbus.registerRail(railName)
        mbus.createGroup(address)

        value = [0]
        def testResponder(**kwargs):
            value[0] += kwargs.get("x", 1)
            return True

        try:
            mbus.createEndpoint(
                address,
                'testEvent',
                'event',
                responders=[testResponder, testResponder]
            )

            mbus.callEvent(address + '.testEvent')
            self.assertEqual(value[0], 2)

            newValue = random.randint(0, 1023)
            mbus.callEvent(address + '.testEvent', x = newValue)
            self.assertEqual(value[0], 2 + newValue * 2)

        except BusException:
            failed = True
        else:
            failed = False

        self.assertFalse(failed)

# ------------------------------
#    Set/Get field Sync
# ------------------------------
    def test_getSetFieldSync(self):
        railName = "setgetFieldSync"
        groupName = "callEventSync"
        address = f'{railName}.{groupName}'
        mbus.registerRail(railName)
        mbus.createGroup(address)

        try:
            mbus.createEndpoint(
                address,
                'testField',
                'field',
                type=int,
                value=0
            )

            self.assertEqual(mbus.getFieldValue(address + ".testField"), 0)
            for i in range(100):
                value = random.randint(0, 100)
                mbus.setFieldValue(address + ".testField", value)
                self.assertEqual(mbus.getFieldValue(address + ".testField"), value)

        except BusException:
            failed = True
        else:
            failed = False

        self.assertFalse(failed)

# ------------------------------
#    Call action Sync
# ------------------------------
    def test_callActionSync(self):
        railName = "callEventSync"
        groupName = "callEventSync"
        address = f'{railName}.{groupName}'
        mbus.registerRail(railName)
        mbus.createGroup(address)

        value = [0]
        def testResponder(**kwargs):
            value[0] += kwargs.get("x", 1)
            return True

        try:
            mbus.createEndpoint(
                address,
                'testEvent',
                'event',
                responders=[testResponder, testResponder]
            )

            mbus.callEvent(address + '.testEvent')
            self.assertEqual(value[0], 2)

            newValue = random.randint(0, 1023)
            mbus.callEvent(address + '.testEvent', x = newValue)
            self.assertEqual(value[0], 2 + newValue * 2)

        except BusException:
            failed = True
        else:
            failed = False

        self.assertFalse(failed)

if __name__ == "__main__":
    unittest.main()

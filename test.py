#!/bin/env python3
from logging import exception
import unittest
from mbus import BusException, GroupExistsException, GroupNotFoundException, InvalidEnpointParameterException, InvalidGroupNameException, InvalidRailNameException, MissingEndpointParameter, RailAlreadyBoundException, RailExistsException, RailNotFoundException
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
        except RailExistsException:
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
        except RailAlreadyBoundException:
            failed = True
        else:
            failed = False

        self.assertTrue(failed)

        try:
            mbus.bindModuleToRail("sdjlganj")
        except RailNotFoundException:
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
            except InvalidGroupNameException:
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
        except GroupExistsException:
            failed = True
        else:
            failed = False

        self.assertTrue(failed)

    def test_groupNotFound(self):
        railName = "groupNotFound"
        mbus.registerRail(railName)
        try:
            mbus.createGroup(f"{railName}.notfound.test")
        except GroupNotFoundException:
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
        except GroupNotFoundException:
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
        except InvalidEnpointParameterException:
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

if __name__ == "__main__":
    unittest.main()

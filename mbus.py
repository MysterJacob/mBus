import re
import inspect
from dataclasses import dataclass
from typing import Union

class BusException(Exception):
    def __init__(self, message) -> None:
        self.message = message

    def __str__(self) -> str:
        return self.message

    def __repr__(self) -> str:
        return str(self)

class InvalidRailNameException(BusException):
    """Exception thrown when provided rail name is invalid"""

class RailExistsException(BusException):
    """Exception thrown when rail with provided name does already exist"""

class RailAlreadyBoundException(BusException):
    """Exception thrown when rail is already bound to module"""

class RailNotFoundException(BusException):
    """Exception thrown when rail with given name is not found on target"""

class InvalidGroupNameException(BusException):
    """Exception thrown when provided group name is invalid"""

class GroupExistsException(BusException):
    """Exception thrown when group with provided name does already exist"""

class GroupNotFound(BusException):
    """Exception thrown when group is not found on target"""

RAIL_NAME_REGEX = '^([A-Z]|[a-z])([A-Z]|[a-z]|[0-9]|_)*$'
def isRailNameInvalid(railName : str) -> bool:
    return re.fullmatch(RAIL_NAME_REGEX, railName) is None

GROUP_NAME_REGEX = '^([A-Z]|[a-z])([A-Z]|[a-z]|[0-9])*$'
def isGroupNameInvalid(railName : str) -> bool:
    return re.fullmatch(GROUP_NAME_REGEX, railName) is None

@dataclass
class busEndpoint:
    pass

@dataclass
class busGroup:
    groupName : str
    groups : dict[str, 'busGroup']
    endpoints : dict[str, busEndpoint]

    def __hash__(self) -> int:
        return hash(self.groupName)

    def getGroup(self, groupName : str) -> 'busGroup':
        if not groupName in self.groups.keys():
            raise GroupNotFound(f"Group {groupName} is not found in group {self.groupName}")

        return self.groups[groupName]

    def getEndpoint(self, endpointName : str) -> busEndpoint:
        if not endpointName in self.endpoints.keys():
            raise GroupNotFound(f"Group {endpointName} is not found in group {self.groupName}")

        return self.endpoints[endpointName]

    def createGroup(self, groupName : str) -> None:
        if groupName in self.groups.keys():
            raise GroupExistsException(f"Group {groupName} exists on rail {self.railName}")

        if isGroupNameInvalid(groupName):
            raise InvalidGroupNameException(f"Group name {groupName} is not vaild name for group")

        newGroup = busGroup(groupName, {}, {})
        self.groups[groupName] = newGroup

@dataclass
class busRail:
    railName : str
    groups : dict[str, busGroup]
    boundModule : Union[str, None]

    def __hash__(self) -> int:
        return hash(self.railName)

    def getGroup(self, groupName : str) -> busGroup:
        if not groupName in self.groups.keys():
            raise GroupNotFound(f"Group {groupName} is not found on rail {self.railName}")

        return self.groups[groupName]

    def createGroup(self, groupName : str) -> None:
        if groupName in self.groups.keys():
            raise GroupExistsException(f"Group {groupName} exists on rail {self.railName}")

        if isGroupNameInvalid(groupName):
            raise InvalidGroupNameException(f"Group name {groupName} is not vaild name for group")

        newGroup = busGroup(groupName, {}, {})
        self.groups[groupName] = newGroup

class __mBusSingleton:
    def __init__(self) -> None:
        self.__rails : dict[str, busRail] = {}
        self.__railsBindsToModules : dict[str, busRail] = {}

    def __railExists(self, railName : str):
        return railName in self.__rails.keys()

    def __getRail(self, railName : str):
        if not self.__railExists(railName):
            raise RailNotFoundException(f"Rail {railName} is not found on bus")
        return self.__rails[railName]

    def __bindModuleToRail(self, railName : str):
        rail = self.__getRail(railName)

        if not self.__rails[railName].boundModule is None:
            raise RailAlreadyBoundException(f"Rail {railName} is already bound to module {rail.boundModule}")

        moduleName = inspect.stack()[2][0].f_locals["self"].__class__.__name__

        rail.boundModule = moduleName
        self.__railsBindsToModules[moduleName] = rail

    def registerRail(self, railName : str, bindToModule : bool = False) -> None:
        if isRailNameInvalid(railName):
            raise InvalidRailNameException(f"Rail name {railName} is not vaild name for rail")

        if self.__railExists(railName):
            raise RailExistsException(f"Rail name {railName} is already registered")

        newRail = busRail(railName, {}, None)
        self.__rails.update({railName : newRail})

        if bindToModule:
            self.__bindModuleToRail(railName)

    def getRails(self) -> set[str]:
        return set(rail.railName for rail in self.__rails.values())

    def bindModuleToRail(self, railName : str) -> None:
        self.__bindModuleToRail(railName)

    def __getGroupFromAddresses(self, addresses : list[str]) -> busRail | busGroup:
        railName, *groupNames = addresses
        finalElement = self.__getRail(railName)

        for groupName in groupNames:
            finalElement = finalElement.getGroup(groupName)

        return finalElement

    def __getGroupFromAddress(self, address : str) -> busRail | busGroup | busEndpoint:
        return self.__getGroupFromAddresses(address.split("."))

    def createGroup(self, address : str) -> None:
        if address.count(".") == 0:
            raise InvalidGroupNameException("No group name is provided on address")

        *addresses, newGroupName = address.split(".")

        finalGroup = self.__getGroupFromAddresses(addresses)

        finalGroup.createGroup(newGroupName)

    def addressExists(self, address : str) -> bool:
        *groupAddress, endpoint = address.split(".")
        lastGroup = self.__getGroupFromAddresses(groupAddress)

        if endpoint in lastGroup.groups:
            return True
        elif isinstance(lastGroup, busRail):
            return False
        elif endpoint in lastGroup.endpoints:
            return True

        return False

mbus = __mBusSingleton()

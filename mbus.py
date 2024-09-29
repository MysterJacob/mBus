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

class RailNotFoundExceptionException(BusException):
    """Exception thrown when rail with given name is not found on target"""

RAIL_NAME_REGEX = '^([A-z])([A-z]|[0-9]|_)*$'

@dataclass
class busEndpoint:
    pass

@dataclass
class busGroup:
    groupName : str
    groups : list['busGroup']
    endpoints : list[busEndpoint]

    def __hash__(self) -> int:
        return hash(self.groupName)

@dataclass
class busRail:
    railName : str
    groups : list[busGroup]
    boundModule : Union[str, None]

    def __hash__(self) -> int:
        return hash(self.railName)

class __mBusSingleton:
    def __init__(self) -> None:
        self.__rails : dict[str, busRail] = {}
        self.__railsBindsToModules : dict[str, busRail] = {}

    def __isRailNameInvalid(self, railName : str) -> bool:
        return re.fullmatch(RAIL_NAME_REGEX, railName) is None

    def __railExists(self, railName : str):
        return railName in self.__rails.keys()

    def __bindModuleToRail(self, railName : str):
        if not self.__railExists(railName):
            raise RailNotFoundExceptionException(f"Rail {railName} is not found on bus")

        rail = self.__rails[railName]

        if not self.__rails[railName].boundModule is None:
            raise RailAlreadyBoundException(f"Rail {railName} is already bound to module {rail.boundModule}")

        moduleName = inspect.stack()[2][0].f_locals["self"].__class__.__name__

        rail.boundModule = moduleName
        self.__railsBindsToModules[moduleName] = rail

    def registerRail(self, railName : str, bindToModule : bool = False) -> None:
        if self.__isRailNameInvalid(railName):
            raise InvalidRailNameException(f"Rail name {railName} is not vaild name for rail")

        if self.__railExists(railName):
            raise RailExistsException(f"Rail name {railName} is already registered")

        newRail = busRail(railName, [], None)
        self.__rails.update({railName : newRail})

        if bindToModule:
            self.__bindModuleToRail(railName)

    def getRails(self) -> set[str]:
        return set(rail.railName for rail in self.__rails.values())

    def bindModuleToRail(self, railName : str) -> None:
        self.__bindModuleToRail(railName)

mbus = __mBusSingleton()

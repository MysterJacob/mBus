import re
import inspect

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

class __mBusSingleton:
    def __init__(self) -> None:
        self.__rails : set[str] = set()
        self.__railsBindsToModules : dict[str, str] = {}

    def __isRailNameInvalid(self, railName : str) -> bool:
        return re.fullmatch(RAIL_NAME_REGEX, railName) is None

    def __bindModuleToRail(self, railName : str):
        if not railName in self.__rails:
            raise RailNotFoundExceptionException(f"Rail {railName} is not found on bus")

        if railName in self.__railsBindsToModules.keys():
            raise RailAlreadyBoundException(f"Rail {railName} is already bound to module {self.__railsBindsToModules[railName]}")

        moduleName = inspect.stack()[2][0].f_locals["self"].__class__.__name__

        self.__railsBindsToModules.update({railName : moduleName})

    def registerRail(self, railName : str, bindToModule : bool = False) -> None:
        if self.__isRailNameInvalid(railName):
            raise InvalidRailNameException(f"Rail name {railName} is not vaild name for rail")

        if railName in self.__rails:
            raise RailExistsException(f"Rail name {railName} is already registered")

        self.__rails.add(railName)

        if bindToModule:
            self.__bindModuleToRail(railName)

    def getRails(self) -> set[str]:
        return self.__rails.copy()

    def bindModuleToRail(self, railName : str) -> None:
        self.__bindModuleToRail(railName)

mbus = __mBusSingleton()

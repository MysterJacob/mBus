import re
from typing import Callable, Union
import logging


class BusException(Exception):
    def __init__(self, message) -> None:
        self.message = message

    def __str__(self) -> str:
        return self.message

    def __repr__(self) -> str:
        return str(self)


class ModuleLoadingError(BusException):
    """Error while loading module"""


class ModuleUnloadingError(BusException):
    """Error while loading module"""


class GroupCreationError(BusException):
    """Error while creating group"""


class EndpointCreationError(BusException):
    """Error while creating endpoint"""


class EndpointeCallError(BusException):
    """Error while calling an endpoint"""


MODULE_NAME_REGEX = "^([A-Z]|[a-z])([A-Z]|[a-z]|[0-9]|_)*$"


def isModuleNameInvalid(railName: str) -> bool:
    return re.fullmatch(MODULE_NAME_REGEX, railName) is None


GROUP_NAME_REGEX = "^([a-z])([A-Z]|[a-z]|[0-9])*$"


def isGroupNameInvalid(railName: str) -> bool:
    return re.fullmatch(GROUP_NAME_REGEX, railName) is None


class busEndpoint:
    name: str
    owner: "mbusModule"


class busTrigger(busEndpoint):
    __callback: Callable

    def __init__(self, name: str, owner: "mbusModule", **kwargs):
        if "callback" not in kwargs:
            raise EndpointCreationError(
                """Missing required argument <callback> for trigger endpoint"""
            )
        callback = kwargs["callback"]
        self.name = name
        self.owner = owner
        self.__callback = callback

    def trigger(self, *args, **kwargs):
        try:
            result = self.__callback(*args, **kwargs)
            if result is None:
                return False
            return result
        except TypeError:
            raise EndpointeCallError(
                f"""Endpoint <{self.name}> called with invalid arguments"""
            )


class busGroup:
    groupName: str
    __subBus: dict[str, Union["busGroup", "busEndpoint"]]

    def __init__(self, owner: "mbusModule", groupName: str) -> None:
        self.owner = owner
        self.groupName = groupName
        self.__subBus = dict()

    def createGroup(self, groupName: str) -> "busGroup":
        return groupCreator(self.__subBus, self.owner, groupName)

    def createEndpoint(self, endpointName: str, **kwargs) -> "busEndpoint":
        return endpointCreator(
            self.__subBus, self.owner, endpointName, **kwargs
        )

    def get(self, *args, **kwargs):
        return self.__subBus.get(*args, **kwargs)


class mbusModule:
    name: str
    dependencies: set[str] = set()
    _createGroup: Callable[[str], "busGroup"]
    _createEndpoint: Callable

    def __init__(self, mbus: "mBus", **kwargs) -> None:
        self.mbus = mbus
        self._createGroup = kwargs["createGroup"]
        self._createEndpoint = kwargs["createEndpoint"]

    def load(self, mbus: "mBus"):
        pass

    def unload(self):
        pass


def groupCreator(moduleGroups, owner: mbusModule, groupName: str):
    if isGroupNameInvalid(groupName):
        raise GroupCreationError(
            f"""Name <{groupName}> is invalid name for group"""
        )
    if groupName in moduleGroups:
        raise GroupCreationError(
            f"""Name <{groupName}> is already present on the bus"""
        )

    newGroup = busGroup(owner, groupName)

    moduleGroups[groupName] = newGroup

    return newGroup


def endpointCreator(
    moduleGroups, owner: mbusModule, endpointName: str, **kwargs
):
    if isGroupNameInvalid(endpointName):
        raise EndpointCreationError(
            f"""Name <{endpointName}> is invalid name for endpoint"""
        )
    if endpointName in moduleGroups:
        raise EndpointCreationError(
            f"""Name <{endpointName}> is already present on the bus"""
        )

    match kwargs.get("type"):
        case "trigger":
            newTrigger = busTrigger(endpointName, owner, **kwargs)
            moduleGroups[endpointName] = newTrigger
            return newTrigger

        case None:
            raise EndpointCreationError(
                """Missing required field <type> in endpoint creation"""
            )
        case _:
            raise EndpointCreationError(
                f"""Unknown endpoint type <{kwargs["type"]}>"""
            )


class mBus(object):
    __loadedModules: dict[str, mbusModule]
    __loadingQueue: set[type[mbusModule]]
    __bus: dict[str, dict[str, Union["busGroup", "busEndpoint"]]]

    def __new__(cls):
        if not hasattr(cls, "singleton"):
            cls.singleton = super(mBus, cls).__new__(cls)
        return cls.singleton

    def __init__(self) -> None:
        self.__loadedModules = dict()
        self.__loadingQueue = set()
        self.__bus = dict()

    def loadModule(self, module: type[mbusModule]):
        if isModuleNameInvalid(module.name):
            raise ModuleLoadingError(
                f"""Module <{module.name}> has invalid name"""
            )

        if module in self.__loadingQueue or self.isModuleLoaded(module.name):
            raise ModuleLoadingError(
                f"""Module <{module.name}> is already in loading queue"""
            )

        logging.info(f"Loading module <{module.name}>")
        logging.debug(
            f"Module <{module.name} dependencies: {','.join(module.dependencies)}>"
        )

        self.__loadingQueue.add(module)
        self.__tryLoadFromQueue()

    def __tryLoadFromQueue(self):
        while True:
            loadedModuleNames = set(self.__loadedModules.keys())
            removeFromQueue = set()
            for moduleInQueue in self.__loadingQueue:
                requirementsMet = len(
                    moduleInQueue.dependencies
                ) == 0 or moduleInQueue.dependencies.issubset(loadedModuleNames)
                if not requirementsMet:
                    continue

                self.__loadModule(moduleInQueue)
                removeFromQueue.add(moduleInQueue)

            for moduleToRemove in removeFromQueue:
                self.__loadingQueue.remove(moduleToRemove)

            if len(removeFromQueue) == 0:
                return

    def __createGroup(self, module: mbusModule, groupName: str):
        moduleGroups = self.__bus[module.name]
        return groupCreator(moduleGroups, module, groupName)

    def __createEndpoint(self, module: mbusModule, endpointName: str, **kwargs):
        moduleGroups = self.__bus[module.name]
        return endpointCreator(moduleGroups, module, endpointName, **kwargs)

    def __loadModule(self, module: type[mbusModule]):
        if module.name in self.__loadedModules:
            raise ModuleLoadingError(
                f"""Module <{module.name}> is already loaded"""
            )
        moduleInstance = module(
            self,
            createGroup=lambda groupName: self.__createGroup(
                moduleInstance, groupName
            ),
            createEndpoint=lambda endpointName, **kwargs: self.__createEndpoint(
                moduleInstance, endpointName, **kwargs
            ),
        )
        self.__loadedModules[module.name] = moduleInstance
        self.__bus[module.name] = dict()
        moduleInstance.load(
            self,
        )
        logging.info(f"Module <{module.name}> has been loaded")

    def isModuleLoaded(self, moduleName: str):
        return moduleName in self.__loadedModules

    def unloadModule(self, moduleName: str):
        if not self.isModuleLoaded(moduleName):
            raise ModuleUnloadingError(
                f"""Module <{moduleName}> is not loaded"""
            )

        module = self.__loadedModules[moduleName]
        module.unload()
        logging.info(f"Module <{module.name}> has been unloaded")
        del self.__loadedModules[moduleName]
        del self.__bus[moduleName]

    def addressExisits(self, address: str):
        if len(address) == 0:
            return False

        start = self.__bus
        splited = address.split(".")
        for i, step in enumerate(splited):
            start = start.get(step, None)

            if isinstance(start, busEndpoint):
                return i + 1 == len(splited)

            if start is None:
                return False

        return True

    def __findEndpoint(self, address: str):
        if len(address) == 0:
            raise EndpointeCallError(f"""Address <{address}> not found""")

        start = self.__bus
        splited = address.split(".")
        for step in splited:
            if isinstance(start, busEndpoint):
                raise EndpointeCallError(f"""Address <{address}> not found""")

            start = start.get(step, None)

            if start is None:
                raise EndpointeCallError(f"""Address <{address}> not found""")

        return start

    def fireTrigger(self, address: str, *args, **kwargs):
        trigger = self.__findEndpoint(address)
        if not isinstance(trigger, busTrigger):
            raise EndpointeCallError(
                f"""Endpoint on address <{address}> is not a trigger"""
            )

        return trigger.trigger(*args, **kwargs)

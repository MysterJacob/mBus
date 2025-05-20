import re
from dataclasses import dataclass
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


MODULE_NAME_REGEX = "^([A-Z]|[a-z])([A-Z]|[a-z]|[0-9]|_)*$"


def isModuleNameInvalid(railName: str) -> bool:
    return re.fullmatch(MODULE_NAME_REGEX, railName) is None


GROUP_NAME_REGEX = "^([A-Z]|[a-z])([A-Z]|[a-z]|[0-9])*$"


def isGroupNameInvalid(railName: str) -> bool:
    return re.fullmatch(GROUP_NAME_REGEX, railName) is None


@dataclass
class __busEndpoint:
    pass


@dataclass
class __busGroup:
    def __createGroup(self, module: "mbusModule", groupName) -> "__busGroup":
        pass

    def __createEndpoint(
        self, module: "mbusModule", groupName
    ) -> "__busEndpoint":
        pass


class mbusModule:
    name: str
    dependencies: set[str] = set()

    def __init__(self, mbus: "__mBusSingleton") -> None:
        self.mbus = mbus

    def load(self, mbus: "__mBusSingleton", createGroup: Callable):
        pass

    def unload(self):
        pass


class __mBusSingleton:
    __loadedModules: dict[str, mbusModule]
    __loadingQueue: set[type[mbusModule]]

    def __init__(self) -> None:
        self.__loadedModules = dict()
        self.__loadingQueue = set()

    def loadModule(self, module: type[mbusModule]):
        if isModuleNameInvalid(module.name):
            raise ModuleLoadingError(
                f"""Module {module.name} has invalid name"""
            )

        if module in self.__loadingQueue or self.isModuleLoaded(module.name):
            raise ModuleLoadingError(
                f"""Module {module.name} is already in loading queue"""
            )

        logging.info(f"Loading module {module.name}")
        logging.debug(
            f"Module {module.name} dependencies: {','.join(module.dependencies)}"
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
        pass

    def __loadModule(self, module: type[mbusModule]):
        if module.name in self.__loadedModules:
            raise ModuleLoadingError(
                f"""Module {module.name} is already loaded"""
            )
        moduleInstance = module(self)
        self.__loadedModules[module.name] = moduleInstance
        moduleInstance.load(
            self,
            lambda groupName: self.__createGroup(moduleInstance, groupName),
        )
        logging.info(f"Module {module.name} has been loaded")

    def isModuleLoaded(self, moduleName: str):
        return moduleName in self.__loadedModules

    def unloadModule(self, moduleName: str):
        if not self.isModuleLoaded(moduleName):
            raise ModuleUnloadingError(f"""Module {moduleName} is not loaded""")

        module = self.__loadedModules[moduleName]
        module.unload()
        logging.info(f"Module {module.name} has been unloaded")
        del self.__loadedModules[moduleName]


mbus = __mBusSingleton()

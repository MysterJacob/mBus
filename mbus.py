import re
import logging
import tomllib
import importlib
from pydantic import BaseModel
from typing import Any, Callable, Union


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


class FieldValueTypeError(BusException):
    """Trying to set value with different type than expected in the field"""


class MissingConfigForModule(BusException):
    """Missing config for a module"""


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


class busEvent(busEndpoint):
    __responders: set[Callable]

    def __init__(self, name: str, owner: "mbusModule", **kwargs):
        responders = kwargs.get("responders", set())
        self.name = name
        self.owner = owner
        self.__responders = responders

    def addEventListener(self, listener: Callable):
        self.__responders.add(listener)

    def call(self, *args, **kwargs):
        for responder in self.__responders:
            responder(*args, **kwargs)


class busField(busEndpoint):
    __fieldValue: Any
    __fieldType: type
    __onChangeCallbacks: set[Callable]

    def __init__(self, name: str, owner: "mbusModule", **kwargs):
        if "fieldType" not in kwargs:
            raise EndpointCreationError(
                """Missing required argument <fieldType> for trigger endpoint"""
            )
        if "value" not in kwargs:
            raise EndpointCreationError(
                """Missing required argument <value> for trigger endpoint"""
            )

        self.name = name
        self.owner = owner
        self.__onChangeCallbacks = set()
        if "onChangeCallback" in kwargs:
            self.__onChangeCallbacks.add(kwargs["onChangeCallback"])
        self.__fieldType = kwargs["fieldType"]
        self.setValue(kwargs["value"])

    def setValue(self, value: Any):
        if not isinstance(value, self.__fieldType):
            raise FieldValueTypeError(
                f"""Value <{value}> of type <{type(value)}> found, <{self.__fieldType}> expected."""
            )

        self.__fieldValue = value
        self.__makeCallback()

    def __makeCallback(self):
        for callback in self.__onChangeCallbacks:
            callback(self.__fieldValue)

    def addOnChangeCallback(self, callback: Callable):
        self.__onChangeCallbacks.add(callback)

    def getValue(self):
        return self.__fieldValue


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
    _configTemplate: Union[type[BaseModel], None] = None
    _createGroup: Callable[[str], "busGroup"]
    _createEndpoint: Callable
    _callEvent: Callable
    _setFieldValue: Callable

    def __init__(self, mbus: "mBus", **kwargs) -> None:
        self.mbus = mbus
        self._createGroup = kwargs["createGroup"]
        self._createEndpoint = kwargs["createEndpoint"]
        self._callEvent = kwargs["callEvent"]
        self._setFieldValue = kwargs["setFieldValue"]

        self.__loadConfig(kwargs.get("config", None))

    def __loadConfig(self, config: Union[dict, None]):
        if self._configTemplate is None:
            return
        if config is None:
            raise MissingConfigForModule(
                f"""Missing config for module {self.name}"""
            )

        self._config = self._configTemplate(**config)

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
        case "event":
            newEvent = busEvent(endpointName, owner, **kwargs)
            moduleGroups[endpointName] = newEvent
            return newEvent
        case "field":
            newField = busField(endpointName, owner, **kwargs)
            moduleGroups[endpointName] = newField
            return newField

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
    __config: dict[str, Any]

    def __new__(cls):
        if not hasattr(cls, "singleton"):
            cls.singleton = super(mBus, cls).__new__(cls)
        return cls.singleton

    def __init__(self) -> None:
        self.__loadedModules = dict()
        self.__loadingQueue = set()
        self.__bus = dict()
        self.__config = {}
        self.__logger = logging.getLogger(__name__)

    def loadConfigFile(self, path: str):
        with open(path, "rb") as f:
            data = tomllib.load(f)
            self.__config = data
        return self.__config

    def loadModule(self, module: type[mbusModule]):
        if isModuleNameInvalid(module.name):
            raise ModuleLoadingError(
                f"""Module <{module.name}> has invalid name"""
            )

        if module in self.__loadingQueue or self.isModuleLoaded(module.name):
            raise ModuleLoadingError(
                f"""Module <{module.name}> is already in loading queue"""
            )

        self.__logger.info(f"Loading module <{module.name}>")
        self.__logger.debug(
            f"Module <{module.name} dependencies: {','.join(module.dependencies)}>"
        )

        self.__loadingQueue.add(module)
        self.__tryLoadFromQueue()

    def loadModuleFromFile(self, path: str):
        moduleName = path.split(".")[-1]
        try:
            moduleFile = importlib.import_module(path)
        except ModuleNotFoundError:
            raise ModuleLoadingError(f"""Can not find module from {path}""")

        if not hasattr(moduleFile, moduleName):
            raise ModuleUnloadingError(
                f"""File {path} is not a valid mbus module"""
            )

        module = getattr(moduleFile, moduleName)
        self.loadModule(module)

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

    def __loadModule(self, module: type[mbusModule]):
        if module.name in self.__loadedModules:
            raise ModuleLoadingError(
                f"""Module <{module.name}> is already loaded"""
            )
        moduleConfig = self.__config.get(module.name, None)
        isDisabled = moduleConfig is not None and moduleConfig.get(
            "disabled", False
        )
        if isDisabled:
            return

        moduleInstance = module(
            self,
            config=moduleConfig,
            createGroup=lambda groupName: self.__createGroup(
                moduleInstance, groupName
            ),
            createEndpoint=lambda endpointName, **kwargs: self.__createEndpoint(
                moduleInstance, endpointName, **kwargs
            ),
            callEvent=lambda address, *args, **kwargs: self.__callEvent(
                moduleInstance, address, *args, **kwargs
            ),
            callEventAsync=lambda address,
            *args,
            **kwargs: self.__callEventAsync(
                moduleInstance, address, *args, **kwargs
            ),
            setFieldValue=lambda address, value: self.__setValue(
                moduleInstance, address, value
            ),
        )
        self.__loadedModules[module.name] = moduleInstance
        self.__bus[module.name] = dict()
        moduleInstance.load(
            self,
        )
        self.__logger.info(f"Module <{module.name}> has been loaded")

    def __createGroup(self, module: mbusModule, groupName: str):
        moduleGroups = self.__bus[module.name]
        return groupCreator(moduleGroups, module, groupName)

    def __createEndpoint(self, module: mbusModule, endpointName: str, **kwargs):
        moduleGroups = self.__bus[module.name]
        return endpointCreator(moduleGroups, module, endpointName, **kwargs)

    def __callEvent(self, module: mbusModule, address: str, *args, **kwargs):
        event = self.__findEndpoint(module.name + "." + address)
        if not isinstance(event, busEvent):
            raise EndpointeCallError(
                f"""Endpoint on address <{address}> is not a event"""
            )

        if event.owner is not module:
            raise EndpointeCallError(
                f"""Event <{address}> has been called not by owning module"""
            )

        event.call(*args, **kwargs)

    async def __callEventAsync(
        self, module: mbusModule, address: str, *args, **kwargs
    ):
        return self.__callEvent(module, address, *args, **kwargs)

    def __setValue(self, module: mbusModule, address: str, value):
        field = self.__findEndpoint(module.name + "." + address)
        if not isinstance(field, busField):
            raise EndpointeCallError(
                f"""Endpoint on address <{address}> is not a field"""
            )

        if field.owner is not module:
            raise EndpointeCallError(
                f"""Field <{address}> has been set not by owning module"""
            )

        field.setValue(value)

    def isModuleLoaded(self, moduleName: str):
        return moduleName in self.__loadedModules

    def unloadModule(self, moduleName: str):
        if not self.isModuleLoaded(moduleName):
            raise ModuleUnloadingError(
                f"""Module <{moduleName}> is not loaded"""
            )

        module = self.__loadedModules[moduleName]
        module.unload()
        self.__logger.info(f"Module <{module.name}> has been unloaded")
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

    async def fireTriggerAsync(self, address: str, *args, **kwargs):
        return self.fireTrigger(address, *args, **kwargs)

    def addEventListener(self, address: str, listener):
        event = self.__findEndpoint(address)
        if not isinstance(event, busEvent):
            raise EndpointeCallError(
                f"""Endpoint on address <{address}> is not a event"""
            )

        event.addEventListener(listener)

    def getValue(self, address: str):
        field = self.__findEndpoint(address)
        if not isinstance(field, busField):
            raise EndpointeCallError(
                f"""Endpoint on address <{address}> is not a field"""
            )

        return field.getValue()

    def addFieldChangeCallback(self, address: str, callback: Callable):
        field = self.__findEndpoint(address)
        if not isinstance(field, busField):
            raise EndpointeCallError(
                f"""Endpoint on address <{address}> is not a field"""
            )

        field.addOnChangeCallback(callback)

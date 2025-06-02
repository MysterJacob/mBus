from pydantic import BaseModel
from mbus import mbusModule, mBus


class testmodConfig(BaseModel):
    testValue: str


class testmod(mbusModule):
    name = "testmod"
    _configTemplate = testmodConfig
    _config: testmodConfig

    def load(self):
        self._createEndpoint(
            endpointName="testTrigger",
            type="trigger",
            callback=self.__callback
        )

    def __callback(self):
        return self._config.testValue

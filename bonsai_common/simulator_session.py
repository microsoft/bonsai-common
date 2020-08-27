"""
Simulator session base class for bonsai3 library
"""
__copyright__ = "Copyright 2020, Microsoft Corp."

# pyright: strict

import abc
import logging
from typing import Dict, Any, Optional
import jsons

from microsoft_bonsai_api.simulator.client import BonsaiClient, BonsaiClientConfig
from microsoft_bonsai_api.simulator.generated.models import (
    Event,
    EventType,
    SimulatorInterface,
    SimulatorSessionResponse,
    SimulatorState,
)

logFormatter = "[%(asctime)s][%(levelname)s] %(message)s"
logging.basicConfig(format=logFormatter, datefmt="%Y-%m-%d %H:%M:%S")
log = logging.getLogger(__name__)
log.setLevel(level=logging.INFO)


Schema = Dict[str, Any]


class SimulatorSession(abc.ABC):
    _registered = None  # type: Optional[SimulatorSessionResponse]
    _sequence_id = 1  # type: int

    def __init__(self, config: BonsaiClientConfig):
        self._config = config

        self._registered = None
        self._client = BonsaiClient(config)
        self._sequence_id = 1

    # interface and state
    def get_state(self) -> Schema:
        """Called to retreive the current state of the simulator. """
        raise NotImplementedError("get_state not implemented.")

    def get_interface(self) -> SimulatorInterface:
        """Called to retreive the simulator interface during registration. """
        raise NotImplementedError("get_interface not implemented.")

    def get_simulator_context(self) -> str:
        """
        Called to retrieve the simulator context field for the SimulatorInterface.
        """
        return self._config.simulator_context or ""

    def halted(self) -> bool:
        """
        Should return weather the episode is halted, and
        no further action will result in a state.
        """
        raise NotImplementedError("halted not implemented.")

    # callbacks
    def registered(self):
        """Called after simulator is successfully registered. """
        log.info("Registered.")
        pass

    @abc.abstractmethod
    def episode_start(self, config: Schema) -> None:
        """Called at the start of each episode. """
        raise NotImplementedError("episode_start not implemented.")

    @abc.abstractmethod
    def episode_step(self, action: Schema) -> None:
        """Called for each step of the episode. """
        raise NotImplementedError("episode_step not implemented.")

    def episode_finish(self, reason: str) -> None:
        """Called at the end of an episode. """
        pass

    # TODO
    # def playback_start(self, config: dict):
    # def playback_step(self, action: dict, stateDescription: dict, action: dict):
    # def playback_finish(self):

    def idle(self, callbackTime: float):
        """Called when the simulator should idle and perform no action. """
        log.info("Idling...")
        pass

    def unregistered(self, reason: str):
        """Called when the simulator has been unregistered and should exit. """
        log.info("Unregistered.")
        pass

    def run(self) -> bool:
        """
        Runs simulator. Returns false when the simulator should exit.
        Example usage:
            ...
            mySim = MySimulator(config)
            while mySim.run():
                continue
            ...
        returns True if the simulator should continue.
        returns False if the simulator should exit its simulation loop.
        """
        unregister = False
        try:
            if self._registered is None:
                log.info("Registering Sim")
                self._registered = self._client.session.create(
                    self._config.workspace, self.get_interface()
                )
                self.registered()
                return True
            else:
                session_id = self._registered.session_id

                # TODO: Figure out what to do here. Moab sim has a complex type in it's state (numpy.float)
                #       Workaround is the following two lines because the swagger libraries do not like it.
                state = jsons.dumps(self.get_state())
                state = jsons.loads(state)

                sim_state = SimulatorState(
                    sequence_id=self._sequence_id, state=state, halted=self.halted(),
                )
                advance_response = self._client.session.advance(
                    self._config.workspace, session_id, body=sim_state
                )  # # type: Event

                self._sequence_id = advance_response.sequence_id
                log.info("Received event: {}".format(advance_response.type))
                self._dispatch_event(advance_response)
                return True
        except KeyboardInterrupt:
            unregister = True
        except Exception as err:
            unregister = True
            log.error("Exiting due to the following error: {}".format(err))
            raise err
        finally:
            if self._registered and unregister:
                try:
                    log.info("Attempting to unregister simulator.")
                    self._client.session.delete(
                        self._config.workspace, session_id=self._registered.session_id,
                    )
                    log.info("Successfully unregistered simulator.")
                except Exception as err:
                    log.error("Unregister simulator failed with error: {}".format(err))
        return False

    def _dispatch_event(self, event: Event) -> bool:
        """
            Examines the SimulatorEvent and calls one of the
            dispatch functions for the appropriate event.

            return false if there are no more events.
        """

        if event.type == EventType.episode_start.value and event.episode_start:
            self.episode_start(event.episode_start.config)

        elif event.type == EventType.episode_step.value and event.episode_step:
            self.episode_step(event.episode_step.action)

        elif event.type == EventType.episode_finish.value and event.episode_finish:
            self.episode_finish(event.episode_finish.reason)

        elif event.type == EventType.idle.value and event.idle:
            try:
                self.idle(event.idle.callback_time)
            except AttributeError:
                # callbacktime is always 0. Sometimes the attribute is missing.
                # Idle for 0 seconds if attribute is missing.
                self.idle(0)

        elif event.type == EventType.unregister.value and event.unregister:
            self.unregistered(event.unregister.reason)
            return False

        return True

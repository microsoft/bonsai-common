"""
Simulator session base class for bonsai3 library
"""
__copyright__ = "Copyright 2020, Microsoft Corp."

# pyright: strict

import abc
import logging
import sys
import signal
import time

from functools import partial
from types import FrameType
from typing import Dict, Any, Optional, List, cast

import jsons

from microsoft_bonsai_api.simulator.client import BonsaiClient, BonsaiClientConfig
from microsoft_bonsai_api.simulator.generated.models import (
    Event,
    EventType,
    SimulatorInterface,
    SimulatorSessionResponse,
    SimulatorState,
)

from azure.core.exceptions import (
    ServiceRequestError,
    ServiceResponseError,
    ServiceResponseTimeoutError,
)

logFormatter = "[%(asctime)s][%(levelname)s] %(message)s"
logging.basicConfig(format=logFormatter, datefmt="%Y-%m-%d %H:%M:%S")
log = logging.getLogger(__name__)
log.setLevel(level=logging.INFO)


Schema = Dict[str, Any]

# Numpy is heavy dependency that we would like to avoid in cases whenever
# is possible. Here we are making numpy a soft-dependency that will be used
# only if it's available
if "numpy" in sys.modules:
    try:
        import numpy as np

        def default_numpy_bool_serializer(
            np_bool: np.bool_, **kwargs: Dict[str, Any]
        ) -> bool:
            """
            Serialize the given numpy bool instance to a native python object.
            :param np_obj: the numpy object instance that is to be serialized.
            :param kwargs: not used.
            :return: native python object equivalent to the numpy object representation.
            """
            return np_bool.item()

        jsons.set_serializer(default_numpy_bool_serializer, np.bool_)

        def default_numpy_number_serializer(
            np_number: np.number, **kwargs: Dict[str, Any]
        ) -> object:
            """
            Serialize the given numpy number instance to a native python object.
            :param np_obj: the numpy object instance that is to be serialized.
            :param kwargs: not used.
            :return: native python object equivalent to the numpy object representation.
            """
            return np_number.item()

        jsons.set_serializer(default_numpy_number_serializer, np.number)

        def default_numpy_array_serializer(
            np_array: np.ndarray, **kwargs: Dict[str, Any]
        ) -> List[Any]:
            """
            Serialize the given numpy object instance to a string. It uses
            str because all numpy object str representation are compatible
            with the Python built-in equivalent.
            :param np_obj: the numpy object instance that is to be serialized.
            :param kwargs: not used.
            :return: str with the numpy object representation.
            """
            native_list = np_array.tolist()
            return jsons.default_iterable_serializer(native_list, **kwargs)

        jsons.set_serializer(default_numpy_array_serializer, np.ndarray)

    except Exception:
        log.info("Erro trying to import Numpy")


class SimulatorSession(abc.ABC):
    _registered = None  # type: Optional[SimulatorSessionResponse]
    _sequence_id = 1  # type: int
    _last_event = None  # type: Optional[Event]

    def __init__(self, config: BonsaiClientConfig, *, log_dispatch: bool = True):
        self._config = config

        self._registered = None
        self._client = BonsaiClient(config)
        self._sequence_id = 1
        self._log_dispatch = log_dispatch
        self._first_run_made = False
        self._includes_complex_state = False
        self._transient_error_retry_count = 5
        self._current_retry_count = 0

    @property
    def force_complex_state(self):
        """
        Indicates that the state has to be handle as complex state regardless
        of be one or not. A complex state is any state that contains fields
        of types that are not built in the Python interpreter. For example,
        if the simulator is using Numpy types in any of the fields, then the
        Simulator session will auto-detected and automatically mark the state
        as complex. This property is useful to handle special cases where
        the Simulator Session is not able to auto-detect a complex type.
        """
        return False

    @property
    def attach_to_sigterm(self):
        """Indicates if the session should handle the sigterm.
        By default we are handling the sigterm but a subclass
        could override this property to change the behavior.
        """
        return True

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

    def idle(self, callback_time: float):
        """Called when the simulator should idle and perform no action. """
        log.info("Idling for {} seconds...".format(callback_time))
        if callback_time > 0:
            time.sleep(callback_time)

    def unregistered(self, reason: str):
        """Called when the simulator has been unregistered and should exit. """
        log.info("Unregistered, Reason: {}".format(reason))
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

        # Boolean used to determine if we should attempt to unregister simulator
        unregister = False

        try:
            if self._registered is None:
                log.info("Registering Sim")
                self._registered = self._client.session.create(
                    self._config.workspace, self.get_interface()
                )

                # Attach SIGTERM handler to attempt to unregister sim when a SIGTERM is detected
                if self.attach_to_sigterm and (
                    sys.platform == "linux" or sys.platform == "darwin"
                ):
                    signal.signal(
                        signal.SIGTERM, partial(_handleSIGTERM, sim_session=self)
                    )
                self.registered()
                self._sequence_id = 1
                log.info(
                    "Registered Sim, SessionId: {}".format(self._registered.session_id)
                )

                return True
            else:
                session_id = self._registered.session_id

                state = self.get_state()
                if not self._first_run_made:
                    self._first_run_made = True

                    def check_for_complex_state(state_fields: Dict[str, Any]):
                        for v in state_fields.values():
                            # We need to have these two conditions because
                            # numpy types, which we consider here complex types,
                            # are subclass of builtin types. For example, the following
                            # statement is True: isinstance(np.float64(3.0), float)
                            if (
                                not isinstance(v, (int, float, bool, str, dict))
                                or type(cast(Any, v)).__module__ != float.__module__
                            ):
                                self._includes_complex_state = True
                                break
                            elif isinstance(v, dict):
                                check_for_complex_state(cast(Dict[str, Any], v))

                        if self._includes_complex_state:
                            log.info("Complex type detected for sim state")
                        else:
                            log.info("No complex type detected for sim state")
                            if self.force_complex_state:
                                self._includes_complex_state = True
                                log.info("Complex type for sim state has been forced")

                    check_for_complex_state(state)

                if self._includes_complex_state:
                    state = jsons.dumps(state)
                    state = jsons.loads(state)

                sim_state = SimulatorState(
                    sequence_id=self._sequence_id,
                    state=state,
                    halted=self.halted(),
                )
                self._last_event = self._client.session.advance(
                    self._config.workspace, session_id, body=sim_state
                )  # # type: Event

                self._sequence_id = self._last_event.sequence_id
                if self._log_dispatch:
                    log.info("Received event: {}".format(self._last_event.type))

                keep_going = self._dispatch_event(self._last_event)
                if keep_going is False:
                    log.debug(
                        "Setting flag to indicate that sim should attempt to unregister."
                    )
                    unregister = True

                # because the advance call succeeded, reset the current-retry-counter, if it was set.
                if self._current_retry_count > 0:
                    self._current_retry_count = 0

                return True
        except KeyboardInterrupt:
            unregister = True
        except (
            ServiceRequestError,
            ServiceResponseError,
            ServiceResponseTimeoutError,
        ) as e:
            log.exception("Tranisent Error: {}".format(e))
            if self._current_retry_count < self._transient_error_retry_count:
                sleep_time = (
                    2 ** self._current_retry_count * 1
                )  # sleep time in seconds.
                self._current_retry_count += 1
                log.info(
                    "Ignoring transient exception, Retrying with backoff time: {}".format(
                        sleep_time
                    )
                )
                time.sleep(sleep_time)  # Back off
            else:
                log.info(
                    "RetryLimit exceeded, Unregistering the session and continuing the event loop!"
                )
                self.unregister()
                self._current_retry_count = 0

            # we want to continue the training loop, on these transient error.
            return True
        except Exception as err:
            unregister = True
            log.exception("Exiting due to the following error: {}".format(err))
            raise err
        finally:
            if unregister:
                self.unregister()
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
            log.info("Unregister Event, Reason: {}".format(event.unregister.reason))

            self._registered = None  # Invalidate the registered session record.

        return True

    def unregister(self):
        """Attempts to unregister simulator session"""
        if self._registered:
            try:
                log.info(
                    "Attempting to unregister simulator. {}".format(
                        self._registered.session_id
                    )
                )
                self._client.session.delete(
                    self._config.workspace,
                    session_id=self._registered.session_id,
                )

                if (
                    self._last_event is not None
                    and self._last_event.type == EventType.unregister.value
                    and self._last_event.unregister
                ):
                    self.unregistered(self._last_event.unregister.reason)

                log.info(
                    "Successfully unregistered simulator: {}".format(
                        self._registered.session_id
                    )
                )

                # Invalidate the previous registered session.
                self._registered = None
            except Exception as err:
                log.error("Unregister simulator failed with error: {}".format(err))


def _handleSIGTERM(
    signalType: int, frame: Optional[FrameType], sim_session: SimulatorSession
) -> None:
    """Attempts to unregister sim when a SIGTERM signal is detected"""
    log.info("Handling SIGTERM.")
    sim_session.unregister()
    log.info("SIGTERM Handled, exiting.")
    sys.exit()

Bonsai SDK
==========

A python library for integrating data sources with Bonsai BRAIN.


Installation
------------
To install from source (assuming you are in this directory)
    `$ pip install ./`

To install the current release version (NOT PUBLICLY AVAILABLE YET. IT WILL NOT WORK):
    `$ pip install bonsai-common`

Usage
-----
Clients will subsclass "bonsai-common.SimulatorSession" and implement the required methods.

Example:
::

    #!/usr/bin/env python3

    import sys
    from bonsai-common import SimulatorSession, SimulatorInterface, ServiceConfig

    class SimModel(SimulatorSession):
        def get_state(self) -> Dict[str, Any]:
        """Called to retreive the current state of the simulator. """
            pass

        def get_interface(self) -> SimulatorInterface:
        """Called to retreive the simulator interface during registration. """
            pass
        
        def halted(self) -> bool
        """
        Should return weather the episode is halted, and
        no further action will result in a state.
        """
            pass

        def episode_start(self, config: Dict[str, Any]):
        """ Called at the start of each episode """
            pass
        
        def episode_step(self, action: Dict[str, Any]):
        """ Called for each step of the episode """
            pass

Then, the simulator is configured and assigned a BRAIN and run.
::

    def example():
        config = ServiceConfig(argv=sys.argv)
        sim = SimModel(config)
        while sim.run():
            continue

Example of how to run simulator.
    `python mysim.py --accesskey <ACCESSKEY> --api-host <API-HOST> --workspace <WORKSPACE> --sim-context <SIM_CONTEXT>`

    `python cartpole.py --api-host https://api.bons.ai --workspace <WORKSPACE_ID> --accesskey <KEY> --sim-context '{"deploymentMode": "Testing", "simulatorClientId": "123456", "purpose": { "action": "Train", "target": { "workspaceName": "11111111", "brainName": "testsdk3", "brainVersion": 4, "conceptName": "balance"} } }'`

Running tests using Dockerfile
------------------------------
To build dockerfile:
    `docker build -t testbonsai3 -f Dockerfile ./`

To run tests:
    `docker run testbonsai3`


Microsoft Open Source Code of Conduct
==========

This repository is subject to the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct).

# Bonsai Common
![Python Tests](https://github.com/microsoft/bonsai-common/workflows/Python%20Tests/badge.svg?branch=main)
A python library for integrating data sources with Bonsai brain.

## Installation

To install from source (assuming you are in this directory)
`$ pip install ./`

To install the current release from the git repo:
`$ pip install git+https://github.com/microsoft/bonsai-common`

## Usage

Clients will subclass "bonsai-common.SimulatorSession" and implement the required methods.

Example:
::

    #!/usr/bin/env python3

    import sys
    from bonsai-common import SimulatorSession, Schema
    from microsoft_bonsai_api.simulator.client import BonsaiClientConfig
    from microsoft_bonsai_api.simulator.generated.models import SimulatorInterface

    class SimModel(SimulatorSession):
        def get_state(self) -> Schema:
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

        def episode_start(self, config: Schema):
        """ Called at the start of each episode """
            pass

        def episode_step(self, action: Schema):
        """ Called for each step of the episode """
            pass

Then, the simulator is configured and assigned a BRAIN and run.
::

    def example():
        config = BonsaiClientConfig(argv=sys.argv)
        sim = SimModel(config)
        while sim.run():
            continue

Example of how to run simulator.
`python mysim.py --accesskey <ACCESSKEY> --workspace <WORKSPACE>`

    `python mysim.py --workspace <WORKSPACE_ID> --accesskey <KEY>`

## Running tests using Dockerfile

To build dockerfile:
`docker build -t testbonsai3 -f Dockerfile ./`

To run tests:
`docker run testbonsai3`

# Microsoft Open Source Code of Conduct

This repository is subject to the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct).

# DEVICE_KIT_MARKET_SIMULATIONS
This is a simple wrapper over [device_kit](https://github.com/sgpinkus/device_kit) microgrid modelling tool, that simulates market / auction based price adjustment (or equivalently distributed gradient descent), to find an optimal resource allocation and corresponding prices. Currently only supports point bid agent strategy with an optional proximal penalty. Some convenience scripts to generate plots and gifs are included.

# INSTALLATION
Using virtualenv:

```
virtualenv venv --python=$(which python3)
export PYTHONPATH=$PYTHONPATH${PYTHONPATH:+:}$(dirname $(readlink -f "$f")) # You need to do this coz Python package system is stupid.
. ./venv/bin/activate
pip install -r requirements.txt
```

# USAGE
You need `device_kit` "scenarios" which are model of day-ahead flexibility to do anything. Given a scenario:

    ./run.py device_kit/sample_scenarios/ev_charge_scenario.py -i50

This will create a directory in the CWD that stores the results. The results can be inspected with `report.py`.

This more complex scenario is a variation of the scenario presented in [Li, Chen & Low 2011][lcl]:

    ./run.py scenario/lcl/lcl_scenario.py --stepsize="1/(steps+10)" --maxiter=100 --tol="5e-3" -d my-run
    ./report.py my-run --movie -v0 -e5

[lcl]: (https://ieeexplore.ieee.org/abstract/document/6039082/)

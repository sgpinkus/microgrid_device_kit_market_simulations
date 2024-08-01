# MICROGRID DEVICE_KIT MARKET SIMULATIONS
This is a simple wrapper over [device_kit](https://github.com/sgpinkus/device_kit) microgrid modelling tool, that simulates market / auction based price adjustment (or equivalently distributed gradient descent), to find an optimal resource allocation and corresponding prices. Currently only supports point bid agent strategy with an optional proximal penalty. Some convenience scripts to generate plots and gifs are included.

# INSTALLATION

```
git clone https://github.com/sgpinkus/device_kit_market_simulations && cd device_kit_market_simulations
pip install -r requirements.txt
```

# USAGE
`run.py` runs `device_kit` "scenarios" which are model of day-ahead flexibility to do anything. Example:

    ./run.py device_kit/sample_scenarios/ev_charge_scenario.py -i50

This will create a directory in the CWD that stores the results. The results can be inspected with `report.py`.

This more complex scenario is a variation of the scenario presented in [Li, Chen & Low 2011][lcl]:

    ./run.py scenario/lcl/lcl_scenario.py --stepsize="1/(steps+10)" --maxiter=100 --tol="5e-3" -d my-run
    ./report.py my-run --movie -v0 -e5

[lcl]: https://ieeexplore.ieee.org/abstract/document/6039082/

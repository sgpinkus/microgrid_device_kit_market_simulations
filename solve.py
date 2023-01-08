#!/usr/bin/env python3
''' Convenience script to just solve for outright cost minimized balanced flow - no market sim crap.
'''
from os.path import basename
import logging
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import argparse
from scipy.optimize import minimize
import device_kit
from device_kit_market_simulations.run import load_scenario

logging.basicConfig()
logging.getLogger().setLevel(logging.INFO)
np_printoptions = {
  'linewidth': 1e6,
  'threshold': 1e6,
  'formatter': {
    'float_kind': lambda v: '%+0.3f' % (v,),
    'int_kind': lambda v: '%+0.3f' % (v,),
  },
}
np.set_printoptions(**np_printoptions)


def main():
  parser = argparse.ArgumentParser(description='Run a power market simulation.')
  parser.add_argument('scenario', action='store',
    help='name of a python module containing scenario to run'
  )
  # parser.add_argument('--ftol',
  #   dest='ftol', type=float, default=1e-4,
  #   help='function tolerance for convergence of solution')
  # parser.add_argument('-d',
  #   dest='output_dir', default=None, type=str,
  #   help='where to dump simulation data. If not provided dumped to tmp file'
  # )
  args = parser.parse_args()

  (scenario, meta, _void) = load_scenario(**vars(args))
  scenario.sbounds = (0,0)
  (x, solve_meta) = device_kit.solve(scenario, p=0) # Convenience convex solver.
  print(solve_meta.message)
  df = pd.DataFrame.from_dict(dict(scenario.map(x)), orient='index')
  df.loc['total'] = df.sum()
  pd.set_option('display.float_format', lambda v: '%+0.3f' % (v,),)
  print(df.sort_index())
  print('Utility: ', scenario.u(x, p=0))
  df.transpose().plot(drawstyle='steps', grid=True)
  plt.ylabel('Power (kWh)')
  plt.xlabel('Time (H)')
  plt.savefig('solve.png');


main()

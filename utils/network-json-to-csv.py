#!/usr/bin/env python3
''' This script loads a configuration, then prints it, and exits. Mainly for testing / inspection. '''
import sys
import logging
import json
import numpy as np
import pandas as pd
from pprint import pprint
from device_kit_market_simulations.writer import *
from device_kit_market_simulations.reporting.templates import *


logging.basicConfig()
logging.getLogger().setLevel(logging.INFO)

# https://pandas.pydata.org/pandas-docs/stable/generated/pandas.set_option.html
pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 500)
pd.set_option('display.width', 1000)
pd.set_option('display.float_format', lambda v: '%+0.6f' % (v,),)


def main():
  if len(sys.argv) <= 1:
    sys.exit('usage: %s <json-file|json-dump-dir>' % (sys.argv[0]))
  src = sys.argv[1]
  n = load_list(src)
  for i, v in enumerate(n):
    raw = dict(v.leaf_items())
    ids = ['%d.%s' % (i, k) for k in raw.keys()]
    dat = np.vstack(raw.values())
    df = pd.DataFrame(dat, index=ids)
    print(df.to_csv(float_format='%.2f'))


def load_list(src):
  paths = []
  if os.path.isdir(src):
    paths = list(NetworkReader(src))
  elif os.path.isfile(src):
    with open(sys.argv[1], 'r') as f:
      paths = [json.load(f, object_hook=JSONDecoderObjectHook)]
  return paths

main()

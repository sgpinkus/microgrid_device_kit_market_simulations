#!/usr/bin/env python3
''' This script loads a configuration, then prints it, and exits. Mainly for testing / inspection. '''
import sys
import logging
import json
from device_kit_market_simulations.reporting.writer import *
from device_kit_market_simulations.reporting.templates import *


logging.basicConfig()
logging.getLogger().setLevel(logging.INFO)


def main():
  if len(sys.argv) <= 1:
    sys.exit('usage: %s <json-file>' % (sys.argv[0]))
  print(sys.argv[1])
  with open(sys.argv[1], 'r') as f:
    d = json.load(f, object_hook=JSONDecoderObjectHook)
    print(network_to_str(d))
    indent = get_indent()
    print(json.dumps(d, indent=indent, cls=JSONEncoder))


def get_indent():
  v = sys.version_info
  indent = None
  if v.major == 3 and 4 <= v.minor <= 6:
    from . import _make_iterencode
    json.encoder._make_iterencode = _make_iterencode._make_iterencode
    indent = (2, None)
  return indent

main()

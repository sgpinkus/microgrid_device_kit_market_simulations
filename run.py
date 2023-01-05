#!/usr/bin/env python3
''' This script loads a Network configuration, initializes it, hooks up the in and outs then runs it. '''
import sys
import re
import argparse
import importlib
import time
import json
import logging
from os.path import *
from device_kit_market_simulations.network import Network
from device_kit_market_simulations.reporting.templates import network_to_str
from device_kit_market_simulations.reporting.writer import NetworkWriter, JSONDecoderObjectHook


logging.basicConfig()
logging.getLogger().setLevel(logging.INFO)
logger = logging.getLogger(__name__)


def main():
  parser = argparse.ArgumentParser(description='Run a power market simulation.')
  parser.add_argument('scenario', action='store',
    help='name of a python module containing device_kit scenario to run.'
  )

  group = parser.add_argument_group('Network')
  group.add_argument('--network', '-n',
    dest='network_class', type=str, default=None,
    help='name of Network class to load'
  ),
  group.add_argument('--tol', '-t',
    dest='tol', type=float,
    help='tolerance for convergence of solution')
  group.add_argument('--stepsize', '-l',
    dest='stepsize', type=str,
    help='step size gradient ascent. Can be an expression'
  )
  group.add_argument('--maxsteps', '-i',
    dest='maxsteps', type=int,
    help='maximum number of iterations to perform'
  )
  group.add_argument('--agent-prox', '-p',
    dest='prox',
    help='proximal penalty for agent demand changes. Can be an expression'
  )
  group.add_argument('--agent-strategy', '-x',
    dest='agent_strategy',
    help='agent bid strategy'
  )
  group = parser.add_argument_group('Output')
  group.add_argument('-d',
    dest='output_dir', default=None, type=str,
    help='where to dump simulation data. If not provided dumped to tmp file'
  )
  group.add_argument('-v', dest='verbose', default=0, type=int,
    help='verbosity'
  )

  args = parser.parse_args()
  (network, meta, matplotlib_cb) = load_network(**vars(args))
  output_dir = args.output_dir if args.output_dir else '{filename}-{time}-network'.format(
    filename=basename(args.scenario),
    time=time.strftime('%Y%m%d-%H%M%S%z'),
  )

  # Init writers, run, close writers.
  # NetworkWriter just dumps JSON file encoding complete network with every call to update().
  writers = load_writers(network, meta, output_dir, args, matplotlib_cb)
  listeners = [
    lambda network, event, verbose=args.verbose: print_listener(network, event, verbose),
    lambda network, event, w=writers: [writer.update(network, event) for writer in w]
  ]
  network.run(listeners)
  [writer.close() for writer in writers]


def load_writers(network, meta, output_dir, args, matplotlib_cb):
  ''' Load default writers. '''
  writers = [
    NetworkWriter(network, output_dir, meta)
  ]
  return writers


def load_network(scenario, network_class=None, **kwargs):
  ''' Load scenario which either a couple JSON files or a conforming python module.
  Python module:
    contains a function called make_network(**kwargs)
  JSON:
    The input file must be a JSON encoded Network created by serializing Network.to_dict(). This
    script creates JSON dumps of the Network instantiated from a scenario module so they can be
    (possibly modified, then) reloaded. If a meta.json file in same dir as main JSON network file
    it is loaded as meta (described above).

  @todo don't always want to (re)init() Network loaded from JSON.
  '''
  meta = None
  cb = None

  print('Loading %s' % (scenario))
  if re.match('.*\.py$', scenario):
    try:
      scenario = importlib.import_module(make_module_path(scenario))
      meta = scenario.meta if hasattr(scenario, 'meta') else None
      cb = scenario.matplot_network_writer_hook if hasattr(scenario, 'matplot_network_writer_hook') else None
    except Exception as e:
      logger.error('Could not load scenario "%s" [%s]' % (scenario, e))
      sys.exit(1)
    print('Loaded scenario module %s.' % (scenario,))
    print('Loading network')
    known_network_args = ['maxiter', 'tol', 'stepsize', 'prox', 'agent_strategy']
    network_params = {k: v for k, v in kwargs.items() if k in known_network_args and v is not None}
    if network_class is None:
      network = Network
    else:
      try:
        network = make_module_path(network_class)
        module, classname = '.'.join(network.split('.')[0:-1]), network.split('.')[-1]
        network = getattr(importlib.import_module(module), classname)
      except Exception as e:
        logger.error('Could not load network "%s" [%s]' % (network_class, e))
        sys.exit(1)
    network = network(scenario.make_deviceset(), **network_params)
  elif re.match('.*\.json$', scenario):
    try:
      with open(scenario, 'r') as f:
        network = json.load(f, object_hook=JSONDecoderObjectHook)
      meta_filename = dirname(scenario) + '/' + 'meta.json'
      if isfile(meta_filename):
        with open(meta_filename, 'r') as f:
          meta = json.load(f)
    except Exception as e:
      print('Could not load %s. [%s]' % (scenario, e))
      sys.exit(1)
    print('Loaded scenario JSON file %s.' % (scenario,))
  else:
    print('Could not load %s. [Unknown format]' % (scenario,))
    sys.exit(1)
  print('Initializing network [%s]' % (network.__class__.__name__))
  network.init()
  print('Initialize network done [%s]' % (network.__class__.__name__))
  return (network, meta, cb)


def make_module_path(s):
  ''' Convert apossible filepath to a module-path. Does nothing it s is already a module-path '''
  return s.replace('.py', '').replace('/', '.').replace('..', '.').lstrip('.')


def print_listener(network, event, verbose=0):
  if event in ('after-step', 'after-init'):
    print('--- %d %s' % (network.steps, '-'*100))
    print(network_to_str(network, verbose))

if __name__ == '__main__':
  main()

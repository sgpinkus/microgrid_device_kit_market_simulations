import contextlib
import numpy as np
import matplotlib.pyplot as plt
from device_kit_market_simulations.network import Network


colors = ['red', 'orange', 'yellow', 'purple', 'fuchsia', 'lime', 'green', 'blue', 'navy', 'black']
np_printoptions = {
    'linewidth': 1e6,
    'threshold': 1e6,
    'formatter': {
      'float_kind': lambda v: '%+0.4f' % (v,),
      'int_kind': lambda v: '%+0.4f' % (v,),
    },
  }


@contextlib.contextmanager
def printoptions(*args, **kwargs):
    original = np.get_printoptions()
    np.set_printoptions(*args, **kwargs)
    try:
        yield
    finally:
        np.set_printoptions(**original)


def network_to_str(network: Network, verbose=0):
  ''' Summary stats for network. Note supplier cost only really make sense in scenarios where there
  are one or more strict suppliers, and at the top level. Use pseudo convention that suppliers must
  be id-ed like 'supply'.
  '''
  suppliers = [a for a in network.deviceset.devices if a.id.find('supply') >= 0]
  num_agents = len(network.deviceset.devices)
  zeros = np.zeros(len(network))
  _str = ''
  _str += '%-22s %d\n' % ('num_agents', num_agents)
  _str += '%-22s %.4f\n' % ('load_factor', network.lf)
  _str += '%-22s %.4f\n' % ('peak', network.demand.max())
  _str += '%-22s %.4f\n' % ('price (avg)', np.average(network.price))
  _str += '%-22s %.4f; %.4f\n' % ('excess (tot/avg)', network.excess.sum(), np.average(network.excess))
  _str += '%-22s %.4f; %.4f\n' % ('demand (tot/avg)', network.demand.sum(), np.average(network.demand))
  _str += '%-22s %.4f; %.4f\n' % ('supply (tot/avg)', network.supply.sum(), np.average(network.supply))
  _str += '%-22s %.4f; %.4f\n' % ('cost [p*demand] (tot/avg)', (network.supply*network.price).sum(), np.average(network.supply*network.price))
  _str += '%-22s %.4f; %.4f\n' % ('utility (tot/avg)', network.u(), network.u()/num_agents)
  _str += '%-22s %.4f; %.4f\n' % ('utility[p=0] (tot/avg)', network.deviceset.u(network.s, p=zeros), network.u()/num_agents)
  _str += '%-22s %d/%d\n' % ('steps', network.steps, network.maxsteps)
  _str += '%-22s %.6f\n' % ('stepsize', network.get_stepsize())
  _str += '%-22s %s (thold=%.4f)\n' % ('stable', network.stable, network.tol)
  with printoptions(**np_printoptions):
    if verbose:
      _str += '%-12s %s\n' % ('cost', network.cost)
      _str += '%-12s %s\n' % ('price', network.price)
      _str += '%-12s %s\n' % ('excess', network.excess)
      _str += '%-12s %s\n' % ('demand', network.demand)
      _str += '%-12s %s\n' % ('supply', network.supply)
      _str += '%-12s %s\n' % ('utilities', np.array([d.u(network.s[slice(*_slice),:], network.price) for d, _slice in network.deviceset.slices]))
      _str += '%-12s %s\n' % ('utilities[p=0]', np.array([d.u(network.s[slice(*_slice),:], zeros) for d, _slice in network.deviceset.slices]))
    if verbose > 1:
      for a in network.deviceset:
        _str += '%-8s %s\n' % (a.id, a.r)
        if verbose > 2:
          for (k, v) in a.leaf_items():
            _id = a.id + '.' + k
            _str += '%-16s %s\n' % (_id, str(v))
  return _str
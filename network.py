import sys
import logging
import numpy as np
import pandas as pd
from scipy import linalg
from multiprocessing import Pool
from device_kit import DeviceSet, OptimizationException, solve, step
from device_kit.sample_scenarios.lcl.lcl_scenario import make_deviceset


logging.basicConfig()


def agent_point_bid_update(x):
  solver_options = {  # Default options to 'solver' - scipy.optimize.minimize - where it's used.
    'ftol': 1e-06,
    'maxiter': 500,
    'disp': False,
  }
  (device, p, s0, prox) = x
  try:
    result = solve(device, p, s0, solver_options=solver_options, prox=prox)
  except OptimizationException as e:
    logging.warn('OptimizationException on %s agent :\n%s', device.id, e)
  return result[0].reshape(device.shape)


def agent_limited_minimization_update(x):
  solver_options = {  # Default options to 'solver' - scipy.optimize.minimize - where it's used.
    'ftol': 1e-06,
    'maxiter': 500,
    'disp': False,
  }
  (device, p, s0, prox) = x # TODO: Ignoring pro
  try:
    result = step(device, p, s0, solver_options=solver_options)
  except OptimizationException as e:
    logging.warn('OptimizationException on %s agent :\n%s', device.id, e)
  return result[0].reshape(device.shape)


class Network:
  ''' Simulates a price adjustment process. Each top level device of a device_kit DeviceSet is
  considered owned by some agent. run() method passes each agent a price vector, asks for bid back,
  then adjusts prices until equillibrium of maxsteps. This price adjustment procedure is exactly
  equivalent to distributed gradient descent, where is "agent" solves separable part of the problem.
  '''
  tol = None            # Used for stability condition. Units of watts. @see stable().
  maxsteps = None       # Max iterations condition.
  stepsize = None       # Step size passed to agents. Not used directly here.
  prox = None
  steps = 0          # Step counter. @see step(), solve().
  demand = price = 0    # Demand and price a vectors with same length as deviceset.
  last_demand = last_price = 0   # Internally track changes as converge to equilibrium price.
  s = 0                 # The entire flow matrix for the deviceset.
  deviceset = None
  agent_strategy = agent_point_bid_update

  def __init__(self,
    deviceset: DeviceSet, tol=1e-3, maxsteps=100, stepsize=1e-3, agent_strategy=None, s=None, price=None,  **kwargs
  ):
    ''' Init things. kwargs hack to support deserialization mainly. '''
    self.deviceset = deviceset
    self.tol = tol
    self.maxsteps = maxsteps
    self.stepsize = stepsize
    self.set_price(price)
    self.set_s(s)
    self.set_agent_strategy(agent_strategy)
    self.last_demand = np.zeros(len(self))
    self.last_price = np.zeros(len(self))
    self.logger = logging.getLogger('network')
    self.logger.setLevel(logging.INFO)
    for k, v in kwargs.items():
      setattr(self, k, v)

  def __str__(self):
    _str = ''
    _str += '%-12s %s\n' % ('price', self.price)
    _str += pd.DataFrame(self.deviceset.map(self.s)).transform()


  def __len__(self):
    return len(self.deviceset)

  def init(self, solve=True):
    self.steps = 0
    self.price = np.zeros(len(self))
    self.s = np.zeros(self.deviceset.shape)
    self.last_demand = np.zeros(len(self))
    self.last_price = np.zeros(len(self))

  def run(self, listeners=[]):
    ''' Solve for optimal by stepping until stability. Use callbacks to instrumentate. Note,
    only at equillibrium (if one exists) is demand actually that demanded at the current price and vice versa.
    At any other given time one or the other is always out of step. Supposing a point bid strategy (the default),
    demand is demand at last_price or price is price at last_demand. At "after-step" demand is rel last_price and
    price is rel current demand.
    '''
    listeners.append(lambda n, e, logger=self.logger: logger.debug('%s-12 %s: %s' % (e, n.steps, str(n.excess))))
    with Pool(processes=len(self.deviceset.devices)) as pool:
      self.init()
      [cb(self, 'before-start') for cb in listeners]
      while self.steps == 0 or not self.stable and self.steps < self.maxsteps:
        (self.last_demand, self.last_price) = (self.demand, self.price)  # Stash for stability calculation.
        prox = None if self.steps == 0 else self.get_prox() # Ensure prox is 0 so demand goes to 0 price optimal on first step.
        _map = [(device, self.price, self.s[slice(*_slice),:], prox) for device, _slice in self.deviceset.slices]
        _s = pool.map(self.agent_strategy, _map)
        self.s = np.array(np.concatenate(_s)).reshape(self.deviceset.shape)
        self.update_price()
        self.steps += 1
        [cb(self, 'after-step') for cb in listeners]
      [cb(self, 'after-done') for cb in listeners]
    return self.steps < self.maxsteps

  def update_price(self):
    ''' Update global network price. Many variations to price adjustment methods have been proposed.
    Generally the can be categorized as synchronous vs asynchronous and point base vs function based.
    This implementation is the most basic type of point based, synchronous implementation (in which
    we have no information about demand/supply function gradients). Also price is adjusted in linear
    proportion to the excess which is the "standard" original way. Some possible alternatives:
      - a * r                               // Standard point based linear.
      - a * normal(r)                       // Effectively just a different step size.
      - a * r * randint(0,2,size=len(self)) // Simulate asynchronous bid/offer.
    '''
    self.price = self.price + self.get_stepsize() * self.excess

  def get_stepsize(self):
    ''' If a str interpret it as dynamic stepsize expression. First step value will be 0. '''
    if isinstance(self.stepsize, str):
      return eval(self.stepsize, {'steps': self.steps})
    return self.stepsize

  def get_prox(self):
    if isinstance(self.prox, str):
      return eval(self.prox, {'steps': self.steps})
    return self.prox

  def u(self):
    return self.deviceset.u(self.s, self.price)

  def set_price(self, p):
    self.price = (np.ones(len(self))*p).reshape(len(self)) if p else np.zeros(len(self))

  def set_s(self, s, copy=False):
    if not s:
      self.s = np.zeros(self.deviceset.shape)
    else:
      if not isinstance(s, np.ndarray) or copy:
        s = np.array(s, copy=copy)
      self.s = s.reshape(self.deviceset.shape)

  def set_agent_strategy(self, name):
    if not name:
      self.agent_strategy = agent_point_bid_update
    elif name == 'limited_minimization':
      self.agent_strategy = agent_limited_minimization_update
    else:
      raise Exception('Unkown agent update strategy "%s"' % (name,))

  def map(self):
    return self.deviceset.map(self.s)

  def df(self):
    return pd.DataFrame(dict(self.map())).transpose()

  @property
  def excess(self):
    ''' Can be +ve or -ve to depending on excess demand (+ve) or supply (-ve) at last price. '''
    return self.s.sum(axis=0)

  @property
  def demand(self):
    ''' Outright demand vector. '''
    return np.maximum(self.s, 0).sum(axis=0)

  @property
  def supply(self):
    ''' Outright supply vector. '''
    return np.minimum(self.s, 0).sum(axis=0)

  @property
  def normal(self):
    r = self.excess
    return r/(np.square(r).sum()**(1/2.))

  @property
  def stability(self):
    return self.excess

  @property
  def stable(self):
    return (np.abs(self.excess) <= self.tol).all()

  @property
  def lf(self):
    _max = self.demand.max()
    return np.average(self.demand)/_max if _max else 1

  @property
  def cost(self):
    return self.demand*self.price

  def to_dict(self):
    ''' Dump object as a dict. '''
    return {
      'deviceset': self.deviceset,
      'price': self.price.tolist(),
      's': self.s.tolist(),
      'tol': self.tol,
      'maxsteps': self.maxsteps,
      'stepsize': self.stepsize,
      'steps': self.steps,
      'last_demand': self.last_demand,
      'last_price': self.last_price,
    }

  @classmethod
  def from_dict(cls, d):
    return cls(**d)


if __name__ == '__main__':
  deviceset = make_deviceset()
  m = Network(deviceset)
  m.run()

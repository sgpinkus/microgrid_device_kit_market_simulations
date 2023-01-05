import os
import re
import numpy as np
from urllib.request import quote
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, Animation
import logging
from logging import *
from copy import deepcopy
from ..network import Network


class MatPlotNetworkWriter():
  ''' NetworkWriter that draws a live matplotlib plot of simulation. On close will converts bunch of
  PNG files generated with matplotlib into a GIF.

  This write can be used on any DeviceAgent, not just a network.

  Has to use system call to `iconv` for GIF gen as could not get matplotlib animation to do this!
  '''
  network = None
  title = None        # Title for plot.
  fig = ax = None     # Refs to matplotlib figure and axes.
  frame_count = -1    # How many times update() has been called.
  each = 1            # How many calls to update() per rendering image.
  save = True         # Whether to save an image when done.
  save_animation = False
  output_dir = None     # A working dir.
  file_prefix = None  # For output file.
  fltr = None         # Sub item fltr.
  _colors = ['red', 'orange', 'yellow', 'purple', 'fuchsia', 'lime', 'green', 'blue', 'navy', 'black']
  ylim  = (None, None)
  plot_globals = True

  def __init__(self, network: Network, output_dir=None, title=None, description=None, save=True, save_animation=True, fltr=None, cb=None, each=1):
    self.network = network
    self.title = title
    self.save = save
    self.save_animation = save_animation
    self.fltr = fltr
    self.cb = cb
    self.each = each
    self.output_dir = output_dir if output_dir else'/tmp/{id}-network-animation'.format(id=network.deviceset.id)
    if not os.path.isdir(self.output_dir):
      os.mkdir(self.output_dir)
    logging.info('Output to %s' % (output_dir,))
    self.fig, self.ax = plt.subplots()
    self.init_plot()

  def init_plot(self):
    plt.ion()
    self.cb('after-init', plt, self) if self.cb else False

  def update(self, network, event, force=False):
    ''' Plot price and consumption of network. '''
    self.frame_count += 1
    if self.frame_count%self.each == 0 or force:
      self._plot(network)

  def _plot(self, network):
    # Setup canvas.
    self.ax.clear()

    if self.plot_globals:
      self.ax.plot(range(0, len(network)), network.price, color='b', label='price')
      self.ax.plot(range(0, len(network)), network.excess, color='r', label='excess')

    # Plot possibly filtered list of items of network as stacked bars.
    df = network.df()
    if self.fltr:
      df_sums = df.filter(like=self.fltr, axis=0)
    else:
      df_sums = df.groupby(lambda l: l.split('.')[1]).sum()
    bottom = np.zeros(len(network))
    neg_bottom = np.zeros(len(network))
    for (i, (label, r)) in enumerate(df_sums.iterrows()):
      use_bottom = np.choose(np.array(r < 0, dtype=int), [bottom, neg_bottom])
      self.ax.bar(range(0, len(network)), r, color=self._colors[i%len(self._colors)], label=label, bottom=use_bottom)
      neg_bottom += np.minimum(np.zeros(len(network)), r)
      bottom += np.maximum(np.zeros(len(network)), r)

    # Setup ax meta.
    self.ax.set_xlim(-2, len(network)+2)
    self.ax.set_ylim(*self.ylim)
    self.ax.set_title(self.title)
    self.ax.legend(
      prop={'size': 12},
      loc='upper right',
      framealpha=0.6,
      frameon=True,
      fancybox=True,
      borderaxespad=-3
    )

    self.cb('after-update', self.fig, self) if self.cb else False

    if self.save:
      filename = self._make_filename('%04d' %(self.frame_count,))
      self.fig.savefig(filename)
      self.fig.savefig(self._make_filename('%04d' %(self.frame_count,), 'eps'))
      logging.info('Saved image %s' % (filename,))
    else:
      logging.info('Not saving image')

  def close(self):
    if self.save_animation:
      out_file = '%s/%s%s.gif' % (self.output_dir, 'animation', "-" + str(self.fltr) if self.fltr else "")
      glob = self._make_filename("*")
      cmd = 'convert -loop 0 -delay 30 %s %s' % (glob, out_file)
      logging.info('Writer wrote generated graphics: %s / %s' % (cmd, os.system(cmd)))
      # logging.info('Writer spawning image viewer')
      # os.spawnlp(os.P_NOWAIT, 'display', 'display', out_file)
    else:
      logging.info('Not saving animation')

  def _make_filename(self, part, ext='png'):
    return '%s/%s-%s%s-%s.%s' % (self.output_dir, 'animation', self.network.deviceset.id, "-" + str(self.fltr) if self.fltr else "", part, ext)


#!/usr/bin/env python3
''' Convenience script to dump some graphics and numbers. '''
import sys
import os
import re
import argparse
import logging
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from device_kit import *
from device_kit_market_simulations.network import Network
from device_kit_market_simulations.reporting.writer import NetworkReader
from device_kit_market_simulations.reporting.templates import network_to_str, colors
from device_kit_market_simulations.reporting.matplotlibwriter import MatPlotNetworkWriter


logging.basicConfig()
logging.getLogger().setLevel(logging.INFO)


def main():
  # Parse args.
  parser = argparse.ArgumentParser(description='LCL simulation report generator.')
  parser.add_argument('data_dir', type=str,
    help='directory containing simulation results'
  )
  parser.add_argument('--std-plots', '-p', dest='std_plots', action='store_true',
    help='generate a various PNG plots for steps of network'
  )
  parser.add_argument('--more-plots', '-m', dest='more_plots', action='store_true',
    help='generate a various PNG plots for steps of network'
  )
  parser.add_argument('-i', dest='max_steps', default=-1, type=int,
    help='max number of steps'
  )
  parser.add_argument('-v', dest='verbose', default=0, type=int,
    help='verbosity'
  )
  parser.add_argument('--movie', dest='movie', action='store_true',
    help='generate a movie (GIF) for steps of network'
  )
  parser.add_argument('--movie-target', dest='fltr',
    help='generate a various PNG plots for steps of network'
  )
  parser.add_argument('--movies', dest='movies', action='store_true',
    help='generate a movie for all top level network agents'
  )
  parser.add_argument('--each', '-e', dest='each', default=10, type=int,
    help='how many steps between each frame of movie'
  )

  args = parser.parse_args()
  output_dir = args.data_dir.rstrip('/') + '-report'

  if not os.path.isdir(args.data_dir):
    print('Not a directory [%s]' % (args.data_dir,))
    sys.exit()
  if not os.path.isdir(output_dir):
    os.makedirs(output_dir)

  reader = NetworkReader(args.data_dir)
  (first, last) = (reader.first(), reader.last())

  # Generate CLI output.
  if args.verbose:
    for i, network in enumerate(reader):
      print('--- %d %s' % (i, '-'*100))
      print(network_to_str(network, args.verbose))
  print('--- FIRST %s' % ('-'*100,))
  print(network_to_str(first, args.verbose+1))
  print('--- LAST %s' % ('-'*100,))
  print(network_to_str(last, args.verbose+1))
  # print('--- DIFFERENCE LAST - FIRST %s' % ('-'*100,))
  # print(network_diff(last, first))

  # Generate CSV Output
  for i, network in enumerate(reader):
    df = network.df()
    print(df)
    df.to_csv('%s/network-%d.csv' % (output_dir, i), float_format='%.5f', header=None)

  # # Movie of network.
  # if args.movie:
  #   movie = MatPlotNetworkWriter(first, output_dir, fltr=args.fltr, each=args.each, **reader.meta)
  #   movie.ylim = get_ylim(first, last, lambda x: movie._fltr(x, args.fltr))
  #   for i, network in enumerate(reader):
  #     movie.update(network, 'after-step', force=(i == len(reader)-1))
  #   movie.close()
  # # Movie of all network child agents.
  # if args.movies:
  #   # Calculate fixed ylim for series of plots in advance based on first and last.
  #   ylims = [get_ylim(f,l, lambda x: MatPlotNetworkWriter._fltr(x, "")) for f,l in zip(first.agents, last.agents)]
  #   for i, agent in enumerate(network.agents):
  #     agent = network.agents[i]
  #     movie = MatPlotNetworkWriter(agent, output_dir, each=args.each, save_animation=False, fltr="", **reader.meta)
  #     movie.ylim = ylims[i]
  #     for j, network in enumerate(reader):
  #       agent = network.agents[i]
  #       logging.info("%d %d %s", i,j, agent.id)
  #       movie.plot_globals = False
  #       movie.update(agent, 'after-step', force=True) #(i == len(reader)-1))
  #     movie.close()
  # Generate std set of still images.
  if args.std_plots:
    report_plots(reader, output_dir)
  # Generate std set of additional still images.
  if args.more_plots:
    report_plots_market_trends(reader, output_dir)


def get_ylim(first, last, fltr):
  first = np.array(list(dict(fltr(first)).values()))
  last  = np.array(list(dict(fltr(last)).values()))
  ymax = max(np.maximum(first, 0).sum(axis=0).max(), np.maximum(last, 0).sum(axis=0).max())*1.05
  ymin = min(np.minimum(first, 0).sum(axis=0).min(), np.minimum(last, 0).sum(axis=0).min())*1.05
  return ymin, ymax


def report_plots(reader, output_dir):
  ''' Print some standard summary plots with matplotlib. '''
  init = reader.first()
  final = reader.last()
  # Total demand
  plt.bar(range(0, len(init)), reader.first().demand, label='demand-zero-price', edgecolor='r', fill=False)
  plt.bar(range(0, len(init)), reader.last().demand, label='demand-final', edgecolor='b', fill=False)
  plt.title('Total demand (KWH)')
  plt.legend()
  plt.savefig(output_dir + '/total-demand.png')
  plt.clf()
  # For each agent for each sub-device (if any) initial base-case demands c/w total.
  report_plots_agents(plt, init, 'Total demand initial (KWH)', 'demand-init-agent', output_dir)
  report_plots_agents(plt, final, 'Total demand final (KWH)', 'demand-final-agent', output_dir)


def report_plots_agents(plt, network, title, filename, output_dir):
  df = network.df()
  df_sums = df.groupby(lambda l: l.split('.')[1]).sum()
  for i, agent_label in enumerate(df_sums.index):
    plt.bar(range(0, len(network)), df_sums.loc[agent_label], label='total', width=1, edgecolor='black', fill=False, linewidth=2)
    df_agent = df.filter(like=agent_label, axis=0)
    for (i, (device_label, r)) in enumerate(df_agent.iterrows()):
      plt.bar(range(0, len(network)), r, label=device_label, width=1, edgecolor=colors[(i+1)%len(colors)], fill=False, linewidth=2)
    plt.xlim(0, len(network)+10)
    plt.legend()
    plt.title('%s; Agent %s' % (title, str(agent_label)))
    plt.savefig(output_dir + '/%s-%s.png' % (filename, str(agent_label)))
    plt.clf()


def report_plots_market_trends(reader, output_dir):
  # Welfare Trend lines.
  init = reader.first()
  final = reader.last()
  welfare_base = reader.get(1).u()
  welfares = [n.u() - welfare_base for n in list(reader)[1:]]
  lf_base = reader.first().lf
  lf = [(n.lf - lf_base) for n in reader]
  excess = [n.excess.sum() for n in reader]
  # Plot welfare trend.
  plt.plot(welfares, label='welfare')
  plt.title('Change in welfare and with steps of market')
  plt.legend()
  plt.savefig(output_dir + '/welfares-trend.png')
  plt.clf()
  # Plot load factor trend.
  plt.plot(lf, label='lf')
  plt.title('Change in load factor with steps of market')
  plt.legend()
  plt.savefig(output_dir + '/load-factor-trend.png')
  plt.clf()
  # Plot excess demand trend.
  plt.plot(excess, label='excess demand')
  plt.title('Excess demand and with steps of market')
  plt.legend()
  plt.savefig(output_dir + '/excess-demand-trend.png')
  plt.clf()

if __name__ == '__main__':
  main()

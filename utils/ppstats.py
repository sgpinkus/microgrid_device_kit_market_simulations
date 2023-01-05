#!/usr/bin/python3
'''
Script to process output of profiler. Gen prof data like this for ex:

    python3 -m cProfile -o prof device_kit_market_simulations/utils/central-solver.py scenario1.py
    time python3 -m cProfile -o prof ./run.py scenario/single_home_against_supply.py

Gen stats like this:

    python3 ppstats.py  prof tot

'''
import sys
import pstats
sys.exit('Usage: stats <file> <sort>. See https://docs.python.org/3/library/profile.html#pstats.Stats.sort_stats') if len(sys.argv) != 3 else None
p = pstats.Stats(sys.argv[1])
p.strip_dirs().sort_stats(sys.argv[2]).print_stats(50)

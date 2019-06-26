#!/usr/bin/env python

# make sure this is run with python 2 (blah)
import sys
import os
import argparse
if sys.version_info[0] != 2:
    raise RuntimeError("This script must be run with python2.")

import utils.parser
from utils.visualizer import Visualizer

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("launch_file", help="Path to the launch file to analyze.")

    args = parser.parse_args()
    return args

if __name__ == "__main__":
    # parse arguments
    args = parse_args()

    # sanity check arguments
    if not os.path.isfile(os.path.expanduser(args.launch_file)):
        raise RuntimeError("Cannot find launch file {}".format(args.launch_file))

    # parse launch file
    graph = utils.parser.build_graph(args.launch_file, verbose=False)

    # construct visualizer and plot
    visualizer = Visualizer(args.launch_file, graph)
    visualizer.plot()

    import code
    code.interact(local=locals())
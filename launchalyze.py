#!/usr/bin/env python

# make sure this is run with python 2 (blah)
import sys
import os
import argparse
import logging
if sys.version_info[0] != 2:
    raise RuntimeError("This script must be run with python2.")

import utils.parser
from utils.visualizer import Visualizer

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("launch_info", help="Path to the launch file to analyze and optional arguments", nargs="+")
    parser.add_argument("-v", "--verbose", help="increase output verbosity", action="store_true")
    parser.add_argument("-q", "--quiet", help="decrease output verbosity", action="store_true")
    parser.add_argument("-np", "--noplot", help="don't plot the generated html", action="store_true")

    args = parser.parse_args()
    return args

if __name__ == "__main__":
    # parse arguments
    args = parse_args()

    # sanity check arguments
    launch_file = args.launch_info[0]
    if not os.path.isfile(os.path.expanduser(launch_file)):
        raise RuntimeError("Cannot find launch file {}".format(launch_file))

    input_arguments = {}
    for argument in args.launch_info[1::]:
        if ":=" not in argument:
            raise RuntimeError("Input arguments must follow format 'ARG:VALUE'; got '{}']".format(argument))
        arg, value = argument.split(":=")
        input_arguments[arg] = value

    if args.verbose:
        level = logging.DEBUG
    elif args.quiet:
        level = logging.WARNING
    else:
        level = logging.INFO
    logging.basicConfig(level=level)
    logger = logging.getLogger(__name__)

    # parse launch file
    logger.info("Analyzing {} with arguments {}".format(launch_file, input_arguments))
    graph = utils.parser.build_graph(launch_file, input_arguments, args.verbose)

    # construct visualizer and plot
    visualizer = Visualizer(launch_file, graph)
    if not args.noplot:
        visualizer.plot()

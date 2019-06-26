""" Module of classes / functions for parsing launch files.

@TODO clean up the recursive parsing stuff; make it less hardcoded
@TODO figure out what to do if our keys (full launch file path) are non-unique (which they might be?)
"""

import os
import re
import copy
import argparse
from collections import defaultdict
import xml.etree.ElementTree as ET

from roslaunch.config import ROSLaunchConfig
from roslaunch.xmlloader import XmlLoader

from substitution_args import SubstitutionArgs

""" Class to store directional information about launch files (i.e. Network Graph representation).

This class also contains and API to parse for child launch files (found via the 'include' tag) and
child nodes (found via the 'node' tag). In order to do this properly it also searches for and evaluates
all input and contextual arguments.
"""
class LaunchFile:
    substituter = None
    verbose = False
    initialized = False

    """Set class variables; this should be called once and only once before any instances are instantiated.
    """
    @classmethod
    def initialize(cls, verbose=False):
        if cls.initialized:
            raise RuntimeError("Initialize called on already initialized LaunchFile")
        
        cls.verbose = verbose
        cls.substituter = SubstitutionArgs(verbose)
        cls.initialized = True

    def __init__(self, fullpath, parent=None, input_arguments=None, namespace="/"):
        # sanity check that fullpath is a real file
        if not os.path.isfile(fullpath):
            raise RuntimeError("Unable to find launch file {}".format(fullpath))

        # file location information
        self.fullpath = fullpath
        self.name = os.path.basename(fullpath)
        self.path = os.path.dirname(fullpath)
        self.namespace = namespace

        # Node graph information
        self.parent = parent
        self.children = None

        # get the XML object representation of this file 
        self.xml_context = self._get_xml_context()

        # parse arguments; incoming and internal. This is necessary to properly evaluate all substitution arguments in the file.
        self.input_arguments = {} if input_arguments is None else input_arguments
        self.print_("Parsing top level arguments for {}".format(self.name))
        self.args = self.parse_arguments(self.xml_context, self.input_arguments)

    """Determine all the top level arguments of this launch file, as well as those sent via the parent.
    """
    def parse_arguments(self, xml_to_parse, arg_context):
        # callback performed upon elements that match the 'arg' tag.
        def parsing_callback(arg, arguments, namespace):
            name = arg.attrib["name"]
            input_arg = arg_context[name] if name in arg_context.keys() else None

            # interpret arg based on default / value tags
            if "default" in arg.attrib.keys():
                value = input_arg if input_arg else arg.attrib["default"]
            elif "value" in arg.attrib.keys():
                # warn if we passed an argument that will be unused
                if input_arg:
                    print("Warning: argument {} passed to {} is unused.".format(name, self.name))
                value = arg.attrib["value"]
            else:
                # no default, this must be an input
                if not input_arg:
                    raise RuntimeError("arg {} required in {}".format(name, self.name))
                value = input_arg
        
            arguments[name] = self.substituter.evaluate(value, arg_context, arguments)

        # convenience object to set up parsing configuration parameters
        config = self.RecursiveParseConfig(
            primary_context=arg_context,
            tag="arg",
            namespace=self.namespace,
            callback=parsing_callback,
            use_secondary_context=True)

        parsed_arguments = self.recursive_parse(config, xml_to_parse, {})
        return parsed_arguments

    """Parse this launch files XML and return the element/fullpath of all child nodes.
    """
    def get_nodes(self):
        self.print_("Getting nodes spawned by {}".format(self.name))

        def parsing_callback(node, nodes, namespace):
            name = self.substituter.evaluate(node.attrib["name"], self.args)
            nodes.append(namespace + name)

        # convenience object to set up parsing configuration parameters
        config = self.RecursiveParseConfig(
            primary_context=self.args,
            tag="node",
            namespace=self.namespace,
            callback=parsing_callback)

        parsed_nodes = self.recursive_parse(config, self.xml_context, [])
        self.nodes = parsed_nodes
        return parsed_nodes

    """Parse this launch files XML and return the element/fullpath of all child launch files.
    """
    def get_children(self):

        print("Getting children of {}".format(self.name))

        def parsing_callback(child_element, children, namespace):
            # get file name (relative path)
            if not "file" in child_element.attrib.keys():
                raise KeyError("Unable to find 'file' attribute for an include in {};".format(self.fullpath))
        
            file_ = copy.copy(child_element.attrib["file"])
            path = self.substituter.evaluate(file_, self.args)

            children[path]["namespace"] = namespace
            children[path]["element"] = child_element

            self.print_("Parsing input arguments for {}".format(path))
            children[path]["args"] = self.parse_arguments(child_element, self.args)

            self.print_("Added child {} to {}".format(file_, self.name))

        # set up configuration parameters for parser
        config = self.RecursiveParseConfig(
            primary_context=self.args,
            tag="include",
            namespace=self.namespace,
            callback=parsing_callback)

        elements = defaultdict(lambda: {"element": None, "args": None, "namespace": None})
        parsed_children = self.recursive_parse(config, self.xml_context, elements)
        self.children = list(parsed_children.keys())
        return parsed_children

    #------------------------------------- INTERNAL FUNCTIONS ------------------------------------#

    """ Convenience object to set up parsing configuration parameters
    """
    class RecursiveParseConfig:
        def __init__(self, primary_context, tag, callback, namespace, secondary_tags=["group"], use_secondary_context=False):
            self.primary_context = primary_context
            self.primary_tag = tag
            self.secondary_tags = secondary_tags
            self.namespace = namespace
            self.callback = callback
            self.use_secondary_context = use_secondary_context

    """ Traverse a given XML object and return all the matching 'tags' that satisfy our if/unless conditions.

    Args:
        xml_context:        The xml.etree.ElementTree.Element to parse.
        primary_context:    A dict containing contextual information for evaluating substitution_arg based strings.

    @todo remove xml_context / elements structure from config
    """
    def recursive_parse(self, config, xml_context, elements):
        if not isinstance(config, self.RecursiveParseConfig):
            raise RuntimeError("Config must be of class type 'RecursiveParseConfig'.")

        def _recursive_parse(config, xml_context, elements, namespace):
            for element in xml_context:
                # ignore all other tags than those specified
                if (element.tag != config.primary_tag) and (element.tag not in config.secondary_tags):
                    continue

                # check if we should use our own elements as args to evaluate the given expression
                extra_args = elements if config.use_secondary_context else {}

                # useful variables
                attrib = element.attrib
                skip = False
                
                # evaluate any if/unless statements
                if "if" in attrib.keys() and not self.substituter.evaluate_if(attrib["if"], config.primary_context, extra_args):
                    self.print_("Skipping '{}' because if='{}' evaluated to False.".format(element.tag, attrib["if"]))
                    skip = True
                if "unless" in attrib.keys() and not self.substituter.evaluate_unless(attrib["unless"], config.primary_context, extra_args):
                    self.print_("Skipping '{}' because unless='{}' evaluated to True.".format(element.tag, attrib["unless"]))
                    skip = True

                if skip:
                    continue

                # get namespace information:
                sub_namespace = ""
                if "ns" in attrib.keys():
                    sub_namespace += self.substituter.evaluate(attrib["ns"], config.primary_context, extra_args) + "/"
                new_namespace = (namespace + sub_namespace).replace("//", "/")

                # if this is our desired end tag, evaluate it
                if element.tag == config.primary_tag:
                    config.callback(element, elements, new_namespace)
                elif element.tag in config.secondary_tags:                    
                    _recursive_parse(config, element, elements, new_namespace)

        _recursive_parse(config, xml_context, elements, config.namespace)
        return elements

    def _get_xml_context(self):
        # parse XML context
        tree = ET.parse(self.fullpath)
        xml_context = tree.getroot()

        if not xml_context.tag == "launch":
            raise RuntimeError("Launch file {} doesn't start with a launch element; is it malformed?".format(self.fullpath))
        return xml_context

    def print_(self, string):
        if self.verbose:
            print(string)

""" Use the roslaunch parsing library to get parse the given launch file.

Returns:
    A dict containing all nodes / machines / params and information about them.
"""
def roslaunch_parse(filename, verbose=False):
    """ Take advantage of the roslaunch python package to parse the given file.
    """
    print("Parsing {}".format(filename))
    config = ROSLaunchConfig()
    loader = XmlLoader()
    loader.load(filename, config, verbose=verbose)
    return config

""" Parse the given launch file for all information necessary to build a network graph.

Returns:
    A dict of "LaunchFile" objects keyed against the full path of their files.
"""
def build_graph(filename, input_arguments=None, verbose=True):
    """ Construct a graph of launch file nodes, starting with the top level file.
    """
    # recursive function to build the network graph
    def _process_parent(parent, config, graph):
        # create node in the graph
        graph[parent.fullpath]["object"] = parent
        graph[parent.fullpath]["children"] = parent.get_children()
        nodes = parent.get_nodes()

        # try to pair all nodes to those parsed from the roslaunch parser:
        resolve_name = lambda node: node.namespace + node.name
        for node in nodes:
            matches = [n for n in config.nodes if node==resolve_name(n)]
            if len(matches) < 1:
                # check if this is an anonymous node; this may not work properly
                matches = [n for n in config.nodes if resolve_name(n).startswith(node)]
                if len(matches) == 0:
                    raise RuntimeError("Bad matching found for {}; canditates are: {}".format(node, config.resolved_node_names))
                else:
                    print("WARNING: Possible anonymous node {} can't be identified. ".format(node) \
                        + "\nChose {} from {} arbitrarily. ".format(resolve_name(matches[0]), [resolve_name(m) for m in matches]) \
                        + "The information about this node may be incorrect")
            elif len(matches) > 1:
                print("WARNING: Multiple nodes called {} detected; something is deeply wrong.".format(node))
            graph[parent.fullpath]["nodes"].append(matches[0])

        for child in graph[parent.fullpath]["children"]:
            _process_parent(
                LaunchFile(child, 
                           parent.fullpath, 
                           input_arguments=graph[parent.fullpath]["children"][child]["args"], 
                           namespace=graph[parent.fullpath]["children"][child]["namespace"]),
                config,
                graph)

    # initial inputs to recursively build
    graph = defaultdict(lambda: {"object": [], "children": [], "nodes": []})
    input_arguments = {} if input_arguments is None else input_arguments
    # initialize class variables of LaunchFile (onetime thing)
    LaunchFile.initialize(verbose)

    # get roslaunch's version of the parsed XML:
    config = roslaunch_parse(filename, verbose)

    # process parent
    _process_parent(LaunchFile(filename, input_arguments=input_arguments), config, graph)
    return graph

import re
import copy
import logging
import plotly
try:
    import chart_utils.plotly as py
except ImportError as e:
    import plotly.plotly as py

logger = logging.getLogger(__name__)

class Visualizer:
    def __init__(self, root_file, graph):
        self.graph = graph
        self.root_file = root_file

        # regexp expressions
        self.dict_pattern = re.compile(r"[{},]")
        self.xml_pattern = re.compile(r"\[|\(|\),|\]")

        self.data, self.layout = self.get_config()

    def get_total_nodes(self, launch_file):
        # get the sum total of nodes + launch files spawned by the given launch file
        def _count_children(launch_file):
            # add nodes
            my_offspring = len(self.graph[launch_file]["nodes"])
            for child in self.graph[launch_file]["object"].children:
                my_offspring += _count_children(child)
            return my_offspring
        return _count_children(launch_file)

    """ Construct the dictionaries used by plotly to generate a Sankey graph.
    """
    def get_config(self):

        # sankey object inputs (initialized with first launch file)
        nodes = list(self.graph.keys())
        node_colors = []
        node_labels = []
        node_hover_labels = []
        link_labels = []
        sources = []
        targets = []
        values = []

        # build the sources / targets / labels / colors
        for parent in nodes:
            node_colors.append("blue")
            node_labels.append(parent.split("/")[-1])
            node_hover_labels.append(parent)

            # process all launch file children of this file
            for launch_file in self.graph[parent]["object"].children:
                link_labels.append("<b>Input arguments from {} to {}: </b><br> {}".format(
                    parent.split("/")[-1], 
                    launch_file.split("/")[-1], 
                    self.dict_pattern.sub("<br>", str(self.graph[launch_file]["object"].input_arguments))))
                sources.append(nodes.index(parent))
                targets.append(nodes.index(launch_file))
                values.append(self.get_total_nodes(launch_file))

        for key, value in self.graph.items():
            # process all node children of this file:
            for node in value["nodes"]:
                nodes.append(node.namespace + node.name)
                node_colors.append("red")
                node_labels.append(node.name)
                node_hover_labels.append("Node {}".format(nodes[-1]))
                link_labels.append("<b>Node {} launched from {}:</b><br>{}".format(
                    node.name.split("/")[-1],
                    key.split("/")[-1], 
                    self.xml_pattern.sub("<br>", str(node.xmlattrs()))))
                sources.append(nodes.index(key))
                targets.append(len(nodes)-1)
                values.append(1)

        data=dict(
            type='sankey',
            orientation="h",
            valueformat="s",
            valuesuffix=" children",
            node=dict(
                thickness=35,
                label=node_labels,
                color=node_colors),
            link=dict(
                source=sources,
                target=targets,
                label=link_labels,
                value=values))

        layout=dict(
            title="Launchalyzer view of {}".format(self.root_file.split("/")[-1]),
            font=dict(
                size=14))

        return data, layout

    def plot(self):
        fig = dict(data=[self.data], layout=self.layout)
        plotly.offline.plot(fig, validate=False)

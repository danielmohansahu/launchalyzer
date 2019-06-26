import copy
import plotly
import plotly.plotly as py

"""
For each node I need to know

 - distance from root (0 -> N, )
 - cumulative total of nodes it spawns

 - 


@TODO clean up and prettify

"""


class Visualizer:
    def __init__(self, root_file, graph):
        self.graph = graph
        self.root_file = root_file

        # construct the launch file relationships
        NODES = list(graph.keys())
        NODE_LABELS = []
        SOURCES = []
        TARGETS = []
        VALUES = []
        for key, value in self.graph.items():
            for child in value["object"].children:
                SOURCES.append(NODES.index(key))
                TARGETS.append(NODES.index(child))
                VALUES.append(1)
                NODE_LABELS.append("Launchfile {}\nInput_args:\n{}".format(self.graph[child]["object"].fullpath, str(self.graph[child]["object"].input_arguments).replace(",","\n\t")))

        # add in the nodes themselves
        NODES_FULL = [a.split("/")[-1] for a in NODES]
        for key, value in self.graph.items():
            for node in value["nodes"]:
                NODES_FULL.append(node.name)
                SOURCES.append(NODES.index(key))
                TARGETS.append(len(NODES_FULL)-1)
                VALUES.append(1)
                NODE_LABELS.append("Node {}".format(node.name)) # @TODO put all information like input args, executable, machine tag, etc.

        self.data, self.layout = self.get_config(NODES_FULL, SOURCES, TARGETS, VALUES, NODE_LABELS)
        self.plot()

    """ Construct the dictionaries used by plotly to generate a Sankey graph.
    """
    def get_config(self, nodes, sources, targets, values, labels):

        data = dict(
            type='sankey',
            orientation = "h",
            valuesuffix = " children",
            node = dict(
                label = nodes,
                hoverlabel = labels,
                color = ["blue" if (n.endswith(".launch") or n.endswith(".xml")) else "red" for n in nodes]),
            link = dict(
                source = sources,
                target = targets,
                value = values))

        layout = dict(
            title = "Launchalyzer view of {}".format(self.root_file.split("/")[-1]),
            font = dict(
                size = 10))

        return data, layout

    def plot(self):
        fig = dict(data=[self.data], layout=self.layout)
        plotly.offline.plot(fig, validate=False)

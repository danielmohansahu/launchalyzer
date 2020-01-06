# launchalyzer
This tool provides a top level overview of a given ROS launch file. The intention is to provide 
offline visibility into the relationship between particular launch files and nodes, as well as 
to aid debugging of fairly large file hierarchies.

# installation and dependencies
This tool assumes ROS and python 2 are installed. Additional dependencies can be installed via:

```bash
pip2 install plotly --user
# potentially also necessary:
# pip2 install chart_utils --user
```

# usage

```bash
source {PATH_TO_CATKIN_REPOSITORY}/setup.bash
./launchalyzer {PATH_TO_LAUNCH_FILE}
```


@TODO:
 - clean up visualizer
 - add more description on hover for visualizer.
 - click should open file for viewing?
 - should be able to supply {package name} + file name 
 - handle plotting of nodelets better

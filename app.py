from flask import Flask
from flask import request
from flask import jsonify
import os
import re
import requests

app = Flask(__name__)


def step_one(available_nodes, graphed_output):
    '''
    if node only has 1 child,
    add that mapping and remove from total for neighbor
    also remove the parent from other people to not confuse step 2
    {node: current_node, neighbor: only_child, count: count}
    '''
    available_node_list = (item for item in available_nodes
                           if len(item["children"]) == 1)
    for available_node in available_node_list:
        count, neighbor, node = \
            int(available_node['count']), \
            available_node['children'][0], \
            available_node['id']
        graphed_output.append(
            {'node': node, 'neighbor': neighbor, 'count': count}
        )
        neighbor_node = next((item for item in available_nodes
                             if item["id"] == neighbor), None)
        if neighbor_node is not None:
            neighbor_node['count'] = int(neighbor_node['count']) - count
        available_nodes.remove(available_node)


def step_two(available_nodes, graphed_output):
    '''
    if neighbor has only 1 parent,
    map all those to that parent and subtract count from parent
    {node: parent_node, neighbor: current_node, count: count}
    '''
    available_node_list = (item for item in available_nodes
                           if len(item["parents"]) == 1)
    for available_node in available_node_list:
        count, neighbor, node = \
            int(available_node['count']), \
            available_node['id'], \
            available_node['parents'][0]
        graphed_output.append(
            {'node': node, 'neighbor': neighbor, 'count': count}
        )
        parent_node = next((item for item in available_nodes
                             if item["id"] == node), None)
        if parent_node is not None:
            parent_node['count'] = int(parent_node['count']) - count
        available_nodes.remove(available_node)


@app.route('/', methods=['POST'])
def index():
    #get data from request
    request_data = request.data
    response_json = []
    jolokia_response = requests.get("http://localhost:7777/jolokia/read/"
                     "%22com.rackspace.com.papi.components.checker.handler"
                     "%22:type=%22InstrumentedHandler%22,scope=*,name=*/Count")
    jolokia_response_json = jolokia_response.json()
    #get all nodes: count ending in u
    #get all nodes: count ending in m
    #all nodes ending in U will be replaced with all nodes ending in u (1 to many) during the below iteration
    #all nodes ending in M will be replaced with all nodes ending in m (1 to many) during the below iteration
    basename = os.path.basename(request_data)
    #load the file into a stream
    f = open(request_data)
    for line in f:
        regex = re.compile(r"^\s+([\w_]+)->([\w_]+)")
        match = regex.match(line)
        if match:
            node = match.group(1)
            neighbor = match.group(2)
            if next(
                    (
                        item for item in response_json
                        if item["id"] == basename
                    ), None
            ) is None:
                response_json.append({"id": basename})
            file_dict = next(
                item for item in response_json if item["id"] == basename)
            counter = next((item for item in jolokia_response_json['value'] if "name=\"{0}\"".format(node) in item), None)
            count = 0
            if counter is not None:
                count = jolokia_response_json['value'][counter]['Count']
            if "nodes" in file_dict:
                if next(
                        (
                            item for item in file_dict["nodes"]
                            if item["id"] == node
                        ), None) is None:
                    # does not exist
                    parent_list = []
                    for parent_node in [item for item in file_dict["nodes"] if node in item["children"]]:
                        parent_list.append(parent_node['id'])
                    file_dict["nodes"].append(
                        {
                            "id": node,
                            "children": [neighbor],
                            "parents": parent_list,
                            "count": count
                        }
                    )

                else:
                    # does exist
                    node_dict = next(
                        item for item in file_dict["nodes"]
                        if item["id"] == node
                    )
                    node_dict["children"].append(neighbor)
                    neighbor_dict = next(
                        (
                            item for item in file_dict["nodes"] if
                            item["id"] == neighbor
                        ), None
                    )
                    if neighbor_dict is not None:
                        neighbor_dict["parents"].append(node)
            else:
                file_dict["nodes"] = [
                    {
                        "id": node,
                        "children": [neighbor],
                        "parents": [],
                        "count": count
                    }
                ]

    f.close()

    '''
    graphed_json will be overall
    [
        {'node': blah, 'neighbor': blah2, 'count': 3},
        {'node': blah2, 'neighbor': blah4, 'count': 1},
        {'node': blah3, 'neighbor': blah4, 'count': 2}
    ]
    '''

    graph_nodes_to_parse = {
        'available_nodes': response_json,
        'graphed_json': []
    }

    print graph_nodes_to_parse

    for dot_dict in graph_nodes_to_parse['available_nodes']:
        #while len(dot_dict['nodes']) > 0:
        step_one(dot_dict['nodes'], graph_nodes_to_parse['graphed_json'])
        step_two(dot_dict['nodes'], graph_nodes_to_parse['graphed_json'])
        print graph_nodes_to_parse

    return jsonify({"results": response_json})

if __name__ == "__main__":
    app.run()

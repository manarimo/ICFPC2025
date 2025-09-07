from dash import Dash, html
import dash_cytoscape as cyto
import json

classes = {0: "red", 1: "blue", 2: "green", 3: "gray"}

graph = json.load(open("../graph-dump/vau/1757261883.json"))
nodes = [
    {
        "data": {"id": str(i), "label": str(room)},
        "classes": classes[room],
    }
    for i, room in enumerate(graph["rooms"])
]
edges = [
    {
        "data": {
            "source": str(connection["from"]["room"]),
            "target": str(connection["to"]["room"]),
        }
    }
    for connection in graph["connections"]
]
elements = nodes + edges

app = Dash()

app.layout = html.Div(
    [
        cyto.Cytoscape(
            id="cytoscape-two-nodes",
            layout={"name": "cose"},
            style={"width": "100%", "height": "800px"},
            elements=elements,
            stylesheet=[
                {
                    "selector": ".red",
                    "style": {"background-color": "red", "line-color": "red"},
                },
                {
                    "selector": ".blue",
                    "style": {"background-color": "blue", "line-color": "blue"},
                },
                {
                    "selector": ".green",
                    "style": {"background-color": "green", "line-color": "green"},
                },
                {
                    "selector": ".gray",
                    "style": {"background-color": "gray", "line-color": "gray"},
                },
                {"selector": ".triangle", "style": {"shape": "triangle"}},
            ],
        )
    ],
)

if __name__ == "__main__":
    app.run(debug=True)

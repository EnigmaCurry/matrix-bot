from database import mapper_registry

from sqlalchemy_schemadisplay import create_schema_graph

graph = create_schema_graph(metadata=mapper_registry.metadata,
                            show_datatypes=False,
                            show_indexes=False,
                            rankdir="LR",
                            concentrate=False)
graph.write_png("database.png")

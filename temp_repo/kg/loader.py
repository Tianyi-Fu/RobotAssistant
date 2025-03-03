# kg/loader.py
from rdflib import Graph, Namespace

EX = Namespace("http://example.org/")
OWL = Namespace("http://www.w3.org/2002/07/owl#")
XSD = Namespace("http://www.w3.org/2001/XMLSchema#")

g = Graph()
g.bind("ex", EX)
g.bind("owl", OWL)
g.bind("xsd", XSD)

def load_kg(file_path):

    g.parse(file_path, format="turtle")

    return g

def save_kg(file_path):

    g.serialize(destination=file_path, format="turtle")


def get_graph():

    return g

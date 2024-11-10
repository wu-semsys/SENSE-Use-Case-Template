import argparse
import json
import logging
from typing import TextIO
import pandas as pd
import csv
import os
import warnings

from rdflib import Graph, Literal, Namespace
from rdflib.namespace import RDF, RDFS, SOSA
from pyshacl import validate
from jinja2 import Environment, FileSystemLoader

'''
# RML mapping of System Data Input to the SENSE Ontology
The input for the workflow is an Excelfile containing the following sheets with their respective columns:
- PlatformTypes (PlatformType, subClassOf_PlatformType)
- SensorTypes (SensorType, subClassOf_SensorType)
- Platforms (Platform, PlatformType, hostedBy_Platform)
- Sensors (Sensor, SensorType, hostedBy_Platform, observes_ObservableProperty)
- StateTypes (StateType, SensorType_associated)
- StateTypeCausality (StateType_cause, causalityType, temporalRelation, PlatformRequirements, StateType_effect)
- EventStateMapping (EventType, StateType_starts, StateType_ends, MonitoredPlatform, MonitoredSignal, SignalProperty, <SignalPropertyDefinitions using triples of Name, Type, LiteralOrSensor>)
'''

arg_parser = argparse.ArgumentParser(prog="XLSXtoTTL.py")
arg_parser.add_argument("namespace")
arg_parser.add_argument("input")
arg_parser.add_argument("output")
arg_parser.add_argument("--shacl-path", required=True, help="Path to the SHACL shapes file")
args = arg_parser.parse_args()

# Define Data Source
namespace = args.namespace
excel_path = args.input
ttl_path = args.output
shacl_path = args.shacl_path
 
def excel_to_csv(source) -> dict[str, TextIO]:
    # Suppress specific warnings related to data validation
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=UserWarning)
        if not os.path.exists(excel_path):
            print("XLSX input file does not exist, please provide an input file to the system folder.")
            return
        # create folder if it does not exist yet
        if not os.path.exists(source):
            os.makedirs(source)

        # Read the Excel file
        with pd.ExcelFile(excel_path) as xls:  
        # Loop through each sheet in the Excel file
            for sheet_name in xls.sheet_names:
                # Read the sheet into a DataFrame
                df = pd.read_excel(excel_path, sheet_name=sheet_name)
                
                # Construct the output file path
                output_file = f"./{source}/{sheet_name}.csv"
                
                # Write the DataFrame to a CSV file
                df.to_csv(output_file, index=False)

dataSource = os.path.join(os.path.dirname(excel_path), "SystemData")
excel_to_csv(dataSource)

# imported namespaces: RDF, RDFS, SKOS, XSD, SOSA, SSN
SENSE = Namespace("http://w3id.org/explainability/sense#")
NS = Namespace(namespace)

g = Graph()
g.bind("", NS)
g.bind("sense", SENSE)
g.bind("sosa", SOSA)
g.bind("rdfs", RDFS)
g.bind("rdf", RDF)

# convert Platform Types to RDF
input_file = csv.DictReader(open(dataSource+"/PlatformTypes.csv"))

for row in input_file:
    row = dict(row)
    g.add((NS[row["PlatformType"]], RDFS.subClassOf, NS[row["subClassOf_PlatformType"]]))
    g.add((NS[row["PlatformType"]], RDFS.subClassOf, SENSE.PlatformType))
#    g.add((NS[row["subClassOf_PlatformType"]], RDFS.subClassOf, SOSA.Platform))

# deprecated with SENSE Ontology V2
# # convert Sensor Types to RDF (only accepting Sensors as a System currently)
# input_file = csv.DictReader(open(dataSource+"/SensorTypes.csv"))

# for row in input_file:
#     row = dict(row)
#     g.add((NS[row["SensorType"]], RDFS.subClassOf, NS[row["subClassOf_SensorType"]]))    
#     g.add((NS[row["subClassOf_SensorType"]], RDFS.subClassOf, SENSE.SensorType))

# convert Observable Properties to RDF
input_file = csv.DictReader(open(dataSource+"/ObservableProperties.csv"))

for row in input_file:
    row = dict(row)
    g.add((NS[row["ObservableProperty"]], RDF.type, SOSA.ObservableProperty))

# convert State Types to RDF
input_file = csv.DictReader(open(dataSource+"/1_StateTypes.csv"))

for row in input_file:
    row = dict(row)    
    # check if Observable Property is defined
    if not (NS[row["associatedObservableProperty"]], None, None) in g:
        print("The ObservableProperty", row["associatedObservableProperty"], "has not been defined as an Observable Property yet!" )
    # check if PlatformType is defined
    if not (NS[row["associatedPlatformType"]], None, None) in g:
        print("The Platform Type", row["associatedPlatformType"], "has not been defined as a Platform Type yet!" )
    
    id = row["StateType"].replace(" ", "")
    g.add((NS[id], RDF.type, SENSE.StateType))
    g.add((NS[id], RDFS.label, Literal(row["StateType"])))
    g.add((NS[id], SENSE.associatedObservableProperty, SENSE[row["associatedObservableProperty"]]))
    g.add((NS[id], SENSE.associatedPlatformType, SENSE[row["associatedPlatformType"]]))
    g.add((NS[id], SENSE.isTriggerState, Literal(bool(row["isTriggerState"]))))

# convert Platforms to RDF
input_file = csv.DictReader(open(dataSource+"/Platforms.csv"))

for row in input_file:
    row = dict(row)    
    # check if Platform Type is defined
    if not (NS[row["PlatformType"]], None, None) in g:
        print("The Platform Type", row["PlatformType"], "has not been defined as a Platform Type yet!" )  
    
    g.add((NS[row["Platform"]], RDF.type, SENSE.PlatformOfInterest))
    g.add((NS[row["Platform"]], SENSE.hasPlatformType, NS[row["PlatformType"]]))
    g.add((NS[row["Platform"]], RDFS.label, Literal(row["Platform"])))
    if row["hostedBy_Platform"] != "":
        g.add((NS[row["hostedBy_Platform"]], SOSA.hosts, NS[row["Platform"]]))
        g.add((NS[row["Platform"]], SOSA.isHostedBy, NS[row["hostedBy_Platform"]]))


# convert Sensors to RDF
input_file = csv.DictReader(open(dataSource+"/Sensors.csv"))

for row in input_file:
    row = dict(row) 
    # deprecated - check if Sensor Type is defined   
    # if not (NS[row["SensorType"]], None, None) in g:
    #     print("The Sensor Type", row["SensorType"], "has not been defined as a Sensor Type yet!" )  
    # check if Platform is defned
    if not (NS[row["hostedBy_Platform"]], None, None) in g:
        print("The Platform", row["hostedBy_Platform"], "has not been defined as a Platform yet!" )  
    # check if observable property is defined
    if not (NS[row["observes_ObservableProperty"]], None, None) in g:
        print("The Observable Property", row["observes_ObservableProperty"], "has not been defined as an Observable Property yet!" )  

    g.add((NS[row["Sensor"]], RDF.type, SOSA.Sensor))
    #g.add((NS[row["Sensor"]], SENSE.hasSensorType, NS[row["SensorType"]]))

    g.add((NS[row["Sensor"]], RDFS.label, Literal(row["Sensor"])))
    g.add((NS[row["hostedBy_Platform"]], SOSA.hosts, NS[row["Sensor"]]))
    g.add((NS[row["Sensor"]], SOSA.isHostedBy, NS[row["hostedBy_Platform"]]))
    g.add((NS[row["Sensor"]], SOSA.observes, NS[row["observes_ObservableProperty"]]))

    if row["TimeseriesId"] != "":
        g.add((NS[row["Sensor"]], SENSE.dataSource, Literal(row["TimeseriesId"])))

# convert Event-to-State Mapping to RDF
input_file = csv.DictReader(open(dataSource+"/2_EventStateMapping.csv"))

for row in input_file:
    row = dict(row)

    if row["StateType_starts"] == "" and row["StateType_ends"] == "":
        continue # ignore rows in the data that do not specify event to state mappings, specifically row number 2 in 2_EventStateMapping, which is used as a second header row for formatting reasons in Excel
    
    # define Event Type
    g.add((NS[row["EventType"]], RDF.type, SENSE.EventType))
    g.add((NS[row["EventType"]], RDFS.label, Literal(row["EventType"])))
    #TODO add associated Sensor Type to the EventType

    # add Mapping relation - check if State Type is defined
    if row["StateType_starts"] != "":
        if not (NS[row["StateType_starts"]], None, None) in g:
            print("The State Type", row["StateType_starts"], "has not been defined as a State Type yet!" )      
        g.add((NS[row["StateType_starts"]], SENSE.hasStartEventType, NS[row["EventType"]]))
        g.add((NS[row["EventType"]], SENSE.startsStateType, NS[row["StateType_starts"]]))
    if row["StateType_ends"] != "":
        if not (NS[row["StateType_ends"]], None, None) in g:
            print("The State Type", row["StateType_ends"], "has not been defined as a State Type yet!" )  
        g.add((NS[row["StateType_ends"]], SENSE.hasEndEventType, NS[row["EventType"]]))
        g.add((NS[row["EventType"]], SENSE.endsStateType, NS[row["StateType_ends"]]))


# convert State Type Causality to RDF
input_file = csv.DictReader(open(dataSource+"/1_StateTypeCausality.csv"))
id = 1
for row in input_file:
    row = dict(row) 
    # check if Sensor Type is defined   
    if not (NS[row["StateType_cause"].replace(" ", "")], None, None) in g:
        print("The State Type", row["StateType_cause"], "has not been defined as a State Type yet!" )  
    if not (NS[row["StateType_effect"].replace(" ", "")], None, None) in g:
        print("The State Type", row["StateType_effect"], "has not been defined as a State Type yet!" ) 

    label = row["StateType_cause"]+" "+row["causalRelation"]+" "+row["StateType_effect"]
    g.add((NS["StateTypeCausality"+str(id)], RDF.type,                    SENSE.StateTypeCausality))
    g.add((NS["StateTypeCausality"+str(id)], RDFS.label,                  Literal(label)))
    g.add((NS["StateTypeCausality"+str(id)], SENSE.cause,                 NS[row["StateType_cause"].replace(" ", "")]))
    g.add((NS["StateTypeCausality"+str(id)], SENSE.effect,                NS[row["StateType_effect"].replace(" ", "")]))

    g.add((NS["StateTypeCausality"+str(id)], SENSE.causalRelation,          Literal(row["causalRelation"])))
    g.add((NS["StateTypeCausality"+str(id)], SENSE.temporalRelation,        Literal(row["temporalRelation"])))
    g.add((NS["StateTypeCausality"+str(id)], SENSE.topologicalRelation,     Literal(row["topologicalRelation"])))
# deprecated in SENSE Ontology V2:
#    g.add((NS["StateTypeCausality"+str(id)], SENSE.hasCausalRelation,     SENSE[row["causalRelation"]]))
#    g.add((NS["StateTypeCausality"+str(id)], SENSE.hasTemporalRelation,   SENSE[row["temporalRelation"]]))
#    g.add((NS["StateTypeCausality"+str(id)], SENSE.hasTopologicalRelation,SENSE[row["topologicalRelation"]]))
#    g.add((SENSE[row["causalRelation"]],      RDF.type,   SENSE.causalRelation))
#    g.add((SENSE[row["temporalRelation"]],    RDF.type,   SENSE.temporalRelation))
#    g.add((SENSE[row["topologicalRelation"]], RDF.type,   SENSE.topologicalRelation))

    id +=1


with open('reasoning-templates.json') as fd:
    templates = json.load(fd)

def read_parameters(template_info, row):
    """
    Reads the parameters for a signal property
    """
    FIRST_PARAMETER_COLUMN = 6
    i = FIRST_PARAMETER_COLUMN

    result = dict()
    for p in template_info["parameters"]:
        result[p["name"]] = None
        if "default" in p:
            result[p["name"]] = {
                "type": "LiteralValue",
                "value": p["default"]
            }


    while True:
        name = row[i]
        type = row[i + 1]
        value = row[i + 2]

        if name is None or name == "":
            break

        result[name] = {
            "type": type,
            "value": value
        }

        i += 3

    for p in template_info["parameters"]:
        parameter = result[p["name"]]
        if p["required"] == True and parameter is None:
            parameter_name = p["name"]
            print(f"Error: Parameter {parameter_name} not defined!")
        
        if parameter is not None:
            if not p.get("allow_sensor_binding", True) and parameter["type"] != "LiteralValue":
                parameter_name = p["name"]
                print(f"Error: Parameter {parameter_name} cannot be bound to a sensor!")
            
            if not p.get("implemented", True):
                parameter_name = p["name"]
                print(f"Error: Parameter {parameter_name} is not implemented!")


    return result

templateLoader = FileSystemLoader(searchpath="./templates/")
templateEnv = Environment(loader=templateLoader)
reasoning_rules = Graph()
input_file = csv.reader(open(dataSource+"/2_EventStateMapping.csv"))
next(input_file)
for row in input_file:
    event_type = row[0]
    monitored_platform = row[3]
    monitored_observable_property = row[4]
    signal_property = row[5]

    if signal_property == "":
        continue # ignore rows in the data that do not specify events, specifically row number 2 in 2_EventStateMapping, which is used as a second header row for formatting reasons in Excel

    if signal_property not in templates:
        logging.error(f"{event_type}: Signal property {signal_property} not yet supported!")
        continue

    template_info = templates[signal_property]

    parameters = read_parameters(template_info, row)

    render_input = {
        "namespace": namespace,
        "event_type": event_type,
        "monitored_platform": monitored_platform,
        "monitored_observable_property": monitored_observable_property,
        "signal_property": signal_property,
        "p": parameters,
    }

    template = templateEnv.get_template(template_info["template"])
    render_result = template.render(render_input)

    if not os.path.exists("./SystemData/.debug/"):
        os.mkdir("./SystemData/.debug/")
    with open(f"./SystemData/.debug/{monitored_platform}_{event_type}.ttl", "w") as df:
        df.write(render_result)

    reasoning_rules.parse(data=render_result, format="turtle")


def validate_ontology(ontology_graph: Graph, shacl_graph: Graph):
    """
    Validates the ontology graph against the SHACL shapes graph.

    Parameters:
    - ontology_graph (Graph): The RDF graph of the ontology.
    - shacl_graph (Graph): The RDF graph of the SHACL shapes.

    Returns:
    - conforms (bool): Whether the ontology conforms to the SHACL shapes.
    - results_graph (Graph): Graph containing the validation results.
    - results_text (str): Textual description of the validation results.
    """
    conforms, results_graph, results_text = validate(
        data_graph=ontology_graph,
        shacl_graph=shacl_graph,
        ont_graph=None,  
        inference='rdfs',  
        abort_on_first=False,  
        meta_shacl=False,  
        advanced=True,  
        js=False,  
    )

    print("Conforms:", conforms)
    print("Results Graph:")
    print(results_graph.serialize(format="turtle"))
    print("Results Text:")
    print(results_text)

    return conforms, results_graph, results_text

# Load SHACL shapes
shacl_graph = Graph()
shacl_graph.parse(shacl_path, format="turtle")

# Perform SHACL validation
conforms, results_graph, results_text = validate_ontology(g, shacl_graph)

if conforms:
    g.serialize(destination=ttl_path, format='turtle')
    print(f"Ontology serialized to {ttl_path}")
else:
    print("The ontology does NOT conform to the SHACL shapes. The TTL file was not generated.")
    exit(1)

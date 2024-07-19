import argparse
from typing import TextIO
import pandas as pd
import csv
import os
from rdflib import Graph, Literal, Namespace
from rdflib.namespace import RDF, RDFS, SOSA
from pyshacl import validate

'''
# RML mapping of System Data Input to the SENSE Ontology
The input for the workflow is an Excelfile containing the following sheets with their respective columns:
- PlatformTypes (PlatformType, subClassOf_PlatformType)
- SensorTypes (SensorType, subClassOf_SensorType)
- Platforms (Platform, PlatformType, hostedBy_Platform)
- Sensors (Sensor, SensorType, hostedBy_Platform, observes_ObservableProperty)
- StateTypes (StateType, SensorType_possible)
- StateTypeCausality (StateType_cause, causalityType, temporalRelation, PlatformRequirements, StateType_effect)
'''

arg_parser = argparse.ArgumentParser(prog="XLSXtoTTL.py")
arg_parser.add_argument("namespace")
arg_parser.add_argument("input")
arg_parser.add_argument("output")
arg_parser.add_argument("--shacl-path")
args = arg_parser.parse_args()

# Define Data Source
namespace = args.namespace
excel_path = args.input
ttl_path = args.output
 
def excel_to_csv(source) -> dict[str, TextIO]:
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
g.bind("s", SENSE)
g.bind("sosa", SOSA)
g.bind("rdfs", RDFS)
g.bind("rdf", RDF)

# convert Platform Types to RDF
input_file = csv.DictReader(open(dataSource+"/PlatformTypes.csv"))

for row in input_file:
    row = dict(row)
    g.add((NS[row["PlatformType"]], RDFS.subClassOf, NS[row["subClassOf_PlatformType"]]))
    g.add((NS[row["subClassOf_PlatformType"]], RDFS.subClassOf, SOSA.Platform))

# convert Sensor Types to RDF (only accepting Sensors as a System currently)
input_file = csv.DictReader(open(dataSource+"/SensorTypes.csv"))

for row in input_file:
    row = dict(row)
    g.add((NS[row["SensorType"]], RDFS.subClassOf, NS[row["subClassOf_SensorType"]]))    
    g.add((NS[row["subClassOf_SensorType"]], RDFS.subClassOf, SENSE.SensorType))

#TODO how to define different Sensor Types in the SENSE ontology? is it an instance or a subclass of sensor type?
#TODO if instance, how to define SensorTypes as subtypes of sensors?

# convert State Types to RDF
input_file = csv.DictReader(open(dataSource+"/1_StateTypes.csv"))

for row in input_file:
    row = dict(row)    
    # check if Sensor Type is defined
    if not (NS[row["SensorType_possible"]], None, None) in g:
        print("The Sensor Type", row["SensorType_possible"], "has not been defined as a Sensor Type yet!" )  
    
    id = row["StateType"].replace(" ", "")
    g.add((NS[id], RDF.type, SENSE.StateType))
    g.add((NS[id], RDFS.label, Literal(row["StateType"])))
    g.add((NS[id], SENSE.associatedSensorType, SENSE[row["SensorType_possible"]]))

# convert Platforms to RDF
input_file = csv.DictReader(open(dataSource+"/Platforms.csv"))

for row in input_file:
    row = dict(row)    
    # check if Platform Type is defined
    if not (NS[row["PlatformType"]], None, None) in g:
        print("The Platform Type", row["PlatformType"], "has not been defined as a Platform Type yet!" )  
    
    g.add((NS[row["Platform"]], RDF.type, NS[row["PlatformType"]]))
    g.add((NS[row["Platform"]], RDFS.label, Literal(row["Platform"])))
    if row["hostedBy_Platform"] != "":
        g.add((NS[row["hostedBy_Platform"]], SOSA.hosts, NS[row["Platform"]]))


# convert Sensors to RDF
input_file = csv.DictReader(open(dataSource+"/Sensors.csv"))

for row in input_file:
    row = dict(row) 
    # check if Sensor Type is defined   
    if not (NS[row["SensorType"]], None, None) in g:
        print("The Sensor Type", row["SensorType"], "has not been defined as a Sensor Type yet!" )  
    
    g.add((NS[row["Sensor"]], RDF.type, SOSA.Sensor))
    g.add((NS[row["Sensor"]], SENSE.hasSensorType, NS[row["SensorType"]]))

    g.add((NS[row["Sensor"]], RDFS.label, Literal(row["Sensor"])))
    g.add((NS[row["hostedBy_Platform"]], SOSA.hosts, NS[row["Sensor"]]))
    g.add((NS[row["Sensor"]], SOSA.observes, NS[row["observes_ObservableProperty"]]))

    if row["TimeseriesId"] != "":
        g.add((NS[row["Sensor"]], SENSE.hasTimeseriesId, Literal(row["TimeseriesId"])))

# convert Event-to-State Mapping to RDF
input_file = csv.DictReader(open(dataSource+"/2_EventStateMapping.csv"))

for row in input_file:
    row = dict(row)
    
    # define Event Type
    g.add((NS[row["EventType"]], RDF.type, SENSE.EventType))
    g.add((NS[row["EventType"]], RDFS.label, Literal(row["EventType"])))
    #TODO add associated Sensor Type to the EventType

    # add Mapping relation - check if State Type is defined
    if row["StateType_starts"] != "":
        if not (NS[row["StateType_starts"]], None, None) in g:
            print("The State Type", row["StateType_starts"], "has not been defined as a State Type yet!" )      
        g.add((NS[row["StateType_starts"]], SENSE.hasStartEventType, NS[row["EventType"]]))
    if row["StateType_ends"] != "":
        if not (NS[row["StateType_ends"]], None, None) in g:
            print("The State Type", row["StateType_ends"], "has not been defined as a State Type yet!" )  
        g.add((NS[row["StateType_ends"]], SENSE.hasEndEventType, NS[row["EventType"]]))


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
    g.add((NS["StateTypeCausality"+str(id)], SENSE.hasCausalRelation,     SENSE[row["causalRelation"]]))
    g.add((NS["StateTypeCausality"+str(id)], SENSE.hasTemporalRelation,   SENSE[row["temporalRelation"]]))
    g.add((NS["StateTypeCausality"+str(id)], SENSE.hasTopologicalRelation,SENSE[row["topologicalRelation"]]))
    g.add((NS["StateTypeCausality"+str(id)], SENSE.cause,                 NS[row["StateType_cause"].replace(" ", "")]))
    g.add((NS["StateTypeCausality"+str(id)], SENSE.effect,                NS[row["StateType_effect"].replace(" ", "")]))

    g.add((SENSE[row["causalRelation"]],      RDF.type,   SENSE.causalRelation))
    g.add((SENSE[row["temporalRelation"]],    RDF.type,   SENSE.temporalRelation))
    g.add((SENSE[row["topologicalRelation"]], RDF.type,   SENSE.topologicalRelation))

    id +=1

if args.shacl_path is not None:
    reasoning_rules = Graph().parse(args.shacl_path, format="turtle")

    validate(
        g,
        shacl_graph=reasoning_rules,
        inference="none",
        abort_on_first=False,
        allow_infos=False,
        allow_warnings=False,
        meta_shacl=False,
        advanced=True,  # needed to execute SHACL rules
        js=False,
        debug=False,
        inplace=g,  # Add derived event specifications to the system model
    )

g.serialize(destination = f"{ttl_path}", format='ttl')
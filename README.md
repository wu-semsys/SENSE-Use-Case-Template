# Use Case Template

We provide this Use Case Template repository as a starting point for creating a new SENSE instance from the [SENSE Core](https://git.ai.wu.ac.at/sense/sense-core). Check out the SENSE Core documentation for information about the general concept and detailed information about the individual modules.

## Table of Conents
- [SENSE Use Case Instantiation Instructions](#sense-use-case-instantiation-instructions)
- [1. Fork the SENSE Use Case Template](#1-fork-the-sense-use-case-template)
- [2. Prepare the Use-Case-Specific Information](#2-prepare-the-use-case-specific-information)
- [3. Generate system-data.ttl ](#3-generate-system-datattl)
- [4. Set up a Connection to an Existing InfluxDB Instance](#4-set-up-a-connection-to-an-existing-influxdb-instance)
- [5. Optional: Build the Docker Images](#5-optional-build-the-docker-images)
- [6. Run the Application](#6-run-the-application)
- [7. Request Events and Explanations](#7-request-events-and-explanations)

## SENSE Use Case Instantiation Instructions
There are several steps listed below that will create a new use-case-specific repository from this Use Case Template repository and populate the template with use-case-specific information. Note that, on several occasions, it is necessary to define a name for the use case. We use USE_CASE_NAME as a placeholder. 

### 1. Fork the SENSE Use Case Template
If your use-case-specific instance of SENSE should be hosted on the same Git server as this Use Case Template repository, utilize the built-in fork functionality to create a fork of this repository.

If you need to host your use-case-specific instance of SENSE on a different Git server, follow the steps below:
1. Create an empty repository on your Git server, but do not initialize it with any files
2. Clone the repository you've just created to your local machine using the following commands:
```bash
git clone git@git.auto.tuwien.ac.at:tfruehwirth/USE_CASE_NAME.git
cd USE_CASE_NAME
```

2. Add the Use Case Template repository as remote repository named "upstream":
```bash
git remote add upstream git@git.ai.wu.ac.at:sense/use-case-template.git
```
3. Fetch the latest changes from the remote repository "upstream" using the command:
```bash
git fetch upstream
```
4. Merge into your local branch:
```bash
git merge remotes/upstream/main
```

This will result in a repository with the following file structure:

```bash
├── README.md (# this README file)
├── compose.yml # (docker compose file)
├── config # (configuration files for all modules)
│   ├── config.docker.json
├── infrastructure # (additional module-specific configuration and data files)
│   └── knowledgebase
│       ├── SystemData.xlsx
│       ├── data
│       │   └── SENSE.ttl
│       ├── graphdb_repo_config.ttl
│       └── reasoning
│           └── event-reasoning.ttl
└── tools
    └── requirements.txt # python package requirements for XLSXtoTTL.py
    └── XLSXtoTTL.py # script for converting SystemData.xlsx to system-data.ttl
```

The USE_CASE_NAME placeholder is currently quite havily used. We are working on reducing the number of occurances. We suggest search-and-replace for replacing the USE_CASE_NAME with an expressive name for your use case. For now, it is present in the following files:

```bash
./config/config.docker.json
./infrastructure/knowledgebase/graphdb_repo_config.ttl
./infrastructure/knowledgebase/reasoning/event-reasoning.ttl
```

### 2. Prepare the Use-Case-Specific Information
Follow our [Guide]() (TODO: add link to the guide on the necessary steps for analyzing the data, identifying relevant events, and defining appropriate explanations). During this step, the use-case-specific information will be collected and used to populate the [SystemData.xlsx](./infrastructure/knowledgebase/SystemData.xlsx) file. 

### 3. Generate system-data.ttl 
The [SystemData.xlsx](./infrastructure/knowledgebase/SystemData.xlsx) has to be converted to a Turtle (ttl) file, before it can be used by the SENSE system. We provide a script for this purpose.

```bash
cd tools

# install required python packages
pip install -r requirements.txt

# create system-data.ttl from SystemData.xlsx
python3 XLSXtoTTL.py "http://example.org/USE_CASE_NAME#" \
    ../infrastructure/knowledgebase/SystemData.xlsx \
    ../infrastructure/knowledgebase/data/system-data.ttl \
    --shacl-path ../infrastructure/knowledgebase/reasoning/event-reasoning.ttl
```

### 4. Set up a Connection to an Existing InfluxDB Instance
The SENSE system needs to connect to an existing InfluxDB database to access data that should be monitored and explained. Additional information on how to configure the data-ingestion module accordingly is provided in the [README file of the data-ingestion module](https://git.ai.wu.ac.at/sense/sense-core/-/blob/main/sense_core/data_ingestion/README.md)

### 5. Optional: Build the Docker Images
We provide pre-built images via [registry.ai.wu.ac.at](registry.ai.wu.ac.at). However, if you would rather build the images locally, you can use the Dockerfiles/Containerfiles provided in the [SENSE Core](https://git.ai.wu.ac.at/sense/sense-core) repository under the sense_core directory. As an example, the knowledgebase image can be built with:

```bash
cd sense-core/sense_core
docker build --tag sense-core/knowledgebase:latest -f knowledgebase.amd64.Containerfile .
```

### 6. Run the Application
If you want to use our pre-built images, you need to login into the container registry so that you can access the images. Once logged in, simply spin up your compose tool of choice to get a running system.

```bash
docker login -u <your-email> -p <api-token> registry.ai.wu.ac.at
docker compose up
```

Alternatively, if you want to use the Docker image you built locally in the [previous step](#5-optional-build-the-docker-images), you need to adjust the [compose.yml](compose.yml) file accordingly. E.g., for the knowledgebase module, you need to replace 

```image: registry.ai.wu.ac.at/sense/sense-core/knowledgebase:latest``` 

with ```image: sense-core/knowledgebase:latest```. 

Then, start the application with:
```
docker compose up
```

### 7. Request Events and Explanations

Refer to [https://git.ai.wu.ac.at/sense/sense-core/-/blob/main/sense_core/simple_event_detection/README.md](https://git.ai.wu.ac.at/sense/sense-core/-/blob/main/sense_core/simple_event_detection/README.md) for instructions on how to retrieve a list of **events** from your SENSE system instantiation.

Refer to [https://git.ai.wu.ac.at/sense/sense-core/-/tree/main/sense_core/explanation-engine/README.md](https://git.ai.wu.ac.at/sense/sense-core/-/tree/main/sense_core/explanation-engine/README.md) for instructions on how to retrieve **explanations** for events from your SENSE system instantiation. 
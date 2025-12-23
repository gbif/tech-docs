import sys
import requests
import json

if len(sys.argv) != 3:
    print("Need 2 arguments, output directory and environment")
    exit(1)

output = sys.argv[1]
env = sys.argv[2]

if env == 'dev' or env == 'dev2':
    indent = 2
else:
    indent = None

print("--- Fetching and processing OpenAPI documentation ---")
print("Output to "+output+" for environment "+env)
print("")

print("--- Finding available webservices ---")
response = requests.get('http://ws.gbif.org/applications', headers={'Accept': 'application/json'})
services = json.loads(response.text)

urls = {}

# Find services
for s in services:
    for i in s["instances"]:
        if (i['tags']['env'] == env):
            if i['registration']['serviceUrl'].find('gbif') > 0:
                urls[s['name']] = i['registration']['serviceUrl']
                print("Found "+env+" "+s['name']+" at "+urls[s['name']])
print("")

def to_filename(ws):
    ws = ws.replace('-ws', '')
    if (ws == 'vectortile-server'):
        ws = 'v2-maps'
    if (ws == 'pipelines-validator'):
        ws = 'validator'
    if (ws == 'vocabulary-rest'):
        ws = 'vocabulary'
    return ws

def to_url(ws, url):
    if (url.endswith('/')):
        return url+"v3/api-docs"
    else:
        return url+"/v3/api-docs"

# Retrieve the documentation
print("--- Retrieving OpenAPI specifications ---")
for ws, url in urls.items():
    filename = output + '/' + to_filename(ws) + '.json'
    print("Fetching documentation for "+ws+" from "+to_url(ws, url))
    response = requests.get(to_url(ws, url))
    if response.status_code == 200:
        if ws == 'registry-ws':
            registry = json.loads(response.text)
        elif ws == 'occurrence-ws':
            occurrence = json.loads(response.text)
        elif ws == 'event-ws':
            event = json.loads(response.text)
        elif ws == 'metrics-ws':
            metrics = json.loads(response.text)
        elif ws == 'geocode-ws':
            geocode = json.loads(response.text)
        elif ws == 'checklistbank-ws':
            checklistbank = json.loads(response.text)
        elif ws == 'matching-ws-gbif':
            matchingwsgbif = json.loads(response.text)
        elif ws == 'occurrence-annotation-ws':
            occurrenceannotation = json.loads(response.text)
        elif ws == 'vectortile-server':
            maps = json.loads(response.text)
        elif ws == 'event-vectortile-server':
            event_maps = json.loads(response.text)
        else:
            openapi = json.loads(response.text)
            with open(filename, "w") as write_file:
                json.dump(openapi, write_file, separators=(',', ':'), indent=indent)
        print("Retrieved documentation for "+ws)

    else:
        if ws == 'directory-ws':
            print("Ignoring internal service")
        elif ws == 'content-ws':
            print("Ignoring internal service")
        elif ws == 'crawler-ws':
            print("Service not yet documented")
        else:
            raise Exception("Response "+str(response.status_code)+" for "+ws+", not continuing.")
print("")

# Development
#response = requests.get("http://localhost:8080/v3/api-docs")
#registry = json.loads(response.text)

#response = requests.get("http://localhost:8080/v3/api-docs")
#occurrence = json.loads(response.text)

#response = requests.get("http://localhost:8080/v3/api-docs")
#checklistbank = json.loads(response.text)
# End development

# Special cases for registry and occurrence
print("--- Moving some method-paths from Registry to Occurrence ---")

toRemove = []

movePrefixFromRegistryToOccurrence = [
    '/occurrence/download/'
]

for path in registry["paths"]:
    for prefix in movePrefixFromRegistryToOccurrence:
        if path.startswith(prefix):
            occurrence["paths"][path] = registry["paths"][path]
            print("Added "+path+" to occurrence")
            toRemove.append(path)
            #json.dump(registry["paths"][path], sys.stdout, separators=(',', ':'), indent=indent)

movePrefixFromRegistryToEvent = [
    '/event/download/'
]

for path in registry["paths"]:
    for prefix in movePrefixFromRegistryToEvent:
        if path.startswith(prefix):
            event["paths"][path] = registry["paths"][path]
            print("Added "+path+" to event")
            toRemove.append(path)

# Schemas need duplicating
registrySchemas = [
    'PagingResponseDownloadStatistics',
    'DownloadStatistics',
    'PagingResponseDatasetOccurrenceDownloadUsage',
    'DatasetOccurrenceDownloadUsage',
    #'DOI',
    'Download',
    'DownloadRequest',
    'PagingResponseDownload'
    ]
for schema in registrySchemas:
    occurrence['components']['schemas'][schema] = registry['components']['schemas'][schema]
    event['components']['schemas'][schema] = registry['components']['schemas'][schema]

for path in toRemove:
    if path in registry["paths"]:
        del registry["paths"][path]
        print("Removed "+path+" from registry")

# Preface registry description
registry_description = registry['info']['description']
registry['info']['description'] = "**This is a view of *all Registry methods* available for advanced use.  Most users of GBIF data will prefer the [Registry API — Principal methods](registry-principal-methods) page instead.**\n\n" + registry_description
print("")

# Special cases for geocode (moving to occurrence)
print("--- Moving some method-paths from Geocode to Occurrence ---")

movePrefixFromGeocodeToOccurrenceAndEvent = [
    '/geocode/gadm/'
]

for path in geocode["paths"]:
    for prefix in movePrefixFromGeocodeToOccurrenceAndEvent:
        if path.startswith(prefix):
            occurrence["paths"][path] = geocode["paths"][path]
            print("Added "+path+" to occurrence")
            event["paths"][path] = geocode["paths"][path]
            print("Added "+path+" to event")


# Schemas need duplicating
geocodeSchemas = ['GadmRegion', 'Region', 'Pageable', 'PagingResponseGadmRegion']
for schema in geocodeSchemas:
    occurrence['components']['schemas'][schema] = geocode['components']['schemas'][schema]
    event['components']['schemas'][schema] = geocode['components']['schemas'][schema]
print("")

# Special cases for maps (moving to event maps to maps)
print("--- Moving some method-paths from Event maps to Occurrence maps ---")

movePrefixFromEventToOccurrenceMaps = [
    '/event/'
]

for path in event_maps["paths"]:
    for prefix in movePrefixFromEventToOccurrenceMaps:
        if path.startswith(prefix):
            maps["paths"][path] = event_maps["paths"][path]
            print("Added "+path+" to occurrence maps")


# Schemas need duplicating
# eventMapsSchemas = ['GadmRegion', 'Region', 'Pageable', 'PagingResponseGadmRegion']
# for schema in geocodeSchemas:
#     occurrence['components']['schemas'][schema] = geocode['components']['schemas'][schema]
#     event['components']['schemas'][schema] = geocode['components']['schemas'][schema]
# print("")



# Special cases for metrics (moving to occurrence)
# Metrics schema can be ignored.
print("--- Moving all method-paths from Metrics to Occurrence ---")

for path in metrics["paths"]:
    occurrence["paths"][path] = metrics["paths"][path]
    print("Added "+path+" to occurrence")

# Schemas need duplicating
metricsSchemas = ['DimensionObject', 'Rollup']
for schema in metricsSchemas:
    occurrence['components']['schemas'][schema] = metrics['components']['schemas'][schema]
print("")

# Special cases for occurrence-annotation (moving to occurrence), but not for prod.
if (env != 'prod'):
    print("--- Moving some method-paths from Occurrence-Annotation to Occurrence ---")

    movePrefixFromOccurrenceAnnotationToOccurrence = [
        '/occurrence/experimental/annotation/'
    ]

    for path in occurrenceannotation["paths"]:
        for prefix in movePrefixFromOccurrenceAnnotationToOccurrence:
            if path.startswith(prefix):
                occurrence["paths"][path] = occurrenceannotation["paths"][path]
                print("Added "+path+" to occurrence")

                # Schemas need duplicating
                occurrenceAnnotationSchemas = ['Ruleset', 'Project', 'Rule', 'Comment']
                for schema in occurrenceAnnotationSchemas:
                    occurrence['components']['schemas'][schema] = occurrenceannotation['components']['schemas'][schema]
                print("")
else:
    print("--- Skipping Occurrence-Annotation as this is prod ---")

# Special cases for checklistbank (moving to registry)
print("--- Moving some method-paths from Checklistbank to Registry ---")

movePrefixFromChecklistbankToRegistry = [
    '/dataset/{key}/metrics'
]

toRemove = []

for path in checklistbank["paths"]:
    for prefix in movePrefixFromChecklistbankToRegistry:
        if path.startswith(prefix):
            registry["paths"][path] = checklistbank["paths"][path]
            print(f"Added {path} to registry")
            toRemove.append(path)

for path in toRemove:
    if path in checklistbank["paths"]:
        del checklistbank["paths"][path]
        print("Removed "+path+" from checklistbank")

# Schemas need duplicating
checklistbankSchemas = [
    'DatasetMetrics'
    ]
for schema in checklistbankSchemas:
    registry['components']['schemas'][schema] = checklistbank['components']['schemas'][schema]

# Special cases for checklistbank / matchingwsgbif
print("--- Moving all method-paths from matchingwsgbif to Checklistbank ---")

# Schemas need duplicating
matchingwsgbifSchemas = ['NameUsageMatch', 'Usage', 'RankedName', 'Diagnostics', 'Status', 'ExternalID', 'APIMetadata', 'BuildInfo', 'IndexMetadata']
for schema in matchingwsgbifSchemas:
    if schema in matchingwsgbif['components']['schemas']:
        checklistbank['components']['schemas'][schema] = matchingwsgbif['components']['schemas'][schema]

# remove the /v1/ suffix from the server URL if present
for server in checklistbank["servers"]:
    if server['url'].endswith('/v1/'):
        server['url'] = server['url'][:-3]

paths = checklistbank["paths"]
for path in list(paths.keys()):  # iterate over a copy of keys
    if not path.startswith('/v1/') and not path.startswith('/v2/'):
        new_path = '/v1' + path
        paths[new_path] = paths.pop(path)  # move value to new key
        print(f"Modified {new_path} to checklistbank")

print("--- Moving all method-paths from matchingwsgbif to Checklistbank ---")

for path in matchingwsgbif["paths"]:
    checklistbank["paths"][path] = matchingwsgbif["paths"][path]
    print("Added "+path+" to checklistbank")

print("")

# Write the result of all that moving.

with open(output+"/registry.json", "w") as write_file:
    json.dump(registry, write_file, separators=(',', ':'), indent=indent)

with open(output+"/occurrence.json", "w") as write_file:
    json.dump(occurrence, write_file, separators=(',', ':'), indent=indent)

with open(output+"/event.json", "w") as write_file:
    json.dump(event, write_file, separators=(',', ':'), indent=indent)

with open(output+"/checklistbank.json", "w") as write_file:
    json.dump(checklistbank, write_file, separators=(',', ':'), indent=indent)
print("")

print("--- Filtering for basic Registry API view ---")

# Selected registry path-methods for the basic view
registryBasicPath = {}
registryBasicPath['get'] = [
    '/dataset',
    '/dataset/doi/{prefix}/{suffix}',
    '/dataset/metadata/{key}',
    '/dataset/metadata/{key}/document',
    '/dataset/search',
    '/dataset/search/export',
    '/dataset/{key}',
    '/derivedDataset/dataset/{doiPrefix}/{doiSuffix}',
    '/derivedDataset/dataset/{key}',
    '/derivedDataset/user/{user}',
    '/derivedDataset/{doiPrefix}/{doiSuffix}',
    '/derivedDataset/{doiPrefix}/{doiSuffix}/citation',
    '/derivedDataset/{doiPrefix}/{doiSuffix}/datasets',
    '/grscicoll/collection',
    '/grscicoll/collection/export',
    '/grscicoll/collection/{key}',
    '/grscicoll/institution',
    '/grscicoll/institution/export',
    '/grscicoll/institution/{key}',
    '/grscicoll/search',
    '/installation',
    '/installation/{key}',
    '/network',
    '/network/{key}',
    '/node',
    '/node/{key}',
    '/organization',
    '/organization/{key}'
]
registryBasicPath['post'] = [
    '/derivedDataset'
]
registryBasicPath['put'] = [
    '/derivedDataset/{doiPrefix}/{doiSuffix}'
]
registryBasicPath['delete'] = []

complicated = {}
complicated['get'] = []
complicated['post'] = []
complicated['put'] = []
complicated['delete'] = []

tags_to_keep = []

#for tag in registry["tags"]:
#    tags_to_remove.append(registry["tags"][tag]['name'])

for path in registry["paths"]:
    for method in registry["paths"][path]:
        if path not in registryBasicPath[method]:
            print("Excluding "+method+" "+path+" from Registry principal methods view.")
            complicated[method].append(path)
        else:
            print("Including "+method+" "+path+" from Registry principal methods view.")
            for tag in registry["paths"][path][method]['tags']:
                #if tag in tags_to_remove:
                tags_to_keep.append(tag)

        # Alternative way using code annotations, but see https://github.com/swagger-api/swagger-core/issues/3249
        # if "x-Category" in registry["paths"][path][method]:
        #     print("Keep "+method+" "+path)
        # else:
        #     print("Discard "+method+" "+path)
        #     complicated.append(path)

# Delete unwanted path-methods
for method in complicated:
    for path in complicated[method]:
        if path in registry["paths"]:
            if method in registry["paths"][path]:
                del registry["paths"][path][method]

# Delete unneeded tags
new_tags = []
for tag in registry["tags"]:
    if tag['name'] in tags_to_keep:
        new_tags.append(tag)
registry["tags"] = new_tags

# Add heading
registry['info']['title'] = registry['info']['title'] + " — Principal methods only"
registry['info']['description'] = "**This is a view of *principal methods only*, sufficient for most users of GBIF data.**  Data publishers with write access to the GBIF Registry should refer to the [full Registry API documentation](registry).\n\n" + registry_description

with open(output+"/registry-principal-methods.json", "w") as write_file:
    json.dump(registry, write_file, separators=(',', ':'), indent=indent)
print("")

with open(output+"/v2-maps.json", "w") as write_file:
    json.dump(maps, write_file, separators=(',', ':'), indent=indent)
print("")

print("=== OpenAPI specification generation completed ===")

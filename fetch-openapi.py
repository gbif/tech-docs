import sys
import requests
import json

if len(sys.argv) != 3:
    print("Need 2 arguments, output directory and environment")
    exit(1)

output = sys.argv[1]
env = sys.argv[2]

if env == 'dev':
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
            if i['registration']['serviceUrl'].find('gbif.org') > 0:
                urls[s['name']] = i['registration']['serviceUrl']
                print("Found "+env+" "+s['name']+" at "+urls[s['name']])
print("")

def to_filename(ws):
    ws = ws.replace('-ws', '')
    if (ws == 'vectortile-server'):
        ws = 'v2-maps'
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
        elif ws == 'metrics-ws':
            metrics = json.loads(response.text)
        elif ws == 'geocode-ws':
            geocode = json.loads(response.text)
        else:
            openapi = json.loads(response.text)
            with open(filename, "w") as write_file:
                json.dump(openapi, write_file, separators=(',', ':'), indent=indent)
        print("Retrieved documentation for "+ws)

    else:
        print("Response "+str(response.status_code)+" for "+ws+", ignoring while in dev.")
print("")

# Development
#response = requests.get("http://localhost:8080/v3/api-docs")
#registry = json.loads(response.text)

#response = requests.get("http://localhost:8080/v3/api-docs")
#occurrence = json.loads(response.text)
# End development

# Special cases for registry and occurrence
print("--- Moving some method-paths from Registry to Occurrence ---")

movePrefixFromRegistryToOccurrence = [
    '/occurrence/download/'
]

# Although these are @Hidden, they still end up being produced for some reason.
removePrefixFromRegistry = [
    '/event/download',
    '/occurrence/download'
]

toRemove = []

for path in registry["paths"]:
    for prefix in movePrefixFromRegistryToOccurrence:
        if path.startswith(prefix):
            occurrence["paths"][path] = registry["paths"][path]
            print("Added "+path+" to occurrence")
            toRemove.append(path)
            #json.dump(registry["paths"][path], sys.stdout, separators=(',', ':'), indent=indent)
    for prefix in removePrefixFromRegistry:
        if path.startswith(prefix):
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

for path in toRemove:
    if path in registry["paths"]:
        del registry["paths"][path]
        print("Removed "+path+" from registry")
print("")

# Special cases for geocode (moving to occurrence)
print("--- Moving some method-paths from Geocode to Occurrence ---")

movePrefixFromGeocodeToOccurrence = [
    '/geocode/gadm/'
]

for path in geocode["paths"]:
    for prefix in movePrefixFromGeocodeToOccurrence:
        if path.startswith(prefix):
            occurrence["paths"][path] = geocode["paths"][path]
            print("Added "+path+" to occurrence")

# Schemas need duplicating
geocodeSchemas = ['GadmRegion', 'Region', 'Pageable', 'PagingResponseGadmRegion']
for schema in geocodeSchemas:
    occurrence['components']['schemas'][schema] = geocode['components']['schemas'][schema]
print("")

# Special cases for metrics (moving to occurrence)
# Metrics schema can be ignored.
print("--- Moving all method-paths from Metrics to Occurrence ---")

for path in metrics["paths"]:
    occurrence["paths"][path] = metrics["paths"][path]
    print("Added "+path+" to occurrence")

# Schemas need duplicating
metricsSchemas = ['DimensionObject', 'Rollup', 'CountQuery', 'Parameter']
for schema in metricsSchemas:
    occurrence['components']['schemas'][schema] = metrics['components']['schemas'][schema]

# Write the result of all that moving.

with open(output+"/registry.json", "w") as write_file:
    json.dump(registry, write_file, separators=(',', ':'), indent=indent)

with open(output+"/occurrence.json", "w") as write_file:
    json.dump(occurrence, write_file, separators=(',', ':'), indent=indent)
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
    '/dataset/{key}/process',
    '/derivedDataset/dataset/{doiPrefix}/{doiSuffix}',
    '/derivedDataset/dataset/{key}',
    '/derivedDataset/user/{user}',
    '/derivedDataset/{doiPrefix}/{doiSuffix}',
    '/derivedDataset/{doiPrefix}/{doiSuffix}/citation',
    '/derivedDataset/{doiPrefix}/{doiSuffix}/datasets',
    '/enumeration/basic',
    '/enumeration/basic/{name}',
    '/enumeration/country',
    '/enumeration/extension',
    '/enumeration/interpretationRemark',
    '/enumeration/language',
    '/enumeration/license',
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
    '/oai-pmh/registry',
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
            print("Excluding "+method+" "+path+" from Registry key methods view.")
            complicated[method].append(path)
        else:
            print("Including "+method+" "+path+" from Registry key methods view.")
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
registry['info']['title'] = registry['info']['title'] + " — Key methods only"
registry['info']['description'] = "**This is a view of *key methods only*, sufficient for most users of GBIF data.**  Data publishers with write access to the GBIF Registry should refer to the [full Registry API documentation](registry).\n\n" + registry['info']['description']

with open(output+"/registry-key-methods.json", "w") as write_file:
    json.dump(registry, write_file, separators=(',', ':'), indent=indent)
print("")

print("=== OpenAPI specification generation completed ===")

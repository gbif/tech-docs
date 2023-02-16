import sys
import requests
import json

response = requests.get('http://ws.gbif.org/applications', headers={'Accept': 'application/json'})
services = json.loads(response.text)

if len(sys.argv) != 3:
    print("Need 2 arguments, output directory and environment")
    exit(1)

output = sys.argv[1]
env = sys.argv[2]

if env == 'dev':
    indent = 2
else:
    indent = None

print("Output to "+output+" for environment "+env)

urls = {}

# Find services
for s in services:
    for i in s["instances"]:
        if (i['tags']['env'] == env):
            if i['registration']['serviceUrl'].find('gbif.org') > 0:
                urls[s['name']] = i['registration']['serviceUrl']
                print("Found "+env+" "+s['name']+" at "+urls[s['name']])

# Retrieve the documentation
for ws, url in urls.items():
    filename = output + '/' + ws.replace('-ws', '') + '.json'
    print("Fetching documentation for "+ws)
    response = requests.get(url+"v3/api-docs")
    if response.status_code == 200:
        if ws == 'registry-ws':
            registry = json.loads(response.text)
        elif ws == 'occurrence-ws':
            occurrence = json.loads(response.text)
        else:
            openapi = json.loads(response.text)
            with open(filename, "w") as write_file:
                json.dump(openapi, write_file, separators=(',', ':'), indent=indent)
        print("Retrieved documentation for "+ws)

    else:
        print("Response "+str(response.status_code)+" for "+ws+", ignoring while in dev.")

# Special cases for registry and occurrence
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

occurrence['components']['schemas']['PagingResponseDownloadStatistics'] = registry['components']['schemas']['PagingResponseDownloadStatistics']
occurrence['components']['schemas']['DownloadStatistics'] = registry['components']['schemas']['DownloadStatistics']
occurrence['components']['schemas']['PagingResponseDatasetOccurrenceDownloadUsage'] = registry['components']['schemas']['PagingResponseDatasetOccurrenceDownloadUsage']
occurrence['components']['schemas']['DatasetOccurrenceDownloadUsage'] = registry['components']['schemas']['DatasetOccurrenceDownloadUsage']
occurrence['components']['schemas']['DOI'] = registry['components']['schemas']['DOI']
occurrence['components']['schemas']['Download'] = registry['components']['schemas']['Download']
occurrence['components']['schemas']['DownloadRequest'] = registry['components']['schemas']['DownloadRequest']
occurrence['components']['schemas']['PagingResponseDownload'] = registry['components']['schemas']['PagingResponseDownload']

for path in toRemove:
    if path in registry["paths"]:
        del registry["paths"][path]
        print("Removed "+path+" from registry")

with open(output+"/registry.json", "w") as write_file:
    json.dump(registry, write_file, separators=(',', ':'), indent=indent)

with open(output+"/occurrence.json", "w") as write_file:
    json.dump(occurrence, write_file, separators=(',', ':'), indent=indent)

print("------")
print()

complicated = []

for path in occurrence["paths"]:
    for method in occurrence["paths"][path]:
        if "x-Category" in occurrence["paths"][path][method]:
            print("Keep "+method+" "+path)
        else:
            print("Discard "+method+" "+path)
            complicated.append(path)

for path in complicated:
    if path in occurrence["paths"]:
        del occurrence["paths"][path]
        print("Removed "+path+" from basic occurrence")

with open(output+"/basic-occurrence.json", "w") as write_file:
    json.dump(occurrence, write_file, separators=(',', ':'), indent=indent)

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
    indent = None
else:
    indent = 2

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
moveFromRegistryToOccurrence = [
    '/occurrence/download/'
]

toRemove = []

for path in registry["paths"]:
    for prefix in moveFromRegistryToOccurrence:
        if path.startswith(prefix):
            occurrence["paths"][path] = registry["paths"][path]
            print("Added "+path+" to occurrence")
            toRemove.append(path)

for path in toRemove:
    del registry["paths"][path]
    print("Removed "+path+" from registry")

with open(output+"/registry.json", "w") as write_file:
    json.dump(registry, write_file, separators=(',', ':'), indent=indent)

with open(output+"/occurrence.json", "w") as write_file:
    json.dump(occurrence, write_file, separators=(',', ':'), indent=indent)

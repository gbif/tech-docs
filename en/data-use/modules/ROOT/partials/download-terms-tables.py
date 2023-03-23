#
# Create AsciiDoctor tables of the various GBIF download format term definitions.
#

import json
import re
import requests
import sys

from xml.dom.minidom import parse
import xml.dom.minidom

DWC_OCCURRENCE="https://rs.gbif.org/core/dwc_occurrence_2022-02-02.xml"
SIMPLE_MULTIMEDIA="http://rs.gbif.org/terms/1.0/Multimedia"
OPENAPI_OCCURRENCE="https://tech-docs.gbif-dev.org/openapi/occurrence.json"
#OPENAPI_OCCURRENCE="http://localhost:8080/v3/api-docs"
GBIF_API = 'http://api.gbif-dev.org/v1'
#GBIF_API = 'http://localhost:8080'

if len(sys.argv) != 3:
    print("Need 2 arguments, output directory and environment")
    exit(1)

output = sys.argv[1]
env = sys.argv[2]

if env == 'dev':
    indent = 2
else:
    indent = None

def parseExtension(url):
    terms = {}
    response = requests.get(url)
    tree = DOMTree = xml.dom.minidom.parseString(response.text)
    for prop in tree.getElementsByTagName("property"):
        qualName = prop.getAttribute('qualName')
        description = prop.getAttribute('dc:description')
        comments = prop.getAttribute('comments')
        examples = prop.getAttribute('examples')
        possibleElementsName = re.sub(r'purl.org/dc/elements/1.1', r'purl.org/dc/terms', qualName)
        terms[qualName] = { 'description': description, 'comments': comments, 'examples': examples }
        if qualName != possibleElementsName:
            terms[possibleElementsName] = terms[qualName]
    return terms

# Fetch Darwin Core term descriptions
dwc_terms = parseExtension(DWC_OCCURRENCE)

# Fetch Simple Multimedia extension term descriptions
multimedia_terms = parseExtension(SIMPLE_MULTIMEDIA)

# Fetch GBIF Occurrence OpenAPI definitions
gbif_descriptions = {}
response = requests.get(OPENAPI_OCCURRENCE)
occurrence_api = json.loads(response.text)
for prop in occurrence_api['components']['schemas']['Occurrence']['properties']:
    if 'description' in occurrence_api['components']['schemas']['Occurrence']['properties'][prop]:
        prop_key = 'gbifID' if prop == 'key' else prop
        prop_def = occurrence_api['components']['schemas']['Occurrence']['properties'][prop]['description']
        prop_def = re.sub(r'\[(.*?)\]\((.*?)\)', r'link:\2[\1]', prop_def)
        gbif_descriptions[prop_key] = { 'description': prop_def }
    else:
        print("No OpenAPI description for", prop)
gbif_descriptions['issue'] = gbif_descriptions['issues']

# Additional descriptions not defined
gbif_descriptions['eventType'] = {'description': 'The type for sampling event records.'}
gbif_descriptions['hasCoordinate'] = {'description': 'Boolean indicating that a valid latitude and longitude exists.'}
gbif_descriptions['hasGeospatialIssues'] = {'description': 'Boolean indicating that some spatial validation rule has not passed.'}
gbif_descriptions['level0Gid'] = {'description': 'The identifier for the top-level division from the https://gadm.org/[GADM database]. This is usually a three-letter code from ISO 3166.'}
gbif_descriptions['level0Name'] = {'description': 'The English name for the top-level division from the https://gadm.org/[GADM database].'}
gbif_descriptions['level1Gid'] = {'description': 'The identifier for the first-level division from the https://gadm.org/[GADM database].'}
gbif_descriptions['level1Name'] = {'description': 'The English name for the first-level division from the https://gadm.org/[GADM database].'}
gbif_descriptions['level2Gid'] = {'description': 'The identifier for the second-level division from the https://gadm.org/[GADM database].'}
gbif_descriptions['level2Name'] = {'description': 'The English name for the second-level division from the https://gadm.org/[GADM database].'}
gbif_descriptions['level3Gid'] = {'description': 'The identifier for the third-level division from the https://gadm.org/[GADM database].'}
gbif_descriptions['level3Name'] = {'description': 'The English name for the third-level division from the https://gadm.org/[GADM database].'}
gbif_descriptions['mediaType'] = {'description': 'The media type given as Dublin Core type values, in particular StillImage, MovingImage or Sound.'}
gbif_descriptions['numberOfOccurrences'] = {'description': 'The number of occurrences of this species/taxon.'}
gbif_descriptions['projectId'] = {'description': ''}
gbif_descriptions['publisher'] = {'description': 'The name of the organization publishing this record'}
gbif_descriptions['repatriated'] = {'description': 'Boolean indicating if the publishing country is different to the location country.'}
gbif_descriptions['verbatimScientificName'] = {'description': 'Scientific name as provided by the source.'}
#gbif_descriptions[''] = {'description': ''}


types = {
    'STRING': 'String',
    'BOOLEAN': 'Boolean',
    'INT': 'Integer',
    'DOUBLE': 'Double',
    'DATE': 'ISO 8601 Date',
    'ARRAY<STRING>': 'String array, delimited with `;`',
    'STRUCT<concept: STRING,lineage: ARRAY<STRING>>': 'String structure'
}

def write_description_table(term_url, term_set, section, gbif_first, output_file):
    response = requests.get(term_url)
    definitions = json.loads(response.text)

    print("Writing %s to %s" % (term_url, output_file))

    with open(output_file, "w") as f:
        print('[cols="3h,1,1,~"]', file=f)
        print("|===", file=f)
        print("|Column name |Data type |Nullable |Definition", file=f)

        print("", file=f)

        for field in term_set(definitions):
            field_name = field['name']

            # Name
            print('|%s[%s]' % (field['term'], field_name), file=f)

            # Type
            if field['type'] in types:
                print('|%s' % (types[field['type']]), file=f)
            else:
                print('|%s' % (field['type']), file=f)

            # Always present
            print('|%s' % ('No' if field['required'] else 'Yes'), file=f)

            # GBIF definition
            if gbif_first and field_name in gbif_descriptions:
                print('|[[%s.%s]]{gbif_source} %s' % (section, field_name, gbif_descriptions[field_name]['description']), file=f)
            # DWC definition
            elif field['term'] in dwc_terms:
                print('|[[%s.%s]]{dwc_source} %s' % (section, field_name, dwc_terms[field['term']]['description']), file=f)
            # GBIF (if not first)
            elif field_name in gbif_descriptions:
                print('|[[%s.%s]]{gbif_source} %s' % (section, field_name, gbif_descriptions[field_name]['description']), file=f)
            # Simple Multimedia definiton
            elif field['term'] in multimedia_terms:
                print('|[[%s.%s]]{gbif_source} %s' % (section, field_name, multimedia_terms[field['term']]['description']), file=f)
            else:
                print(field_name, "not found in GBIF, DWC or Simple Multimedia definitions")
                print('|–', file=f)

            print('', file=f)

        print("|===", file=f)


# Fetch simple format download terms
write_description_table(GBIF_API + '/occurrence/download/describe/simpleCsv',
                        lambda x : x['fields'],
                        'simpleCsv',
                        True,
                        output+"/download-simple-terms-table.adoc")

# Fetch species list format download terms
write_description_table(GBIF_API + '/occurrence/download/describe/speciesList',
                        lambda x : x['fields'],
                        'speciesList',
                        True,
                        output+"/download-species-list-terms-table.adoc")

# Fetch DWCA format download terms
write_description_table(GBIF_API + '/occurrence/download/describe/dwca',
                        lambda x : x['verbatim']['fields'],
                        'dwca.verbatim',
                        False,
                        output+"/download-dwca-verbatim-terms-table.adoc")

# Fetch DWCA format download terms
write_description_table(GBIF_API + '/occurrence/download/describe/dwca',
                        lambda x : x['interpreted']['fields'],
                        'dwca.interpreted',
                        True,
                        output+"/download-dwca-interpreted-terms-table.adoc")

# Fetch DWCA format download terms
write_description_table(GBIF_API + '/occurrence/download/describe/dwca',
                        lambda x : x['multimedia']['fields'],
                        'dwca.multimedia',
                        True,
                        output+"/download-dwca-multimedia-terms-table.adoc")

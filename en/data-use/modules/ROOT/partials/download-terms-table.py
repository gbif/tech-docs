#
# Create AsciiDoctor tables of the various GBIF download format term definitions.
#

import sys
import requests
import json

from xml.dom.minidom import parse
import xml.dom.minidom

if len(sys.argv) != 3:
    print("Need 2 arguments, output directory and environment")
    exit(1)

output = sys.argv[1]
env = sys.argv[2]

if env == 'dev':
    indent = 2
else:
    indent = None

# Fetch term descriptions
all_terms = {}

response = requests.get('https://rs.gbif.org/core/dwc_occurrence_2022-02-02.xml')
dwc_tree = DOMTree = xml.dom.minidom.parseString(response.text)
#dwc_collection = dwc_tree.documentElement
for prop in dwc_tree.getElementsByTagName("property"):
    qualName = prop.getAttribute('qualName')
    description = prop.getAttribute('dc:description')
    comments = prop.getAttribute('comments')
    examples = prop.getAttribute('examples')
    all_terms[qualName] = { 'description': description, 'comments': comments, 'examples': examples }

types = {
    'STRING': 'String',
    'BOOLEAN': 'Boolean',
    'INT': 'Integer',
    'DOUBLE': 'Double',
    'DATE': 'ISO 8601 Date',
    'ARRAY<STRING>': 'String array',
    'STRUCT<concept: STRING,lineage: ARRAY<STRING>>': 'String structure'
}

def write_description_table(term_url, term_set, output_file):
    response = requests.get(term_url)
    definitions = json.loads(response.text)

    print("Writing %s→%s to %s" % (term_url, term_set, output_file))

    with open(output_file, "w") as f:
        print('[cols="3h,1h,1h,~"]', file=f)
        print("|===", file=f)
        print("|Column name |Data type |Nullable |Description", file=f)

        print("", file=f)

        for field in term_set(definitions):
            print(field)
            print('|%s[%s]' % (field['term'], field['name']), file=f)
            if field['type'] in types:
                print('|%s' % (types[field['type']]), file=f)
            else:
                print('|%s' % (field['type']), file=f)
            print('|%s' % ('No' if field['required'] else 'Yes'), file=f)
            if field['term'] in all_terms:
                print('|%s' % (all_terms[field['term']]['description']), file=f)
            else:
                print('|–', file=f)
            print('', file=f)

        print("|===", file=f)


# Fetch simple format download terms
write_description_table('https://api.gbif.org/v1/occurrence/download/describe/simpleCsv',
                        lambda x : x['fields'],
                        output+"/download-simple-terms-table.adoc")

# Fetch species list format download terms
write_description_table('https://api.gbif.org/v1/occurrence/download/describe/speciesList',
                        lambda x : x['fields'],
                        output+"/download-species-list-terms-table.adoc")

# Fetch DWCA format download terms
write_description_table('https://api.gbif.org/v1/occurrence/download/describe/dwca',
                        lambda x : x['verbatim']['fields'],
                        output+"/download-dwca-verbatim-terms-table.adoc")

# Fetch DWCA format download terms
write_description_table('https://api.gbif.org/v1/occurrence/download/describe/dwca',
                        lambda x : x['interpreted']['fields'],
                        output+"/download-dwca-interpreted-terms-table.adoc")

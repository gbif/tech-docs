#!/bin/bash

set -e

env=dev

if [[ ./en/data-use/modules/ROOT/partials/download-dwca-verbatim-terms-table.adoc -nt ./en/data-use/modules/ROOT/partials/download-terms-tables.py ]]; then
    echo "=== Download term tables already generated, skipping ==="
else
    echo "=== Generate download terms. ==="
    mkdir -p ./en/data-use/modules/ROOT/partials
    python3 ./en/data-use/modules/ROOT/partials/download-terms-tables.py ./en/data-use/modules/ROOT/partials $env
fi
echo

echo "====== Generating HTML ======="
# Not generating internal informatics documentation.

# Only generating English
for lang in en; do
  echo "------- Generating $lang --------"
  rm -Rf output/$lang
  docker run -u $(id -u) -e CI=true -v $PWD:/antora:Z --rm -t antora/antora:3.1.2 development-$lang-playbook.yml
done
echo

if [[ ./output/openapi/registry.json -nt fetch-openapi.py ]]; then
    echo "=== OpenAPI already generated, skipping ==="
else
    echo "=== Fetch OpenAPI schemas. ==="
    mkdir -p ./output/openapi
    python3 fetch-openapi.py output/openapi $env
fi
echo

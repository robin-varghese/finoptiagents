# Biology REST API Examples

Below are example scripts demonstrating how to call the listed Biology REST APIs using Python. These scripts use the `requests` library to make HTTP requests and retrieve data from each API.

## Prerequisites
Install the `requests` library:
```bash
pip install requests
```

## Example Script
```python
import requests

# 1. UniProt REST API
def get_uniprot_data():
    url = "https://rest.uniprot.org/uniprotkb/P00533.fasta"
    response = requests.get(url)
    if response.status_code == 200:
        print("UniProt - Protein P00533 Sequence:", response.text)
    else:
        print("UniProt - Error:", response.status_code)

# 2. Ensembl REST API
def get_ensembl_data():
    url = "https://rest.ensembl.org/sequence/id/ENSG00000139618?content-type=application/json"
    response = requests.get(url)
    if response.status_code == 200:
        print("Ensembl - Gene ENSG00000139618 Sequence:", response.json())
    else:
        print("Ensembl - Error:", response.status_code)

# 3. PDB REST API
def get_pdb_data():
    url = "https://www.rcsb.org/pdb/rest/describeMol?structureId=4HHB"
    response = requests.get(url)
    if response.status_code == 200:
        print("PDB - Hemoglobin 4HHB Details:", response.text)
    else:
        print("PDB - Error:", response.status_code)

# 4. KEGG REST API
def get_kegg_data():
    url = "https://rest.kegg.jp/get/hsa:1"
    response = requests.get(url)
    if response.status_code == 200:
        print("KEGG - Human Pathway hsa:1:", response.text)
    else:
        print("KEGG - Error:", response.status_code)

# 5. Gene Ontology API
def get_go_data():
    url = "https://api.geneontology.org/api/go/ontology/annotations?gene_id=FBgn0000008"
    response = requests.get(url)
    if response.status_code == 200:
        print("GO - Gene FBgn0000008 Annotations:", response.json())
    else:
        print("GO - Error:", response.status_code)

# 6. InterPro REST API
def get_interpro_data():
    url = "https://www.ebi.ac.uk/interpro/api/entry/interpro/IPR000126"
    response = requests.get(url)
    if response.status_code == 200:
        print("InterPro - Entry IPR000126 Details:", response.json())
    else:
        print("InterPro - Error:", response.status_code)

# 7. STRING API
def get_string_data():
    url = "https://string-db.org/api/tsv/get_link?identifiers=9606.ENSP00000303830&limit=10&confidence=0.4"
    response = requests.get(url)
    if response.status_code == 200:
        print("STRING - Protein ENSP00000303830 Interactions:", response.text)
    else:
        print("STRING - Error:", response.status_code)

# 8. BioModels REST API
def get_biomodels_data():
    url = "https://www.ebi.ac.uk/biomodels/model/BIOMD0000000001"
    response = requests.get(url)
    if response.status_code == 200:
        print("BioModels - Model BIOMD0000000001:", response.text)
    else:
        print("BioModels - Error:", response.status_code)

# 9. NCBI Datasets API
def get_ncbi_datasets_data():
    url = "https://api.ncbi.nlm.nih.gov/datasets/v2/genome/taxon/human"
    response = requests.get(url)
    if response.status_code == 200:
        print("NCBI Datasets - Human Genome Data:", response.json())
    else:
        print("NCBI Datasets - Error:", response.status_code)

# 10. RCSB PDB Data API
def get_rcsb_pdb_data():
    url = "https://data.rcsb.org/rest/v1/core/entry/4HHB"
    response = requests.get(url)
    if response.status_code == 200:
        print("RCSB PDB - Entry 4HHB Details:", response.json())
    else:
        print("RCSB PDB - Error:", response.status_code)

# Run all API calls
if __name__ == "__main__":
    get_uniprot_data()
    get_ensembl_data()
    get_pdb_data()
    get_kegg_data()
    get_go_data()
    get_interpro_data()
    get_string_data()
    get_biomodels_data()
    get_ncbi_datasets_data()
    get_rcsb_pdb_data()
```

## Usage Notes
- Ensure you have an active internet connection.
- Some APIs (e.g., KEGG, STRING) have usage limits (e.g., 3 requests per second for KEGG). Implement delays (e.g., `time.sleep(0.34)`) for high-volume requests.
- Check the respective API documentation for additional endpoints and parameters:
  - UniProt: [https://www.uniprot.org/help/programmatic_access](https://www.uniprot.org/help/programmatic_access)
  - Ensembl: [https://rest.ensembl.org/](https://rest.ensembl.org/)
  - PDB: [https://www.rcsb.org/pdb/rest/](https://www.rcsb.org/pdb/rest/)
  - KEGG: [https://www.kegg.jp/kegg/rest/](https://www.kegg.jp/kegg/rest/)
  - Gene Ontology: [https://api.geneontology.org/](https://api.geneontology.org/)
  - InterPro: [https://www.ebi.ac.uk/interpro/api/](https://www.ebi.ac.uk/interpro/api/)
  - STRING: [https://string-db.org/help/api/](https://string-db.org/help/api/)
  - BioModels: [https://www.ebi.ac.uk/biomodels/docs/](https://www.ebi.ac.uk/biomodels/docs/)
  - NCBI Datasets: [https://www.ncbi.nlm.nih.gov/datasets/docs/v2/api/rest-api/](https://www.ncbi.nlm.nih.gov/datasets/docs/v2/api/rest-api/)
  - RCSB PDB Data: [https://data.rcsb.org/](https://data.rcsb.org/)
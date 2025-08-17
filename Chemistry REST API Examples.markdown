# Chemistry REST API Examples

Below are example scripts demonstrating how to call the listed Chemistry REST APIs using Python. These scripts use the `requests` library to make HTTP requests and retrieve data from each API.

## Prerequisites
Install the `requests` library:
```bash
pip install requests
```

## Example Script
```python
import requests

# 1. Chemical Identifier Resolver (CIR)
def get_cir_data():
    url = "http://cactus.nci.nih.gov/chemical/structure/aspirin/smiles"
    response = requests.get(url)
    if response.status_code == 200:
        print("CIR - Aspirin SMILES:", response.text)
    else:
        print("CIR - Error:", response.status_code)

# 2. OPSIN
def get_opsin_data():
    url = "http://opsin.ch.cam.ac.uk/opsin/benzoic+acid.smi"
    response = requests.get(url)
    if response.status_code == 200:
        print("OPSIN - Benzoic Acid SMILES:", response.text)
    else:
        print("OPSIN - Error:", response.status_code)

# 3. CDK Web Services
def get_cdk_data():
    url = "http://ws1.bmc.uu.se:8182/cdk/fingerprint/std/CCO"
    response = requests.get(url)
    if response.status_code == 200:
        print("CDK - Ethanol Fingerprint:", response.text)
    else:
        print("CDK - Error:", response.status_code)

# 4. PubChem PUG-REST
def get_pubchem_data():
    url = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/aceticacid/property/MolecularWeight/JSON"
    response = requests.get(url)
    if response.status_code == 200:
        print("PubChem - Acetic Acid Molecular Weight:", response.json())
    else:
        print("PubChem - Error:", response.status_code)

# 5. PDB REST API
def get_pdb_data():
    url = "http://www.rcsb.org/pdb/rest/describeHet?chemicalID=CB3"
    response = requests.get(url)
    if response.status_code == 200:
        print("PDB - Ligand CB3 Details:", response.text)
    else:
        print("PDB - Error:", response.status_code)

# 6. ChEMBL REST API
def get_chembl_data():
    url = "https://www.ebi.ac.uk/chembl/api/data/molecule.json?molecule_structures__canonical_smiles__flexmatch=OCC"
    response = requests.get(url)
    if response.status_code == 200:
        print("ChEMBL - Molecules with SMILES OCC:", response.json())
    else:
        print("ChEMBL - Error:", response.status_code)

# 7. UniProt REST API
def get_uniprot_data():
    url = "https://rest.uniprot.org/uniprotkb/P00533.fasta"
    response = requests.get(url)
    if response.status_code == 200:
        print("UniProt - Protein P00533 Sequence:", response.text)
    else:
        print("UniProt - Error:", response.status_code)

# 8. KEGG REST API
def get_kegg_data():
    url = "https://rest.kegg.jp/get/hsa:1"
    response = requests.get(url)
    if response.status_code == 200:
        print("KEGG - Human Pathway hsa:1:", response.text)
    else:
        print("KEGG - Error:", response.status_code)

# 9. ChEBI REST API
def get_chebi_data():
    url = "https://www.ebi.ac.uk/chebi/services/search?searchString=ethanol"
    response = requests.get(url)
    if response.status_code == 200:
        print("ChEBI - Ethanol Search Results:", response.text)
    else:
        print("ChEBI - Error:", response.status_code)

# 10. MetaboLights REST API
def get_metabolights_data():
    url = "https://www.ebi.ac.uk/metabolights/ws/studies/MTBLS1"
    response = requests.get(url)
    if response.status_code == 200:
        print("MetaboLights - Study MTBLS1 Metadata:", response.json())
    else:
        print("MetaboLights - Error:", response.status_code)

# Run all API calls
if __name__ == "__main__":
    get_cir_data()
    get_opsin_data()
    get_cdk_data()
    get_pubchem_data()
    get_pdb_data()
    get_chembl_data()
    get_uniprot_data()
    get_kegg_data()
    get_chebi_data()
    get_metabolights_data()
```

## Usage Notes
- Ensure you have an active internet connection.
- Some APIs (e.g., PubChem, KEGG) have usage limits (e.g., 5 requests per second for PubChem). Implement delays (e.g., `time.sleep(0.2)`) for high-volume requests.
- Check the respective API documentation for additional endpoints and parameters:
  - CIR: http://cactus.nci.nih.gov/chemical/structure_documentation
  - OPSIN: http://opsin.ch.cam.ac.uk/instructions.html
  - CDK: http://rest.rguha.net/
  - PubChem: https://pubchem.ncbi.nlm.nih.gov/docs/pug-rest
  - PDB: http://www.rcsb.org/pdb/software/rest.do
  - ChEMBL: https://www.ebi.ac.uk/chembl/api/data/docs
  - UniProt: https://www.uniprot.org/help/programmatic_access
  - KEGG: https://www.kegg.jp/kegg/rest/keggapi.html
  - ChEBI: https://www.ebi.ac.uk/chebi/webServices.do
  - MetaboLights: https://www.ebi.ac.uk/metabolights/ws/api/spec.html
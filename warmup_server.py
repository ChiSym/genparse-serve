import requests
import argparse

parser = argparse.ArgumentParser()
# e.g., "http://34.122.30.137:8888/infer"
parser.add_argument('--endpoint', help='Endpoint to warmup')

args = parser.parse_args()

def load_grammar(grammar_path):
    with open(f"{grammar_path}", "r", encoding="utf-8") as f:
        grammar_str = f.read()
    return grammar_str

grammar_paths = ["resources/us_lpm_prob.lark", "resources/us_lpm_cols.lark"]
grammars = list(map(load_grammar, grammar_paths))
endpoint = args.endpoint

for grammar in grammars:
    request = {
        "prompt": "This is a test prompt",
        "method": "smc-standard",
        "n_particles": 10,
        "lark_grammar": grammar,
        "proposal_name": "character",
        "proposal_args": {},
        "max_tokens": 50,
        "temperature": 1.
    }
    headers = {
        "Content-type": "application/json",
        "Accept": "application/json"
        }
    x = requests.post(endpoint, json = request, headers=headers)
    response = x.json()
    posterior = response['posterior']
    print(posterior)


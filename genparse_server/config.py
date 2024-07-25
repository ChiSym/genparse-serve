model_name = 'meta-llama/Meta-Llama-3.1-8B'
#"hugging-quants/Meta-Llama-3.1-70B-Instruct-AWQ-INT4"

n_processes = 8

proposal_cache_size = 10

type_expectations = {
    'prompt': str,
    'method': str,
    'n_particles': int,
    'lark_grammar': str,
    'proposal_name': str,
    'proposal_args': dict,
    'max_tokens': int,
    'temperature': float
}

defaults = {
    'prompt': None,
    'method': 'smc-standard',
    'n_particles': 30,
    'lark_grammar': None,
    'proposal_name': 'character',
    'proposal_args': {},
    'max_tokens': 100,
    'temperature': 1.0
}
"""
This is a Flask application which provides a web service for running inference using GenParse. 
"""

import logging
import traceback
import argparse
from flask import Flask, request, jsonify, abort
from transformers import AutoTokenizer
import torch
import re
from functools import lru_cache
import threading
import numpy as np

from genparse.cfglm import BoolCFGLM
from genparse.proposal import CharacterProposal, TokenProposal
from genparse.lm import TokenizedLLM
from genparse.backends.vllm import vllmpplLLM, VLLMSampler
from genparse.util import LarkStuff
from genparse import EOS

parser = argparse.ArgumentParser()
parser.add_argument('--debug', action='store_true', help='Enable debug mode')
parser.add_argument('--log-file', type=str, default='log/server.log', help='Path to log file')

args = parser.parse_args()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

if args.log_file is not None:
    file_handler = logging.FileHandler(args.log_file)
    file_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    logging.getLogger().addHandler(file_handler)

## utils

def load_lark_guide(grammar_path):
    grammar = open(grammar_path, 'r').read()
    return make_guide(grammar)

def load_proposal(proposal_name, llm, guide, args):
    if proposal_name == 'character':
        return CharacterProposal(llm=llm, guide=guide, **args)
    elif proposal_name == 'token':
        return TokenProposal(llm=llm, guide=guide, **args)
    else:
        raise ValueError(f'invalid proposal name {proposal_name!r}')
    
@lru_cache(maxsize=10)
def make_guide(grammar_string):
    try:
        lark = LarkStuff(grammar_string)
    except Exception as e:
        raise ValueError(f"Lark error : {e}")
    return BoolCFGLM(lark.char_cfg())
    
def post_process_posterior(posterior):
    return {re.sub('</s>', '', re.sub(EOS, '', x)) : p for x,p in posterior.items()}

## guides and llm

BATCH_SIZE = 80
#MODEL_ID = 'codellama/CodeLlama-7b-hf'
MODEL_ID = 'meta-llama/Meta-Llama-3-8B-Instruct'

logging.info(f"loading {MODEL_ID} with batch_size={BATCH_SIZE}")

LLM = TokenizedLLM(
    model=vllmpplLLM(MODEL_ID, dtype=torch.float16),
    tokenizer=AutoTokenizer.from_pretrained(MODEL_ID),
    batch_size=BATCH_SIZE
)

## app

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
    'n_particles': 25,
    'lark_grammar': None,
    'proposal_name': 'character',
    'proposal_args': {},
    'max_tokens': 100,
    'temperature': 1.0
}

app = Flask(__name__)
task_lock = threading.Lock()  

def process_inference_task(data):
    for param_name, expected_type in type_expectations.items():
        d = data.get(param_name, defaults[param_name])
        if not isinstance(d, expected_type):
            raise ValueError(
                f'{param_name} should be of type {expected_type.__name__} not {type(d).__name__}'
            )

    prompt = data['prompt']
    method = data.get('method', defaults['method'])
    n_particles = data.get('n_particles', defaults['n_particles'])
    lark_grammar = data.get('lark_grammar', defaults['lark_grammar'])
    proposal_name = data.get('proposal_name', defaults['proposal_name'])
    proposal_args = data.get('proposal_args', defaults['proposal_args'])
    temperature = data.get('temperature', defaults['temperature'])
    max_tokens = data.get('max_tokens', defaults['max_tokens'])

    guide = make_guide(lark_grammar)
    logging.info('Loaded guide for custom grammar')

    proposal = load_proposal(proposal_name, LLM, guide, proposal_args)
    logging.info(f'Loaded proposal {proposal_name}')

    LLM.temperature = temperature

    sampler = VLLMSampler(llm=LLM, guide=guide)
    logging.info('Loaded sampler')

    results = sampler.run_inference(
        prompt=prompt,
        method=method,
        n_particles=n_particles,
        proposal=proposal,
        max_tokens=max_tokens,
        verbosity=int(args.debug)
    )

    if not hasattr(results, 'posterior'):
        raise ValueError('Invalid results object, posterior attribute not found')

    logging.info('Inference completed successfully')

    return {
        'posterior' : post_process_posterior(results.posterior),
        'log_ml_estimate' : results.log_ml
    }

@app.route('/infer', methods=['POST'])
def run_inference():
    try:
        data = request.get_json(force=True)
        # force sequential processing of concurrent requests with lock
        with task_lock:
            return jsonify(process_inference_task(data))

    except Exception as e:
        logging.error(f'Server error: {str(e)}')
        logging.error(traceback.format_exc())
        abort(500, f'Server error: {str(e)}')

if __name__ == '__main__':
    from waitress import serve
    serve(app, host="0.0.0.0", port=8888)
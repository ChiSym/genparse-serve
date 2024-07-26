"""
This is a Flask application which provides a web service for running inference using GenParse. 
"""

import os
import time
import logging
import traceback
import argparse
import threading
from flask import Flask, request, jsonify, abort

from util import load_llm, post_process_posterior
from config import model_name, defaults, type_expectations, proposal_cache_size
from cache import ProposalCache

from genparse.experimental.batch_inference import BatchStepModel, BatchVLLM, smc 

os.environ['TOKENIZERS_PARALLELISM'] = '(true | false)'

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

llm = load_llm(model_name)

logging.info(f"Loaded {model_name}")

app = Flask(__name__)
task_lock = threading.Lock() 

proposal_cache = ProposalCache(maxsize=proposal_cache_size)

def process_inference_task(request):
    start_time = time.time()

    for param_name, expected_type in type_expectations.items():
        d = request.get(param_name, defaults[param_name])
        if not isinstance(d, expected_type):
            raise ValueError(
                f'{param_name} should be of type {expected_type.__name__} not {type(d).__name__}'
            )
        request[param_name] = d

    if request['n_particles'] > 350:
        ValueError('n_particles must be less than 350')

    parallel_proposal = proposal_cache.fetch_or_create_proposal(request, llm)
    step_model = BatchStepModel(parallel_proposal, BatchVLLM(llm), max_tokens = request['max_tokens'])

    start_time = time.time()

    step_model.batch_llm.set_prompt(request['prompt'])
    results = smc(step_model, n_particles=request['n_particles'])

    logging.info(f'Inference complete in {time.time() - start_time:.2f} secs')

    return {
        'posterior' : post_process_posterior(results.posterior),
        'log_ml_estimate' : results.log_ml
    }

@app.route('/infer', methods=['POST'])
def run_inference():
    try:
        request_data = request.get_json(force=True)
        # force sequential processing of concurrent requests with lock
        with task_lock:
            return jsonify(process_inference_task(request_data))

    except Exception as e:
        logging.error(f'Server error: {str(e)}')
        logging.error(traceback.format_exc())
        abort(500, f'Server error: {e}')

if __name__ == '__main__':
    from waitress import serve
    serve(app, host="0.0.0.0", port=8888)
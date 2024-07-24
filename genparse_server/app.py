"""
This is a Flask application which provides a web service for running inference using GenParse. 
"""

import time
import logging
import traceback
import argparse
import threading
from flask import Flask, request, jsonify, abort

from util import load_llm, post_process_posterior, load_proposal, make_guide
from config import model_name, defaults, type_expectations

from genparse.experimental.batch_inference import BatchStepper, BatchVLLM, smc 

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

def modify_request(request):
    global PREV_REQUEST
    PREV_REQUEST = request

def modify_step_model(step_model):
    global STEP_MODEL
    STEP_MODEL = step_model

def maintain_current_model(request, prev_request):
    if prev_request is None:
        return False
    else:
        return (
            request['lark_grammar'] == prev_request['lark_grammar'] and 
            request['proposal_name'] == prev_request['proposal_name'] and
            request['proposal_args'] == prev_request['proposal_args']
        )
    
modify_request(None)
modify_step_model(None)

def process_inference_task(request):
    start_time = time.time()

    for param_name, expected_type in type_expectations.items():
        d = request.get(param_name, defaults[param_name])
        if not isinstance(d, expected_type):
            raise ValueError(
                f'{param_name} should be of type {expected_type.__name__} not {type(d).__name__}'
            )
        request[param_name] = d

    if maintain_current_model(request, PREV_REQUEST):
        logging.info('Maintaining current step model')
        step_model = STEP_MODEL
        step_model.max_tokens = request['max_tokens']
    else:
        logging.info('Initializing new step model')

        if STEP_MODEL is not None:
            start_time = time.time()
            STEP_MODEL.cleanup()
            logging.info(f'Cleaned up previous step model {time.time() - start_time:.2f}')

        start_time = time.time()
        guide = make_guide(request['lark_grammar'])
        logging.info(f'Loaded guide for custom grammar {time.time() - start_time:.2f}')

        start_time = time.time()
        parallel_proposal = load_proposal(
            request['proposal_name'], llm, guide, request['proposal_args']
        )
        logging.info(f'Loaded proposal {time.time() - start_time:.2f}')

        start_time = time.time()
        step_model = BatchStepper(parallel_proposal, BatchVLLM(llm), max_tokens = request['max_tokens'])
        logging.info(f'Loaded step model {time.time() - start_time:.2f}')

        modify_step_model(step_model)

    modify_request(request)

    start_time = time.time()
    step_model.batch_llm.set_prompt(request['prompt'])
    results = smc(step_model, n_particles=request['n_particles'])
    logging.info(f'Inference complete {time.time() - start_time:.2f}')

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
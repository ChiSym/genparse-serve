"""
This is a Flask application which provides a web service for running inference using GenParse. 
"""

import os
import time
import logging
import traceback
import argparse
import threading
import uuid
from flask import Flask, request, jsonify, abort, send_from_directory
from flask_socketio import SocketIO
from collections import defaultdict
import psutil
import GPUtil

from util import load_llm, post_process_posterior, emit_status_update
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

socketio = SocketIO(app, async_mode='eventlet')
# In-memory storage for requests
historical_requests = defaultdict(
    lambda: {'steps': [], 'attributes': None, 'result': None, 'error': None, 'ongoing': True, 'request_id' : None}
)

proposal_cache = ProposalCache(maxsize=proposal_cache_size)

def validate_request(request):
    for param_name, expected_type in type_expectations.items():
        d = request.get(param_name, defaults[param_name])
        if not isinstance(d, expected_type):
            raise ValueError(
                f'{param_name} should be of type {expected_type.__name__} not {type(d).__name__}'
            )
        request[param_name] = d

    if request['n_particles'] > 350:
        raise ValueError('n_particles must be less than 350')

    return request

def process_inference_task(request):
    request = validate_request(request)

    max_tokens = request['max_tokens']
    request_id = request['request_id']
    n_particles = request['n_particles']
    
    emit_status_update(
        socketio=socketio, 
        historical_requests=historical_requests, 
        request_id=request_id, 
        step='Received inference request', 
        attributes=request
    )

    parallel_proposal = proposal_cache.fetch_or_create_proposal(
        request=request, 
        llm=llm, 
        socketio=socketio, 
        historical_requests=historical_requests
    )

    step_model = BatchStepModel(
        batch_proposal=parallel_proposal, 
        batch_llm=BatchVLLM(llm), 
        max_tokens=max_tokens
    )

    emit_status_update(
        socketio=socketio, 
        historical_requests=historical_requests, 
        request_id=request_id, 
        step='Running inference'
    )

    start_time = time.time()

    step_model.batch_llm.set_prompt(request['prompt'])
    results = smc(step_model, n_particles=n_particles)

    inference_time = time.time() - start_time

    result = {
        'posterior': post_process_posterior(results.posterior),
        'log_ml_estimate': results.log_ml
    }

    emit_status_update(
        socketio=socketio, 
        historical_requests=historical_requests, 
        request_id=request_id, 
        step='Inference complete',
        result=result,
        duration=inference_time
    )

    logging.info(f'inference complete in {inference_time} seconds')

    return result
  

@app.route('/infer', methods=['POST'])
def run_inference():
    request_id = str(uuid.uuid4())
    try:
        request_data = request.get_json(force=True)
        # force sequential processing of concurrent requests with lock
        with task_lock:
            request_data['request_id'] = request_id
            historical_requests[request_id]['request_id'] = request_id
            return jsonify(process_inference_task(request_data))

    except Exception as e:
        logging.error(f'Server error: {str(e)}')
        logging.error(traceback.format_exc())
        emit_status_update(
            socketio=socketio, 
            request_id=request_id, 
            step=f'Request failed',
            historical_requests=historical_requests,
            error=str(e)
        )
        abort(500, f'Server error: {e}')

@app.route('/history', methods=['GET'])
def get_history():
    logging.info('sending history')
    return jsonify(list(historical_requests.values()))

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

if __name__ == '__main__':
    socketio.run(app, host="0.0.0.0", port=8888)
from collections import deque
from util import load_proposal, make_guide, emit_status_update
import logging
import time

class ProposalCache:
    def __init__(self, maxsize=10):
        self.maxsize = maxsize
        self.cache = {}
        self.recent_keys = deque(maxlen=10)

    def make_cache_key(self, request):
        if len(request['proposal_args']) == 0:
            return (
                request['lark_grammar'],
                request['proposal_name']
            )
        elif len(request['proposal_args']) == 1 and 'K' in request['proposal_args']:
            return (
                request['lark_grammar'],
                request['proposal_name'],
                request['proposal_args']['K']
            )
        else:
            raise ValueError('Invalid proposal arguments.')
    
    def fetch_or_create_proposal(
        self, request, llm, socketio=None, historical_requests=None
    ):
        
        key = self.make_cache_key(request)

        if key in self.cache:
            logging.info('Reusing cached parallel proposal')
            
            if socketio is not None:
                emit_status_update(
                    socketio=socketio, 
                    request_id=request['request_id'], 
                    step='Fetching cached proposal',
                    historical_requests=historical_requests
                )
            
            self.recent_keys.append(key)
            
            return self.cache[key]
        else:
            logging.info('Creating new parallel proposal')

            if socketio is not None:
                emit_status_update(
                    socketio=socketio, 
                    request_id=request['request_id'], 
                    historical_requests=historical_requests,
                    step='Initializing grammar'
                )

            start_time = time.time()
            guide = make_guide(request['lark_grammar'])

            if socketio is not None:
                emit_status_update(
                    socketio=socketio, 
                    request_id=request['request_id'], 
                    historical_requests=historical_requests,
                    step='Initialized grammar',
                    duration=time.time() - start_time
                )

                emit_status_update(
                    socketio=socketio, 
                    request_id=request['request_id'], 
                    historical_requests=historical_requests,
                    step='Creating new proposal',
                )
            
            parallel_proposal = load_proposal(
                request['proposal_name'], llm, guide, request['proposal_args']
            )
    
            self.cache[key] = parallel_proposal
            self.recent_keys.append(key)
            
            if len(self.cache) > self.maxsize:
                logging.info('Evicting old parallel proposal')
                self.evict_objects()
            
            return parallel_proposal
    
    def evict_objects(self):
        keys_to_remove = set(self.cache.keys()) - set(self.recent_keys)
        
        for key in keys_to_remove:
            self.cache[key].cleanup()
            del self.cache[key]
    
    def clear_cache(self):
        self.cache.clear()
        self.recent_keys.clear()
    
    def __repr__(self):
        return f"ProposalCache(maxsize={self.maxsize}, current_size={len(self.cache)})"
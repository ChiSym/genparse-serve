import re
from functools import lru_cache
from genparse.util import lark_guide
from genparse import EOS

from genparse.experimental.batch_inference import ParallelCharacterProposal, ParallelTokenProposal

from config import n_processes

def load_proposal(proposal_name, llm, guide, args):
    if proposal_name == 'character':
        return ParallelCharacterProposal(
            llm=llm, guide=guide, num_processes=n_processes, max_n_particles=350, seed=0
        )
    elif proposal_name == 'token':
        return ParallelTokenProposal(
            llm=llm, guide=guide, K=args['K'], num_processes=n_processes, max_n_particles=350, seed=0
        )
    else:
        raise ValueError(f'Invalid proposal name {proposal_name!r}')
    
@lru_cache(maxsize=10)
def make_guide(grammar_string):
    try:
        guide = lark_guide(grammar_string)
    except Exception as e:
        raise ValueError(f"Guide initialization error : {e}")
    return guide
    
def post_process_posterior(posterior):
    return {re.sub('</s>', '', re.sub(EOS, '', x)) : p for x,p in posterior.items()}

def load_llm(model_name):
    from genparse.lm import VirtualTokenizedLLM

    llm = VirtualTokenizedLLM.from_name(model_name, seed = 0)

    return llm

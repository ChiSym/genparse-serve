# genparse-serve

This is a repository for a Flask application which serves GenParse requests from a GCP instance.


## Setup

* Create a GCP instance (ideally with at least one GPU).
* Setup a static external IP address for this instance:
    * Promote the VM’s ephemeral external address to a static one by following the instructions [here](https://cloud.google.com/vpc/docs/reserve-static-external-ip-address#promote_ephemeral_ip).
    * Allow HTTP and HTTPS traffic.
    * Expose ports `8888` and `9999`. In `probcomp-caliban`, this can be done by adding the `caliban` and `expose-port-9999` network tags.
* SSH into the GCP instance.
* Setup `genparse` by running:
	```bash
	git clone git@github.com:probcomp/genparse.git
 	cd genparse
 	make env
	```
 	We recommend setting up a genparse in a conda environment with python 3.10.
* Clone this repository.
* Install flask and waitress with `pip install flask waitress`
* Create a service file and start the server with 
	```bash
	sh start.sh path-to-genparse-conda-env
 	```
 	For example:
	```bash
	sh start.sh /home/lebrunb/miniconda3/envs/genparse
	```

* Check the status of the server with `sudo systemctl status genparse-server-app.service`.
* You can restart the server with `sudo systemctl restart genparse-server-app.service`.

This repository also contains a Flask application to remotely restart the GenParser server in case of failure. This application is located in `src/restart_service_app` and can be accessed at `<STATIC-IP>:9999/` in a browser. This app will be started when you run `start.sh`, and you can check its status with `sudo systemctl status restart-service-app.service`. 


## Example usage

Once setup, the server should accept requests made to `<STATIC-IP>:8888/infer`.

```python
import requests

url = '<STATIC-IP>:8888/infer'
headers = {'Content-Type': 'application/json'}
data = {
    "prompt": "",
    "method": "smc-standard",
    "n_particles": 5,
    "lark_grammar": "start: \"Sequential Monte Carlo is \" ( \"good\" | \"bad\" )",
    "proposal_name": "character",
    "proposal_args": {},
    "max_tokens": 25
}

response = requests.post(url, json=data, headers=headers)
```

```bash
curl -X POST <STATIC-IP>:8888/infer \
		-H "Content-Type: application/json" \
		-d '{
			    "prompt": "",
			    "method": "smc-standard",
			    "n_particles": 5,
			    "lark_grammar": "start: \"Sequential Monte Carlo is \" ( \"good\" | \"bad\" )",
			    "proposal_name": "character",
			    "proposal_args": {},
			    "max_tokens": 25
		}'
```


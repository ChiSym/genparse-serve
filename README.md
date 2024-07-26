# genparse-serve

This is a repository for a simple Flask application which serves GenParse requests from a GCP instance.



## Setup

* Create a GCP instance (ideally with at least one GPU).
* Setup a static external IP address for this instance:
    * Promote the VM’s ephemeral external address to a static one by following the instructions [here](https://cloud.google.com/vpc/docs/reserve-static-external-ip-address#promote_ephemeral_ip).
    * Allow HTTP and HTTPS traffic.
    * Expose port `8888`. In `probcomp-caliban`, this can be done by adding the `caliban` network tag.
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
sh init_genparse_service.sh path-to-genparse-server-sub-dir path-to-genparse-conda-env
# for example:
sh init_genparse_service.sh $PWD/genparse_server /home/lebrunb/miniconda3/envs/genparse
```

* Check the status of the server with `sudo systemctl status genparse-server-app.service`.
* You can restart the server with `sudo systemctl restart genparse-server-app.service`.


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
## Optional: Setup an app to restart the server remotely

This repository also contains a Flask application to remotely restart the GenParser server in case of failure. This application is located in `restart_service_app`.

### Setup

* Expose port 9999. In `probcomp-caliban`, this can be done by adding the `expose-port-9999` network tag.
* Create a service file at `/etc/systemd/system/restart-service-app.service`. This file should be of the form:
  	```bash
   	[Unit]
	Description=GenParse Server Restart Application
	After=network.target
	
	[Service]
	User=lebrunb
	Group=lebrunb
	WorkingDirectory=/home/lebrunb/genparse-serve/restart_service_app
	Environment="PATH=/home/lebrunb/miniconda3/envs/genparse/bin"
	Environment="USERNAME=<USERNAME>"
	Environment="PASSWORD=<PASSWORD>"
	ExecStart=/home/lebrunb/miniconda3/envs/genparse/bin/python /home/lebrunb/genparse-serve/restart_service_app/app.py
	Restart=always
	RestartSec=3
	StandardOutput=append:/home/lebrunb/genparse-serve/log/genparse-restart-service.log
	StandardError=append:/home/lebrunb/genparse-serve/log/genparse-restart-service.log
	
	[Install]
	WantedBy=multi-user.target
   	```
  	Note that you will need to chose a `USERNAME` and `PASSWORD`.
* Enable the service with `sudo systemctl enable /etc/systemd/system/restart-service-app.service`.
* Start the service with `sudo systemctl start restart-service-app.service`.
* Check the status of the server with `sudo systemctl status restart-service-app.service`. You should expect to see a status of the form:
	```bash
	● restart-service-app.service - GenParse Server Restart Application
     Loaded: loaded (/etc/systemd/system/restart-service-app.service; enabled; preset: enabled)
     Active: active (running) since Tue 2024-07-23 20:07:04 UTC; 6s ago
   Main PID: 62688 (python)
      Tasks: 5 (limit: 102548)
     Memory: 18.1M
        CPU: 165ms
     CGroup: /system.slice/restart-service-app.service
             └─62688 /home/lebrunb/miniconda3/envs/genparse/bin/python /home/lebrunb/genparse-serve/restart_service_app/app.py
 	```
* You should now be able to go to `<STATIC-IP>:9999/` on a browser to restart the server. 




# genparse-serve

## Setup

* Create a GCP instance
* Setup a static external IP address for this instance:
    * Promote the VM’s ephemeral external address to a static one.
    * Allow HTTP and HTTPS traffic.
    * Expose port `8888`. In `probcomp-caliban`, this can be done by adding the `caliban` network tag.
* SSH into the GCP instance.
* Setup `genparse`
    * `git clone git@github.com:probcomp/genparse.git`
    * `cd genparse`
    * `make env`
* Clone this repo
* Create directory for log files with `mkdir log`
* Install flask and waitress with `pip install flask waitress`
* Create a service file at `/etc/systemd/system/genparse-server-app.service`. For example:
  ```bash
  [Unit]
  Description=GenParse Flask Application
  After=network.target
    
  [Service]
  User=lebrunb
  Group=lebrunb
  WorkingDirectory=/home/lebrunb/genparse-serve
  Environment="PATH=/home/lebrunb/miniconda3/genparse/bin"
  ExecStart=/home/lebrunb/miniconda3/envs/genparse/bin/python /home/lebrunb/genparse-serve/app.py
  Restart=always
  RestartSec=3
  StandardOutput=append:/home/lebrunb/genparse-serve/log/genparse-service-error.log
  StandardError=append:/home/lebrunb/genparse-serve/log/genparse-service-error.log
    
  [Install]
  WantedBy=multi-user.target
  ```
  - Enable service: `sudo systemctl enable /etc/systemd/system/genparse-server-app.service`
  - Start service: `sudo systemctl start genparse-server-app.service`
  - Check status: `sudo systemctl status genparse-server-app.service`

## Example usage

```python
import requests

url = '<STATIC-IP>/infer'
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

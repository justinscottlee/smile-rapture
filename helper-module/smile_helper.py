EXPERIMENT_ID = 0

import requests

def log(message: str):
	url = f"http://localhost:5001/upload_results/{EXPERIMENT_ID}"
	obj = {"message": message}
	req = requests.post(url, json = obj)

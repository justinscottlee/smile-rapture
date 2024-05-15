import kubernetes
import requests

try:
    kubernetes.config.load_kube_config(config_file="/etc/rancher/k3s/k3s.yaml")
except Exception as e:
    print(f"Kubernetes not loaded, continuing in debug mode\n{str(e)}")

core_v1 = kubernetes.client.CoreV1Api()
batch_v1 = kubernetes.client.BatchV1Api()


# Make sure we can connect to the kubernetes API
def get_kube_connected_state():
    try:
        core_v1.list_node()
        return "API connection successful"
    except Exception as e:
        print(f"Failed to connect to Kubernetes API: {e}")
        return "API connection failed"


def check_docker_registry_status(registry_url):
    try:
        # Typically, the /v2/_catalog endpoint can be used to list repositories, if accessible.
        response = requests.get(f"{registry_url}/v2/_catalog")

        # Check if the request was successful
        if response.status_code == 200:
            return True
        else:
            print(f"Failed to reach Docker registry. Status code: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"Error connecting to Docker registry: {e}")
        return False

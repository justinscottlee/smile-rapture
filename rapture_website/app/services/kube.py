import kubernetes

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

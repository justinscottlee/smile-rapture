import kubernetes

try:
    kubernetes.config.load_kube_config(config_file="/etc/rancher/k3s/k3s.yaml")
except Exception as E:
    print("Kubernetes not loaded, continuing in debug mode")
    
core_v1 = kubernetes.client.CoreV1Api()
batch_v1 = kubernetes.client.BatchV1Api()

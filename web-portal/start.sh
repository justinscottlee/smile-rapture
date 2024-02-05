docker buildx build --push --platform linux/arm64,linux/amd64 --tag $1/registry/$2 . --output=type=registry,registry.insecure=true

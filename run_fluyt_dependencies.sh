# Start redis
docker stop agent-test-harness-redis || true
docker run -d --rm --name agent-test-harness-redis -p 6379:6379 redis:7-alpine 

# Start qdrant
docker stop agent-test-harness-qdrant || true
docker run -d --rm --name agent-test-harness-qdrant -p 6333:6333 -p 6334:6334 qdrant/qdrant:v1.9.2

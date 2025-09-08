#!/bin/bash
# Simple script to test Docker build locally before Railway deployment

echo "🐳 Testing Docker build for Railway deployment..."
echo "=================================================="

# Build the Docker image
echo "📦 Building Docker image..."
docker build -t sage-ai-test .

if [ $? -ne 0 ]; then
    echo "❌ Docker build failed!"
    exit 1
fi

echo "✅ Docker build successful!"

# Test running the container
echo "🚀 Testing container startup..."
docker run -d --name sage-test -p 5000:5000 -e PORT=5000 sage-ai-test

# Wait a few seconds for startup
sleep 5

# Test if the container is running
if docker ps | grep -q sage-test; then
    echo "✅ Container started successfully!"
    
    # Test health endpoint
    echo "🔍 Testing health endpoint..."
    if curl -f http://localhost:5000/api/health > /dev/null 2>&1; then
        echo "✅ Health endpoint responding!"
    else
        echo "⚠️ Health endpoint not responding (may need API keys)"
    fi
else
    echo "❌ Container failed to start!"
    docker logs sage-test
fi

# Cleanup
echo "🧹 Cleaning up..."
docker stop sage-test 2>/dev/null
docker rm sage-test 2>/dev/null
docker rmi sage-ai-test 2>/dev/null

echo "🎉 Docker test complete!"
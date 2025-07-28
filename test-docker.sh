#!/bin/bash

# Test script for Docker GPG webservice

echo "Building Docker image..."
docker-compose build

echo "Starting the service..."
docker-compose up -d

echo "Waiting for service to start..."
sleep 5

echo "Testing registration endpoint..."
curl -X POST http://localhost:5000/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "testpass123",
    "email": "test@example.com"
  }'

echo -e "\n\nTesting login endpoint..."
API_KEY=$(curl -s -X POST http://localhost:5000/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "testpass123"
  }' | grep -o '"api_key":"[^"]*"' | cut -d'"' -f4)

echo "API Key: $API_KEY"

echo -e "\n\nTesting get public key endpoint..."
curl -X GET http://localhost:5000/get_public_key \
  -H "X-API-KEY: $API_KEY"

echo -e "\n\nStopping service..."
docker-compose down

echo -e "\nDocker test completed!"

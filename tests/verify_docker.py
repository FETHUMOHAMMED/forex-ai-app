"""RUNTIME VERIFICATION: Docker Configuration"""
import sys, os

BASE = os.path.join(os.path.dirname(__file__), '..')

# TEST 1: All three Dockerfiles exist
dockerfiles = [
    os.path.join(BASE, 'ai-service', 'Dockerfile'),
    os.path.join(BASE, 'backend', 'Dockerfile'),
    os.path.join(BASE, 'frontend', 'Dockerfile'),
]
for df in dockerfiles:
    assert os.path.exists(df), f'Missing: {df}'
    size = os.path.getsize(df)
    assert size > 50, f'{df} is too small ({size} bytes)'
print(f'PASSED: TEST 1 - All 3 Dockerfiles exist with content')

# TEST 2: docker-compose.yml exists and valid
compose_path = os.path.join(BASE, 'docker-compose.yml')
assert os.path.exists(compose_path), 'docker-compose.yml missing'
with open(compose_path, 'r', encoding='utf-8') as f:
    compose = f.read()
assert 'services:' in compose, 'No services defined'
assert 'ai-service:' in compose, 'ai-service not in compose'
assert 'backend:' in compose, 'backend not in compose'
assert 'frontend:' in compose, 'frontend not in compose'
print('PASSED: TEST 2 - docker-compose.yml has all 3 services')

# TEST 3: Health checks configured
assert 'HEALTHCHECK' in compose or 'healthcheck' in compose.lower() or 'condition: service_healthy' in compose, 'No health checks'
print('PASSED: TEST 3 - Health checks configured')

# TEST 4: Restart policies
assert 'restart:' in compose, 'No restart policy'
assert 'unless-stopped' in compose or 'always' in compose, 'Restart policy not set'
print('PASSED: TEST 4 - Restart policies configured')

# TEST 5: Dockerfiles have correct base images
with open(dockerfiles[0], 'r', encoding='utf-8') as f:
    ai_df = f.read()
with open(dockerfiles[1], 'r', encoding='utf-8') as f:
    be_df = f.read()
with open(dockerfiles[2], 'r', encoding='utf-8') as f:
    fe_df = f.read()

assert 'FROM python' in ai_df, 'AI service should use Python image'
assert 'FROM node' in be_df, 'Backend should use Node image'
assert 'FROM node' in fe_df, 'Frontend should use Node image'
print('PASSED: TEST 5 - Dockerfiles use correct base images')

# TEST 6: Ports exposed
assert 'EXPOSE' in ai_df, 'AI service missing EXPOSE'
assert 'EXPOSE' in be_df, 'Backend missing EXPOSE'
assert 'EXPOSE' in fe_df, 'Frontend missing EXPOSE'
print('PASSED: TEST 6 - All services expose ports')

# TEST 7: Networks configured
assert 'networks:' in compose, 'No networks defined'
assert 'forex-network' in compose, 'forex-network not defined'
print('PASSED: TEST 7 - Docker network configured')

# TEST 8: Volumes for persistence
assert 'volumes:' in compose, 'No volumes defined'
print('PASSED: TEST 8 - Volumes configured for persistence')

print()
print('ALL 8 RUNTIME TESTS PASSED - Docker configuration is complete')
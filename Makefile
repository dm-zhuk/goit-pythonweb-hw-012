# Configuration
COV_FILE=.coverage
PYTHON=poetry run python
POETRY=poetry run
DOCKER_COMPOSE=docker-compose -f docker-compose.test.yaml

# Unit tests (run locally via Poetry)
.coverage.unit:
	@echo "🧪 Running local unit tests (pure mocks)..."
	$(POETRY) pytest tests/unit --cov-report=term-missing --cov-config=.coveragerc
	@mv .coverage .coverage.unit

# Integration tests (run inside Docker)
.coverage.integration:
	@echo "🐳 Starting integration services (DB + Redis)..."
	$(DOCKER_COMPOSE) up -d --build redis-test test-db
	sleep 5  # Wait for health checks to pass
	@echo "🧪 Running integration tests in Docker..."

	# Step 1: Run tests without auto-removal
	docker-compose -f docker-compose.test.yaml run --name contacts-test-temp contacts-test \
		pytest tests/integration --cov-report=term-missing --cov-config=.coveragerc

	# Step 2: Copy coverage from container
	docker cp contacts-test-temp:/app/.coverage .coverage.integration

	# Step 3: Clean up container
	docker rm contacts-test-temp >/dev/null

# Combine host + Docker coverage results
combine-coverage: .coverage.unit .coverage.integration
	@echo "📦 Combining unit + integration coverage..."
	$(POETRY) coverage combine .coverage.unit .coverage.integration
	$(POETRY) coverage report --rcfile=.coveragerc
	$(POETRY) coverage html --rcfile=.coveragerc
	@echo "✅ HTML report at htmlcov/index.html"

# Full test pipeline
test-all: clean combine-coverage

# Cleanup
clean:
	@echo "🧹 Cleaning up..."
	rm -f .coverage .coverage.unit .coverage.integration
	rm -rf htmlcov
	$(DOCKER_COMPOSE) down -v --remove-orphans

.PHONY: unit integration combine-coverage test-all clean
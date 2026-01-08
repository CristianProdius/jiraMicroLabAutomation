.PHONY: help install install-backend install-frontend dev dev-backend dev-frontend build test test-backend lint clean docker-up docker-down db-migrate db-upgrade

# Default target
help:
	@echo "Jira Feedback Dashboard - Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make install          Install all dependencies (backend + frontend)"
	@echo "  make install-backend  Install backend Python dependencies"
	@echo "  make install-frontend Install frontend Node dependencies"
	@echo ""
	@echo "Development:"
	@echo "  make dev              Run both backend and frontend in development mode"
	@echo "  make dev-backend      Run only backend in development mode"
	@echo "  make dev-frontend     Run only frontend in development mode"
	@echo ""
	@echo "Testing:"
	@echo "  make test             Run all tests"
	@echo "  make test-backend     Run backend tests only"
	@echo "  make lint             Run linters for both backend and frontend"
	@echo ""
	@echo "Database:"
	@echo "  make db-migrate       Create new Alembic migration"
	@echo "  make db-upgrade       Apply all pending migrations"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-up        Start all services with Docker Compose"
	@echo "  make docker-down      Stop all Docker services"
	@echo "  make docker-build     Build Docker images"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean            Remove build artifacts and caches"

# ===================
# Installation
# ===================
install: install-backend install-frontend
	@echo "All dependencies installed!"

install-backend:
	@echo "Installing backend dependencies..."
	cd backend && pip install -e ".[dev]"

install-frontend:
	@echo "Installing frontend dependencies..."
	cd frontend && npm install

# ===================
# Development
# ===================
dev:
	@echo "Starting backend and frontend in development mode..."
	@trap 'kill 0' SIGINT; \
	(cd backend && uvicorn api.main:app --reload --port 8000) & \
	(cd frontend && npm run dev) & \
	wait

dev-backend:
	@echo "Starting backend in development mode..."
	cd backend && uvicorn api.main:app --reload --port 8000

dev-frontend:
	@echo "Starting frontend in development mode..."
	cd frontend && npm run dev

# ===================
# Build
# ===================
build:
	@echo "Building frontend..."
	cd frontend && npm run build
	@echo "Build complete!"

# ===================
# Testing
# ===================
test: test-backend
	@echo "All tests passed!"

test-backend:
	@echo "Running backend tests..."
	cd backend && pytest -v

lint:
	@echo "Linting backend..."
	cd backend && ruff check src/ tests/ api/
	@echo "Linting frontend..."
	cd frontend && npm run lint

# ===================
# Database
# ===================
db-migrate:
	@echo "Creating new migration..."
	@read -p "Migration message: " msg; \
	cd backend && alembic revision --autogenerate -m "$$msg"

db-upgrade:
	@echo "Applying migrations..."
	cd backend && alembic upgrade head

# ===================
# Docker
# ===================
docker-up:
	docker-compose up -d
	@echo "Services started! Frontend: http://localhost:3000, Backend: http://localhost:8000"

docker-down:
	docker-compose down

docker-build:
	docker-compose build

docker-logs:
	docker-compose logs -f

# ===================
# Cleanup
# ===================
clean:
	@echo "Cleaning up..."
	rm -rf backend/.pytest_cache backend/.coverage backend/htmlcov
	rm -rf backend/src/*.egg-info backend/dist backend/build
	rm -rf frontend/.next frontend/node_modules/.cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@echo "Cleanup complete!"

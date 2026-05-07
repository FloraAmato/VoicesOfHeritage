.PHONY: dev backend frontend test docker clean

backend:
	cd backend && uvicorn app.main:app --reload --port 8000

frontend:
	cd frontend && npm run dev

test:
	cd backend && python -m pytest -q

docker:
	docker compose up --build

dev:
	@echo "Avvia backend e frontend in due terminali separati:"
	@echo "  make backend"
	@echo "  make frontend"

clean:
	rm -rf backend/data/history_*.csv backend/models/*.pkl
	rm -rf frontend/node_modules frontend/dist
	find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

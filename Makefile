# ──────────────────────────────────────────────────────────────────
#  MusiCLI — Project Makefile
#  A feature-rich terminal music player.
#  https://github.com/tott1o/musiCLI
# ──────────────────────────────────────────────────────────────────

# Configuration
PYTHON       ?= python
PIP          ?= pip
PACKAGE      := musicli
SRC_DIR      := src
TEST_DIR     := tests
DOCS_DIR     := docs

# Colors (ANSI)
BOLD   := \033[1m
CYAN   := \033[36m
GREEN  := \033[32m
YELLOW := \033[33m
RED    := \033[31m
RESET  := \033[0m

# ──────────────────────────────────────────────────────────────────
#  Default target
# ──────────────────────────────────────────────────────────────────

.DEFAULT_GOAL := help

.PHONY: help
help: ## Show this help message
	@printf "\n$(BOLD)$(CYAN)🎵 MusiCLI — Available Commands$(RESET)\n\n"
	@printf "$(BOLD)Usage:$(RESET)  make $(CYAN)<target>$(RESET)\n\n"
	@awk 'BEGIN {FS = ":.*##"} \
		/^[a-zA-Z_-]+:.*##/ { \
			printf "  $(CYAN)%-18s$(RESET) %s\n", $$1, $$2 \
		}' $(MAKEFILE_LIST)
	@printf "\n"

# ──────────────────────────────────────────────────────────────────
#  Project Setup (Working on MusiCLI)
# ──────────────────────────────────────────────────────────────────

.PHONY: setup
setup: ## Standard development setup (editable install)
	@printf "$(GREEN)▸ Setting up MusiCLI for development…$(RESET)\n"
	$(PIP) install -e .

.PHONY: dev
dev: ## Setup with full development tools (ruff, pytest, etc.)
	@printf "$(GREEN)▸ Setting up MusiCLI with dev tools…$(RESET)\n"
	$(PIP) install -e ".[dev]"

.PHONY: deps
deps: ## Install only runtime dependencies
	@printf "$(GREEN)▸ Installing dependencies…$(RESET)\n"
	$(PIP) install -r requirements.txt

# ──────────────────────────────────────────────────────────────────
#  Running
# ──────────────────────────────────────────────────────────────────

.PHONY: run
run: ## Run MusiCLI
	$(PYTHON) -m $(PACKAGE)

# ──────────────────────────────────────────────────────────────────
#  Code Quality
# ──────────────────────────────────────────────────────────────────

.PHONY: lint
lint: ## Run linter (Ruff)
	@printf "$(YELLOW)▸ Linting…$(RESET)\n"
	ruff check $(SRC_DIR)/ $(TEST_DIR)/

.PHONY: format
format: ## Auto-format code (Ruff)
	@printf "$(YELLOW)▸ Formatting…$(RESET)\n"
	ruff format $(SRC_DIR)/ $(TEST_DIR)/

.PHONY: format-check
format-check: ## Check formatting without modifying files
	@printf "$(YELLOW)▸ Checking format…$(RESET)\n"
	ruff format --check $(SRC_DIR)/ $(TEST_DIR)/

.PHONY: typecheck
typecheck: ## Run type checker (mypy) — install mypy separately
	@printf "$(YELLOW)▸ Type-checking…$(RESET)\n"
	mypy $(SRC_DIR)/$(PACKAGE)

.PHONY: check
check: lint format-check ## Run all checks (lint + format-check)
	@printf "$(GREEN)▸ All checks passed.$(RESET)\n"

# ──────────────────────────────────────────────────────────────────
#  Testing
# ──────────────────────────────────────────────────────────────────

.PHONY: test
test: ## Run tests with pytest
	@printf "$(YELLOW)▸ Running tests…$(RESET)\n"
	pytest $(TEST_DIR)/ -v

.PHONY: test-cov
test-cov: ## Run tests with coverage report
	@printf "$(YELLOW)▸ Running tests with coverage…$(RESET)\n"
	pytest $(TEST_DIR)/ -v --cov=$(SRC_DIR)/$(PACKAGE) --cov-report=term-missing --cov-report=html

.PHONY: test-fast
test-fast: ## Run tests without verbose output
	pytest $(TEST_DIR)/ -q

# ──────────────────────────────────────────────────────────────────
#  Building & Publishing
# ──────────────────────────────────────────────────────────────────

.PHONY: build
build: clean-build ## Build source and wheel distributions
	@printf "$(GREEN)▸ Building package…$(RESET)\n"
	$(PYTHON) -m build

.PHONY: publish-test
publish-test: build ## Upload to TestPyPI
	@printf "$(YELLOW)▸ Uploading to TestPyPI…$(RESET)\n"
	twine upload --repository testpypi dist/*

.PHONY: publish
publish: build ## Upload to PyPI (use with caution!)
	@printf "$(RED)▸ Uploading to PyPI…$(RESET)\n"
	twine upload dist/*

# ──────────────────────────────────────────────────────────────────
#  Cleanup
# ──────────────────────────────────────────────────────────────────

.PHONY: clean
clean: clean-build clean-pyc clean-test ## Remove ALL build, cache, and test artifacts

.PHONY: clean-build
clean-build: ## Remove build artifacts
	rm -rf build/ dist/ *.egg-info src/*.egg-info
	find . -name '*.egg' -exec rm -f {} +

.PHONY: clean-pyc
clean-pyc: ## Remove Python bytecode and caches
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name '*.py[cod]' -exec rm -f {} +
	find . -type f -name '*~' -exec rm -f {} +

.PHONY: clean-test
clean-test: ## Remove test and coverage artifacts
	rm -rf .pytest_cache .ruff_cache .mypy_cache htmlcov .coverage coverage.xml

# ──────────────────────────────────────────────────────────────────
#  Project Info
# ──────────────────────────────────────────────────────────────────

.PHONY: version
version: ## Display the current package version
	@$(PYTHON) -c "from importlib.metadata import version; print(version('$(PACKAGE)'))" 2>/dev/null \
		|| $(PYTHON) -c "import $(PACKAGE); print($(PACKAGE).__version__)"

.PHONY: info
info: ## Show project metadata
	@printf "$(BOLD)$(CYAN)🎵 MusiCLI Project Info$(RESET)\n"
	@printf "  $(BOLD)Package:$(RESET)  $(PACKAGE)\n"
	@printf "  $(BOLD)Source:$(RESET)   $(SRC_DIR)/$(PACKAGE)/\n"
	@printf "  $(BOLD)Tests:$(RESET)    $(TEST_DIR)/\n"
	@printf "  $(BOLD)Python:$(RESET)   $$($(PYTHON) --version 2>&1)\n"
	@printf "  $(BOLD)Pip:$(RESET)      $$($(PIP) --version 2>&1 | cut -d' ' -f1-2)\n"
	@printf "\n"

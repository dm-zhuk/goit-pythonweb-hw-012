# Contacts Management REST API

This project is a fully tested and Dockerized RESTful API for managing contacts, featuring:

- JWT-based authentication
- Role-based access control
- PostgreSQL & Redis integration
- Pytest coverage for both unit and integration tests

## 🧪 Testing & Coverage

This project uses **Poetry**, **Pytest**, **Coverage.py**, and **Docker Compose** to run unit and integration tests with combined coverage reporting.

### 🔧 Prerequisites

- [Poetry](https://python-poetry.org/docs/)
- [Docker](https://www.docker.com/)
- [Docker Compose](https://docs.docker.com/compose/)


### 🧼 Clean up previous results

```bash
make clean

### ✅ Run local unit tests (pure mocks)

```bash
make .coverage.unit

### 🐳 Run integration tests (DB + Redis via Docker)

```bash
make .coverage.integration

### 📦 Combine & view coverage reports

```bash
make combine-coverage

Combines coverage data from unit + integration runs and generates an HTML report:

👉 Open htmlcov/index.html in your browser to view it.

### 🚀 Full test pipeline (clean → test → report)

```bash
make test-all

#### Runs everything in order:

Run Clean up

Run unit tests

Run integration tests

Combine coverage reports

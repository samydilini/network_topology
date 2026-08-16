# Network Topology Tracing API

A headless REST API (Django + Django REST Framework) for managing network
infrastructure — **Sites**, **Devices**, **Interfaces**, and the **Connections**
between interfaces — plus a specialised endpoint for tracing the connections
associated with a site, device, or interface.

See [`docs/specification.md`](docs/specification.md) and
[`docs/architecture.md`](docs/architecture.md) for the full requirements and
design, and [`docs/implementation-plan.md`](docs/implementation-plan.md) for the
phased build plan.

## Requirements

- Python 3.12
- Dependencies pinned in [`requirements.txt`](requirements.txt) (Django, DRF,
  drf-spectacular). SQLite is used as the database and needs no setup.

## Setup

```bash
# 1. Create and activate a virtual environment
python3.12 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Apply migrations (creates the local db.sqlite3)
python manage.py migrate

# 4. Run the development server
python manage.py runserver
```

The API is then available under `http://127.0.0.1:8000/api/`. Individual resources are available under paths such as /api/sites/ and /api/sites/{id}/.

## Running the tests

```bash
python manage.py test
```

## API documentation

Interactive and machine-readable OpenAPI documentation is generated directly
from the implementation with `drf-spectacular`:

- Swagger UI: <http://127.0.0.1:8000/api/docs/>
- OpenAPI schema: <http://127.0.0.1:8000/api/schema/>

## Endpoints

| Resource    | Endpoint             | Operations                      |
| ----------- | -------------------- | ------------------------------- |
| Sites       | `/api/sites/`        | list, create, retrieve, update, delete |
| Devices     | `/api/devices/`      | list, create, retrieve, update, delete |
| Interfaces  | `/api/interfaces/`   | list, create, retrieve, update, delete |
| Connections | `/api/connections/`  | list, create, retrieve, update, delete |
| Trace       | `/api/trace/`        | GET (query by `type` and `id`)  |

All CRUD resources expose `GET`, `POST`, `PUT`, and `DELETE`.

## Design summary

The project is a single Django app (`topology`) inside the `config` project,
kept intentionally simple for the scope of the assessment:

- **Models** (`topology/models.py`) hold the domain data and enforce persistent
  integrity — unique constraints (site name, device name/serial number,
  connection id), the composite `(device, name)` uniqueness for interfaces, and
  `on_delete=PROTECT` on every foreign key.
- **Serializers** (`topology/serializers.py`) validate requests at the API
  boundary. Connections use separate input and output representations: writes
  accept flat interface IDs (`start_interface`, `end_interface`) while responses
  expose the derived `start_target` / `end_target` `{site, device, interface}`
  hierarchy.
- **ViewSets** (`topology/views.py`) are thin DRF `ModelViewSet`s registered with
  a router.
- **Tracing logic** lives in a dedicated service (`topology/services/tracer.py`)
  so it can be tested independently of HTTP. Matching and de-duplication are done
  at the database level (`Q(...) | Q(...)` + `distinct()`), and the endpoint
  responses use `select_related` to avoid N+1 queries.

## Example usage

Create a site, a couple of devices, their interfaces, and a connection, then
trace it. Assumes a fresh database (IDs start at 1).

```bash
# Create a site
curl -X POST http://127.0.0.1:8000/api/sites/ \
  -H 'Content-Type: application/json' \
  -d '{"name": "London Data Center", "description": "Primary London facility", "status": "Active"}'

# Create two devices in that site
curl -X POST http://127.0.0.1:8000/api/devices/ \
  -H 'Content-Type: application/json' \
  -d '{"name": "London-Router-01", "site": 1, "serial_number": "SN123456789"}'

curl -X POST http://127.0.0.1:8000/api/devices/ \
  -H 'Content-Type: application/json' \
  -d '{"name": "Core-Switch-02", "site": 1, "serial_number": "SN987654321"}'

# Create an interface on each device
curl -X POST http://127.0.0.1:8000/api/interfaces/ \
  -H 'Content-Type: application/json' \
  -d '{"name": "GigabitEthernet0/1", "device": 1, "speed": 1000, "status": "Up"}'

curl -X POST http://127.0.0.1:8000/api/interfaces/ \
  -H 'Content-Type: application/json' \
  -d '{"name": "GigabitEthernet0/24", "device": 2, "speed": 1000, "status": "Up"}'

# Create a connection between the two interfaces
curl -X POST http://127.0.0.1:8000/api/connections/ \
  -H 'Content-Type: application/json' \
  -d '{"connection_id": "CONN1002", "name": "Core Switch Uplink", "status": "Connected", "start_interface": 1, "end_interface": 2}'

# Trace connections by interface / device / site
curl 'http://127.0.0.1:8000/api/trace/?type=interface&id=1'
curl 'http://127.0.0.1:8000/api/trace/?type=device&id=2'
curl 'http://127.0.0.1:8000/api/trace/?type=site&id=1'
```

A connection response (and each connection inside a trace response) exposes the
full endpoint hierarchy:

```json
{
  "id": 1,
  "connection_id": "CONN1002",
  "name": "Core Switch Uplink",
  "status": "Connected",
  "start_target": {
    "site": {"id": 1, "name": "London Data Center"},
    "device": {"id": 1, "name": "London-Router-01"},
    "interface": {"id": 1, "name": "GigabitEthernet0/1"}
  },
  "end_target": {
    "site": {"id": 1, "name": "London Data Center"},
    "device": {"id": 2, "name": "Core-Switch-02"},
    "interface": {"id": 2, "name": "GigabitEthernet0/24"}
  }
}
```

## Assumptions

- **Distinct endpoints.** A connection is point-to-point and must join two
  different interfaces; a connection referencing the same interface as both its
  start and end endpoint is rejected.
- **Protected deletion.** Foreign keys use protected deletion to prevent
  accidental cascading removal of network topology. A resource with dependants
  cannot be deleted until its dependants are removed; a `DELETE` against such a
  resource returns `409 Conflict`.
- **`connection_id` format.** The specification requires a "unique alphanumeric
  identifier", so `connection_id` is validated as alphanumeric only (e.g.
  `CONN1002`), without the hyphen shown in some earlier examples.
- **Interface speed.** `speed` is a positive integer in Mbps.
- **Trace error handling.** A malformed (non-integer) `id` is a bad request
  (`400`); a well-formed integer `id` with no matching row is `404`. A missing
  `type`/`id`, or an invalid `type` value, is `400`.
- **Trace ordering.** Traced connections are returned in ascending `id` order.

## Scope notes

Authentication/authorisation, a frontend, and Docker are out of scope
(see `docs/architecture.md`). The generated `db.sqlite3` is excluded from version
control.

# Network Topology Tracing API

## 1. Overview

The Network Topology Tracing API is a headless REST API implemented using Django and Django REST Framework (DRF).

The application manages four core network resources:

* Site
* Device
* Interface
* Connection

The system exposes standard RESTful CRUD operations for these resources and a specialised tracing endpoint for identifying Connections associated with a Site, Device, or Interface.

The architecture intentionally uses a simple Django/DRF structure appropriate for the scope of the assessment. No frontend application is required.

---

## 2. Architectural Goals

The architecture is designed around the following goals:

* Keep the implementation simple and easy to understand.
* Use Django's ORM for relational data modelling and integrity.
* Use Django REST Framework for API endpoints and request/response handling.
* Keep API validation close to the API boundary.
* Isolate the connection tracing logic so that it can be tested independently.
* Avoid unnecessary abstraction and infrastructure.
* Provide automated API tests.
* Provide automatically generated OpenAPI documentation.

---

## 3. High-Level Architecture

```text
                    HTTP Client
                        |
                        v
              +-------------------+
              |   Django / DRF    |
              |    REST API       |
              +-------------------+
                        |
            +-----------+-----------+
            |                       |
            v                       v
     CRUD ViewSets             Trace Endpoint
            |                       |
            v                       v
      Serializers             Topology Tracer
            |                       |
            +-----------+-----------+
                        |
                        v
                 Django ORM
                        |
                        v
                 SQLite Database
```

The application is a single Django application. There are no separate frontend, API gateway, worker, or microservice components.

---

## 4. Technology Stack

### Application

* Python 3.12
* Django
* Django REST Framework

### Database

SQLite is used as the default development and assessment database.

The assessment does not specify a particular database engine or require a production deployment. SQLite provides a relational database with minimal setup and is sufficient for the scope of this assessment.

The database file is generated locally and is not committed to source control.

### API Documentation

`drf-spectacular` is used to generate an OpenAPI schema and provide Swagger UI.

### Testing

Django's testing framework and Django REST Framework's API testing utilities are used for automated tests.

---

## 5. Project Structure

The application uses a conventional Django structure.

```text
project-root/
│
├── config/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
│
├── topology/
│   ├── migrations/
│   ├── tests/
│   │   ├── test_models.py
│   │   ├── test_serializers.py
│   │   ├── test_api.py
│   │   └── test_tracing.py
│   ├── models.py
│   ├── serializers.py
│   ├── views.py
│   ├── urls.py
│   └── services/
│       └── tracer.py
│
├── docs/
│   ├── specification.md
│   └── architecture.md
│
├── manage.py
├── requirements.txt
├── README.md
└── .gitignore
```

The exact test file organisation may be adjusted during implementation if a simpler structure provides better maintainability.

---

## 6. Domain Model Architecture

The database model follows the network hierarchy:

```text
Site
 |
 +-- Device
      |
      +-- Interface
```

A Connection references two Interfaces:

```text
                 +----------------+
                 |   Connection   |
                 +----------------+
                    /          \
                   /            \
                  v              v
          start Interface    end Interface
                  |              |
                  v              v
               Device          Device
                  |              |
                  v              v
                Site            Site
```

This means the Site and Device associated with a Connection endpoint can be derived from the endpoint Interface.

The Connection model therefore does not require separate Site or Device foreign keys.

---

## 7. Django Models

### Site

The `Site` model contains:

* `name`
* `description`
* `status`

The `name` field has a database-level uniqueness constraint.

The `status` field uses a constrained set of values.

---

### Device

The `Device` model contains:

* `name`
* `site`
* `serial_number`

`site` is a foreign key to `Site`.

Both `name` and `serial_number` are unique.

---

### Interface

The `Interface` model contains:

* `name`
* `device`
* `speed`
* `status`

`device` is a foreign key to `Device`.

A database-level unique constraint is applied to:

```text
(device, name)
```

This allows interfaces with the same name on different devices while preventing duplicate interface names on the same device.

---

### Connection

The `Connection` model contains:

* `connection_id`
* `name`
* `status`
* `start_interface`
* `end_interface`

Both endpoint fields reference the `Interface` model.

The API exposes these endpoints as the hierarchical `start` and `end` structures required by the specification.

The `connection_id` field is unique.

---

## 8. Serializer Architecture

Django REST Framework serializers are responsible for:

* validating incoming API data
* converting request JSON into Python/Django objects
* converting Django model instances into JSON responses
* enforcing API-level validation rules

Separate representations may be used for connection input and output because the API has different requirements for each direction.

### Connection input

Create/update requests use:

```json
{
  "start": {
    "site": 1,
    "device": 2,
    "interface": 5
  },
  "end": {
    "site": 1,
    "device": 3,
    "interface": 8
  }
}
```

The serializer validates:

1. Site exists.
2. Device exists.
3. Device belongs to the supplied Site.
4. Interface exists.
5. Interface belongs to the supplied Device.
6. Start and end interfaces are different.

### Connection output

Responses expose endpoint information as:

```json
{
  "start_target": {
    "site": {
      "id": 1,
      "name": "London Data Center"
    },
    "device": {
      "id": 2,
      "name": "Core-Switch-02"
    },
    "interface": {
      "id": 5,
      "name": "GigabitEthernet0/24"
    }
  }
}
```

The same representation is used for `end_target`.

This avoids requiring API consumers to make additional requests to determine the hierarchy associated with a Connection endpoint.

---

## 9. ViewSet Architecture

Standard CRUD resources are implemented using Django REST Framework ViewSets.

Conceptually:

```text
SiteViewSet
DeviceViewSet
InterfaceViewSet
ConnectionViewSet
```

The ViewSets are registered with DRF routers.

This provides the standard REST operations:

```text
GET     /resource/
POST    /resource/
GET     /resource/{id}/
PUT     /resource/{id}/
DELETE  /resource/{id}/
```

The ViewSets should remain thin and should delegate complex validation to serializers or model constraints.

---

## 10. URL Routing

DRF routers are used for the four CRUD resources.

Conceptually:

```text
/api/sites/
/api/devices/
/api/interfaces/
/api/connections/
```

The tracing endpoint is a specialised endpoint and is exposed separately:

```text
/api/trace/?type={type}&id={id}
```

OpenAPI documentation endpoints are exposed separately:

```text
/api/schema/
/api/docs/
```

---

## 11. Connection Tracing Architecture

The connection tracing operation contains the primary business logic of the API.

The tracing logic is isolated from the HTTP layer in a dedicated service component:

```text
Trace endpoint
      |
      v
TopologyTracer
      |
      v
Django ORM
      |
      v
Connection queryset
```

This keeps the endpoint responsible primarily for:

* reading query parameters
* validating the request
* resolving the traced object
* invoking the tracing operation
* serializing the result

The `TopologyTracer` is responsible for determining which Connections match the requested object.

---

## 12. Tracing Algorithm

### Interface

For an Interface:

```text
Connection.start_interface = interface
OR
Connection.end_interface = interface
```

The resulting Connections are returned without duplicates.

---

### Device

For a Device, the tracer identifies all Interfaces belonging to that Device.

It then finds Connections where either endpoint belongs to that set of Interfaces.

Conceptually:

```text
Device
  |
  +-- Interface A
  +-- Interface B
  +-- Interface C
           |
           v
      Connections
```

---

### Site

For a Site, the tracer identifies:

1. Devices belonging to the Site.
2. Interfaces belonging to those Devices.
3. Connections associated with those Interfaces.

Conceptually:

```text
Site
 |
 +-- Device A
 |     +-- Interface 1
 |     +-- Interface 2
 |
 +-- Device B
       +-- Interface 3
       +-- Interface 4
              |
              v
         Connections
```

A Connection is returned if either endpoint Interface belongs to an Interface within the Site.

---

## 13. Duplicate Connection Handling

A Connection must appear at most once in a trace response.

This is particularly important when tracing a Site or Device because both endpoints of a Connection may belong to the traced object.

For example:

```text
Site A
 |
 +-- Device 1
      |
      +-- Interface 1 -------- Interface 2
                                  |
                              Device 2
```

If both Interfaces belong to the same traced Site, the Connection must still appear only once.

The implementation should use database-level filtering and/or queryset deduplication rather than performing duplicate removal purely in application code.

---

## 14. Query Efficiency

The implementation should use Django ORM capabilities appropriately to avoid unnecessary database queries.

Where related objects are required for the response, `select_related()` and `prefetch_related()` should be considered where appropriate.

The implementation should avoid obvious N+1 query patterns when serializing Connections and their endpoint hierarchy.

The goal is not to introduce premature optimisation, but to ensure the tracing endpoint and Connection response do not unnecessarily query Site, Device, and Interface records individually for every Connection.

---

## 15. Validation Strategy

Validation is performed at multiple appropriate layers.

### Database-level constraints

Used for rules such as:

* unique Site name
* unique Device name
* unique Device serial number
* unique `(device, interface name)`
* unique Connection ID

### Serializer-level validation

Used for request-specific rules such as:

* validating the complete endpoint hierarchy
* checking that an Interface belongs to the supplied Device
* checking that a Device belongs to the supplied Site
* ensuring start and end Interfaces are different
* validating request fields and status values

This provides both strong database integrity and clear API-level validation errors.

---

## 16. Error Handling

The API will use standard DRF error handling and HTTP status codes.

The implementation should return:

```text
400 Bad Request
```

for invalid input or validation failures.

It should return:

```text
404 Not Found
```

when a requested resource does not exist.

The API should use consistent JSON error responses following DRF conventions.

Custom exception handling should only be introduced where it provides clear value beyond DRF's standard behaviour.

---

## 17. API Documentation Architecture

`drf-spectacular` generates the OpenAPI schema by inspecting the DRF API implementation.

The architecture is:

```text
Django Models
      |
DRF Serializers
      |
DRF ViewSets / Views
      |
      v
drf-spectacular
      |
      +----> OpenAPI Schema
      |
      +----> Swagger UI
```

The application exposes:

```text
/api/schema/
/api/docs/
```

The standard CRUD endpoints should be discoverable automatically.

Additional schema metadata should be provided for the custom tracing endpoint where necessary, particularly for:

* `type`
* `id`
* trace response structure
* possible error responses

The OpenAPI documentation should be generated from the implementation rather than maintaining a separate manually written Swagger file.

---

## 18. Database and Infrastructure

The assessment does not require a specific database or containerisation technology.

The initial implementation uses SQLite because:

* it provides a relational database
* it requires no external service
* it is sufficient for the assessment's data model
* it makes local setup straightforward
* it reduces unnecessary infrastructure

Docker is not required and will not be introduced unless a specific implementation need emerges.

The generated SQLite database is excluded from version control.

---

## 19. Authentication and Authorisation

Authentication and authorisation are outside the scope of the assessment.

The API is intended to demonstrate the required network topology functionality rather than production identity management.

No authentication mechanism will be introduced unless required by the assessment.

---

## 20. Frontend

No frontend application is required.

The application is explicitly a headless REST API.

API consumers can interact with the application through:

* HTTP clients
* curl
* Postman
* automated tests
* Swagger UI

Django Admin is not required as part of the solution.

---

## 21. Testing Architecture

Tests will be organised around the main responsibilities of the application.

### Model tests

Verify:

* model constraints
* relationships
* status choices
* uniqueness rules

### Serializer tests

Verify:

* valid payloads
* invalid hierarchical endpoint combinations
* duplicate values
* invalid statuses
* identical start/end Interfaces

### API tests

Verify:

* CRUD operations
* HTTP status codes
* request/response structures
* validation errors

### Tracing tests

Verify:

* Interface tracing
* Device tracing
* Site tracing
* connections through both endpoints
* duplicate prevention
* empty results
* invalid parameters
* nonexistent traced objects

The tracing logic should be tested both through the API and, where useful, directly at the service level.

---

## 22. Design Principles

The implementation follows these principles:

### Simplicity

Use Django and DRF conventions rather than introducing unnecessary abstractions.

### Separation of concerns

* Models represent persistent domain data.
* Serializers validate and transform API data.
* ViewSets handle HTTP/API operations.
* The topology tracing service contains tracing business logic.

### Database integrity

Use database constraints wherever a rule represents persistent data integrity.

### Explicit API contracts

Request and response structures are defined by the API specification and represented clearly through DRF serializers.

### Testability

Business logic should be structured so that important behaviour can be tested independently of HTTP handling.

### Minimal infrastructure

Only technologies required to satisfy the assessment are introduced.

---

## 23. Architectural Boundaries

The application intentionally remains a modular monolith.

```text
+--------------------------------------------------+
|                Django Application                |
|                                                  |
|  +------------+    +--------------------------+  |
|  | CRUD API   |    | Connection Trace Service |  |
|  +------------+    +--------------------------+  |
|         |                     |                  |
|         +----------+----------+                  |
|                    |                             |
|               Django ORM                        |
|                    |                             |
|                SQLite                           |
+--------------------------------------------------+
```

No separate services are required.

This provides sufficient separation for the current scope while avoiding unnecessary complexity.

---

## 24. Implementation Sequence

Implementation should proceed incrementally:

1. Configure Django project.
2. Configure DRF.
3. Implement Site model and CRUD.
4. Implement Device model and CRUD.
5. Implement Interface model and CRUD.
6. Implement Connection model.
7. Implement Connection endpoint validation.
8. Implement Connection CRUD.
9. Implement tracing logic.
10. Add tracing API endpoint.
11. Add automated tests.
12. Add OpenAPI/Swagger documentation.
13. Review query efficiency.
14. Update README with setup, design, assumptions, API usage, and documentation links.

The implementation should remain aligned with `docs/specification.md` and this architecture document throughout development.

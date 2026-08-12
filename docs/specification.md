# Network Topology Tracing API

## 1. Purpose

The Network Topology Tracing API is a headless REST API implemented using Django REST Framework (DRF).

The API manages network infrastructure components and the connections between their interfaces. It provides standard CRUD operations for network resources and a specialised tracing endpoint that identifies connections associated with a particular site, device, or interface.

The API does not require a web-based user interface.

---

## 2. Scope

The API provides the following resources:

* Site
* Device
* Interface
* Connection

The API must provide:

1. CRUD operations for all four resources.
2. Validation of relationships and data integrity.
3. A connection tracing endpoint supporting sites, devices, and interfaces.
4. Structured JSON responses.
5. Automated tests covering the required behaviour.
6. OpenAPI/Swagger documentation generated from the API implementation.

---

## 3. Domain Model

### 3.1 Site

A Site represents a physical or logical location containing network devices.

| Field         | Type    | Required | Constraints                              |
| ------------- | ------- | -------: | ---------------------------------------- |
| `id`          | Integer |       No | Auto-generated primary key               |
| `name`        | String  |      Yes | Must be unique                           |
| `description` | Text    |       No | Optional                                 |
| `status`      | String  |      Yes | `Active`, `Planned`, or `Decommissioned` |

A Site can contain multiple Devices.

---

### 3.2 Device

A Device represents a network device installed at a Site.

| Field           | Type        | Required | Constraints                     |
| --------------- | ----------- | -------: | ------------------------------- |
| `id`            | Integer     |       No | Auto-generated primary key      |
| `name`          | String      |      Yes | Must be unique                  |
| `site`          | Foreign key |      Yes | Must reference an existing Site |
| `serial_number` | String      |      Yes | Must be unique                  |

A Device belongs to exactly one Site.

A Site can contain multiple Devices.

---

### 3.3 Interface

An Interface represents a network interface belonging to a Device.

| Field    | Type        | Required | Constraints                                        |
| -------- | ----------- | -------: | -------------------------------------------------- |
| `id`     | Integer     |       No | Auto-generated primary key                         |
| `name`   | String      |      Yes | Unique per Device                                  |
| `device` | Foreign key |      Yes | Must reference an existing Device                  |
| `speed`  | Integer     |      Yes | Throughput in Mbps; must be a valid positive value |
| `status` | String      |      Yes | `Up`, `Down`, or `Maintenance`                     |

The combination of `device` and `name` must be unique.

A Device can contain multiple Interfaces.

An Interface belongs to exactly one Device.

---

### 3.4 Connection

A Connection represents a point-to-point connection between two network Interfaces.

| Field           | Type               | Required | Constraints                                    |
| --------------- | ------------------ | -------: | ---------------------------------------------- |
| `id`            | Integer            |       No | Auto-generated primary key                     |
| `connection_id` | String             |      Yes | Unique alphanumeric identifier                 |
| `name`          | String             |       No | Optional description                           |
| `status`        | String             |      Yes | `Connected` or `Disconnected`                  |
| `start`         | Interface endpoint |      Yes | Complete `{site, device, interface}` hierarchy |
| `end`           | Interface endpoint |      Yes | Complete `{site, device, interface}` hierarchy |

A Connection has exactly two endpoints:

* `start`
* `end`

Each endpoint must identify an Interface through the complete hierarchy:

```json
{
  "site": 1,
  "device": 2,
  "interface": 5
}
```

The hierarchy must be valid:

```text
Site
 └── Device
      └── Interface
```

Therefore:

* The supplied Device must belong to the supplied Site.
* The supplied Interface must belong to the supplied Device.
* The supplied Interface must exist.
* The start and end Interfaces must be distinct.

A Connection must not reference the same Interface as both its start and end endpoint.

---

## 4. Relationships

The domain relationships are:

```text
Site 1 ──────── * Device
                    |
                    |
                    * Interface

Connection
    |
    ├── start ─── Interface
    |
    └── end ───── Interface
```

Connections are represented through their Interface endpoints.

No additional Site or Device relationship is required on Connection because Site and Device can be determined through the endpoint Interfaces.

---

## 5. Data Validation Rules

### 5.1 Site

* `name` is required.
* `name` must be unique.
* `status` must be one of:

  * `Active`
  * `Planned`
  * `Decommissioned`

### 5.2 Device

* `name` is required and unique.
* `serial_number` is required and unique.
* `site` must reference an existing Site.

### 5.3 Interface

* `name` is required.
* `device` must reference an existing Device.
* `speed` must be a positive integer.
* `status` must be one of:

  * `Up`
  * `Down`
  * `Maintenance`
* The combination of `device` and `name` must be unique.

### 5.4 Connection

* `connection_id` is required.
* `connection_id` must be unique.
* `connection_id` must contain only alphanumeric characters, with the permitted identifier format documented by the API.
* `status` must be one of:

  * `Connected`
  * `Disconnected`
* Both `start` and `end` endpoints are required.
* Each endpoint must contain `site`, `device`, and `interface`.
* The Site, Device, and Interface hierarchy must be valid.
* The start and end Interfaces must be different.

Invalid input must result in an appropriate HTTP `400 Bad Request` response.

---

## 6. REST API

All resources are exposed through RESTful endpoints.

The API uses JSON request and response bodies.

The resource endpoints are:

```text
/api/sites/
/api/devices/
/api/interfaces/
/api/connections/
```

The exact API prefix may be configured consistently across the application.

---

## 7. Site CRUD

### List Sites

```http
GET /api/sites/
```

Returns a collection of Sites.

### Create Site

```http
POST /api/sites/
```

Example request:

```json
{
  "name": "London Data Center",
  "description": "Primary London facility",
  "status": "Active"
}
```

### Retrieve Site

```http
GET /api/sites/{id}/
```

### Update Site

```http
PUT /api/sites/{id}/
```

### Delete Site

```http
DELETE /api/sites/{id}/
```

The API should rely on relational integrity and appropriate application validation when a Site has dependent Devices.

---

## 8. Device CRUD

### List Devices

```http
GET /api/devices/
```

### Create Device

```http
POST /api/devices/
```

Example:

```json
{
  "name": "Core-Switch-02",
  "site": 1,
  "serial_number": "SN123456789"
}
```

### Retrieve Device

```http
GET /api/devices/{id}/
```

### Update Device

```http
PUT /api/devices/{id}/
```

### Delete Device

```http
DELETE /api/devices/{id}/
```

---

## 9. Interface CRUD

### List Interfaces

```http
GET /api/interfaces/
```

### Create Interface

```http
POST /api/interfaces/
```

Example:

```json
{
  "name": "GigabitEthernet0/24",
  "device": 2,
  "speed": 1000,
  "status": "Up"
}
```

### Retrieve Interface

```http
GET /api/interfaces/{id}/
```

### Update Interface

```http
PUT /api/interfaces/{id}/
```

### Delete Interface

```http
DELETE /api/interfaces/{id}/
```

---

## 10. Connection CRUD

### List Connections

```http
GET /api/connections/
```

### Create Connection

```http
POST /api/connections/
```

The request must accept the complete hierarchical structure for both endpoints.

Example:

```json
{
  "connection_id": "CONN1002",
  "name": "Core Switch Uplink",
  "status": "Connected",
  "start": {
    "site": 1,
    "device": 1,
    "interface": 4
  },
  "end": {
    "site": 1,
    "device": 2,
    "interface": 9
  }
}
```

The API must validate that:

```text
site 1 → device 1 → interface 4
site 1 → device 2 → interface 9
```

are valid hierarchical relationships.

### Retrieve Connection

```http
GET /api/connections/{id}/
```

### Update Connection

```http
PUT /api/connections/{id}/
```

The same endpoint structure and validation rules used during creation apply during updates.

### Delete Connection

```http
DELETE /api/connections/{id}/
```

---

## 11. Connection Response Representation

Connection responses should expose both endpoints using the complete hierarchical representation.

Example:

```json
{
  "id": 12,
  "connection_id": "CONN1002",
  "name": "Core Switch Uplink",
  "status": "Connected",
  "start_target": {
    "site": {
      "id": 1,
      "name": "London Data Center"
    },
    "device": {
      "id": 1,
      "name": "London-Router-01"
    },
    "interface": {
      "id": 4,
      "name": "GigabitEthernet0/1"
    }
  },
  "end_target": {
    "site": {
      "id": 1,
      "name": "London Data Center"
    },
    "device": {
      "id": 2,
      "name": "Core-Switch-02"
    },
    "interface": {
      "id": 9,
      "name": "GigabitEthernet0/24"
    }
  }
}
```

The response representation may differ from the create/update request representation. In particular, create/update requests identify endpoints using IDs, while responses provide useful identifying information including names.

---

## 12. Connection Tracing Endpoint

The API must provide a specialised endpoint for tracing connections associated with a network infrastructure element.

### Endpoint

```http
GET /api/trace/?type={type}&id={id}
```

### Query Parameters

#### `type`

Required.

Allowed values:

```text
site
device
interface
```

#### `id`

Required.

Must be the integer primary key of the object being traced.

Examples:

```http
GET /api/trace/?type=site&id=1
```

```http
GET /api/trace/?type=device&id=2
```

```http
GET /api/trace/?type=interface&id=9
```

---

## 13. Trace Behaviour

### 13.1 Interface Trace

When:

```text
type=interface
```

the endpoint must return every Connection where the specified Interface is either:

* the start endpoint, or
* the end endpoint.

A connection must appear only once in the response.

---

### 13.2 Device Trace

When:

```text
type=device
```

the endpoint must return every Connection where either endpoint Interface belongs to the specified Device.

This includes connections involving any Interface belonging to that Device.

A connection must appear only once in the response.

---

### 13.3 Site Trace

When:

```text
type=site
```

the endpoint must return every Connection where either endpoint Interface belongs to a Device belonging to the specified Site.

This includes connections involving any Interface belonging to any Device within that Site.

A connection must appear only once in the response.

---

## 14. Trace Response

A successful trace request returns:

* the object being traced
* the object's type
* the object's ID
* the object's name
* the number of matching connections
* the matching connections

Example:

```json
{
  "traced_object": {
    "type": "device",
    "id": 2,
    "name": "Core-Switch-02"
  },
  "connections_count": 2,
  "connections": [
    {
      "id": 12,
      "connection_id": "CONN1002",
      "name": "Core Switch Uplink",
      "status": "Connected",
      "start_target": {
        "site": {
          "id": 1,
          "name": "London Data Center"
        },
        "device": {
          "id": 1,
          "name": "London-Router-01"
        },
        "interface": {
          "id": 4,
          "name": "GigabitEthernet0/1"
        }
      },
      "end_target": {
        "site": {
          "id": 1,
          "name": "London Data Center"
        },
        "device": {
          "id": 2,
          "name": "Core-Switch-02"
        },
        "interface": {
          "id": 9,
          "name": "GigabitEthernet0/24"
        }
      }
    }
  ]
}
```

`connections_count` must equal the number of objects contained in `connections`.

---

## 15. Trace Error Handling

The endpoint must return appropriate errors for invalid requests.

Examples:

### Missing `type`

```http
GET /api/trace/?id=1
```

Response:

```text
400 Bad Request
```

### Missing `id`

```http
GET /api/trace/?type=device
```

Response:

```text
400 Bad Request
```

### Invalid type

```http
GET /api/trace/?type=router&id=1
```

Response:

```text
400 Bad Request
```

### Invalid/nonexistent object ID

```http
GET /api/trace/?type=device&id=99999
```

Response:

```text
404 Not Found
```

The exact JSON error representation should follow DRF conventions consistently.

---

## 16. HTTP Status Codes

The API should use conventional HTTP status codes.

| Situation                         |            Status |
| --------------------------------- | ----------------: |
| Successful GET                    |          `200 OK` |
| Successful POST                   |     `201 Created` |
| Successful PUT                    |          `200 OK` |
| Successful DELETE                 |  `204 No Content` |
| Invalid request/validation error  | `400 Bad Request` |
| Requested resource does not exist |   `404 Not Found` |
| Unique constraint violation       | `400 Bad Request` |

---

## 17. API Routing

The CRUD resources should be exposed using Django REST Framework routers.

The API should provide standard resource routes for:

```text
sites
devices
interfaces
connections
```

The trace operation is a specialised API operation and may be implemented separately from the standard CRUD ViewSets.

---

## 18. API Documentation

The API should expose automatically generated OpenAPI documentation.

The implementation should use `drf-spectacular` to generate the OpenAPI schema from the DRF API.

The application should expose:

```text
/api/schema/
```

for the OpenAPI schema and:

```text
/api/docs/
```

for an interactive Swagger UI.

The generated documentation should describe:

* CRUD endpoints
* request schemas
* response schemas
* query parameters
* validation/error responses
* connection tracing endpoint

The OpenAPI documentation is an API documentation feature and does not replace the project README.

---

## 19. Testing Requirements

Automated tests must cover the core functional requirements.

Tests should include:

### Site

* create Site
* retrieve Site
* update Site
* delete Site
* duplicate Site name rejected
* invalid Site status rejected

### Device

* create Device
* retrieve Device
* update Device
* delete Device
* duplicate Device name rejected
* duplicate serial number rejected
* invalid Site rejected

### Interface

* create Interface
* retrieve Interface
* update Interface
* delete Interface
* duplicate interface name within the same Device rejected
* same interface name on different Devices allowed
* invalid Device rejected
* invalid speed rejected
* invalid status rejected

### Connection

* create valid Connection
* retrieve Connection
* update Connection
* delete Connection
* duplicate `connection_id` rejected
* invalid start hierarchy rejected
* invalid end hierarchy rejected
* missing endpoint rejected
* same Interface used as both endpoints rejected
* invalid status rejected

### Trace

Tests must cover:

* Interface tracing
* Device tracing
* Site tracing
* connections appearing through either endpoint
* multiple Interfaces belonging to a Device
* multiple Devices belonging to a Site
* no duplicate Connections in trace results
* invalid trace type
* missing parameters
* nonexistent traced object
* empty trace result

---

## 20. Non-Functional Expectations

The implementation should prioritise:

* clear and maintainable Django/DRF code
* appropriate relational constraints
* validation at the API boundary
* sensible database queries
* consistent API responses
* automated testing
* straightforward local setup
* minimal unnecessary infrastructure

The implementation should avoid unnecessary architectural complexity for the scope of this assessment.

---

## 21. Acceptance Criteria

The implementation is considered complete when:

1. All four resources are represented in the relational data model.
2. Required relationships and uniqueness constraints are enforced.
3. CRUD endpoints are available for Site, Device, Interface, and Connection.
4. Connection creation and update accept complete `{site, device, interface}` endpoint structures.
5. Hierarchical endpoint relationships are validated.
6. A Connection cannot use the same Interface for both endpoints.
7. The trace endpoint accepts `site`, `device`, and `interface` as tracing types.
8. Interface tracing returns all Connections touching that Interface.
9. Device tracing returns all Connections touching Interfaces belonging to that Device.
10. Site tracing returns all Connections touching Interfaces belonging to Devices in that Site.
11. Each Connection appears at most once in a trace result.
12. Trace responses include the traced object and matching Connections.
13. Connection responses include complete `start_target` and `end_target` representations.
14. Appropriate HTTP status codes are returned.
15. Automated tests cover the required behaviour and important validation cases.
16. OpenAPI/Swagger documentation is available.
17. The project can be set up and run using the instructions in the README.
18. The implementation remains appropriately simple for the scope of the assessment.

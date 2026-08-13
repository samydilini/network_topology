# Network Topology Tracing API — Implementation Plan

This plan describes an **incremental** path to implementing the assessment defined in
[`specification.md`](./specification.md) and [`architecture.md`](./architecture.md).

The two source documents are authoritative. Key design decisions that were previously open are
now settled (Section 1) and captured as assumptions in the project [`README.md`](../README.md);
the phases below build on those decisions directly.

Each phase is designed to leave the application in a **working, runnable, and testable**
state: after every phase `python manage.py migrate`, `python manage.py runserver`, and
`python manage.py test` all succeed, and the features added in that phase are exercised by
tests.

---

## 0. Current Baseline

Established from the existing repository state (do **not** re-do this work):

* Django 6.1 and `djangorestframework==3.18.0` are installed in `.venv` and pinned in
  `requirements.txt`.
* `config/` project exists (`settings.py`, `urls.py`, `wsgi.py`, `asgi.py`).
* `manage.py` exists.
* `docs/specification.md`, `docs/architecture.md`, and `README.md` exist.

Gaps versus the target architecture (addressed in Phase 1):

* `rest_framework` is **not** in `INSTALLED_APPS`; no `REST_FRAMEWORK` config block.
* `drf-spectacular` is **not** installed nor in `requirements.txt`.
* No `topology` app exists.
* `config/urls.py` only routes `admin/`.
* `db.sqlite3` is present in the working tree even though the architecture requires the DB
  file to be excluded from version control.

---

## 1. Resolved Design Decisions

These are settled and are treated as fixed inputs to the phases below. The assumptions are
also recorded in `README.md`.

* **Deletion / referential integrity:** all foreign keys use protected deletion
  (`on_delete=PROTECT`). Deleting a resource that still has dependants returns
  **`409 Conflict`**.
* **`connection_id` format:** a unique alphanumeric identifier (e.g. `CONN1002`); required.
* **Connection endpoints (create/update input):** supplied as flat interface IDs only —
  `start_interface` and `end_interface`. Site and Device are derived from the Interface's
  relationships and are **not** part of the request body.
* **Device name:** globally unique.
* **Interface speed:** must be a positive integer (Mbps).
* **HTTP methods:** expose only `GET`, `POST`, `PUT`, and `DELETE`.
* **Pagination:** not implemented; list and trace responses return full collections.
* **Trace `id` handling:** a missing/invalid `type`, or a missing/malformed (non-integer)
  `id`, returns `400`; a well-formed integer `id` with no matching row returns `404`.
* **Trace ordering:** connections are returned in ascending `id` order.
* **URL prefix:** all API endpoints live under `/api/`.

---

## 2. Phased Implementation

Phase dependencies are linear: each phase depends on all prior phases.

---

### Phase 1 — Project & DRF Foundation

**Objective**
Turn the bare Django project into a runnable DRF application with routing, OpenAPI plumbing,
and an empty `topology` app — no domain models yet — so the stack is proven end to end.

**Implementation tasks**
1. Add `drf-spectacular` to `requirements.txt` (DRF already present); install into the venv.
2. Create the `topology` app (`python manage.py startapp topology`) with the
   `services/` package and `tests/` package per architecture §5.
3. `INSTALLED_APPS`: add `rest_framework`, `drf_spectacular`, `topology`.
4. Add `REST_FRAMEWORK = {'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema'}`
   with **no** pagination class configured, and a `SPECTACULAR_SETTINGS` block
   (title, version, description).
5. `topology/urls.py`: create a DRF `DefaultRouter` (empty for now) and expose
   `schema/` (`SpectacularAPIView`) and `docs/` (`SpectacularSwaggerView`).
6. `config/urls.py`: `path('api/', include('topology.urls'))`; keep `admin/`. All endpoints
   resolve under `/api/`.
7. Ensure `db.sqlite3` is git-ignored and untracked.

**Files/components affected**
`requirements.txt`, `config/settings.py`, `config/urls.py`, new `topology/` app
(`apps.py`, `urls.py`, `services/__init__.py`, `services/tracer.py` stub, `tests/__init__.py`),
`.gitignore`.

**Tests**
* Smoke test (`topology/tests/test_api.py`): `GET /api/schema/` returns `200`;
  `GET /api/docs/` returns `200`.
* `python manage.py check` passes; `migrate` succeeds.

**Acceptance criteria**
* Server starts; `/api/schema/` and `/api/docs/` load.
* Test suite runs green (smoke tests only).
* `db.sqlite3` is not tracked by git.

**Dependencies**
Baseline only.

---

### Phase 2 — Site Resource

**Objective**
Implement the `Site` model, serializer, ViewSet, and CRUD routing — the first fully working
resource — and establish the shared ViewSet conventions (allowed HTTP methods, no pagination).

**Implementation tasks**
1. `Site` model: `name` (unique), `description` (blank/optional), `status`
   (`TextChoices`: Active / Planned / Decommissioned). Add `__str__`.
2. Migration for `Site`.
3. `SiteSerializer` (ModelSerializer, all fields; `status` validated by choices).
4. `SiteViewSet` (`ModelViewSet`) registered on the router as `sites`. Restrict methods to the
   required set via `http_method_names = ['get', 'post', 'put', 'delete', 'head', 'options']`
   — this becomes the pattern for all CRUD ViewSets.

**Files/components affected**
`topology/models.py`, `topology/serializers.py`, `topology/views.py`, `topology/urls.py`,
`topology/migrations/`, `topology/tests/test_models.py`, `topology/tests/test_api.py`.

**Tests** (spec §19 — Site)
* create, retrieve, update, delete Site (correct status codes: 201/200/200/204).
* duplicate Site name rejected (`400`).
* invalid `status` value rejected (`400`).
* missing required `name` rejected (`400`).
* an unsupported HTTP method returns `405 Method Not Allowed`.
* model-level: uniqueness constraint and choices enforced.

**Acceptance criteria**
* `/api/sites/` supports full CRUD with conventional status codes (spec §16).
* Uniqueness and status validation return `400`; only the required methods are exposed.
* `Site` appears in `/api/schema/`.

**Dependencies**
Phase 1.

---

### Phase 3 — Device Resource

**Objective**
Implement `Device` with its FK to `Site`, uniqueness constraints, and protected-delete
behaviour on `Site`.

**Implementation tasks**
1. `Device` model: `name` (globally unique), `serial_number` (unique), `site`
   (`ForeignKey(Site, on_delete=PROTECT, related_name='devices')`). Migration.
2. `DeviceSerializer` (`site` as `PrimaryKeyRelatedField`; invalid/nonexistent site → `400`).
3. `DeviceViewSet` registered as `devices` (same method restrictions as Phase 2).
4. Add a custom DRF exception handler (or view-level handling) mapping `ProtectedError` to
   `409 Conflict`, so deleting a Site that still has Devices returns `409`.

**Files/components affected**
`topology/models.py`, `serializers.py`, `views.py`, `urls.py`, migrations, `test_models.py`,
`test_api.py`, and a small exception-handler module wired via `REST_FRAMEWORK['EXCEPTION_HANDLER']`.

**Tests** (spec §19 — Device)
* create, retrieve, update, delete Device.
* duplicate name rejected; duplicate serial_number rejected.
* invalid / nonexistent `site` rejected (`400`).
* deleting a Site that has Devices returns `409 Conflict`.

**Acceptance criteria**
* `/api/devices/` full CRUD; FK integrity and uniqueness enforced.
* Protected-delete returns `409` when dependants exist.

**Dependencies**
Phase 2.

---

### Phase 4 — Interface Resource

**Objective**
Implement `Interface` with its FK to `Device`, positive-speed validation, status choices, and
the `(device, name)` composite uniqueness constraint.

**Implementation tasks**
1. `Interface` model: `name`, `device`
   (`ForeignKey(Device, on_delete=PROTECT, related_name='interfaces')`),
   `speed` (`PositiveIntegerField` + `MinValueValidator(1)`; `PositiveIntegerField` alone
   allows 0, so the validator is required to enforce strictly positive),
   `status` (`TextChoices`: Up / Down / Maintenance),
   `Meta.constraints = [UniqueConstraint(fields=['device', 'name'], ...)]`. Migration.
2. `InterfaceSerializer` — surface composite-uniqueness, speed, and status errors as `400`.
3. `InterfaceViewSet` registered as `interfaces` (same method restrictions).

**Files/components affected**
`topology/models.py`, `serializers.py`, `views.py`, `urls.py`, migrations, `test_models.py`,
`test_api.py`.

**Tests** (spec §19 — Interface)
* create, retrieve, update, delete Interface.
* duplicate interface name within the **same** Device rejected (`400`).
* same interface name on **different** Devices allowed (`201`).
* invalid / nonexistent `device` rejected.
* invalid `speed` (0, negative, non-integer) rejected.
* invalid `status` rejected.

**Acceptance criteria**
* `/api/interfaces/` full CRUD.
* Composite uniqueness, positive speed, and status choices enforced with `400`.

**Dependencies**
Phase 3.

---

### Phase 5 — Connection Resource (model, endpoint validation, CRUD)

**Objective**
Implement `Connection` with distinct input/output serializers and CRUD. Create/update accept
flat interface IDs; responses expose the full derived hierarchy.

**Implementation tasks**
1. `Connection` model: `connection_id` (unique), `name` (optional), `status`
   (`TextChoices`: Connected / Disconnected), `start_interface` and `end_interface`
   (`ForeignKey(Interface, on_delete=PROTECT, related_name='+')`). Migration.
   Default ordering by `id` ascending.
2. **Connection input serializer** (`connection_id`, `name`, `status`, `start_interface`,
   `end_interface`):
   * `connection_id`: required, unique, matches an alphanumeric format
     (e.g. regex `^[A-Za-z0-9]+$`); document the format via `help_text` for OpenAPI.
   * `status`: validated by choices.
   * `start_interface` / `end_interface`: `PrimaryKeyRelatedField(queryset=Interface.objects.all())`,
     both required; a missing or nonexistent interface ID → `400`.
   * cross-field validation: `start_interface != end_interface` → `400`
     (point-to-point connections must join two distinct interfaces).
   * Note: because only interface IDs are supplied, the Site→Device→Interface hierarchy is
     derived from each Interface and is inherently consistent; there is no separate
     site/device cross-check to perform.
3. **Connection output serializer** producing `start_target` / `end_target` nested
   `{site:{id,name}, device:{id,name}, interface:{id,name}}` derived from each endpoint
   Interface (spec §11).
4. `ConnectionViewSet`: use the input serializer for write actions and the output serializer
   for read actions (`get_serializer_class`); apply
   `select_related('start_interface__device__site', 'end_interface__device__site')` to avoid
   N+1 (full review in Phase 7). Same method restrictions as the other ViewSets.
5. Register as `connections`. Use `@extend_schema` with explicit request/response serializers
   so OpenAPI shows the asymmetric request (IDs) vs response (`*_target`) shapes.

**Files/components affected**
`topology/models.py`, `serializers.py`, `views.py`, `urls.py`, migrations,
`topology/tests/test_models.py`, `test_serializers.py`, `test_api.py`.

**Tests** (spec §19 — Connection; architecture §21 serializer tests)
* create valid Connection (`201`) with correct `start_target`/`end_target` output shape.
* retrieve, update, delete Connection.
* duplicate `connection_id` rejected (`400`).
* invalid `connection_id` format rejected (`400`).
* invalid / nonexistent `start_interface` rejected (`400`).
* invalid / nonexistent `end_interface` rejected (`400`).
* missing endpoint (`start_interface` or `end_interface` absent) rejected (`400`).
* same Interface as both endpoints rejected (`400`).
* invalid `status` rejected (`400`).
* update re-applies the same validation rules as create.

**Acceptance criteria**
* `/api/connections/` full CRUD.
* Create/update accept flat `start_interface`/`end_interface` IDs and validate that both
  interfaces exist and are distinct.
* Responses include complete `start_target`/`end_target` (spec acceptance criteria §21.13).
* All validation failures return `400`.

**Dependencies**
Phase 4 (needs Interface, Device, Site).

---

### Phase 6 — Connection Tracing

**Objective**
Implement the isolated `TopologyTracer` service and the `/api/trace/` endpoint for site,
device, and interface tracing with de-duplication and full error handling.

**Implementation tasks**
1. `topology/services/tracer.py` — `TopologyTracer` with methods for interface/device/site
   tracing (architecture §11–§13). Each returns a **de-duplicated, id-ordered**
   `Connection` queryset using ORM `Q(start_interface__...) | Q(end_interface__...)` +
   `.distinct()` (DB-level filtering, not app-side dedup), with `select_related` for the
   output hierarchy.
   * interface: `start_interface=obj OR end_interface=obj`.
   * device: either endpoint's interface `device=obj`.
   * site: either endpoint's interface `device__site=obj`.
2. Trace view (`APIView` / `@api_view`, separate from CRUD ViewSets — spec §17):
   * read `type` and `id` query params;
   * `400` if `type` missing/invalid, or `id` missing/non-integer;
   * resolve the traced object → `404` if not found;
   * invoke the tracer; serialize with the Connection **output** serializer;
   * return `traced_object {type, id, name}`, `connections_count`, `connections`
     (spec §14), guaranteeing `connections_count == len(connections)`.
3. Route `trace/` in `topology/urls.py`. Add `@extend_schema` describing `type`/`id` params,
   the response shape, and error responses.

**Files/components affected**
`topology/services/tracer.py`, `topology/views.py`, `topology/serializers.py` (trace response
serializer), `topology/urls.py`, `topology/tests/test_tracing.py`.

**Tests** (spec §19 — Trace; architecture §21 — tested via API **and** service directly)
* interface tracing returns connections where the interface is start or end.
* device tracing across multiple interfaces of the device.
* site tracing across multiple devices of the site.
* connection appearing via either endpoint.
* no duplicate connection when both endpoints belong to the traced object
  (`connections_count` correct).
* empty trace result (object exists, no connections) → `200`, count `0`.
* missing `type` → `400`; missing `id` → `400`; invalid `type` → `400`;
  non-integer `id` → `400`.
* nonexistent object id → `404`.
* service-level unit tests of `TopologyTracer` independent of HTTP.

**Acceptance criteria**
* `/api/trace/?type=&id=` satisfies spec §12–§15 and acceptance criteria §21.7–§21.12.
* Each connection appears at most once, ordered by ascending `id`.
* De-duplication is done at the queryset level.

**Dependencies**
Phase 5.

---

### Phase 7 — Documentation, Query Efficiency & README

**Objective**
Finalise OpenAPI quality, verify query efficiency, and complete the README so the project can
be set up and run from scratch (spec §18, §21.16–§21.17; architecture §14, §24 steps 12–14).

**Implementation tasks**
1. OpenAPI polish: verify `/api/schema/` and `/api/docs/` describe all CRUD endpoints,
   request/response schemas (including the asymmetric Connection request vs response), the
   trace query params, and error responses. Add `@extend_schema`/`extend_schema_view`
   annotations where the generated schema is inaccurate.
2. Query efficiency review (architecture §14): use `assertNumQueries` around connection list
   and trace serialization; confirm `select_related` coverage; no N+1.
3. README: flesh out setup (venv, install, migrate, runserver), design summary, API usage
   examples (curl for each resource + trace), and links to `/api/docs/` and `/api/schema/`.
   The assumptions already recorded in the README remain the canonical list.
4. Final full-suite run and coverage sanity check against the spec §19 list.

**Files/components affected**
`topology/views.py`, `topology/serializers.py` (schema annotations), `README.md`,
`topology/tests/` (query-count tests).

**Tests**
* `assertNumQueries` tests for connection list and trace endpoints (no N+1).
* Schema generation test: `GET /api/schema/` returns `200` and includes all four resources
  plus the trace path.
* Full `python manage.py test` run green.

**Acceptance criteria**
* Interactive Swagger UI documents all endpoints, params, and error responses (§21.16).
* No obvious N+1 on connection/trace responses (architecture §14).
* A new user can set up and run the project solely from the README (§21.17).
* All spec §19 test cases are covered.

**Dependencies**
Phases 1–6.

---

## 3. Cross-Cutting Notes

* **HTTP methods:** every CRUD ViewSet exposes only `GET/POST/PUT/DELETE`; any other method
  returns `405`.
* **Status codes** (spec §16): `200` GET/PUT, `201` POST, `204` DELETE, `400`
  validation/unique violation, `404` missing resource, `409` delete blocked by dependants.
* **Validation layering** (architecture §15): DB constraints for persistent uniqueness;
  serializer validation for request-shape and endpoint rules. Both are tested.
* **No pagination:** list and trace endpoints return full collections.
* **Test organisation** follows architecture §5 (`test_models`, `test_serializers`,
  `test_api`, `test_tracing`); may be consolidated if simpler.
* **No auth, no frontend, no Docker, SQLite only** (architecture §18–§20).

## 4. Definition of Done (maps to spec §21)

All 18 acceptance criteria in spec §21 are met, the full automated test suite passes, OpenAPI
docs are served at `/api/docs/`, and the project runs from the README instructions with
SQLite and no extra infrastructure.

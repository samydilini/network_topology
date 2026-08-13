# network_topology
Network Topology Tracing API



Setup

1. Create and activate a virtual environment.
2. Install dependencies.
3. Run migrations:
    ```bash
   python manage.py migrate
   ```
4. Start the development server:

   ``` bash
   python manage.py runserver
   ```
   

Assumptions 
A point-to-point connection must connect two distinct interfaces. Therefore, a connection referencing the same interface as both its start and end endpoint is considered invalid.
Deletion behaviour: Resources with dependent resources cannot be deleted. Foreign-key relationships use protected deletion to prevent accidental cascading removal of network topology. Dependencies must be removed explicitly before the parent resource can be deleted. A DELETE against a resource that still has dependants returns 409 Conflict.
connection_id is given as a string (e.g. CONN-1002) is an Alphanumeric + hyphen with 9 characters. However, requirements specifies it as "unique alphanumeric identifier". Therefore, it will be a alpanumeric of 8 eg: CONN1002
Interface speed is a poititve integer value in Mbps.
In trace endpoint malformed `id` is a bad request → `400`; a well-formed integer id with no matching row → `404`. Missing `type`/`id`, or an invalid`type` value → `400`
ordering of connections will be done by id ascending order.
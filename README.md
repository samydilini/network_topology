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
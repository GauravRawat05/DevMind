# Sub-plan 5.2: User Authentication & JWT Security

## Objective
Implement user registration, login, and JWT token authorization to secure the analysis jobs and Q&A endpoints.

## Action Plan
1. Add `password_hash` column to the SQLAlchemy Postgres user model.
2. Install `passlib[bcrypt]` and `python-jose` for hashing passwords and generating JWTs.
3. Write routes:
   - `POST /auth/register` (User registration with hashed password)
   - `POST /auth/login` (User login, returning a JWT token)
4. Implement a dependency function `get_current_user` in FastAPI to validate headers and secure API endpoints.

## GSD XML Task Definition
```xml
<task type="auto">
  <name>Build JWT authentication system</name>
  <files>
    - backend/models/pg_models.py
    - backend/api/routes/auth.py
    - backend/services/auth_service.py
  </files>
  <action>
    Update Postgres database schemas with User credentials.
    Write registration and login logic with bcrypt and JWT signatures.
    Implement FastAPI security dependencies for authorization checks.
  </action>
  <verify>
    Register a test user, request a login token, and verify that passing the token in the Authorization header to a protected route returns a 200 OK.
  </verify>
  <done>
    JWT user authentication system completed.
  </done>
</task>
```

# Sub-plan 1.1: Workspace Structure & Root Configurations

## Objective
Establish the project's base directories and configure root-level settings to ensure clean development.

## Action Plan
1. Create directories:
   - `backend/` (FastAPI backend)
   - `frontend/` (Next.js frontend)
   - `docker/` (Docker configuration files)
2. Create a global `.gitignore` in the root folder.

## GSD XML Task Definition
```xml
<task type="auto">
  <name>Create workspace folders and root configurations</name>
  <files>
    - backend/
    - frontend/
    - docker/
    - .gitignore
  </files>
  <action>
    Create backend/, frontend/, and docker/ folders.
    Write a comprehensive .gitignore file to ignore Python virtual environments, Next.js build outputs, node_modules, and cache files.
  </action>
  <verify>
    Verify directory list and show .gitignore contents.
  </verify>
  <done>
    Root directories and .gitignore created successfully.
  </done>
</task>
```

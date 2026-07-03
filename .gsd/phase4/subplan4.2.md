# Sub-plan 4.2: Repository Submission Homepage

## Objective
Build the Next.js landing page featuring a premium repo URL input form, validation, and submission redirect.

## Action Plan
1. Create `frontend/app/page.tsx`.
2. Write custom CSS modules for the homepage components (hero title, input container, submit button).
3. Implement clientside URL format checks (verifying valid GitHub URL structures) and loading state indicators.
4. Route to `/dashboard/[job_id]` upon API response of 202 Accepted.

## GSD XML Task Definition
```xml
<task type="auto">
  <name>Build repository submission interface</name>
  <files>
    - frontend/app/page.tsx
    - frontend/app/page.module.css
  </files>
  <action>
    Create homepage route.
    Build form layout with URL parsing validation, submit animations, and backend connection handling.
  </action>
  <verify>
    Open homepage locally, input an invalid URL (verify error), then input a valid GitHub URL, click submit, and confirm redirect to dashboard page.
  </verify>
  <done>
    Homepage repo submission UI complete.
  </done>
</task>
```

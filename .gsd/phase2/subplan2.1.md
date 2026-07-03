# Sub-plan 2.1: GitHub Repository Fetcher Service

## Objective
Implement a backend service that downloads the contents of public GitHub repositories using the GitHub API or Git cloning.

## Action Plan
1. Create `backend/services/github_service.py`.
2. Implement functions to clone/download a repository to a local temp folder or fetch files using public API endpoints.
3. Add helper functions to filter out non-code assets (e.g. binaries, images, pdfs) and return a list of text file paths + contents.

## GSD XML Task Definition
```xml
<task type="auto">
  <name>Build GitHub repository downloader service</name>
  <files>
    - backend/services/github_service.py
  </files>
  <action>
    Create github_service.py.
    Implement clean repository extraction, excluding binary/unwanted extensions, and return a dictionary/list of code files.
  </action>
  <verify>
    Write a simple test script passing a public repo URL to check if code files are extracted correctly.
  </verify>
  <done>
    GitHub downloader service written and verified.
  </done>
</task>
```

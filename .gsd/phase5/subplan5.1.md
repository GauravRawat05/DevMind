# Sub-plan 5.1: File Storage Manager & Mock S3 Client

## Objective
Implement a local file storage manager that saves generated documentation files (.md) to a local directory, exposing the same API as an AWS S3 client for easy future integration.

## Action Plan
1. Create `backend/services/storage_service.py`.
2. Implement a `StorageService` interface with `upload_file(file_path, file_data)` and `download_file(file_path)` methods.
3. Configure the backend so that changing `STORAGE_PROVIDER=local` to `STORAGE_PROVIDER=s3` routes file transfers to AWS S3 using `boto3` instead of the local workspace directory (`backend/storage/`).

## GSD XML Task Definition
```xml
<task type="auto">
  <name>Build S3-compatible local storage service</name>
  <files>
    - backend/services/storage_service.py
  </files>
  <action>
    Create storage_service.py.
    Implement S3 mock local-file driver, saving generated files to backend/storage/.
    Write abstract interface for toggleable S3 cloud storage switch.
  </action>
  <verify>
    Call upload_file to write a dummy text file, check if file is written under backend/storage/, and download it back to verify contents match.
  </verify>
  <done>
    Mock S3 storage manager operational.
  </done>
</task>
```

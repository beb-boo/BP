# Analysis and Recommendations for Blood Pressure API

## 1. Code Restructuring (Priority: High)
- [ ] **Refactor `main.py`**: The file is currently over 2,500 lines. It should be split into multiple modules for better maintainability.
    - Create `app/routers/` for logical separation of endpoints:
        - `auth.py`: Login, Register, OTP.
        - `users.py`: User profile management.
        - `ocr.py`: BP image processing.
        - `doctor.py`: Doctor-Patient interactions.
    - Move Pydantic models to `app/schemas.py`.
    - Move SQLAlchemy models to `app/models.py`.
    - Move utility functions (`hash_password`, `jwt`, etc.) to `app/utils/`.

## 2. Robustness & Error Handling
- [ ] **Database Integrity**: In registration and data creation, catch specific `sqlalchemy.exc.IntegrityError` instead of generic `Exception` to handle duplicate entries more gracefully.
- [ ] **Gemini OCR Robustness**: 
    - Improve the prompt to handle cases where the image is NOT a blood pressure monitor. Currently, it might try to hallucinate values.
    - Add a retry mechanism for transient API failures.
    - Consider using `response_schema` in Gemini 2.0 (if available/supported in the lib SDK version) to guarantee JSON structure locally.

## 3. Configuration Management
- [ ] **Environment Variables**: currently `os.getenv` is used directly in multiple places.
    - Suggest using `pydantic-settings` to define a `Settings` class that validates all required environment variables (e.g., `GOOGLE_AI_API_KEY`, `DB_URL`) at startup.

## 4. Testing (Critical)
- [ ] **Add Automated Tests**: There are currently no tests visible.
    - Add `pytest` for unit testing functions.
    - Add integration tests for API endpoints using `TestClient` from FastAPI.

## 5. Security Improvements
- [ ] **CORS**: The current CORS setting is `allow_origins=["*"]`. This should be restricted to specific frontend domains in production.
- [ ] **API Keys**: Ensure `VALID_API_KEYS` is properly managed and rotated.

## 6. Feature Recommendations
- [ ] **Doctor Dashboard**: The current endpoints allow data retrieval. Consider adding an endpoint for "Patient Trends" (e.g., average BP over last 7 days) to reduce frontend calculation load.
- [ ] **Image Storage**: Currently, images are processed and deleted (temp). Consider verifying if there is a requirement to *store* the images for medical audit purposes (e.g., in AWS S3 or Google Cloud Storage) rather than discarding them immediately.

## 7. Bug & Logic Review
- [ ] **Timezone Handling**: Code uses `Asia/Bangkok` explicitly. Ensure the database (Postgres/MySQL) is also configured or stores in UTC to avoid offset issues.
## 8. Requirements & Validation Gaps (from Docs)
- [ ] **Citizen ID Validation**: `Test Scenario.xlsx` (Edit_prof_05) requires "Invalid citizen id format" error. Currently, `citizen_id` is not validated for format (e.g. Thai ID checksum/length).
- [ ] **Weight Limit Discrepancy**: `Test Scenario.xlsx` (Edit_prof_08) states weight should be <= 300. Code allows <= 500. Clarification needed or update code to match reqs.
- [ ] **BP.pdf Review**: Full automated review of `BP.pdf` was not possible due to file format. Manual review recommended to ensure no other non-technical requirements are missed.


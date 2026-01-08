# Multi-Course Architecture Plan

## Overview
To support multiple training domains (e.g., "Sales Trainer", "Phone Videography") with complete separation of content, categories, and statistics, we will evolve the system from a single-context application to a multi-course platform.

This plan ensures that "everything is different" for each course while maintaining a unified, maintainable codebase.

## 1. Database Architecture Changes

We will introduce a "Logical Partitioning" strategy. Instead of managing multiple physical SQLite files (which is error-prone), we will add a `Course` layer that strictly isolates data.

### New Tables
1.  **`courses`**
    *   `id` (Integer, PK)
    *   `name` (Text) - e.g., "Sales Trainer", "Phone Videography"
    *   `slug` (Text) - e.g., "sales", "videography" (for URLs)
    *   `description` (Text)
    *   `created_at` (Timestamp)

2.  **`course_categories`**
    *   *Replaces hardcoded `VALID_CATEGORIES` in code.*
    *   `id` (Integer, PK)
    *   `course_id` (FK -> courses)
    *   `name` (Text) - e.g., "Pre Consultation", "Lighting Setup"
    *   `display_order` (Integer)

### Modified Tables
*   **`sessions`**: Add `course_id` (FK).
*   **`uploads`**: Add `course_id` (FK).
*   **`question_bank`**: Linked via `session_id`, but templates (if added later) will need `course_id`.

## 2. Pinecone Vector Store Strategy

To keep the "Brain" of each course separate, we will update the namespace strategy.

*   **Current Namespace:** `{category}_{video_name}`
*   **New Namespace:** `{course_slug}_{category}_{video_name}`
*   **Logic:**
    *   When a user uploads content, it is tagged with the active Course ID.
    *   When generating questions/evaluating, the system **only** queries namespaces belonging to the active Course.

## 3. Application Logic Updates

### Backend (Python/Flask)
1.  **Context Management:**
    *   Add `current_course_id` to the User Session.
    *   Create a `@course_required` decorator for course-specific routes.
2.  **Dynamic Validation:**
    *   Remove hardcoded categories from `validators.py`.
    *   Validate inputs against `course_categories` table based on the active course.
3.  **API Updates:**
    *   `/api/courses`: List available courses.
    *   `/api/courses/<id>/select`: Switch user's active context.
    *   `/api/admin/config`: Manage courses and categories.

### Frontend (JS/HTML)
1.  **Course Selector:**
    *   New screen or dropdown after Login to select the Course.
    *   "Switch Course" button in the dashboard.
2.  **Dynamic UI:**
    *   Dropdowns for "Category" will fetch from API instead of hardcoded arrays.
    *   Dashboard stats will filter by the active Course.

## 4. Migration Strategy (The "How-To")

We will perform this transition safely without losing existing Sales data.

1.  **Step 1: Schema Migration**
    *   Create `courses` and `course_categories` tables.
    *   Insert "Sales Trainer" as Course ID `1`.
    *   Migrate all existing `sessions` and `uploads` to Course ID `1`.
    *   Populate `course_categories` with the current sales categories.

2.  **Step 2: Code Refactor**
    *   Update `database.py` to support the new tables.
    *   Update `validators.py` to read from DB.
    *   Update `pinecone_service.py` to handle course prefixes.

3.  **Step 3: Frontend Update**
    *   Add the Course Selection UI.
    *   Connect the UI to the new dynamic APIs.

## 5. Summary of "Different" Things
*   **Different Database:** Logical separation via `course_id` (acts like separate DBs).
*   **Different Categories:** Each course defines its own.
*   **Different Content:** Vectors are isolated in Pinecone.
*   **Different Stats:** Dashboard only shows stats for the active course.

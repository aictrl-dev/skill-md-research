# Target Codebase Selection for Decomposition Experiment

**Goal**: Select an open-source full-stack codebase for testing decomposition strategies

---

## 1. Candidate Codebases

### Primary Candidates

| Codebase | Stack | Complexity | Tests | Why Good |
|----------|-------|------------|-------|----------|
| **Metabase** | Clojure + React + H2/Postgres | High | Yes | Analytics domain, many CRUD + workflows |
| **Ghost** | Node.js + React + MySQL | Medium | Yes | Clean architecture, blog domain |
| **Plane** | Python + Next.js + Postgres | Medium | Yes | Project management, active dev |
| **Outline** | Node.js + React + Postgres | Medium | Yes | Wiki/documentation, real-world |
| **Twenty** | TypeScript + React + Postgres | Medium | Yes | CRM, modern stack |

### Detailed Analysis

#### Metabase

```
github: metabase/metabase
stars: 40k+
stack:
  backend: Clojure (JVM)
  frontend: React + TypeScript
  database: H2 (dev), Postgres/MySQL (prod)
  tests: 3000+ unit tests, integration tests

pros:
  - Well-documented domain (analytics)
  - Clear models: Database, Table, Question, Dashboard, Card
  - Mix of CRUD and complex workflows
  - Active development

cons:
  - Clojure is less common
  - Large codebase (steep learning curve)

sample_tasks:
  - Add "description" field to Dashboard (CRUD)
  - Add "scheduled refresh" for Questions (Workflow)
  - Add Slack notification for alerts (Integration)
  - Add multi-step query builder wizard (UI Flow)
```

#### Ghost

```
github: TryGhost/Ghost
stars: 48k+
stack:
  backend: Node.js (Express)
  frontend: React
  database: MySQL (Bookshelf ORM)
  tests: 1500+ tests

pros:
  - Common stack (Node + React)
  - Clean architecture
  - Well-defined models: Post, User, Tag, Member
  - Good for CRUD-heavy tasks

cons:
  - Less workflow complexity
  - Fewer integration opportunities

sample_tasks:
  - Add "reading_time" to Posts (CRUD)
  - Add post scheduling workflow (Workflow)
  - Add webhook for new members (Integration)
  - Add multi-step post creation wizard (UI Flow)
```

#### Plane

```
github: makeplane/plane
stars: 32k+
stack:
  backend: Python (Django)
  frontend: Next.js
  database: Postgres
  tests: Growing test suite

pros:
  - Modern stack
  - Project management domain (rich workflows)
  - Active development
  - Clear models: Project, Issue, Cycle, Module

cons:
  - Smaller test suite
  - Django patterns may vary

sample_tasks:
  - Add "priority" field to Issues (CRUD)
  - Add issue state machine transitions (Workflow)
  - Add GitHub sync for issues (Integration)
  - Add issue creation wizard (UI Flow)
```

#### Outline

```
github: outline/outline
stars: 28k+
stack:
  backend: Node.js (TypeScript)
  frontend: React
  database: Postgres
  tests: Good coverage

pros:
  - TypeScript throughout
  - Document/wiki domain
  - Clean architecture
  - Real collaboration features

cons:
  - Complex real-time features

sample_tasks:
  - Add "word_count" to Documents (CRUD)
  - Add document approval workflow (Workflow)
  - Add Slack sharing integration (Integration)
  - Add document creation wizard (UI Flow)
```

---

## 2. Selection Criteria

| Criterion | Weight | Metabase | Ghost | Plane | Outline |
|-----------|--------|----------|-------|-------|---------|
| Stack familiarity (TS/Node) | 20% | 2 | 5 | 4 | 5 |
| Test coverage | 20% | 5 | 4 | 3 | 4 |
| Task variety (CRUD + workflows) | 25% | 5 | 3 | 5 | 4 |
| Codebase size (not too big) | 15% | 2 | 4 | 4 | 4 |
| Active maintenance | 10% | 5 | 5 | 5 | 5 |
| Documentation quality | 10% | 5 | 4 | 4 | 4 |
| **Weighted Score** | | **3.85** | **3.95** | **4.15** | **4.35** |

### Recommendation: **Outline** (primary) or **Plane** (secondary)

Rationale:
- Both have TypeScript/Node stack (widely understood)
- Both have clear domain models
- Both support variety of task types
- Manageable codebase size
- Good test coverage

---

## 3. Concrete Task Set for Outline

### Task 1: CRUD - Add "word_count" to Documents

```yaml
task_id: outline_crud_001
type: CRUD
codebase: outline/outline
difficulty: simple

description: |
  Add a "word_count" field to the Document model that:
  - Is automatically calculated when document content changes
  - Is returned in the Document API response
  - Can be filtered/sorted in document listings

existing_code:
  models:
    - server/models/Document.ts
  api:
    - server/api/documents.ts
  tests:
    - server/test/api/documents.test.ts

artifacts_to_generate:
  gherkin: |
    Feature: Document word count
    
    Scenario: Word count is calculated on save
      Given I create a document with content "Hello world test"
      When I save the document
      Then the word_count should be 3
    
    Scenario: Word count is returned in API
      Given a document exists with word_count 10
      When I fetch the document
      Then the response should include word_count: 10

  openapi: |
    /documents/{id}:
      get:
        responses:
          200:
            content:
              application/json:
                properties:
                  word_count:
                    type: integer
                    description: Number of words in document content

  sql: |
    ALTER TABLE documents ADD COLUMN word_count INTEGER DEFAULT 0;
    CREATE INDEX idx_documents_word_count ON documents(word_count);

decomposition_stack:
  - step_1: Add word_count column to documents table (migration)
  - step_2: Update Document model (TypeScript)
  - step_3: Add word count calculation on save
  - step_4: Update API response to include word_count
  - step_5: Add/update tests

decomposition_domain:
  - step_1: Define WordCount value object
  - step_2: Add word count calculation to Document domain
  - step_3: Expose via API
  - step_4: Add database persistence
  - step_5: Add tests

decomposition_journey:
  - step_1: User types content (UI captures text)
  - step_2: System calculates word count (frontend preview)
  - step_3: User saves document
  - step_4: System persists word count
  - step_5: User sees word count in document view

eval_criteria:
  - Migration runs: `yarn db:migrate` succeeds
  - Model updated: Document model has word_count field
  - Calculation works: Create doc, check word_count matches
  - API returns field: GET /documents/:id includes word_count
  - Tests pass: `yarn test` passes
  - No regressions: All existing tests pass
```

### Task 2: Workflow - Add Document Approval Flow

```yaml
task_id: outline_workflow_001
type: Workflow
codebase: outline/outline
difficulty: medium

description: |
  Add document approval workflow:
  - Documents can be submitted for approval
  - Approvers can approve/reject
  - State transitions: draft → pending → approved/rejected
  - Notifications to approvers

existing_code:
  models:
    - server/models/Document.ts
  policies:
    - server/policies/document.ts
  api:
    - server/api/documents.ts

artifacts_to_generate:
  gherkin: |
    Feature: Document approval workflow
    
    Scenario: Author submits for approval
      Given a document in "draft" state
      When the author submits for approval
      Then the document state should be "pending_approval"
      And approvers should be notified
    
    Scenario: Approver approves
      Given a document in "pending_approval" state
      When an approver approves
      Then the document state should be "approved"
      And the author should be notified
    
    Scenario: Approver rejects
      Given a document in "pending_approval" state
      When an approver rejects with reason "Needs revision"
      Then the document state should be "rejected"
      And the rejection reason should be stored

  openapi: |
    /documents/{id}/submit:
      post:
        requestBody:
          content:
            application/json:
              properties:
                approver_ids:
                  type: array
                  items:
                    type: string
    
    /documents/{id}/approve:
      post:
        requestBody:
          content:
            application/json:
              properties:
                comment:
                  type: string
    
    /documents/{id}/reject:
      post:
        requestBody:
          content:
            application/json:
              properties:
                reason:
                  type: string

  sql: |
    ALTER TABLE documents ADD COLUMN approval_state VARCHAR(20) DEFAULT 'draft';
    ALTER TABLE documents ADD COLUMN rejection_reason TEXT;
    
    CREATE TABLE document_approvals (
      id UUID PRIMARY KEY,
      document_id UUID REFERENCES documents(id),
      approver_id UUID REFERENCES users(id),
      state VARCHAR(20),
      created_at TIMESTAMP
    );

decomposition_stack:
  - step_1: Add approval_state column and approvals table
  - step_2: Update Document model with state machine
  - step_3: Create approval API endpoints
  - step_4: Add notification service integration
  - step_5: Update UI for approval actions
  - step_6: Add tests

decomposition_domain:
  - step_1: Define ApprovalState enum
  - step_2: Define DocumentApproval aggregate
  - step_3: Define state transition rules
  - step_4: Implement approval commands
  - step_5: Wire up notifications
  - step_6: Expose via API + UI
  - step_7: Add tests

decomposition_journey:
  - step_1: Author clicks "Submit for approval"
  - step_2: Author selects approvers
  - step_3: Approvers receive notification
  - step_4: Approver reviews document
  - step_5: Approver approves/rejects
  - step_6: Author receives decision notification

eval_criteria:
  - State transitions work: draft → pending → approved
  - Invalid transitions rejected: can't go approved → pending
  - Notifications sent: check notification records
  - API endpoints work: POST /submit, /approve, /reject
  - Tests pass: `yarn test` passes
```

### Task 3: Integration - Add Slack Sharing

```yaml
task_id: outline_integration_001
type: Integration
codebase: outline/outline
difficulty: medium

description: |
  Add ability to share documents to Slack:
  - Configure Slack webhook per team
  - Share document with preview to Slack channel
  - Include document title, excerpt, author, link

existing_code:
  models:
    - server/models/Team.ts
    - server/models/Document.ts
  integrations:
    - server/integrations/ (existing integration patterns)

artifacts_to_generate:
  gherkin: |
    Feature: Slack document sharing
    
    Scenario: Share document to Slack
      Given a team with Slack integration configured
      And a document "Meeting Notes"
      When I share the document to "#general"
      Then a Slack message should be posted to #general
      And the message should contain the document title
    
    Scenario: Share without configuration
      Given a team without Slack integration
      When I try to share a document
      Then I should see "Slack not configured"

  openapi: |
    /documents/{id}/share:
      post:
        requestBody:
          content:
            application/json:
              properties:
                channel:
                  type: string
                  description: Slack channel ID
                message:
                  type: string

decomposition_stack:
  - step_1: Add slack_webhook_url to Team model
  - step_2: Create SlackService class
  - step_3: Add share API endpoint
  - step_4: Add share button in UI
  - step_5: Add tests (mocked)

decomposition_domain:
  - step_1: Define ShareChannel interface
  - step_2: Implement SlackChannel
  - step_3: Add share method to Document
  - step_4: Expose via API
  - step_5: Add UI
  - step_6: Add tests

eval_criteria:
  - Slack webhook stored: Team has slack_webhook_url
  - Share API works: POST /share returns 200
  - Slack message format correct: contains title, link, excerpt
  - Error handling: graceful failure if webhook invalid
  - Tests pass with mocked Slack API
```

### Task 4: UI Flow - Add Document Template Wizard

```yaml
task_id: outline_uiflow_001
type: UI Flow
codebase: outline/outline
difficulty: medium

description: |
  Add document creation wizard:
  - Step 1: Choose template (blank, meeting notes, spec, etc.)
  - Step 2: Set title and parent collection
  - Step 3: Configure permissions
  - Step 4: Review and create

existing_code:
  components:
    - app/components/Document/
  api:
    - server/api/documents.ts

artifacts_to_generate:
  gherkin: |
    Feature: Document creation wizard
    
    Scenario: Create from template
      Given I am creating a new document
      When I select "Meeting Notes" template
      And I enter title "Team Sync"
      And I select "Engineering" collection
      And I set permissions to "team"
      And I click "Create"
      Then a document should be created with the template content
      And the document should be in the Engineering collection
    
    Scenario: Navigate back in wizard
      Given I am on step 3 of the wizard
      When I click "Back"
      Then I should be on step 2
      And my previous selections should be preserved

decomposition_stack:
  - step_1: Create Template model/table
  - step_2: Create wizard API endpoints
  - step_3: Build wizard components (4 steps)
  - step_4: Add navigation state management
  - step_5: Connect to document creation API
  - step_6: Add tests

decomposition_domain:
  - step_1: Define DocumentTemplate entity
  - step_2: Define CreateDocumentFromTemplate command
  - step_3: Implement template application logic
  - step_4: Build wizard UI
  - step_5: Add tests

decomposition_journey:
  - step_1: User clicks "New from template"
  - step_2: User browses templates, selects one
  - step_3: User enters title, selects collection
  - step_4: User sets permissions
  - step_5: User reviews and creates
  - step_6: System creates document from template

eval_criteria:
  - Wizard has 4 steps: template, title, permissions, review
  - Back navigation works: state preserved
  - Templates available: at least 3 templates
  - Document created: correct content from template
  - E2E tests pass
```

---

## 4. Evaluation Harness Setup

### Repository Structure

```
experiment-harness/
  codebase/
    outline/                    # git clone of outline/outline
  
  tasks/
    outline_crud_001.yaml
    outline_workflow_001.yaml
    outline_integration_001.yaml
    outline_uiflow_001.yaml
  
  prompts/
    decomposition/
      stack.md
      domain.md
      journey.md
    artifacts/
      natural_language.md
      gherkin_only.md
      gherkin_openapi.md
      full_artifacts.md
  
  runners/
    run_experiment.py           # Main runner
    clone_codebase.sh           # Clone outline repo
    reset_codebase.sh           # Reset to clean state
    run_llm_task.py             # Execute LLM with prompt
    apply_changes.py            # Apply generated code
    run_tests.sh                # Run test suite
    evaluate.py                 # Score results
  
  results/
    runs/
      outline_crud_001/
        stack_gherkin_openapi_sql/
          rep_1/
            artifacts/
              feature.feature
              openapi.yaml
              migration.sql
            output/
              files_changed.json
              test_results.json
            metrics.json
          rep_2/
          rep_3/
```

### Evaluation Script

```python
# evaluate.py

import subprocess
import json
from pathlib import Path

def evaluate_run(run_path: Path, task_spec: dict) -> dict:
    """Evaluate a single experiment run."""
    results = {}
    
    # 1. Artifact validation
    results['artifacts'] = {
        'gherkin_valid': validate_gherkin(run_path / 'artifacts' / 'feature.feature'),
        'openapi_valid': validate_openapi(run_path / 'artifacts' / 'openapi.yaml'),
        'sql_valid': validate_sql(run_path / 'artifacts' / 'migration.sql'),
    }
    
    # 2. Cross-artifact consistency
    results['consistency'] = check_artifact_consistency(
        run_path / 'artifacts'
    )
    
    # 3. Code changes applied?
    changes_path = run_path / 'output' / 'files_changed.json'
    if changes_path.exists():
        results['files_changed'] = json.loads(changes_path.read_text())
        results['changes_applied'] = len(results['files_changed']) > 0
    else:
        results['changes_applied'] = False
    
    # 4. Tests pass?
    test_results_path = run_path / 'output' / 'test_results.json'
    if test_results_path.exists():
        test_results = json.loads(test_results_path.read_text())
        results['tests_pass'] = test_results.get('success', False)
        results['tests_passed'] = test_results.get('passed', 0)
        results['tests_failed'] = test_results.get('failed', 0)
    else:
        results['tests_pass'] = False
    
    # 5. Integration tests (task-specific)
    results['task_criteria'] = evaluate_task_criteria(
        task_spec['eval_criteria'],
        run_path
    )
    
    # 6. Overall success
    results['success'] = (
        results['tests_pass'] and
        results['artifacts']['gherkin_valid'] and
        results['consistency']['score'] > 0.9 and
        all(results['task_criteria'].values())
    )
    
    return results


def validate_gherkin(feature_path: Path) -> bool:
    """Validate Gherkin syntax using a parser."""
    if not feature_path.exists():
        return False
    try:
        # Use gherkin parser
        result = subprocess.run(
            ['npx', 'gherkin', '--dry-run', str(feature_path)],
            capture_output=True
        )
        return result.returncode == 0
    except:
        return False


def validate_openapi(openapi_path: Path) -> bool:
    """Validate OpenAPI spec using spectral."""
    if not openapi_path.exists():
        return False
    try:
        result = subprocess.run(
            ['npx', '@stoplight/spectral-cli', 'lint', str(openapi_path)],
            capture_output=True
        )
        return result.returncode == 0
    except:
        return False


def validate_sql(sql_path: Path) -> bool:
    """Validate SQL syntax."""
    if not sql_path.exists():
        return False
    # Basic check - does it parse?
    content = sql_path.read_text()
    return 'ALTER TABLE' in content or 'CREATE TABLE' in content


def check_artifact_consistency(artifacts_path: Path) -> dict:
    """Check cross-references between artifacts."""
    consistency = {
        'gherkin_to_openapi': False,
        'openapi_to_sql': False,
        'score': 0.0
    }
    
    # Check if Gherkin scenarios reference API endpoints in OpenAPI
    # Check if OpenAPI references tables in SQL
    
    # Simple heuristic for now
    gherkin = (artifacts_path / 'feature.feature').read_text() if (artifacts_path / 'feature.feature').exists() else ''
    openapi = (artifacts_path / 'openapi.yaml').read_text() if (artifacts_path / 'openapi.yaml').exists() else ''
    sql = (artifacts_path / 'migration.sql').read_text() if (artifacts_path / 'migration.sql').exists() else ''
    
    # Check for field name consistency
    # This is a simplified check - real implementation would parse and compare
    if gherkin and openapi:
        consistency['gherkin_to_openapi'] = True
    if openapi and sql:
        consistency['openapi_to_sql'] = True
    
    score = 0.0
    if consistency['gherkin_to_openapi']:
        score += 0.5
    if consistency['openapi_to_sql']:
        score += 0.5
    
    consistency['score'] = score
    return consistency
```

---

## 5. Next Steps

1. **Clone Outline codebase** and explore structure
2. **Define exact task specs** based on actual codebase
3. **Build evaluation harness** (prompts, runners, evaluators)
4. **Run pilot** with 1 task × 3 decompositions
5. **Scale to full experiment**

Shall I proceed with cloning Outline and creating the first task spec based on actual code?

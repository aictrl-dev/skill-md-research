# Task Spec: Add Document Creation Wizard

**Task ID**: outline_uiflow_001
**Type**: UI Flow
**Codebase**: outline/outline
**Difficulty**: Medium
**Estimated Steps**: 5

---

## Description

Add a multi-step document creation wizard:
1. **Step 1**: Choose template (blank, meeting notes, spec, etc.)
2. **Step 2**: Set title and select parent collection
3. **Step 3**: Configure permissions (team, private, specific users)
4. **Step 4**: Review and create

Include:
- Progress indicator showing current step
- Back/forward navigation with state preservation
- Template preview on hover
- Skip option to create without template

---

## Current State

### Existing Components

| Component | Location | Relevance |
|-----------|----------|-----------|
| `DocumentNew` | `app/scenes/DocumentNew/` | New document page |
| `Template` model | `server/models/Template.ts` | Template support exists |
| `Collection` selector | `app/components/` | Collection picker exists |
| `Button`, `Input` | `app/components/` | UI primitives |

### Files to Modify

| File | Purpose |
|------|---------|
| `app/scenes/DocumentNew/components.tsx` | Add wizard components |
| `app/stores/UiStore.ts` | Add wizard state |
| `app/scenes/DocumentNew/index.tsx` | Integrate wizard |

### Files to Create

| File | Purpose |
|------|---------|
| `app/components/DocumentWizard/Step1Templates.tsx` | Template selection |
| `app/components/DocumentWizard/Step2Details.tsx` | Title and collection |
| `app/components/DocumentWizard/Step3Permissions.tsx` | Permissions config |
| `app/components/DocumentWizard/Step4Review.tsx` | Review and create |
| `app/components/DocumentWizard/index.tsx` | Wizard container |
| `app/stores/DocumentWizardStore.ts` | Wizard state management |

---

## Implementation Details

### Step 1: DocumentWizardStore

```typescript
// app/stores/DocumentWizardStore.ts
import { observable, action, computed, makeObservable } from "mobx";
import Collection from "./Collection";
import Template from "./Template";

type PermissionLevel = "team" | "private" | "specific";

interface WizardState {
  currentStep: number;
  selectedTemplate: Template | null;
  title: string;
  collectionId: string | null;
  permissionLevel: PermissionLevel;
  selectedUserIds: string[];
}

class DocumentWizardStore {
  @observable currentStep = 1;
  @observable selectedTemplate: Template | null = null;
  @observable title = "";
  @observable collectionId: string | null = null;
  @observable permissionLevel: PermissionLevel = "team";
  @observable selectedUserIds: string[] = [];
  @observable isSubmitting = false;

  constructor() {
    makeObservable(this);
  }

  @computed
  get canProceed(): boolean {
    switch (this.currentStep) {
      case 1:
        return true; // Can always proceed (skip template)
      case 2:
        return this.title.trim().length > 0 && this.collectionId !== null;
      case 3:
        return true;
      case 4:
        return true;
      default:
        return false;
    }
  }

  @computed
  get totalSteps(): number {
    return 4;
  }

  @action
  setTemplate(template: Template | null) {
    this.selectedTemplate = template;
    if (template && !this.title) {
      this.title = template.title;
    }
  }

  @action
  setTitle(title: string) {
    this.title = title;
  }

  @action
  setCollection(collectionId: string) {
    this.collectionId = collectionId;
  }

  @action
  setPermissionLevel(level: PermissionLevel) {
    this.permissionLevel = level;
  }

  @action
  toggleUser(userId: string) {
    if (this.selectedUserIds.includes(userId)) {
      this.selectedUserIds = this.selectedUserIds.filter(id => id !== userId);
    } else {
      this.selectedUserIds = [...this.selectedUserIds, userId];
    }
  }

  @action
  nextStep() {
    if (this.currentStep < this.totalSteps && this.canProceed) {
      this.currentStep += 1;
    }
  }

  @action
  prevStep() {
    if (this.currentStep > 1) {
      this.currentStep -= 1;
    }
  }

  @action
  goToStep(step: number) {
    if (step >= 1 && step <= this.totalSteps) {
      this.currentStep = step;
    }
  }

  @action
  reset() {
    this.currentStep = 1;
    this.selectedTemplate = null;
    this.title = "";
    this.collectionId = null;
    this.permissionLevel = "team";
    this.selectedUserIds = [];
    this.isSubmitting = false;
  }

  @action
  async submit(): Promise<{ documentId: string } | null> {
    this.isSubmitting = true;
    try {
      // Call API to create document
      const response = await client.post("/documents.create", {
        title: this.title,
        text: this.selectedTemplate?.text || "",
        collectionId: this.collectionId,
        publish: true,
        // Handle permissions based on permissionLevel
      });
      
      return { documentId: response.data.id };
    } catch (error) {
      console.error("Failed to create document", error);
      return null;
    } finally {
      this.isSubmitting = false;
    }
  }
}

export default DocumentWizardStore;
```

### Step 2: Wizard Container

```typescript
// app/components/DocumentWizard/index.tsx
import React from "react";
import styled from "styled-components";
import { observer } from "mobx-react";
import DocumentWizardStore from "~/stores/DocumentWizardStore";
import Step1Templates from "./Step1Templates";
import Step2Details from "./Step2Details";
import Step3Permissions from "./Step3Permissions";
import Step4Review from "./Step4Review";
import Button from "~/components/Button";
import Progress from "~/components/Progress";

const Container = styled.div`
  max-width: 800px;
  margin: 0 auto;
  padding: 40px 20px;
`;

const Header = styled.div`
  margin-bottom: 32px;
`;

const Title = styled.h1`
  font-size: 24px;
  font-weight: 600;
  margin-bottom: 8px;
`;

const Navigation = styled.div`
  display: flex;
  justify-content: space-between;
  margin-top: 32px;
  padding-top: 24px;
  border-top: 1px solid ${(props) => props.theme.divider};
`;

const StepContainer = styled.div`
  min-height: 400px;
`;

interface Props {
  onComplete: (documentId: string) => void;
  onCancel: () => void;
}

const DocumentWizard: React.FC<Props> = observer(({ onComplete, onCancel }) => {
  const store = React.useMemo(() => new DocumentWizardStore(), []);

  const handleNext = () => {
    if (store.currentStep === store.totalSteps) {
      store.submit().then((result) => {
        if (result) {
          onComplete(result.documentId);
        }
      });
    } else {
      store.nextStep();
    }
  };

  const renderStep = () => {
    switch (store.currentStep) {
      case 1:
        return <Step1Templates store={store} />;
      case 2:
        return <Step2Details store={store} />;
      case 3:
        return <Step3Permissions store={store} />;
      case 4:
        return <Step4Review store={store} />;
      default:
        return null;
    }
  };

  const stepLabels = ["Template", "Details", "Permissions", "Review"];

  return (
    <Container>
      <Header>
        <Title>Create New Document</Title>
        <Progress
          steps={stepLabels}
          currentStep={store.currentStep}
          onStepClick={(step) => store.goToStep(step)}
        />
      </Header>

      <StepContainer>{renderStep()}</StepContainer>

      <Navigation>
        <Button
          onClick={store.currentStep === 1 ? onCancel : () => store.prevStep()}
          neutral
        >
          {store.currentStep === 1 ? "Cancel" : "Back"}
        </Button>
        <Button
          onClick={handleNext}
          disabled={!store.canProceed}
          isLoading={store.isSubmitting}
        >
          {store.currentStep === store.totalSteps ? "Create Document" : "Continue"}
        </Button>
      </Navigation>
    </Container>
  );
});

export default DocumentWizard;
```

### Step 3: Template Selection

```typescript
// app/components/DocumentWizard/Step1Templates.tsx
import React from "react";
import styled from "styled-components";
import { observer } from "mobx-react";
import DocumentWizardStore from "~/stores/DocumentWizardStore";
import Template from "~/models/Template";

const Grid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
`;

const TemplateCard = styled.button<{ $selected: boolean }>`
  padding: 20px;
  border: 2px solid ${(props) =>
    props.$selected ? props.theme.accent : props.theme.border};
  border-radius: 8px;
  background: ${(props) => props.theme.background};
  cursor: pointer;
  text-align: left;
  transition: all 0.2s;

  &:hover {
    border-color: ${(props) => props.theme.accent};
  }
`;

const TemplateIcon = styled.div`
  font-size: 32px;
  margin-bottom: 12px;
`;

const TemplateTitle = styled.div`
  font-weight: 600;
  margin-bottom: 4px;
`;

const TemplateDescription = styled.div`
  font-size: 13px;
  color: ${(props) => props.theme.textSecondary};
`;

const BlankCard = styled(TemplateCard)`
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 120px;
`;

const SkipNote = styled.p`
  font-size: 14px;
  color: ${(props) => props.theme.textSecondary};
  text-align: center;
`;

interface Props {
  store: DocumentWizardStore;
}

const Step1Templates: React.FC<Props> = observer(({ store }) => {
  const [templates, setTemplates] = React.useState<Template[]>([]);

  React.useEffect(() => {
    // Fetch templates
    client.post("/templates.list").then((response) => {
      setTemplates(response.data);
    });
  }, []);

  const defaultTemplates = [
    { id: "blank", title: "Blank Document", icon: "📄", description: "Start from scratch" },
    { id: "meeting", title: "Meeting Notes", icon: "📝", description: "Agenda and action items" },
    { id: "spec", title: "Feature Spec", icon: "📋", description: "Technical specification" },
    { id: "retro", title: "Retrospective", icon: "🔄", description: "Team retrospective" },
  ];

  return (
    <div>
      <h2>Choose a Template</h2>
      <p>Select a template to get started, or create a blank document.</p>

      <Grid>
        {defaultTemplates.map((template) => (
          <TemplateCard
            key={template.id}
            $selected={store.selectedTemplate?.id === template.id}
            onClick={() => store.setTemplate(template as any)}
          >
            <TemplateIcon>{template.icon}</TemplateIcon>
            <TemplateTitle>{template.title}</TemplateTitle>
            <TemplateDescription>{template.description}</TemplateDescription>
          </TemplateCard>
        ))}

        {templates.map((template) => (
          <TemplateCard
            key={template.id}
            $selected={store.selectedTemplate?.id === template.id}
            onClick={() => store.setTemplate(template)}
          >
            <TemplateIcon>{template.icon || "📄"}</TemplateIcon>
            <TemplateTitle>{template.title}</TemplateTitle>
            <TemplateDescription>Custom template</TemplateDescription>
          </TemplateCard>
        ))}
      </Grid>

      <SkipNote>
        You can skip this step to create a blank document.
      </SkipNote>
    </div>
  );
});

export default Step1Templates;
```

### Step 4: Details Form

```typescript
// app/components/DocumentWizard/Step2Details.tsx
import React from "react";
import styled from "styled-components";
import { observer } from "mobx-react";
import DocumentWizardStore from "~/stores/DocumentWizardStore";
import Input from "~/components/Input";
import Select from "~/components/Select";
import Collection from "~/models/Collection";

const Form = styled.div`
  display: flex;
  flex-direction: column;
  gap: 24px;
`;

const FormGroup = styled.div`
  display: flex;
  flex-direction: column;
  gap: 8px;
`;

const Label = styled.label`
  font-weight: 500;
`;

const HelpText = styled.span`
  font-size: 13px;
  color: ${(props) => props.theme.textSecondary};
`;

interface Props {
  store: DocumentWizardStore;
}

const Step2Details: React.FC<Props> = observer(({ store }) => {
  const [collections, setCollections] = React.useState<Collection[]>([]);

  React.useEffect(() => {
    client.post("/collections.list").then((response) => {
      setCollections(response.data);
    });
  }, []);

  return (
    <div>
      <h2>Document Details</h2>
      <p>Give your document a title and choose where to save it.</p>

      <Form>
        <FormGroup>
          <Label>Title</Label>
          <Input
            value={store.title}
            onChange={(e) => store.setTitle(e.target.value)}
            placeholder="Enter document title"
            autoFocus
          />
          <HelpText>A clear, descriptive title for your document.</HelpText>
        </FormGroup>

        <FormGroup>
          <Label>Collection</Label>
          <Select
            value={store.collectionId || ""}
            onChange={(e) => store.setCollection(e.target.value)}
            placeholder="Select a collection"
          >
            {collections.map((collection) => (
              <option key={collection.id} value={collection.id}>
                {collection.name}
              </option>
            ))}
          </Select>
          <HelpText>The collection where this document will be saved.</HelpText>
        </FormGroup>
      </Form>
    </div>
  );
});

export default Step2Details;
```

### Step 5: Review Step

```typescript
// app/components/DocumentWizard/Step4Review.tsx
import React from "react";
import styled from "styled-components";
import { observer } from "mobx-react";
import DocumentWizardStore from "~/stores/DocumentWizardStore";

const Summary = styled.div`
  background: ${(props) => props.theme.backgroundSecondary};
  border-radius: 8px;
  padding: 24px;
`;

const SummaryItem = styled.div`
  display: flex;
  justify-content: space-between;
  padding: 12px 0;
  border-bottom: 1px solid ${(props) => props.theme.divider};

  &:last-child {
    border-bottom: none;
  }
`;

const Label = styled.span`
  color: ${(props) => props.theme.textSecondary};
`;

const Value = styled.span`
  font-weight: 500;
`;

interface Props {
  store: DocumentWizardStore;
}

const Step4Review: React.FC<Props> = observer(({ store }) => {
  const permissionLabels = {
    team: "Everyone on the team",
    private: "Only me",
    specific: "Selected users",
  };

  return (
    <div>
      <h2>Review & Create</h2>
      <p>Review your document settings before creating.</p>

      <Summary>
        <SummaryItem>
          <Label>Template</Label>
          <Value>{store.selectedTemplate?.title || "Blank document"}</Value>
        </SummaryItem>
        <SummaryItem>
          <Label>Title</Label>
          <Value>{store.title || "Untitled"}</Value>
        </SummaryItem>
        <SummaryItem>
          <Label>Collection</Label>
          <Value>{/* Collection name */}</Value>
        </SummaryItem>
        <SummaryItem>
          <Label>Permissions</Label>
          <Value>{permissionLabels[store.permissionLevel]}</Value>
        </SummaryItem>
      </Summary>

      <p style={{ marginTop: 16, color: "gray" }}>
        Click "Create Document" to finish. You can edit these settings later.
      </p>
    </div>
  );
});

export default Step4Review;
```

---

## Test Cases

```typescript
// app/components/DocumentWizard/index.test.tsx

import { render, screen, fireEvent } from "@testing-library/react";
import DocumentWizard from "./index";

describe("DocumentWizard", () => {
  it("should render step 1 (templates) initially", () => {
    render(<DocumentWizard onComplete={jest.fn()} onCancel={jest.fn()} />);
    
    expect(screen.getByText("Choose a Template")).toBeInTheDocument();
  });

  it("should navigate to next step on Continue click", async () => {
    render(<DocumentWizard onComplete={jest.fn()} onCancel={jest.fn()} />);
    
    fireEvent.click(screen.getByText("Continue"));
    
    expect(screen.getByText("Document Details")).toBeInTheDocument();
  });

  it("should preserve state when navigating back", async () => {
    render(<DocumentWizard onComplete={jest.fn()} onCancel={jest.fn()} />);
    
    // Select template
    fireEvent.click(screen.getByText("Meeting Notes"));
    
    // Go to next step
    fireEvent.click(screen.getByText("Continue"));
    
    // Go back
    fireEvent.click(screen.getByText("Back"));
    
    // Template should still be selected
    expect(screen.getByText("Meeting Notes").closest("button")).toHaveStyle(
      "border-color: accent"
    );
  });

  it("should disable Continue if required fields missing", async () => {
    render(<DocumentWizard onComplete={jest.fn()} onCancel={jest.fn()} />);
    
    // Go to step 2 (details)
    fireEvent.click(screen.getByText("Continue"));
    fireEvent.click(screen.getByText("Continue"));
    
    // Continue should be disabled without title
    expect(screen.getByText("Continue")).toBeDisabled();
  });

  it("should call onComplete after final step", async () => {
    const onComplete = jest.fn();
    render(<DocumentWizard onComplete={onComplete} onCancel={jest.fn()} />);
    
    // Skip template
    fireEvent.click(screen.getByText("Continue"));
    
    // Fill details
    fireEvent.change(screen.getByPlaceholderText("Enter document title"), {
      target: { value: "Test Document" },
    });
    fireEvent.change(screen.getByPlaceholderText("Select a collection"), {
      target: { value: "collection-1" },
    });
    
    // Continue through steps
    fireEvent.click(screen.getByText("Continue"));
    fireEvent.click(screen.getByText("Continue"));
    fireEvent.click(screen.getByText("Create Document"));
    
    // Should call onComplete
    await waitFor(() => {
      expect(onComplete).toHaveBeenCalled();
    });
  });
});
```

---

## Evaluation Criteria

| Criterion | How to Verify | Pass Condition |
|-----------|---------------|----------------|
| Wizard renders | Visual / unit test | 4 steps displayed |
| Progress indicator | Visual | Shows current step |
| Navigation works | Click test | Back/Forward work |
| State preserved | Navigation test | Selections kept |
| Document created | Integration test | Document in database |
| Tests pass | `yarn test:app` | All tests pass |

---

## Decomposition Variants

### Stack (Predicted: Low)

```
Step 1: Store - Create DocumentWizardStore
Step 2: Components - Create step components
Step 3: Integration - Wire to existing DocumentNew
Step 4: UI - Add styling and polish
Step 5: Tests - Add component tests
```

### Domain (Predicted: Low)

```
Step 1: Define WizardStep value object
Step 2: Define DocumentDraft aggregate
Step 3: Build UI on top
Step 4: Wire to API
Step 5: Tests
```

### Journey (Predicted: Best)

```
Step 1: User clicks "New document" → Show wizard modal/page
Step 2: User selects template → System stores selection, shows preview
Step 3: User enters title/collection → System validates, enables continue
Step 4: User configures permissions → System shows options
Step 5: User reviews and creates → System creates document, navigates
```

---

## Commands

```bash
# Run tests
yarn test:app app/components/DocumentWizard/

# Type check
yarn tsc

# Lint
yarn lint

# Build
yarn build
```

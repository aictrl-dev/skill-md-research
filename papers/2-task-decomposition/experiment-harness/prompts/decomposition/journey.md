# Journey Decomposition Strategy

Decompose the task by **user journey/action**, following the user's perspective:

## Journey Structure

1. Identify the user actions required
2. Map each action to system behavior
3. Ensure flow is complete and coherent
4. Add error handling at each step

## Principles

- Think from the user's perspective
- Each step is a user-visible action
- Actions should feel natural and sequential
- Preserve state between steps
- Handle user errors gracefully

## Step Template

```
Step N: [User Action]
Actor: [Who performs this action]
Trigger: [What initiates this action]
System Response: [What the system does]
Success Criteria: [How user knows it worked]
Error Handling: [What happens on failure]
```

## Example

For "Add document template wizard":

```
Step 1: User clicks "New from template"
  Actor: Content author
  Trigger: User wants to create document from template
  System Response: Show template gallery
  Success Criteria: Templates displayed with previews
  Error Handling: Show empty state if no templates

Step 2: User selects a template
  Actor: Content author
  Trigger: User clicks on template card
  System Response: Navigate to step 2, remember template
  Success Criteria: Template highlighted, can proceed
  Error Handling: Template load error → retry

Step 3: User enters title and selects collection
  Actor: Content author
  Trigger: Template selected
  System Response: Show form with template name as default
  Success Criteria: Title entered, collection selected
  Error Handling: Validation errors shown inline

Step 4: User reviews and creates
  Actor: Content author
  Trigger: Form complete
  System Response: Show preview, create button
  Success Criteria: Document created from template
  Error Handling: Creation error → retry with form state preserved

Step 5: User sees created document
  Actor: Content author
  Trigger: Document created
  System Response: Navigate to document editor
  Success Criteria: Document content matches template
  Error Handling: Redirect to documents list
```

## When to Use

- Multi-step user flows
- Wizard-style interfaces
- User onboarding
- Complex form interactions
- E-commerce checkout flows

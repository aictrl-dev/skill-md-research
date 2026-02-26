# Task Spec: Add Slack Webhook Notification

**Task ID**: outline_integration_001
**Type**: Integration
**Codebase**: outline/outline
**Difficulty**: Medium
**Estimated Steps**: 5

---

## Description

Add ability to share documents to Slack via webhook:
1. Configure Slack webhook URL per team
2. Share document to a Slack channel via webhook
3. Message includes: document title, excerpt, author, link
4. Handle webhook errors gracefully
5. Rate limit notifications (max 10/minute)

---

## Current State

### Existing Integration System

| Model | Location | Relevance |
|-------|----------|-----------|
| `Integration` | `server/models/Integration.ts` | Generic integration model |
| `IntegrationAuthentication` | `server/models/IntegrationAuthentication.ts` | Auth credentials |
| `IntegrationType` | `@shared/types` | POST, embeddings, etc. |
| `IntegrationService` | `@shared/types` | Slack, GitHub, etc. |

### Existing Slack Integration

Outline already has Slack integration for:
- Authentication (OAuth)
- Search
- Notifications (via Integration model)

### Files to Modify

| File | Purpose |
|------|---------|
| `server/models/Integration.ts` | Add slack_webhook settings type |
| `server/routes/api/documents/documents.ts` | Add share endpoint |
| `shared/types.ts` | Add SlackWebhookIntegrationSettings |

### Files to Create

| File | Purpose |
|------|---------|
| `server/services/SlackWebhookService.ts` | Webhook posting logic |

---

## Implementation Details

### Step 1: Define Types

```typescript
// shared/types.ts

// Add to IntegrationSettings union
export interface SlackWebhookIntegrationSettings {
  url: string;           // Webhook URL
  channel?: string;      // Default channel (optional)
  enabled: boolean;
}

// Add to IntegrationService enum if not exists
export enum IntegrationService {
  // ... existing
  SlackWebhook = "slack-webhook",
}
```

### Step 2: SlackWebhookService

```typescript
// server/services/SlackWebhookService.ts
import fetch from "node-fetch";
import Logger from "@server/logging/Logger";
import { IntegrationService } from "@shared/types";
import Integration from "@server/models/Integration";
import Document from "@server/models/Document";
import { rateLimiter } from "@server/utils/RateLimiter";

interface ShareOptions {
  document: Document;
  channel: string;
  message?: string;
  webhookUrl: string;
}

interface SlackMessage {
  text: string;
  blocks?: unknown[];
  channel?: string;
}

class SlackWebhookService {
  /**
   * Share a document to Slack via webhook.
   */
  static async shareToSlack(options: ShareOptions): Promise<{ success: boolean; error?: string }> {
    const { document, channel, message, webhookUrl } = options;
    
    // Rate limiting
    const key = `slack-webhook:${document.teamId}`;
    const allowed = await rateLimiter.consume(key, 10, 60); // 10 per minute
    if (!allowed) {
      return { success: false, error: "Rate limit exceeded" };
    }
    
    const slackMessage = this.buildMessage(document, message);
    
    // Override channel if specified
    if (channel) {
      slackMessage.channel = channel;
    }
    
    try {
      const response = await fetch(webhookUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(slackMessage),
      });
      
      if (!response.ok) {
        const text = await response.text();
        Logger.error("Slack webhook failed", { status: response.status, body: text });
        return { success: false, error: `Slack API error: ${response.status}` };
      }
      
      Logger.info("Document shared to Slack", { documentId: document.id, channel });
      return { success: true };
    } catch (error) {
      Logger.error("Slack webhook error", error);
      return { success: false, error: error.message };
    }
  }
  
  /**
   * Build Slack message payload for a document.
   */
  private static buildMessage(document: Document, customMessage?: string): SlackMessage {
    const excerpt = document.text?.slice(0, 300) || "";
    const truncatedExcerpt = excerpt.length < document.text?.length 
      ? excerpt + "..." 
      : excerpt;
    
    return {
      text: customMessage || `Shared a document: ${document.title}`,
      blocks: [
        {
          type: "header",
          text: {
            type: "plain_text",
            text: document.title,
          },
        },
        {
          type: "section",
          text: {
            type: "mrkdwn",
            text: truncatedExcerpt,
          },
        },
        {
          type: "section",
          fields: [
            {
              type: "mrkdwn",
              text: `*Author:*\n${document.createdBy?.name || "Unknown"}`,
            },
            {
              type: "mrkdwn",
              text: `*Link:*\n<${process.env.URL}${document.path}|View Document>`,
            },
          ],
        },
        {
          type: "actions",
          elements: [
            {
              type: "button",
              text: {
                type: "plain_text",
                text: "View Document",
              },
              url: `${process.env.URL}${document.path}`,
            },
          ],
        },
      ],
    };
  }
  
  /**
   * Get Slack webhook integration for a team.
   */
  static async getIntegration(teamId: string): Promise<Integration | null> {
    return Integration.findOne({
      where: {
        teamId,
        service: IntegrationService.SlackWebhook,
      },
    });
  }
}

export default SlackWebhookService;
```

### Step 3: API Endpoint

```typescript
// server/routes/api/documents/documents.ts

// Add schema
const DocumentsShareSchema = z.object({
  id: z.string().uuid(),
  channel: z.string().optional(),
  message: z.string().max(500).optional(),
});

// Add endpoint
router.post(
  "documents.share",
  auth(),
  rateLimiter(RateLimiterStrategy.TenPerMinute),
  validate(DocumentsShareSchema),
  async (ctx: APIContext) => {
    const { id, channel, message } = ctx.input;
    const { user } = ctx.state;
    
    const document = await Document.findByPk(id, {
      include: [
        { model: User, as: "createdBy" },
      ],
    });
    
    if (!document) {
      throw NotFoundError("Document not found");
    }
    
    authorize(user, "read", document);
    
    // Get Slack webhook integration
    const integration = await SlackWebhookService.getIntegration(user.teamId);
    
    if (!integration) {
      throw ValidationError("Slack webhook not configured for this team");
    }
    
    const settings = integration.settings as SlackWebhookIntegrationSettings;
    
    if (!settings.enabled) {
      throw ValidationError("Slack sharing is disabled");
    }
    
    const result = await SlackWebhookService.shareToSlack({
      document,
      channel: channel || settings.channel,
      message,
      webhookUrl: settings.url,
    });
    
    if (!result.success) {
      throw ValidationError(result.error || "Failed to share to Slack");
    }
    
    ctx.body = {
      success: true,
      message: "Document shared to Slack",
    };
  }
);
```

### Step 4: Integration Setup Endpoint

```typescript
// server/routes/api/integrations/integrations.ts

router.post(
  "integrations.slack_webhook",
  auth({ role: UserRole.Admin }),
  validate(T.CreateSlackWebhookSchema),
  async (ctx: APIContext) => {
    const { url, channel } = ctx.input;
    const { user } = ctx.state;
    
    // Validate webhook URL format
    if (!url.startsWith("https://hooks.slack.com/")) {
      throw ValidationError("Invalid Slack webhook URL");
    }
    
    // Test the webhook
    const testResult = await SlackWebhookService.testWebhook(url);
    if (!testResult.success) {
      throw ValidationError("Webhook test failed: " + testResult.error);
    }
    
    // Create or update integration
    const [integration] = await Integration.upsert({
      teamId: user.teamId,
      service: IntegrationService.SlackWebhook,
      type: IntegrationType.Post,
      settings: {
        url,
        channel,
        enabled: true,
      },
      userId: user.id,
    });
    
    ctx.body = {
      data: {
        id: integration.id,
        service: integration.service,
        settings: {
          channel: integration.settings.channel,
          enabled: integration.settings.enabled,
          // Don't return full URL for security
        },
      },
    };
  }
);
```

### Step 5: Update UI (Optional)

Add share button to document actions:

```typescript
// app/components/DocumentMenu.tsx

<DropdownMenuItem onClick={handleShareToSlack}>
  Share to Slack
</DropdownMenuItem>
```

---

## Test Cases

```typescript
// server/services/SlackWebhookService.test.ts

import SlackWebhookService from "./SlackWebhookService";
import { buildDocument, buildUser, buildTeam } from "@server/test/factories";

describe("SlackWebhookService", () => {
  describe("shareToSlack", () => {
    it("should post message to Slack webhook", async () => {
      const user = await buildUser();
      const document = await buildDocument({
        userId: user.id,
        teamId: user.teamId,
        text: "Test document content for sharing",
      });
      
      // Mock fetch
      const mockFetch = jest.fn().mockResolvedValue({
        ok: true,
        text: () => Promise.resolve("ok"),
      });
      global.fetch = mockFetch;
      
      const result = await SlackWebhookService.shareToSlack({
        document,
        channel: "#general",
        webhookUrl: "https://hooks.slack.com/services/test",
      });
      
      expect(result.success).toBe(true);
      expect(mockFetch).toHaveBeenCalledWith(
        "https://hooks.slack.com/services/test",
        expect.objectContaining({
          method: "POST",
        })
      );
    });

    it("should include document title in message", async () => {
      const document = await buildDocument({ title: "My Document" });
      
      const message = SlackWebhookService["buildMessage"](document);
      
      expect(message.text).toContain("My Document");
      expect(message.blocks[0].text.text).toBe("My Document");
    });

    it("should truncate long excerpts", async () => {
      const longText = "x".repeat(500);
      const document = await buildDocument({ text: longText });
      
      const message = SlackWebhookService["buildMessage"](document);
      const blockText = message.blocks[1].text.text;
      
      expect(blockText.length).toBeLessThanOrEqual(303); // 300 + "..."
    });

    it("should handle webhook errors", async () => {
      const document = await buildDocument();
      
      global.fetch = jest.fn().mockResolvedValue({
        ok: false,
        status: 400,
        text: () => Promise.resolve("Bad request"),
      });
      
      const result = await SlackWebhookService.shareToSlack({
        document,
        channel: "#general",
        webhookUrl: "https://hooks.slack.com/services/test",
      });
      
      expect(result.success).toBe(false);
      expect(result.error).toContain("400");
    });
  });

  describe("rate limiting", () => {
    it("should enforce rate limit of 10 per minute", async () => {
      // Test rate limiter behavior
    });
  });
});
```

---

## Evaluation Criteria

| Criterion | How to Verify | Pass Condition |
|-----------|---------------|----------------|
| Webhook posts to Slack | Mock test / real webhook | 200 response |
| Message format correct | Check Slack message | Title, excerpt, link present |
| Rate limiting works | 11th request blocked | 429 response |
| Error handling | Invalid webhook URL | Graceful error message |
| Integration stored | Query database | Integration record exists |
| Tests pass | `yarn test` | All tests pass |

---

## Decomposition Variants

### Stack (Predicted: Best)

```
Step 1: Service - Create SlackWebhookService with shareToSlack
Step 2: Types - Add SlackWebhookIntegrationSettings
Step 3: API - Add POST /documents.share endpoint
Step 4: API - Add POST /integrations.slack_webhook setup endpoint
Step 5: Tests - Add service and API tests
```

### Domain (Predicted: Medium)

```
Step 1: Define ShareChannel interface
Step 2: Implement SlackChannel (implements ShareChannel)
Step 3: Wire to Document.share() method
Step 4: Expose via API
Step 5: Add tests
```

### Journey (Predicted: Low)

```
Step 1: Admin configures webhook (settings page)
Step 2: User clicks "Share to Slack" on document
Step 3: System validates, posts to webhook
Step 4: User sees success message
```

---

## Commands

```bash
# Run tests
yarn test server/services/SlackWebhookService.test.ts
yarn test server/routes/api/documents/documents.test.ts

# Type check
yarn tsc
```

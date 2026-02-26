[0m
> build · glm-4.7
[0m
I'll implement the document approval workflow based on Outline's existing patterns. Here's the complete code for each file:

**server/migrations/20240101000000-add-approval-state.ts**
```typescript
module.exports = {
  up: async (queryInterface, Sequelize) => {
    await queryInterface.addColumn("documents", "approvalState", {
      type: Sequelize.ENUM("draft", "pending_approval", "approved", "rejected"),
      allowNull: false,
      defaultValue: "draft",
    });

    await queryInterface.sequelize.query(`
      CREATE INDEX index_documents_on_approval_state ON documents(approvalState);
    `);
  },

  down: async (queryInterface, Sequelize) => {
    await queryInterface.sequelize.query(`
      DROP INDEX index_documents_on_approval_state;
    `);
    await queryInterface.removeColumn("documents", "approvalState");
  },
};
```

**server/models/Document.ts**
```typescript
import { DataTypes, Model } from "sequelize";

export class Document extends Model {
  static get VALID_STATES() {
    return ["draft", "pending_approval", "approved", "rejected"];
  }

  async submitForApproval(actorId: string) {
    if (this.approvalState !== "draft") {
      throw new Error("Only draft documents can be submitted for approval");
    }
    await this.update({
      approvalState: "pending_approval",
      lastModifiedById: actorId,
    });
  }

  async approve(actorId: string) {
    if (this.approvalState !== "pending_approval") {
      throw new Error("Only pending approval documents can be approved");
    }
    await this.update({
      approvalState: "approved",
      publishedAt: new Date(),
      lastModifiedById: actorId,
    });
  }

  async reject(actorId: string) {
    if (this.approvalState !== "pending_approval") {
      throw new Error("Only pending approval documents can be rejected");
    }
    await this.update({
      approvalState: "rejected",
      lastModifiedById: actorId,
    });
  }
}
```

**server/routes/api/documents/approval.ts**
```typescript
import Router from "koa-router";
import documentPresenter from "../../../presenters/document";
import { authorize } from "../../../middlewares/authorization";
import { Document } from "../../../models";

const router = new Router();

router.post(
  ":id/approve",
  authorize(),
  async (ctx) => {
    const document = await Document.findByPk(ctx.params.id);
    if (!document) {
      ctx.throw(404, "Document not found");
    }
    await document.approve(ctx.state.user.id);
    ctx.body = {
      success: true,
      data: documentPresenter(document),
    };
  }
);

router.post(
  ":id/reject",
  authorize(),
  async (ctx) => {
    const document = await Document.findByPk(ctx.params.id);
    if (!document) {
      ctx.throw(404, "Document not found");
    }
    await document.reject(ctx.state.user.id);
    ctx.body = {
      success: true,
      data: documentPresenter(document),
    };
  }
);

export default router;
```

**server/presenters/document.ts**
```typescript
export default function documentPresenter(document: any) {
  return {
    id: document.id,
    url: document.url,
    title: document.title,
    text: document.text,
    approvalState: document.approvalState,
    publishedAt: document.publishedAt,
    createdAt: document.createdAt,
    updatedAt: document.updatedAt,
    createdBy: {
      id: document.createdById,
      name: document.createdBy?.name,
      avatarUrl: document.createdBy?.avatarUrl,
    },
    updatedBy: {
      id: document.lastModifiedById,
      name: document.updatedBy?.name,
      avatarUrl: document.updatedBy?.avatarUrl,
    },
  };
}
```

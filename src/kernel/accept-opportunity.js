import {
  ACCEPT_DECISION,
  NORMAL_DECISION_CHANNEL,
  assertApprovalSet,
  requireText,
} from "./contracts.js";
import { IdempotencyConflictError, KernelInvariantError } from "./errors.js";
import { assertTransactionPort, assertUnitOfWork } from "./ports.js";

function assertReplayMatches(existing, command) {
  const matches =
    existing.tenantId === command.tenantId &&
    existing.targetId === command.opportunityId &&
    existing.decision === ACCEPT_DECISION &&
    existing.evidenceVersion === command.evidenceVersion;

  if (!matches) {
    throw new IdempotencyConflictError(
      "idempotency key was already used for a different acceptance intent",
    );
  }
}

export async function acceptOpportunity({ command, approvalSet, unitOfWork }) {
  assertApprovalSet(approvalSet);
  assertUnitOfWork(unitOfWork);

  const tenantId = requireText(command?.tenantId, "command.tenantId");
  const opportunityId = requireText(command?.opportunityId, "command.opportunityId");
  const idempotencyKey = requireText(command?.idempotencyKey, "command.idempotencyKey");
  const evidenceVersion = requireText(command?.evidenceVersion, "command.evidenceVersion");
  const founderIdentity = requireText(command?.founderIdentity, "command.founderIdentity");
  const transcriptReference = requireText(
    command?.transcriptReference,
    "command.transcriptReference",
  );
  const decidedAt = requireText(command?.decidedAt, "command.decidedAt");

  if (command.channel !== NORMAL_DECISION_CHANNEL) {
    throw new KernelInvariantError(
      "VOICE_REQUIRED",
      "voice acceptance is the only normal human decision channel",
    );
  }
  if (command.decision !== ACCEPT_DECISION || command.confirmationState !== "CONFIRMED") {
    throw new KernelInvariantError(
      "ACCEPTANCE_NOT_CONFIRMED",
      "acceptance must be explicit and confirmed",
    );
  }
  if (
    command.confidence !== undefined &&
    command.confidence !== null &&
    (typeof command.confidence !== "number" ||
      !Number.isFinite(command.confidence) ||
      command.confidence < 0 ||
      command.confidence > 1)
  ) {
    throw new KernelInvariantError(
      "INVALID_CONTRACT",
      "command.confidence must be a number from 0 to 1 when supplied",
    );
  }
  if (approvalSet.tenantId !== tenantId) {
    throw new KernelInvariantError("TENANT_BOUNDARY_VIOLATION", "tenant does not own approval set");
  }
  if (
    approvalSet.evidenceVersion !== evidenceVersion ||
    command.approvalSetId !== approvalSet.approvalSetId
  ) {
    throw new KernelInvariantError(
      "STALE_APPROVAL_CONTEXT",
      "approval set or evidence version is stale",
    );
  }

  const opportunity = approvalSet.opportunities.find(
    (candidate) => candidate.opportunityId === opportunityId,
  );
  if (!opportunity) {
    throw new KernelInvariantError(
      "OPPORTUNITY_NOT_IN_TOP_FIVE",
      "accepted opportunity must belong to the exact top-five approval set",
    );
  }

  return unitOfWork.execute(async (rawTransaction) => {
    const transaction = assertTransactionPort(rawTransaction);
    const existing = await transaction.findApprovalByIdempotencyKey(tenantId, idempotencyKey);
    if (existing) {
      assertReplayMatches(existing, { tenantId, opportunityId, evidenceVersion });
      return Object.freeze({ replayed: true, approval: existing });
    }

    const conditions = command.conditions ?? [];
    if (!Array.isArray(conditions) || conditions.some((value) => typeof value !== "string")) {
      throw new KernelInvariantError(
        "INVALID_CONTRACT",
        "command.conditions must be an array of strings",
      );
    }

    const approval = Object.freeze({
      approvalId: requireText(command.approvalId, "command.approvalId"),
      tenantId,
      founderIdentity,
      action: "ACCEPT_OPPORTUNITY",
      targetId: opportunityId,
      decision: ACCEPT_DECISION,
      conditions: Object.freeze([...conditions]),
      evidenceVersion,
      timestamp: decidedAt,
      transcriptReference,
      confidence: command.confidence ?? null,
      confirmationState: "CONFIRMED",
      executionStatus: "ACCEPTED",
      channel: NORMAL_DECISION_CHANNEL,
      idempotencyKey,
    });

    const acceptedOpportunity = Object.freeze({
      acceptedOpportunityId: requireText(
        command.acceptedOpportunityId,
        "command.acceptedOpportunityId",
      ),
      tenantId,
      opportunityId,
      approvalId: approval.approvalId,
      approvalSetId: approvalSet.approvalSetId,
      evidenceVersion,
      market: opportunity.market,
      supplierCountry: opportunity.supplierCountry,
      fulfillmentModel: opportunity.fulfillmentModel,
      status: "ACCEPTED",
      acceptedAt: decidedAt,
    });

    const auditEvent = Object.freeze({
      auditEventId: requireText(command.auditEventId, "command.auditEventId"),
      tenantId,
      aggregateType: "opportunity",
      aggregateId: opportunityId,
      eventType: "OPPORTUNITY_ACCEPTED",
      actorType: "FOUNDER",
      actorId: founderIdentity,
      occurredAt: decidedAt,
      evidenceVersion,
      transcriptReference,
      approvalId: approval.approvalId,
      idempotencyKey,
    });

    await transaction.saveApproval(approval);
    await transaction.saveAcceptedOpportunity(acceptedOpportunity);
    await transaction.appendAuditEvent(auditEvent);

    return Object.freeze({
      replayed: false,
      approval,
      acceptedOpportunity,
      auditEvent,
    });
  });
}

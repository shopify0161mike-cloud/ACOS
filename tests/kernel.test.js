import assert from "node:assert/strict";
import test from "node:test";

import {
  IdempotencyConflictError,
  KernelInvariantError,
  acceptOpportunity,
  selectExactTopFive,
} from "../src/kernel/index.js";

function opportunity(index, overrides = {}) {
  return {
    tenantId: "001",
    opportunityId: `opp-${index}`,
    market: index % 2 ? "NL" : "DE",
    supplierCountry: index % 2 ? "CN" : "PL",
    fulfillmentModel: "branded-dropshipping",
    evidenceVersion: "ev-7",
    qualifiedAt: "2026-07-27T18:00:00.000Z",
    executable: true,
    blockers: [],
    capitalEfficiencyScore: 100 - index,
    expectedContributionProfit: 50 - index,
    evidenceConfidence: 0.9,
    ...overrides,
  };
}

function approvalSet() {
  return selectExactTopFive({
    tenantId: "001",
    approvalSetId: "set-1",
    evidenceVersion: "ev-7",
    selectedAt: "2026-07-27T18:05:00.000Z",
    opportunities: Array.from({ length: 7 }, (_, index) => opportunity(index + 1)),
  });
}

function command(overrides = {}) {
  return {
    tenantId: "001",
    approvalSetId: "set-1",
    opportunityId: "opp-1",
    evidenceVersion: "ev-7",
    founderIdentity: "founder-1",
    channel: "voice",
    decision: "ACCEPT",
    confirmationState: "CONFIRMED",
    transcriptReference: "transcript://voice/42",
    confidence: 0.99,
    conditions: [],
    decidedAt: "2026-07-27T18:10:00.000Z",
    idempotencyKey: "001:set-1:opp-1:accept",
    approvalId: "approval-1",
    acceptedOpportunityId: "accepted-1",
    auditEventId: "audit-1",
    ...overrides,
  };
}

class FakeUnitOfWork {
  constructor({ failAudit = false } = {}) {
    this.state = { approvals: [], accepted: [], audits: [] };
    this.failAudit = failAudit;
  }

  async execute(work) {
    const staged = structuredClone(this.state);
    const transaction = {
      findApprovalByIdempotencyKey: async (tenantId, key) =>
        staged.approvals.find(
          (approval) => approval.tenantId === tenantId && approval.idempotencyKey === key,
        ),
      saveApproval: async (approval) => staged.approvals.push(approval),
      saveAcceptedOpportunity: async (accepted) => staged.accepted.push(accepted),
      appendAuditEvent: async (event) => {
        if (this.failAudit) throw new Error("audit unavailable");
        staged.audits.push(event);
      },
    };

    const result = await work(transaction);
    this.state = staged;
    return result;
  }
}

test("selects exactly five executable opportunities deterministically", () => {
  const selected = selectExactTopFive({
    tenantId: "001",
    approvalSetId: "set-1",
    evidenceVersion: "ev-7",
    selectedAt: "2026-07-27T18:05:00.000Z",
    opportunities: [
      opportunity(6),
      opportunity(3),
      opportunity(1),
      opportunity(2),
      opportunity(5),
      opportunity(4),
      opportunity(7, { executable: false }),
      opportunity(8, { tenantId: "002", capitalEfficiencyScore: 999 }),
    ],
  });

  assert.equal(selected.opportunities.length, 5);
  assert.deepEqual(
    selected.opportunities.map(({ opportunityId }) => opportunityId),
    ["opp-1", "opp-2", "opp-3", "opp-4", "opp-5"],
  );
});

test("fails closed when an exact top five cannot be produced", () => {
  assert.throws(
    () =>
      selectExactTopFive({
        tenantId: "001",
        approvalSetId: "set-1",
        evidenceVersion: "ev-7",
        selectedAt: "2026-07-27T18:05:00.000Z",
        opportunities: Array.from({ length: 4 }, (_, index) => opportunity(index + 1)),
      }),
    (error) =>
      error instanceof KernelInvariantError &&
      error.code === "INSUFFICIENT_EXECUTABLE_OPPORTUNITIES",
  );
});

test("rejects an approval set containing mixed evidence versions", () => {
  assert.throws(
    () =>
      selectExactTopFive({
        tenantId: "001",
        approvalSetId: "set-1",
        evidenceVersion: "ev-7",
        selectedAt: "2026-07-27T18:05:00.000Z",
        opportunities: [
          opportunity(1),
          opportunity(2),
          opportunity(3),
          opportunity(4),
          opportunity(5, { evidenceVersion: "ev-6" }),
        ],
      }),
    (error) =>
      error instanceof KernelInvariantError && error.code === "STALE_APPROVAL_CONTEXT",
  );
});

test("persists approval, accepted opportunity, and audit event atomically", async () => {
  const unitOfWork = new FakeUnitOfWork();
  const result = await acceptOpportunity({
    command: command(),
    approvalSet: approvalSet(),
    unitOfWork,
  });

  assert.equal(result.replayed, false);
  assert.equal(unitOfWork.state.approvals.length, 1);
  assert.equal(unitOfWork.state.accepted.length, 1);
  assert.equal(unitOfWork.state.audits.length, 1);
  assert.equal(result.acceptedOpportunity.tenantId, "001");
});

test("rejects non-voice normal acceptance", async () => {
  await assert.rejects(
    acceptOpportunity({
      command: command({ channel: "screen" }),
      approvalSet: approvalSet(),
      unitOfWork: new FakeUnitOfWork(),
    }),
    (error) => error instanceof KernelInvariantError && error.code === "VOICE_REQUIRED",
  );
});

test("replays an identical idempotent acceptance without duplicate writes", async () => {
  const unitOfWork = new FakeUnitOfWork();
  await acceptOpportunity({ command: command(), approvalSet: approvalSet(), unitOfWork });
  const replay = await acceptOpportunity({
    command: command({
      approvalId: "ignored-on-replay",
      acceptedOpportunityId: "ignored-on-replay",
      auditEventId: "ignored-on-replay",
    }),
    approvalSet: approvalSet(),
    unitOfWork,
  });

  assert.equal(replay.replayed, true);
  assert.equal(unitOfWork.state.approvals.length, 1);
  assert.equal(unitOfWork.state.accepted.length, 1);
  assert.equal(unitOfWork.state.audits.length, 1);
});

test("rejects conflicting reuse of an idempotency key", async () => {
  const unitOfWork = new FakeUnitOfWork();
  await acceptOpportunity({ command: command(), approvalSet: approvalSet(), unitOfWork });

  await assert.rejects(
    acceptOpportunity({
      command: command({ opportunityId: "opp-2" }),
      approvalSet: approvalSet(),
      unitOfWork,
    }),
    IdempotencyConflictError,
  );
});

test("does not commit partial state when the audit append fails", async () => {
  const unitOfWork = new FakeUnitOfWork({ failAudit: true });

  await assert.rejects(
    acceptOpportunity({ command: command(), approvalSet: approvalSet(), unitOfWork }),
    /audit unavailable/,
  );
  assert.deepEqual(unitOfWork.state, { approvals: [], accepted: [], audits: [] });
});

import { KernelInvariantError } from "./errors.js";

export const APPROVAL_SET_SIZE = 5;
export const NORMAL_DECISION_CHANNEL = "voice";
export const ACCEPT_DECISION = "ACCEPT";

export function requireText(value, field) {
  if (typeof value !== "string" || value.trim() === "") {
    throw new KernelInvariantError("INVALID_CONTRACT", `${field} must be a non-empty string`);
  }
  return value.trim();
}

export function requireFiniteNumber(value, field) {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    throw new KernelInvariantError("INVALID_CONTRACT", `${field} must be a finite number`);
  }
  return value;
}

export function createQualifiedOpportunity(input) {
  const blockers = input.blockers ?? [];
  if (!Array.isArray(blockers) || blockers.some((value) => typeof value !== "string")) {
    throw new KernelInvariantError("INVALID_CONTRACT", "blockers must be an array of strings");
  }

  return Object.freeze({
    tenantId: requireText(input.tenantId, "tenantId"),
    opportunityId: requireText(input.opportunityId, "opportunityId"),
    market: requireText(input.market, "market"),
    supplierCountry: requireText(input.supplierCountry, "supplierCountry"),
    fulfillmentModel: requireText(input.fulfillmentModel, "fulfillmentModel"),
    evidenceVersion: requireText(input.evidenceVersion, "evidenceVersion"),
    qualifiedAt: requireText(input.qualifiedAt, "qualifiedAt"),
    executable: input.executable === true,
    blockers: Object.freeze([...blockers]),
    capitalEfficiencyScore: requireFiniteNumber(
      input.capitalEfficiencyScore,
      "capitalEfficiencyScore",
    ),
    expectedContributionProfit: requireFiniteNumber(
      input.expectedContributionProfit,
      "expectedContributionProfit",
    ),
    evidenceConfidence: requireFiniteNumber(input.evidenceConfidence, "evidenceConfidence"),
  });
}

export function assertApprovalSet(approvalSet) {
  requireText(approvalSet?.tenantId, "approvalSet.tenantId");
  requireText(approvalSet?.approvalSetId, "approvalSet.approvalSetId");
  requireText(approvalSet?.evidenceVersion, "approvalSet.evidenceVersion");

  if (!Array.isArray(approvalSet?.opportunities)) {
    throw new KernelInvariantError(
      "INVALID_APPROVAL_SET",
      "approvalSet.opportunities must be an array",
    );
  }
  if (approvalSet.opportunities.length !== APPROVAL_SET_SIZE) {
    throw new KernelInvariantError(
      "INVALID_APPROVAL_SET",
      `approvalSet must contain exactly ${APPROVAL_SET_SIZE} executable opportunities`,
    );
  }

  const ids = new Set();
  for (const opportunity of approvalSet.opportunities) {
    if (!opportunity || !Array.isArray(opportunity.blockers)) {
      throw new KernelInvariantError(
        "INVALID_APPROVAL_SET",
        "approval set contains an invalid opportunity contract",
      );
    }
    if (opportunity.tenantId !== approvalSet.tenantId) {
      throw new KernelInvariantError("TENANT_BOUNDARY_VIOLATION", "approval set crosses tenants");
    }
    if (opportunity.evidenceVersion !== approvalSet.evidenceVersion) {
      throw new KernelInvariantError(
        "STALE_APPROVAL_CONTEXT",
        "approval set contains mixed evidence versions",
      );
    }
    if (!opportunity.executable || opportunity.blockers.length > 0) {
      throw new KernelInvariantError(
        "NON_EXECUTABLE_OPPORTUNITY",
        "approval set contains a non-executable opportunity",
      );
    }
    if (ids.has(opportunity.opportunityId)) {
      throw new KernelInvariantError(
        "DUPLICATE_OPPORTUNITY",
        "approval set contains duplicate opportunities",
      );
    }
    ids.add(opportunity.opportunityId);
  }
  return approvalSet;
}

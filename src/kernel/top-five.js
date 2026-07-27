import {
  APPROVAL_SET_SIZE,
  assertApprovalSet,
  createQualifiedOpportunity,
  requireText,
} from "./contracts.js";
import { KernelInvariantError } from "./errors.js";

const compareDescending = (left, right) => right - left;

export function selectExactTopFive({
  tenantId,
  approvalSetId,
  evidenceVersion,
  selectedAt,
  opportunities,
}) {
  const canonicalTenantId = requireText(tenantId, "tenantId");
  if (!Array.isArray(opportunities)) {
    throw new KernelInvariantError("INVALID_CONTRACT", "opportunities must be an array");
  }

  const eligible = opportunities
    .map(createQualifiedOpportunity)
    .filter(
      (opportunity) =>
        opportunity.tenantId === canonicalTenantId &&
        opportunity.executable &&
        opportunity.blockers.length === 0,
    );

  const unique = new Map(eligible.map((item) => [item.opportunityId, item]));
  if (unique.size < APPROVAL_SET_SIZE) {
    throw new KernelInvariantError(
      "INSUFFICIENT_EXECUTABLE_OPPORTUNITIES",
      `exactly ${APPROVAL_SET_SIZE} executable opportunities cannot be produced`,
    );
  }

  const ranked = [...unique.values()].sort(
    (left, right) =>
      compareDescending(left.capitalEfficiencyScore, right.capitalEfficiencyScore) ||
      compareDescending(left.expectedContributionProfit, right.expectedContributionProfit) ||
      compareDescending(left.evidenceConfidence, right.evidenceConfidence) ||
      left.opportunityId.localeCompare(right.opportunityId),
  );

  return assertApprovalSet(
    Object.freeze({
      tenantId: canonicalTenantId,
      approvalSetId: requireText(approvalSetId, "approvalSetId"),
      evidenceVersion: requireText(evidenceVersion, "evidenceVersion"),
      selectedAt: requireText(selectedAt, "selectedAt"),
      selectionPolicy: "capital-efficiency-v1",
      opportunities: Object.freeze(ranked.slice(0, APPROVAL_SET_SIZE)),
    }),
  );
}

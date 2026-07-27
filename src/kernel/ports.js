import { KernelInvariantError } from "./errors.js";

export function assertUnitOfWork(unitOfWork) {
  if (!unitOfWork || typeof unitOfWork.execute !== "function") {
    throw new KernelInvariantError(
      "INVALID_UNIT_OF_WORK",
      "a transactional PostgreSQL-backed unit of work is required",
    );
  }
  return unitOfWork;
}

export function assertTransactionPort(transaction) {
  for (const method of [
    "findApprovalByIdempotencyKey",
    "saveApproval",
    "saveAcceptedOpportunity",
    "appendAuditEvent",
  ]) {
    if (typeof transaction?.[method] !== "function") {
      throw new KernelInvariantError(
        "INVALID_TRANSACTION_PORT",
        `transaction.${method} must be implemented`,
      );
    }
  }
  return transaction;
}

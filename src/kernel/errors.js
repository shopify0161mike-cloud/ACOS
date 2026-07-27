export class KernelInvariantError extends Error {
  constructor(code, message) {
    super(message);
    this.name = "KernelInvariantError";
    this.code = code;
  }
}

export class IdempotencyConflictError extends KernelInvariantError {
  constructor(message) {
    super("IDEMPOTENCY_CONFLICT", message);
    this.name = "IdempotencyConflictError";
  }
}

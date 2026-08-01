/**
 * Reframing of PPLLM-main/permission_layer for the browser.
 *
 * There is no filesystem to gate here, so the permission layer becomes a CONSENT
 * record: what the app was asked to do with which file, what was decided, and why.
 *
 * The schema mirrors access_log.db so entries mean the same thing in both
 * implementations — ts_utc, agent_id, action, resource_type, resource_id,
 * decision, reason.
 *
 * Two differences from the desktop app, both deliberate improvements:
 *   1. It is actually WIRED IN. The permission layer exists in the Python repo but
 *      the desktop app never calls it, so users get no audit trail at all.
 *   2. The log is visible to the user and clearable by them, rather than sitting
 *      in a SQLite file they will never open.
 */

export type Decision = 'allow' | 'deny';

export interface AuditEntry {
  ts_utc: string;
  agent_id: string;
  action: string;
  resource_type: string;
  resource_id: string;
  decision: Decision;
  reason: string;
}

const entries: AuditEntry[] = [];
const listeners = new Set<(entries: AuditEntry[]) => void>();

function notify(): void {
  const snapshot = [...entries];
  for (const listener of listeners) listener(snapshot);
}

export function record(
  action: string,
  resourceType: string,
  resourceId: string,
  decision: Decision,
  reason: string
): AuditEntry {
  const entry: AuditEntry = {
    ts_utc: new Date().toISOString(),
    agent_id: 'browser_studio',
    action,
    resource_type: resourceType,
    resource_id: resourceId,
    decision,
    reason,
  };
  entries.push(entry);
  notify();
  return entry;
}

export function getEntries(): AuditEntry[] {
  return [...entries];
}

export function clearEntries(): void {
  entries.length = 0;
  notify();
}

export function subscribe(listener: (entries: AuditEntry[]) => void): () => void {
  listeners.add(listener);
  listener([...entries]);
  return () => listeners.delete(listener);
}

/** Export in the same shape the SQLite audit table stores. */
export function exportAuditJson(): string {
  return JSON.stringify(
    { exported_at: new Date().toISOString(), schema: 'access_log', entries },
    null,
    2
  );
}

import type { ChunkArtifact, RawArtifact } from '../core/types';

/**
 * OPT-IN persistence.
 *
 * Ephemeral is the default (CLAUDE.md 10.1): nothing here is touched unless the
 * user explicitly turns saving on. A refresh genuinely loses everything otherwise,
 * and the UI says so.
 *
 * That choice is itself the teaching point — a privacy tool should not quietly
 * accumulate personal data in browser storage, and the user should be able to see
 * exactly what is kept and erase it in one action.
 */

const DB_NAME = 'ppllm-studio';
const DB_VERSION = 1;
const STORE = 'artifacts';

export interface StoredArtifact {
  doc_id: string;
  source_filename: string;
  file_type: string;
  saved_at: string;
  total_chunks: number;
  raw: RawArtifact;
  chunks: ChunkArtifact;
}

async function openDb() {
  const { openDB } = await import('idb');
  return openDB(DB_NAME, DB_VERSION, {
    upgrade(db) {
      if (!db.objectStoreNames.contains(STORE)) {
        db.createObjectStore(STORE, { keyPath: 'doc_id' });
      }
    },
  });
}

export async function saveArtifact(raw: RawArtifact, chunks: ChunkArtifact): Promise<void> {
  const db = await openDb();
  const record: StoredArtifact = {
    doc_id: chunks.doc_id,
    source_filename: chunks.source_filename,
    file_type: chunks.file_type,
    saved_at: new Date().toISOString(),
    total_chunks: chunks.total_chunks,
    raw,
    chunks,
  };
  // Same doc_id overwrites, matching the desktop app's dedup behaviour.
  await db.put(STORE, record);
  db.close();
}

export async function listArtifacts(): Promise<StoredArtifact[]> {
  const db = await openDb();
  const all = (await db.getAll(STORE)) as StoredArtifact[];
  db.close();
  return all.sort((a, b) => b.saved_at.localeCompare(a.saved_at));
}

export async function deleteArtifact(docId: string): Promise<void> {
  const db = await openDb();
  await db.delete(STORE, docId);
  db.close();
}

/** Erase everything. Must remain a single, obvious action for the user. */
export async function clearAll(): Promise<void> {
  const db = await openDb();
  await db.clear(STORE);
  db.close();
}

export async function countArtifacts(): Promise<number> {
  const db = await openDb();
  const count = await db.count(STORE);
  db.close();
  return count;
}

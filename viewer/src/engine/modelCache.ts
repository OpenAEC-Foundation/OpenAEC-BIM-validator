/**
 * Model cache — IndexedDB storage for IFC file bytes + in-memory File cache.
 *
 * IndexedDB survives page refresh, enabling model persistence.
 * The in-memory cache provides quick access to File objects
 * during the current session (e.g., for validation).
 */

const DB_NAME = "bim-validator";
const DB_VERSION = 1;
const STORE_NAME = "model-bytes";

// ---------------------------------------------------------------------------
// IndexedDB helpers
// ---------------------------------------------------------------------------

function openDB(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);
    request.onupgradeneeded = () => {
      request.result.createObjectStore(STORE_NAME);
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

/** Save raw IFC file bytes to IndexedDB, keyed by fileName. */
export async function saveModelBytes(
  fileName: string,
  bytes: ArrayBuffer
): Promise<void> {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, "readwrite");
    tx.objectStore(STORE_NAME).put(bytes, fileName);
    tx.oncomplete = () => {
      db.close();
      resolve();
    };
    tx.onerror = () => {
      db.close();
      reject(tx.error);
    };
  });
}

/** Retrieve cached IFC bytes from IndexedDB. Returns null if not found. */
export async function getModelBytes(
  fileName: string
): Promise<ArrayBuffer | null> {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, "readonly");
    const request = tx.objectStore(STORE_NAME).get(fileName);
    request.onsuccess = () => {
      db.close();
      resolve(request.result ?? null);
    };
    request.onerror = () => {
      db.close();
      reject(request.error);
    };
  });
}

/** Remove cached bytes for a single model. */
export async function removeModelBytes(fileName: string): Promise<void> {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, "readwrite");
    tx.objectStore(STORE_NAME).delete(fileName);
    tx.oncomplete = () => {
      db.close();
      resolve();
    };
    tx.onerror = () => {
      db.close();
      reject(tx.error);
    };
  });
}

// ---------------------------------------------------------------------------
// In-memory File cache (current session only)
// ---------------------------------------------------------------------------

const fileCache = new Map<string, File>();

/** Get a cached File object by fileName. */
export function getCachedFile(fileName: string): File | undefined {
  return fileCache.get(fileName);
}

/** Store a File object in the session cache. */
export function setCachedFile(fileName: string, file: File): void {
  fileCache.set(fileName, file);
}

/** Remove a file from the session cache. */
export function removeCachedFile(fileName: string): void {
  fileCache.delete(fileName);
}

/**
 * PropertyClient — main-thread proxy for the web-ifc PropertyExtractor that
 * actually runs inside propertyWorker.ts.
 *
 * Exposes the same async interface the ViewerEngine used on PropertyExtractor
 * (getProperties / getAllGlobalIds / extractSpatialTree / getContainedElements)
 * but forwards every call to a dedicated Web Worker. This keeps the heavy,
 * synchronous web-ifc parse + entity iteration off the main thread, so the UI
 * never freezes when an element is selected.
 */
import type { IfcElementProperties } from "./PropertyExtractor";
import type { SpatialNode, ElementTypeGroup } from "../types/project";

interface Pending {
  resolve: (value: unknown) => void;
  reject: (reason: Error) => void;
}

export class PropertyClient {
  private worker: Worker | null = null;
  private nextId = 1;
  private readonly pending = new Map<number, Pending>();
  private initPromise: Promise<void> | null = null;
  private readonly bytes: Uint8Array;

  constructor(bytes: Uint8Array) {
    this.bytes = bytes;
  }

  /** Lazily spawn the worker and open the model inside it. */
  private ensureWorker(): Promise<void> {
    if (this.initPromise) return this.initPromise;

    this.initPromise = new Promise<void>((resolve, reject) => {
      try {
        this.worker = new Worker(
          new URL("./propertyWorker.ts", import.meta.url),
          { type: "module" }
        );

        this.worker.onmessage = (e: MessageEvent) => {
          const { id, result, error } = e.data as {
            id: number;
            result?: unknown;
            error?: string;
          };
          const entry = this.pending.get(id);
          if (!entry) return;
          this.pending.delete(id);
          if (error) entry.reject(new Error(error));
          else entry.resolve(result);
        };

        this.worker.onerror = (e: ErrorEvent) => {
          reject(new Error(e.message || "property worker error"));
        };

        const id = this.nextId++;
        this.pending.set(id, { resolve: () => resolve(), reject });
        // Structured-clone the bytes (no transfer) so the caller keeps its copy.
        this.worker.postMessage({ id, type: "init", payload: { bytes: this.bytes } });
      } catch (err) {
        reject(err instanceof Error ? err : new Error(String(err)));
      }
    });

    return this.initPromise;
  }

  private async call<T>(type: string, payload?: unknown): Promise<T> {
    await this.ensureWorker();
    return new Promise<T>((resolve, reject) => {
      const id = this.nextId++;
      this.pending.set(id, {
        resolve: (v) => resolve(v as T),
        reject,
      });
      this.worker!.postMessage({ id, type, payload });
    });
  }

  getProperties(globalId: string): Promise<IfcElementProperties | null> {
    return this.call("getProperties", { globalId });
  }

  getAllGlobalIds(): Promise<string[]> {
    return this.call("getAllGlobalIds");
  }

  extractSpatialTree(): Promise<SpatialNode | null> {
    return this.call("extractSpatialTree");
  }

  getContainedElements(spatialGlobalId: string): Promise<ElementTypeGroup[]> {
    return this.call("getContainedElements", { spatialGlobalId });
  }

  /** Terminate the worker and reject any in-flight calls. */
  dispose(): void {
    this.worker?.terminate();
    this.worker = null;
    this.initPromise = null;
    for (const [, entry] of this.pending) {
      entry.reject(new Error("PropertyClient disposed"));
    }
    this.pending.clear();
  }
}

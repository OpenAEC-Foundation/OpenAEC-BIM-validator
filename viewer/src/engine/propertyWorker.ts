/**
 * propertyWorker — runs the (synchronous, CPU-heavy) web-ifc PropertyExtractor
 * OFF the main thread.
 *
 * web-ifc parses the whole IFC and iterates every entity synchronously when
 * building its GlobalId index; doing that on the main thread froze the UI on
 * the first element selection. Hosting the extractor in this dedicated worker
 * keeps the main thread responsive — the PropertyClient proxy forwards calls
 * here and awaits the results via postMessage.
 */
import { PropertyExtractor } from "./PropertyExtractor";

// Worker global scope; typed loosely to avoid needing the "webworker" tsconfig lib.
const ctx: {
  onmessage: ((e: MessageEvent) => void) | null;
  postMessage: (msg: unknown) => void;
} = self as unknown as typeof ctx;

let reader: PropertyExtractor | null = null;

ctx.onmessage = async (e: MessageEvent) => {
  const { id, type, payload } = e.data as {
    id: number;
    type: string;
    payload?: { bytes?: Uint8Array; globalId?: string; spatialGlobalId?: string };
  };

  try {
    if (type === "init") {
      reader = new PropertyExtractor(payload!.bytes as Uint8Array);
      ctx.postMessage({ id, result: true });
      return;
    }

    if (!reader) throw new Error("PropertyExtractor not initialized");

    let result: unknown;
    switch (type) {
      case "getProperties":
        result = await reader.getProperties(payload!.globalId as string);
        break;
      case "getAllGlobalIds":
        result = await reader.getAllGlobalIds();
        break;
      case "extractSpatialTree":
        result = await reader.extractSpatialTree();
        break;
      case "getContainedElements":
        result = await reader.getContainedElements(
          payload!.spatialGlobalId as string
        );
        break;
      default:
        throw new Error("Unknown message type: " + type);
    }
    ctx.postMessage({ id, result });
  } catch (err) {
    ctx.postMessage({
      id,
      error: err instanceof Error ? err.message : String(err),
    });
  }
};

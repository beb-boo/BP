// IndexedDB queue for BP records created while offline (PWA_SPEC §7.1).
// Contents are PHI on the user's own device: store only the payload,
// never tokens, and clear everything on logout (clearOfflineData).
import { openDB, type DBSchema, type IDBPDatabase } from "idb";

export interface BPRecordCreatePayload {
    systolic: number;
    diastolic: number;
    pulse: number;
    measurement_date: string;
    measurement_time?: string | null;
    notes?: string | null;
    client_record_id: string;
}

export interface QueuedBPRecord {
    id: string;              // client UUID = idempotency key
    payload: BPRecordCreatePayload;
    createdAt: number;
    retryCount: number;
    status: "pending" | "syncing" | "failed";
    lastError?: string;
}

interface BPOfflineDB extends DBSchema {
    "bp-queue": {
        key: string;
        value: QueuedBPRecord;
    };
}

const DB_NAME = "bp-monitor-offline";
const STORE = "bp-queue";

function getDB(): Promise<IDBPDatabase<BPOfflineDB>> {
    return openDB<BPOfflineDB>(DB_NAME, 1, {
        upgrade(db) {
            if (!db.objectStoreNames.contains(STORE)) {
                db.createObjectStore(STORE, { keyPath: "id" });
            }
        },
    });
}

export async function enqueue(payload: BPRecordCreatePayload): Promise<QueuedBPRecord> {
    const item: QueuedBPRecord = {
        id: payload.client_record_id,
        payload,
        createdAt: Date.now(),
        retryCount: 0,
        status: "pending",
    };
    const db = await getDB();
    await db.put(STORE, item);
    return item;
}

export async function getAll(): Promise<QueuedBPRecord[]> {
    const db = await getDB();
    return db.getAll(STORE);
}

export async function count(): Promise<number> {
    const db = await getDB();
    return db.count(STORE);
}

export async function update(item: QueuedBPRecord): Promise<void> {
    const db = await getDB();
    await db.put(STORE, item);
}

export async function remove(id: string): Promise<void> {
    const db = await getDB();
    await db.delete(STORE, id);
}

export async function clearAll(): Promise<void> {
    const db = await getDB();
    await db.clear(STORE);
}

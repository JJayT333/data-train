export class W1RecordGroup {
    constructor() {
        // Behaves like a dictionary in Python, essentially just an object in JS/TS.
        // We can add helper methods if needed, but plain object structure is often enough for JSON.
    }
    /**
     * Returns a plain object representation of the record group,
     * stripping away the class prototype. This is useful for
     * Next.js serialization or other cases where plain objects are required.
     */
    toObject() {
        return { ...this };
    }
    /**
     * Helper for JSON serialization.
     * When JSON.stringify() is called on this object, this method is used.
     */
    toJSON() {
        return this.toObject();
    }
}

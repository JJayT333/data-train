
export const DA_ALTERNATE_ADDR_FIELDS: [string, number, number, string][] = [
    ["record_id", 1, 2, "str"], // 11
    ["address_key", 3, 2, "str"],
    // Line 1 is 33 chars, Line 2 is 35 chars. Overlapping start at 5.
    // We take 35 to cover the maximum length (Line 2).
    ["address_line", 5, 35, "str"],
    // Filler at 40 (len 471)
    // Ignoring fillers.
];

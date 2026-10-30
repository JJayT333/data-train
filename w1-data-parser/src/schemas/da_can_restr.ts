
export const DA_CAN_RESTR_FIELDS: [string, number, number, string][] = [
    ["record_id", 1, 2, "str"], // 06
    ["restriction_key", 3, 2, "int"],
    ["restriction_type", 5, 2, "str"],
    ["restriction_remark", 7, 35, "str"],
    ["restriction_flag", 42, 1, "str"],
    // Filler at 43 (len 10) -> ends 52.
    // Tape filler 458 bytes at ?? Manual says 223? 
    // Previous segs had fillers to maintain size.
    // This segment is simpler, we just need the core data.
];

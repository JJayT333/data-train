
export const DA_REMARK_FIELDS: [string, number, number, string][] = [
    ["record_id", 1, 2, "str"], // 12
    ["remark_sequence_number", 3, 3, "int"],
    ["remark_date_century", 6, 2, "int"],
    ["remark_date_year", 8, 2, "int"],
    ["remark_date_month", 10, 2, "int"],
    ["remark_date_day", 12, 2, "int"],
    ["remark_line", 14, 70, "str"],
    // Filler at 84 (len 10)
    // Tape filler 417 bytes at 94
    // Ignoring fillers.
];

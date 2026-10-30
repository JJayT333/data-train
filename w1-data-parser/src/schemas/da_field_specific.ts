
export const DA_FIELD_SPECIFIC_FIELDS: [string, number, number, string][] = [
    ["record_id", 1, 2, "str"], // 04
    ["field_district", 3, 2, "int"],
    ["field_lease_name", 5, 32, "str"],
    ["field_total_depth", 37, 5, "int"],
    ["field_well_number", 42, 6, "str"],
    ["field_acres", 48, 8, "str"], // Adjusted position from 46 to 48
];

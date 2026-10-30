
export const DA_FIELD_FIELDS: [string, number, number, string][] = [
    ["record_id", 1, 2, "str"], // 03
    ["field_number", 3, 8, "int"],
    ["field_application_well_code", 11, 1, "str"],
    ["field_completion_well_code", 12, 1, "str"],
    ["field_completion_code", 13, 1, "str"],
    ["field_transfer_code", 14, 1, "str"],
    // DA-FIELD-VALIDATION-DATE breakdown
    ["field_validation_century", 15, 2, "int"],
    ["field_validation_year", 17, 2, "int"],
    ["field_validation_month", 19, 2, "int"],
    ["field_validation_day", 21, 2, "int"],
    // DA-FIELD-COMPLETION-DATE breakdown
    ["field_completion_century", 23, 2, "int"],
    ["field_completion_year", 25, 2, "int"],
    ["field_completion_month", 27, 2, "int"],
    ["field_completion_day", 29, 2, "int"],
    ["field_rule37_flag", 31, 1, "str"],
    ["field_rule38_flag", 32, 1, "str"],
    // Filler
];

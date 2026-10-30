
export const DA_PERMIT_BHL_FIELDS: [string, number, number, string][] = [
    ["record_id", 1, 2, "str"], // 10
    ["bhl_section", 3, 8, "str"],
    ["bhl_block", 11, 10, "str"],
    ["bhl_abstract", 21, 6, "str"],
    ["bhl_survey", 27, 55, "str"],
    ["bhl_acres", 82, 8, "str"], // 9(06)V9(2) -> treat as str for now to preserve formatting
    ["bhl_nearest_well", 90, 28, "str"],
    ["bhl_lease_feet_1", 118, 8, "str"],
    ["bhl_lease_direction_1", 126, 13, "str"],
    ["bhl_lease_feet_2", 139, 8, "str"],
    ["bhl_lease_direction_2", 147, 13, "str"],
    ["bhl_survey_feet_1", 160, 8, "str"],
    ["bhl_survey_direction_1", 168, 13, "str"],
    ["bhl_survey_feet_2", 181, 8, "str"],
    ["bhl_survey_direction_2", 189, 13, "str"],
    ["bhl_county", 202, 13, "str"],
    ["bhl_pntrt_dist_1", 215, 8, "str"],
    ["bhl_pntrt_dir_1", 223, 13, "str"],
    ["bhl_pntrt_dist_2", 236, 8, "str"],
    ["bhl_pntrt_dir_2", 244, 13, "str"],
    // Filler at 257 (len 6)
    // Tape filler 288 bytes at 263 (manual says 288 bytes II.62 pos 223?? Typo in manual pos col? No, 244+13=257. 257+6=263.)
    // Ignoring fillers.
];

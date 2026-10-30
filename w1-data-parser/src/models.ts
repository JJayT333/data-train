
export interface RRCRecord {
    record_id: string;
    [key: string]: any;
}

export class W1RecordGroup {
    [key: string]: any;

    constructor() {
        // Behaves like a dictionary in Python, essentially just an object in JS/TS.
        // We can add helper methods if needed, but plain object structure is often enough for JSON.
    }

    /**
     * Returns a plain object representation of the record group,
     * stripping away the class prototype. This is useful for
     * Next.js serialization or other cases where plain objects are required.
     */
    toObject(): Record<string, any> {
        return { ...this };
    }

    /**
     * Helper for JSON serialization.
     * When JSON.stringify() is called on this object, this method is used.
     */
    toJSON(): Record<string, any> {
        return this.toObject();
    }
}

export interface DaRootRecord extends RRCRecord {
    status_number: number;
    status_sequence_number: number;
    county_code: number | string;
    lease_name: string;
    district: number;
    operator_number: number;
    converted_date_comp: string;
    date_app_received: string;
    operator_name: string;
    hb1407_problem_flag: string;
    status_of_app_flag: string;
    not_enough_money_flag: string;
    too_much_money_flag: string;
    p5_problem_flag: string;
    p12_problem_flag: string;
    plat_problem_flag: string;
    w1a_problem_flag: string;
    other_problem_flag: string;
    rule37_problem_flag: string;
    rule38_problem_flag: string;
    rule39_problem_flag: string;
    no_money_flag: string;
    permit_number: number;
    issue_date: string;
    withdrawn_date: string;
    walkthrough_flag: string;
    other_problem_text: string;
    well_number: string;
    built_from_old_master_flag: string;
    status_renumbered_to: number;
    status_renumbered_from: number;
    application_returned_flag: string;
    ecap_filing_flag: string;
}

export interface DaPermitRecord extends RRCRecord {
    permit_number: number;
    sequence_number: number;
    county_code: number | string;
    lease_name: string;
    district: number;
    well_number: string;
    total_depth: number;
    operator_number: number;
    type_application: string;
    other_explanation: string;
    address_unique_number: number;
    zip_code_prefix: string;
    zip_code_suffix: string;
    fiche_set_number: number;
    onshore_county: number | string;
    received_date: string;
    issued_date: string;
    amended_date: string;
    extended_date: string;
    spud_date: string;
    surface_casing_date: string;
    well_status: string;
    well_status_date: string;
    expired_date: string;
    cancelled_date: string;
    cancellation_reason: string;
    p12_filed_flag: string;
    substandard_acreage_flag: string;
    rule_36_flag: string;
    h9_flag: string;
    rule_37_case_number: number;
    rule_38_docket_number: number;
    location_formation_flag: string;
    surface_section: string;
    surface_block: string;
    surface_survey: string;
    surface_abstract: string;
    surface_acres: string;
    surface_miles_from_city: string;
    surface_direction_from_city: string;
    surface_nearest_city: string;
    surface_lease_feet_1: string;
    surface_lease_direction_1: string;
    surface_lease_feet_2: string;
    surface_lease_direction_2: string;
    surface_survey_feet_1: string;
    surface_survey_direction_1: string;
    surface_survey_feet_2: string;
    surface_survey_direction_2: string;
    nearest_well_feet: string;
    nearest_well_direction: string;
    nearest_well_format_flag: string;
    final_update: string;
    cancelled_flag: string;
    spud_in_flag: string;
    directional_well_flag: string;
    sidetrack_well_flag: string;
    moved_indicator: string;
    permit_conv_issued_date: number;
    rule_37_granted_code: string;
    horizontal_well_flag: string;
    duplicate_permit_flag: string;
    nearest_lease_line: string;
    api_number: string;
}

export interface DaFieldRecord extends RRCRecord {
    field_number: number;
    field_application_well_code: string;
    field_completion_well_code: string;
    field_completion_code: string;
    field_transfer_code: string;
    field_validation_century: number;
    field_validation_year: number;
    field_validation_month: number;
    field_validation_day: number;
    field_completion_century: number;
    field_completion_year: number;
    field_completion_month: number;
    field_completion_day: number;
    field_rule37_flag: string;
    field_rule38_flag: string;
}

export interface DaFieldSpecificRecord extends RRCRecord {
    field_district: number;
    field_lease_name: string;
    field_total_depth: number;
    field_well_number: string;
    field_acres: string;
}

export interface DaFieldBhlRecord extends RRCRecord {
    bhl_section: string;
    bhl_block: string;
    bhl_abstract: string;
    bhl_survey: string;
    bhl_acres: string;
    bhl_nearest_well: string;
    bhl_lease_feet_1: string;
    bhl_lease_direction_1: string;
    bhl_lease_feet_2: string;
    bhl_lease_direction_2: string;
    bhl_survey_feet_1: string;
    bhl_survey_direction_1: string;
    bhl_survey_feet_2: string;
    bhl_survey_direction_2: string;
    bhl_county: string;
    bhl_pntrt_dist_1: string;
    bhl_pntrt_dir_1: string;
    bhl_pntrt_dist_2: string;
    bhl_pntrt_dir_2: string;
}

export interface DaCanRestrRecord extends RRCRecord {
    restriction_key: number;
    restriction_type: string;
    restriction_remark: string;
    restriction_flag: string;
}

export interface DaCanRestrFieldRecord extends RRCRecord {
    field_number: string;
}

export interface DaFreeRestrRecord extends RRCRecord {
    restriction_key: number;
    restriction_type: string;
    restriction_remark: string;
    restriction_flag: string;
}

export interface DaFreeRestrFieldRecord extends RRCRecord {
    field_number: string;
}

export interface DaPermitBhlRecord extends RRCRecord {
    bhl_section: string;
    bhl_block: string;
    bhl_abstract: string;
    bhl_survey: string;
    bhl_acres: string;
    bhl_nearest_well: string;
    bhl_lease_feet_1: string;
    bhl_lease_direction_1: string;
    bhl_lease_feet_2: string;
    bhl_lease_direction_2: string;
    bhl_survey_feet_1: string;
    bhl_survey_direction_1: string;
    bhl_survey_feet_2: string;
    bhl_survey_direction_2: string;
    bhl_county: string;
    bhl_pntrt_dist_1: string;
    bhl_pntrt_dir_1: string;
    bhl_pntrt_dist_2: string;
    bhl_pntrt_dir_2: string;
}

export interface DaAlternateAddressRecord extends RRCRecord {
    address_key: string;
    address_line: string;
}

export interface DaRemarkRecord extends RRCRecord {
    remark_sequence_number: number;
    remark_date_century: number;
    remark_date_year: number;
    remark_date_month: number;
    remark_date_day: number;
    remark_line: string;
}

export interface DaCheckRegisterRecord extends RRCRecord {
    register_date_century: number;
    register_date_year: number;
    register_date_month: number;
    register_date_day: number;
    register_number: number;
}

export interface DaSurfaceLocationRecord extends RRCRecord {
    longitude: string;
    latitude: string;
}

export interface DaBottomHoleLocationRecord extends RRCRecord {
    longitude: string;
    latitude: string;
}

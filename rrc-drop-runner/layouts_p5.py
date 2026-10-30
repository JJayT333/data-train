# P-5 Organization (ORF850) ASCII layout, from manuals/ora001_p5_manual_october-2014.pdf sec II.
# (name, start_1based, length). Record length 350; type = cols 1-2.
_H = [('rec_id',1,2),('operator_number',3,6),('organization_name',9,32)]
P5 = {
 '1T': ('specialty_code_table', [('rec_id',1,2),('code_indicator',3,6),('code_type',9,2),('code_name',11,60)]),
 'A ': ('organization', _H+[('refiling_required_flag',41,1),('p5_status',42,1),('hold_mail_code',43,1),('renewal_letter_code',44,1),
        ('organization_code',45,1),('organ_other_comment',46,20),('gatherer_code',66,5),('org_addr_line1',71,31),('org_addr_line2',102,31),
        ('org_addr_city',133,13),('org_addr_state',146,2),('org_addr_zip',148,5),('org_addr_zip_suffix',153,4),('loc_addr_line1',157,31),
        ('loc_addr_line2',188,31),('loc_addr_city',219,13),('loc_addr_state',232,2),('loc_addr_zip',234,5),('loc_addr_zip_suffix',239,4),
        ('date_built',243,8),('date_inactive',251,8),('phone_number',259,10),('refile_notice_month',269,2),('refile_letter_date',271,8),
        ('refile_notice_date',279,8),('refile_received_date',287,8),('last_p5_received_date',295,8),('other_organization_no',303,6),
        ('filing_problem_date',309,8),('filing_problem_ltr_code',317,3),('telephone_verify_flag',320,1),('op_num_multi_used_flag',321,1),
        ('oil_gatherer_status',322,1),('gas_gatherer_status',323,1),('tax_cert',324,1),('emer_phone_number',325,10)]),
 'F ': ('specialty_codes', _H+[('specialty_code',41,6),('addr_line1',47,31),('addr_line2',78,31),('addr_city',109,13),('addr_state',122,2),('addr_zip',124,5),('addr_zip_suffix',129,4)]),
 'H ': ('district_address', _H+[('specialty_code',41,6),('district_flags',47,14),('addr_line1',61,31),('addr_line2',92,31),('addr_city',123,13),('addr_state',136,2),('addr_zip',138,5),('addr_zip_suffix',143,4)]),
 'J ': ('field_address', _H+[('specialty_code',41,6),('field_district_code',47,2),('field_number',49,8),('addr_line1',57,31),('addr_line2',88,31),('addr_city',119,13),('addr_state',132,2),('addr_zip',134,5),('addr_zip_suffix',139,4)]),
 'K ': ('officers', _H+[('officer_name',41,32),('officer_title',73,32),('addr_line1',105,31),('addr_line2',136,31),('addr_city',167,13),('addr_state',180,2),('addr_zip',182,5),('addr_zip_suffix',187,4),
        ('loc_addr_line1',191,31),('loc_addr_line2',222,31),('loc_addr_city',253,13),('loc_addr_state',266,2),('loc_addr_zip',268,5),('loc_addr_zip_sfx',273,4),('officer_type_id',277,1),('officer_id_state',278,2),('officer_id_number',280,20),('officer_agent',300,1)]),
 'P ': ('remarks', _H+[('remarks',41,60),('remarks_line_number',101,4)]),
 'U ': ('activity_indicators', _H+[('act_ind_code',41,6),('district_flags',47,14)]),
 'R ': ('activity_restrictions', _H+[('act_restr_code',41,6),('district_flags',47,14)]),
}
DISTRICTS = ['01','02','03','04','05','06','6E','7B','7C','08','8A','09','10','11']  # assumed order of the 14 flags


import * as fs from 'fs';
import * as readline from 'readline';
import {
    W1RecordGroup,
    DaRootRecord, DaPermitRecord, DaFieldRecord, DaFieldSpecificRecord, DaFieldBhlRecord,
    DaCanRestrRecord, DaCanRestrFieldRecord, DaFreeRestrRecord, DaFreeRestrFieldRecord,
    DaPermitBhlRecord, DaAlternateAddressRecord, DaRemarkRecord, DaCheckRegisterRecord,
    DaSurfaceLocationRecord, DaBottomHoleLocationRecord,
    RRCRecord
} from './models.js';
import {
    SCHEMA_ID_TO_NAME, SCHEMA_NAME_TO_ID,
    DA_ROOT_FIELDS, DA_PERMIT_FIELDS, DA_FIELD_FIELDS, DA_FIELD_SPECIFIC_FIELDS,
    DA_FIELD_BHL_FIELDS, DA_CAN_RESTR_FIELDS, DA_CAN_RESTR_FIELD_FIELDS,
    DA_FREE_RESTR_FIELDS, DA_FREE_RESTR_FIELD_FIELDS, DA_PERMIT_BHL_FIELDS,
    DA_ALTERNATE_ADDR_FIELDS, DA_REMARK_FIELDS, DA_CHECK_REGISTER_FIELDS,
    DA_SURFACE_LOC_FIELDS, DA_BOTTOM_HOLE_LOC_FIELDS
} from './schemas/index.js';
import { COUNTY_CODES, WELL_STATUS_CODES, TYPE_WELL_CODES, CANNED_RESTRICTIONS } from './lookups.js';

export class W1Parser {
    records: W1RecordGroup[];

    constructor() {
        this.records = [];
    }

    async parseFile(filepath: string, schemas?: (string | number)[], transformCodes: boolean = false): Promise<W1RecordGroup[]> {
        this.records = []; // Reset on new parse? Python one didn't explicit reset but created new list in parsed var wait... python re-used self.records? No, it re-initialized in init but parse_file returned self.records appened.
        // Python: `self.records: List[W1RecordGroup] = []` in init. `parse_file` appended to it.
        // Let's stick to accumulating to mimic python, or reset if desired. Standard is usually fresh parse. 
        // Python logic: `if current_record is not None... self.records.append`.
        // If I call parse_file twice on same instance, it appends.

        const allowedIds = this._normalizeSchemaFilter(schemas);

        let currentRecord: W1RecordGroup | null = null;

        const fileStream = fs.createReadStream(filepath, { encoding: 'utf8' });

        const rl = readline.createInterface({
            input: fileStream,
            crlfDelay: Infinity
        });

        for await (const line of rl) {
            if (line.length < 2) continue;

            const recordId = line.substring(0, 2);

            // Check filter
            if (allowedIds && !allowedIds.has(recordId)) {
                continue;
            }

            if (recordId === '01') {
                // Dim previous record
                if (currentRecord) {
                    if (transformCodes) {
                        this._transformGroup(currentRecord);
                    }
                    this.records.push(currentRecord);
                }

                const rootRecord = this._parseDaRoot(line);
                currentRecord = new W1RecordGroup();
                currentRecord["01"] = rootRecord;

            } else {
                if (currentRecord) {
                    let parsedRecord: RRCRecord | null = null;

                    if (recordId === '02') parsedRecord = this._parseDaPermit(line);
                    else if (recordId === '03') { this._addToGroupList(currentRecord, '03', this._parseDaField(line)); parsedRecord = null; } // rrc-tools: repeatable (one per permitted field)
                    else if (recordId === '04') { this._addToGroupList(currentRecord, '04', this._parseDaFieldSpecific(line)); parsedRecord = null; } // rrc-tools: repeatable (one per permitted field)
                    else if (recordId === '05') { this._addToGroupList(currentRecord, '05', this._parseDaFieldBhl(line)); parsedRecord = null; } // rrc-tools: repeatable (one per permitted field)
                    else if (recordId === '06') {
                        parsedRecord = this._parseDaCanRestr(line);
                        this._addToGroupList(currentRecord, '06', parsedRecord);
                        parsedRecord = null; // Handled
                    } else if (recordId === '07') {
                        parsedRecord = this._parseDaCanRestrField(line);
                        this._addToGroupList(currentRecord, '07', parsedRecord);
                        parsedRecord = null;
                    } else if (recordId === '08') {
                        parsedRecord = this._parseDaFreeRestr(line);
                        this._addToGroupList(currentRecord, '08', parsedRecord);
                        parsedRecord = null;
                    } else if (recordId === '09') {
                        parsedRecord = this._parseDaFreeRestrField(line);
                        this._addToGroupList(currentRecord, '09', parsedRecord);
                        parsedRecord = null;
                    } else if (recordId === '10') parsedRecord = this._parseDaPermitBhl(line);
                    else if (recordId === '11') {
                        parsedRecord = this._parseDaAlternateAddr(line);
                        this._addToGroupList(currentRecord, '11', parsedRecord);
                        parsedRecord = null;
                    } else if (recordId === '12') {
                        parsedRecord = this._parseDaRemark(line);
                        this._addToGroupList(currentRecord, '12', parsedRecord);
                        parsedRecord = null;
                    } else if (recordId === '13') {
                        parsedRecord = this._parseDaCheckRegister(line);
                        this._addToGroupList(currentRecord, '13', parsedRecord);
                        parsedRecord = null;
                    } else if (recordId === '14') parsedRecord = this._parseDaSurfaceLoc(line);
                    else if (recordId === '15') {
                        parsedRecord = this._parseDaBottomHoleLoc(line);
                        this._addToGroupList(currentRecord, '15', parsedRecord);
                        parsedRecord = null;
                    }

                    if (parsedRecord) {
                        currentRecord[recordId] = parsedRecord;
                    }
                }
            }
        }

        // End of file
        if (currentRecord) {
            if (transformCodes) {
                this._transformGroup(currentRecord);
            }
            this.records.push(currentRecord);
        }

        return this.records;
    }

    _addToGroupList(group: W1RecordGroup, key: string, record: RRCRecord | null) {
        if (!record) return;
        if (!group[key]) {
            group[key] = [];
        }
        if (Array.isArray(group[key])) {
            group[key].push(record);
        }
    }

    _normalizeSchemaFilter(schemas?: (string | number)[]): Set<string> | null {
        if (!schemas) return null;

        const allowed = new Set<string>();
        for (const s of schemas) {
            const sStr = String(s);
            if (SCHEMA_NAME_TO_ID[sStr]) {
                allowed.add(SCHEMA_NAME_TO_ID[sStr]);
            } else if (SCHEMA_ID_TO_NAME[sStr]) {
                allowed.add(sStr);
            } else if (SCHEMA_ID_TO_NAME[sStr.padStart(2, '0')]) {
                allowed.add(sStr.padStart(2, '0'));
            }
        }
        return allowed;
    }

    _extractFields(line: string, fields: [string, number, number, string][]): any {
        const data: any = {};
        for (const [name, start, length, type] of fields) {
            const idx = start - 1;
            let rawVal = "";
            if (idx < line.length) {
                rawVal = line.substring(idx, idx + length);
            }

            if (rawVal.length < length) {
                rawVal = rawVal.padEnd(length, ' ');
            }

            let val: string | number = rawVal;

            if (type === 'int') {
                const parsed = parseInt(rawVal.trim(), 10);
                if (isNaN(parsed)) {
                    val = 0;
                } else {
                    val = parsed;
                }
            } else {
                val = rawVal.trim();
            }
            data[name] = val;
        }
        return data;
    }

    _parseDaRoot(line: string): DaRootRecord {
        return this._extractFields(line, DA_ROOT_FIELDS) as DaRootRecord;
    }
    _parseDaPermit(line: string): DaPermitRecord {
        return this._extractFields(line, DA_PERMIT_FIELDS) as DaPermitRecord;
    }
    _parseDaField(line: string): DaFieldRecord {
        return this._extractFields(line, DA_FIELD_FIELDS) as DaFieldRecord;
    }
    _parseDaFieldSpecific(line: string): DaFieldSpecificRecord {
        return this._extractFields(line, DA_FIELD_SPECIFIC_FIELDS) as DaFieldSpecificRecord;
    }
    _parseDaFieldBhl(line: string): DaFieldBhlRecord {
        return this._extractFields(line, DA_FIELD_BHL_FIELDS) as DaFieldBhlRecord;
    }
    _parseDaCanRestr(line: string): DaCanRestrRecord {
        return this._extractFields(line, DA_CAN_RESTR_FIELDS) as DaCanRestrRecord;
    }
    _parseDaCanRestrField(line: string): DaCanRestrFieldRecord {
        return this._extractFields(line, DA_CAN_RESTR_FIELD_FIELDS) as DaCanRestrFieldRecord;
    }
    _parseDaFreeRestr(line: string): DaFreeRestrRecord {
        return this._extractFields(line, DA_FREE_RESTR_FIELDS) as DaFreeRestrRecord;
    }
    _parseDaFreeRestrField(line: string): DaFreeRestrFieldRecord {
        return this._extractFields(line, DA_FREE_RESTR_FIELD_FIELDS) as DaFreeRestrFieldRecord;
    }
    _parseDaPermitBhl(line: string): DaPermitBhlRecord {
        return this._extractFields(line, DA_PERMIT_BHL_FIELDS) as DaPermitBhlRecord;
    }
    _parseDaAlternateAddr(line: string): DaAlternateAddressRecord {
        return this._extractFields(line, DA_ALTERNATE_ADDR_FIELDS) as DaAlternateAddressRecord;
    }
    _parseDaRemark(line: string): DaRemarkRecord {
        return this._extractFields(line, DA_REMARK_FIELDS) as DaRemarkRecord;
    }
    _parseDaCheckRegister(line: string): DaCheckRegisterRecord {
        return this._extractFields(line, DA_CHECK_REGISTER_FIELDS) as DaCheckRegisterRecord;
    }
    _parseDaSurfaceLoc(line: string): DaSurfaceLocationRecord {
        return this._extractFields(line, DA_SURFACE_LOC_FIELDS) as DaSurfaceLocationRecord;
    }
    _parseDaBottomHoleLoc(line: string): DaBottomHoleLocationRecord {
        return this._extractFields(line, DA_BOTTOM_HOLE_LOC_FIELDS) as DaBottomHoleLocationRecord;
    }

    _transformGroup(group: W1RecordGroup) {
        for (const key in group) {
            const value = group[key];
            if (Array.isArray(value)) {
                for (const item of value) {
                    this._applyTransformations(item);
                }
            } else if (typeof value === 'object' && value !== null) {
                this._applyTransformations(value);
            }
        }
    }

    _applyTransformations(record: any) {
        if (record.record_id === '01') { // DaRoot
            const r = record as DaRootRecord;
            if (r.county_code && COUNTY_CODES[Number(r.county_code)]) {
                r.county_code = COUNTY_CODES[Number(r.county_code)];
            }
        } else if (record.record_id === '02') { // DaPermit
            const r = record as DaPermitRecord;
            if (r.county_code && COUNTY_CODES[Number(r.county_code)]) {
                r.county_code = COUNTY_CODES[Number(r.county_code)];
            }
            if (r.onshore_county && COUNTY_CODES[Number(r.onshore_county)]) {
                r.onshore_county = COUNTY_CODES[Number(r.onshore_county)];
            }
            if (r.well_status && WELL_STATUS_CODES[r.well_status]) {
                r.well_status = WELL_STATUS_CODES[r.well_status];
            }
            if (r.type_application && TYPE_WELL_CODES[r.type_application]) {
                r.type_application = TYPE_WELL_CODES[r.type_application];
            }
        } else if (record.record_id === '06') { // DaCanRestr
            const r = record as DaCanRestrRecord;
            if (r.restriction_type && CANNED_RESTRICTIONS[r.restriction_type.trim()]) {
                r.restriction_type = CANNED_RESTRICTIONS[r.restriction_type.trim()];
            }
        }
    }

    toJson(): string {
        return JSON.stringify(this.records, null, 2);
    }
}

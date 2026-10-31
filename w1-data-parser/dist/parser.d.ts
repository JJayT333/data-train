import { W1RecordGroup, DaRootRecord, DaPermitRecord, DaFieldRecord, DaFieldSpecificRecord, DaFieldBhlRecord, DaCanRestrRecord, DaCanRestrFieldRecord, DaFreeRestrRecord, DaFreeRestrFieldRecord, DaPermitBhlRecord, DaAlternateAddressRecord, DaRemarkRecord, DaCheckRegisterRecord, DaSurfaceLocationRecord, DaBottomHoleLocationRecord, RRCRecord } from './models.js';
export declare class W1Parser {
    records: W1RecordGroup[];
    constructor();
    parseFile(filepath: string, schemas?: (string | number)[], transformCodes?: boolean): Promise<W1RecordGroup[]>;
    iterateFile(filepath: string, schemas?: (string | number)[], transformCodes?: boolean): AsyncGenerator<W1RecordGroup>;
    _addToGroupList(group: W1RecordGroup, key: string, record: RRCRecord | null): void;
    _normalizeSchemaFilter(schemas?: (string | number)[]): Set<string> | null;
    _extractFields(line: string, fields: [string, number, number, string][]): any;
    _parseDaRoot(line: string): DaRootRecord;
    _parseDaPermit(line: string): DaPermitRecord;
    _parseDaField(line: string): DaFieldRecord;
    _parseDaFieldSpecific(line: string): DaFieldSpecificRecord;
    _parseDaFieldBhl(line: string): DaFieldBhlRecord;
    _parseDaCanRestr(line: string): DaCanRestrRecord;
    _parseDaCanRestrField(line: string): DaCanRestrFieldRecord;
    _parseDaFreeRestr(line: string): DaFreeRestrRecord;
    _parseDaFreeRestrField(line: string): DaFreeRestrFieldRecord;
    _parseDaPermitBhl(line: string): DaPermitBhlRecord;
    _parseDaAlternateAddr(line: string): DaAlternateAddressRecord;
    _parseDaRemark(line: string): DaRemarkRecord;
    _parseDaCheckRegister(line: string): DaCheckRegisterRecord;
    _parseDaSurfaceLoc(line: string): DaSurfaceLocationRecord;
    _parseDaBottomHoleLoc(line: string): DaBottomHoleLocationRecord;
    _transformGroup(group: W1RecordGroup): void;
    _applyTransformations(record: any): void;
    toJson(): string;
}


import { W1Parser } from '../parser.js';
import { DaPermitRecord } from '../models.js';

// We need to expose the private method or move logic to public for unit testing helper functions.
// In TS, we can often access private methods via (parser as any)._methodName using brackets,
// or we can test public behavior.
// test_da_permit.py tested `_parse_da_permit`.
// We will test it similarly.

describe('DaPermitParsing', () => {
    it('should parse da permit record correctly', () => {
        const line = "02091197899003SPDTX SWD                       10  17  0597590032701                              000000000000000000000000202511252025120300000000000000000000000000000000 000000002027120300000000                              NNNN00000000000000N9       A40       PSL / MILES, T J                                       782   00000000275002720W     ANDREWS      00015000FWL          00020000FSL          00035900FWL          00034700FSL          0.0                         O00000000 NNNN09748797 NN       00349279";

        const parser = new W1Parser();
        // Accessing private method for testing purposes
        const record = (parser as any)._parseDaPermit(line) as DaPermitRecord;

        expect(record.record_id).toBe("02");
        expect(record.permit_number).toBe(911978);
        expect(record.sequence_number).toBe(99);
        expect(record.county_code).toBe(3); // 003 -> 3
        expect(record.lease_name.trim()).toBe("SPDTX SWD");
        expect(record.district).toBe(10);
        expect(record.well_number.trim()).toBe("17");
        expect(record.total_depth).toBe(5975);
        expect(record.operator_number).toBe(900327);
        expect(record.type_application).toBe("01");

        // Date fields
        expect(record.received_date).toBe("20251125");
        expect(record.issued_date).toBe("20251203");

        // Flags
        expect(record.p12_filed_flag).toBe("N");

        // Location fields
        expect(record.surface_abstract.trim()).toBe("782");
        expect(record.surface_nearest_city.trim()).toBe("ANDREWS");

        // API
        expect(record.api_number).toBe("00349279");
    });
});

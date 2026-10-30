
import { W1Parser } from '../parser.js';
import { DaFieldRecord, W1RecordGroup } from '../models.js';
import * as fs from 'fs';
import * as path from 'path';

describe('DaFieldParsing', () => {
    it('should parse da field segment correctly', () => {
        const line = "0312345678OGSN1995010119950202YN".padEnd(100, ' ');

        const parser = new W1Parser();
        const record = (parser as any)._parseDaField(line) as DaFieldRecord;

        expect(record.record_id).toBe("03");
        expect(record.field_number).toBe(12345678);
        expect(record.field_application_well_code).toBe("O");
        expect(record.field_completion_well_code).toBe("G");
        expect(record.field_completion_code).toBe("S");
        expect(record.field_transfer_code).toBe("N");
        expect(record.field_validation_century).toBe(19);
        expect(record.field_validation_year).toBe(95);
        expect(record.field_validation_month).toBe(1);
        expect(record.field_validation_day).toBe(1);
        expect(record.field_completion_century).toBe(19);
        expect(record.field_completion_year).toBe(95);
        expect(record.field_completion_month).toBe(2);
        expect(record.field_completion_day).toBe(2);
        expect(record.field_rule37_flag).toBe("Y");
        expect(record.field_rule38_flag).toBe("N");
    });

    it('should integration parse file with segment 03', async () => {
        const tempFilePath = path.join(__dirname, 'test_field_integration.dat');
        const line01 = "01".padEnd(102, ' ') + "\n";
        const line02 = "02".padEnd(503, ' ') + "\n";
        const line03 = "0312345678OGSN1995010119950202YN".padEnd(82, ' ') + "\n"; // min length checks?

        fs.writeFileSync(tempFilePath, line01 + line02 + line03, { encoding: 'utf8' });

        const parser = new W1Parser();
        const records = await parser.parseFile(tempFilePath);

        fs.unlinkSync(tempFilePath);

        expect(records.length).toBe(1);
        const group = records[0];

        expect(group["01"]).toBeDefined();
        expect(group["02"]).toBeDefined();
        expect(group["03"]).toBeDefined();

        const fieldRec = group["03"] as DaFieldRecord;
        expect(fieldRec.field_number).toBe(12345678);
    });
});

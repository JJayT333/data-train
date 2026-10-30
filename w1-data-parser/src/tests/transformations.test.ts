
import { W1Parser } from '../parser.js';
import { DaRootRecord, DaPermitRecord, DaCanRestrRecord } from '../models.js';
import * as fs from 'fs';
import * as path from 'path';

describe('Transformations', () => {
    // Construct test lines
    const LINE_01_ANDERSON = "01000000000001" + " ".repeat(32) + "00000000    00000000" + " ".repeat(32) + "000N0NNNNNNNNNN00000002025010100000000N                    0000000000000000NE" + " ".repeat(500);

    let LINE_02_FULL = "02" + "0".repeat(7) + "00" + "201" + " ".repeat(32) + "00" + "000000" + "00000" + "000000"; // Ends at 65
    LINE_02_FULL += "G "; // 66-67: Type App
    LINE_02_FULL += " ".repeat(30); // 68-97
    LINE_02_FULL += "000000"; // 98-103
    LINE_02_FULL += "78701"; // 104-108
    LINE_02_FULL += "0000"; // 109-112
    LINE_02_FULL += "000000"; // 113-118
    LINE_02_FULL += "003"; // 119-121: Onshore County (ANDREWS)
    LINE_02_FULL += " ".repeat(48); // 122-169
    LINE_02_FULL += "W"; // 170: Well Status
    LINE_02_FULL = LINE_02_FULL.padEnd(524, ' ');

    let LINE_06_FULL = "0601A " + " ".repeat(35) + "N";
    LINE_06_FULL = LINE_06_FULL.padEnd(500, ' ');

    const TEST_CONTENT = LINE_01_ANDERSON + "\n" + LINE_02_FULL + "\n" + LINE_06_FULL;

    it('should not transform codes when disabled (default)', async () => {
        const tempFilePath = path.join(__dirname, 'test_transform_disabled.dat');
        fs.writeFileSync(tempFilePath, TEST_CONTENT, { encoding: 'utf8' });

        const parser = new W1Parser();
        const records = await parser.parseFile(tempFilePath, undefined, false);

        fs.unlinkSync(tempFilePath);

        expect(records.length).toBe(1);
        const group = records[0];

        // Check 01
        const root = group['01'] as DaRootRecord;
        // In TS logic, we typically keep string unless parsed to int in _extractFields.
        // county_code is extracted as number based on schema?
        // Let's check schema. src/schemas/da_root.ts. 
        // Assuming da_root schema defines it as int.
        // The test checks: assert root.county_code == 1.
        expect(Number(root.county_code)).toBe(1);

        // Check 02
        const permit = group['02'] as DaPermitRecord;
        expect(Number(permit.county_code)).toBe(201);
        expect(Number(permit.onshore_county)).toBe(3);
        expect(permit.well_status).toBe("W");
        expect(permit.type_application).toBe("G");

        // Check 06
        const restrs = group['06'] as DaCanRestrRecord[];
        expect(restrs.length).toBe(1);
        expect(restrs[0].restriction_type).toBe("A");
    });

    it('should transform codes when enabled', async () => {
        const tempFilePath = path.join(__dirname, 'test_transform_enabled.dat');
        fs.writeFileSync(tempFilePath, TEST_CONTENT, { encoding: 'utf8' });

        const parser = new W1Parser();
        const records = await parser.parseFile(tempFilePath, undefined, true);

        fs.unlinkSync(tempFilePath);

        expect(records.length).toBe(1);
        const group = records[0];

        // Check 01
        const root = group['01'] as DaRootRecord;
        expect(root.county_code).toBe("ANDERSON");

        // Check 02
        const permit = group['02'] as DaPermitRecord;
        expect(permit.county_code).toBe("HARRIS");
        expect(permit.onshore_county).toBe("ANDREWS");
        expect(permit.well_status).toBe("Final Completion");
        expect(permit.type_application).toBe("Gas");

        // Check 06
        const restrs = group['06'] as DaCanRestrRecord[];
        // The test checks "THIS WELL IS NEVER COMPLETED IN THE SAME RESERVOIR" in restriction_type
        expect(restrs[0].restriction_type).toContain("THIS WELL IS NEVER COMPLETED IN THE SAME RESERVOIR");
    });

    it('should handle unknown codes gracefully', async () => {
        const line01Unknown = LINE_01_ANDERSON.replace("001", "999");
        const tempFilePath = path.join(__dirname, 'test_transform_unknown.dat');
        fs.writeFileSync(tempFilePath, line01Unknown, { encoding: 'utf8' });

        const parser = new W1Parser();
        const records = await parser.parseFile(tempFilePath, undefined, true);

        fs.unlinkSync(tempFilePath);

        const root = records[0]['01'] as DaRootRecord;
        expect(root.county_code).toBe(999);
    });

});

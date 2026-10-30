
import { W1Parser } from '../parser.js';
import { W1RecordGroup, DaRootRecord, DaPermitRecord } from '../models.js';
import * as fs from 'fs';
import * as path from 'path';

describe('W1Parser Workflow', () => {
    const tempFilePath = path.join(__dirname, 'test_data.txt');

    afterAll(() => {
        if (fs.existsSync(tempFilePath)) {
            fs.unlinkSync(tempFilePath);
        }
    });

    it('should parse a file with Schema 01 and 02 correctly', async () => {
        const content =
            "01091197899003SPDTX SWD                       10900327    20251125WATERBRIDGE STATELINE LLC       00ANNNNNNNNNNN09119782025120300000000N                      17  N000000000000000000 E00000000000000000000000000000\n" +
            "02091197899003SPDTX SWD                       10  17  0597590032701                              000000000000000000000000202511252025120300000000000000000000000000000000 000000002027120300000000                              NNNN00000000000000N9       A40       PSL / MILES, T J                                       782   00000000275002720W     ANDREWS      00015000FWL          00020000FSL          00035900FWL          00034700FSL          0.0                         O00000000 NNNN09748797 NN       00349279";

        fs.writeFileSync(tempFilePath, content, { encoding: 'utf8' });

        const parser = new W1Parser();
        const records = await parser.parseFile(tempFilePath);

        // Verify return type
        expect(Array.isArray(records)).toBe(true);
        expect(records.length).toBe(1);

        // Verify grouping type
        const item = records[0];
        expect(item).toBeInstanceOf(W1RecordGroup);

        expect(item["01"]).toBeDefined();
        expect(item["02"]).toBeDefined();

        // Verify content types
        // In TS, we check if they look like the expected objects. Detailed checks in separate tests.
        // We can cast them to verify fields.
        const rootRecord = item["01"] as DaRootRecord;
        const permitRecord = item["02"] as DaPermitRecord;

        // Verify we can access fields
        // Note: In TS implementation, we might not have auto-conversion to numbers for all fields 
        // unless _extractFields handles it. Let's check src/parser.ts again.
        // _extractFields uses parseInt if type is 'int'.
        expect(rootRecord.status_number).toBe(911978);
        expect(permitRecord.api_number).toBe("00349279");

        // Verify object-level serialization
        // toJSON returns a plain object, so JSON.stringify consumes it.

        const itemJson = JSON.stringify(item);
        expect(typeof itemJson).toBe('string');
        const itemDict = JSON.parse(itemJson);
        expect(itemDict["01"]).toBeDefined();
        expect(itemDict["02"]["api_number"]).toBe("00349279");

        // Verify Parser level toJson
        const parserJson = parser.toJson();
        const data = JSON.parse(parserJson);
        expect(data.length).toBe(1);
        expect(data[0]["01"]["lease_name"].trim()).toBe("SPDTX SWD");
    });
});

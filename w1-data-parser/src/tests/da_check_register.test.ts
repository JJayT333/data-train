
import { W1Parser } from '../parser.js';
import { DaCheckRegisterRecord } from '../models.js';
import * as fs from 'fs';
import * as path from 'path';

describe('DaCheckRegisterParsing', () => {
    it('should parse segment 13 from sample correctly', async () => {
        // Construct sample lines
        // Rec ID: 13 (1-2)
        // Date: 20251210 (3-10)
        // Register Number: 12345678 (11-18)
        let line_1 = "13" + "20251210" + "12345678";
        line_1 = line_1.padEnd(100, ' ') + "\n"; // Pad

        let line_2 = "13" + "20251211" + "87654321";
        line_2 = line_2.padEnd(100, ' ') + "\n";

        const content =
            "01091198799103MCKNIGHT SAND HILLS UNIT        10073056    20251125BLACKBEARD OPERATING, LLC       00ANNNNNNNNNNN09119872025120400000000N                    7305H N000000000000000000 X00000000000000000000000000000\n"
            + line_1
            + line_2;

        const tempFilePath = path.join(__dirname, 'test_13.txt');
        fs.writeFileSync(tempFilePath, content, { encoding: 'utf8' });

        const parser = new W1Parser();
        const records = await parser.parseFile(tempFilePath);

        fs.unlinkSync(tempFilePath);

        expect(records.length).toBe(1);
        const group = records[0];

        expect(group["13"]).toBeDefined();
        const seg13List = group["13"] as DaCheckRegisterRecord[];

        expect(Array.isArray(seg13List)).toBe(true);
        expect(seg13List.length).toBe(2);

        const rec1 = seg13List[0];
        expect(rec1.register_date_year).toBe(25);
        expect(rec1.register_number).toBe(12345678);

        const rec2 = seg13List[1];
        expect(rec2.register_number).toBe(87654321);
    });
});

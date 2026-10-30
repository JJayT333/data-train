
import { W1Parser } from '../parser.js';
import { DaRemarkRecord } from '../models.js';
import * as fs from 'fs';
import * as path from 'path';

describe('DaRemarkParsing', () => {
    it('should parse segment 12 from sample correctly', async () => {
        // Construct sample lines
        // Rec ID: 12 (1-2)
        // Seq Num: 001 (3-5)
        // Date: 20251210 (6-13)
        let line_1 = "12" + "001" + "20251210" + "This is a test remark line 1.";
        line_1 = line_1.padEnd(150, ' ') + "\n";

        let line_2 = "12" + "002" + "20251211" + "This is a test remark line 2.";
        line_2 = line_2.padEnd(150, ' ') + "\n";

        const content =
            "01091198799103MCKNIGHT SAND HILLS UNIT        10073056    20251125BLACKBEARD OPERATING, LLC       00ANNNNNNNNNNN09119872025120400000000N                    7305H N000000000000000000 X00000000000000000000000000000\n"
            + line_1
            + line_2;

        const tempFilePath = path.join(__dirname, 'test_12.txt');
        fs.writeFileSync(tempFilePath, content, { encoding: 'utf8' });

        const parser = new W1Parser();
        const records = await parser.parseFile(tempFilePath);

        fs.unlinkSync(tempFilePath);

        expect(records.length).toBe(1);
        const group = records[0];

        expect(group["12"]).toBeDefined();
        const seg12List = group["12"] as DaRemarkRecord[];

        expect(Array.isArray(seg12List)).toBe(true);
        expect(seg12List.length).toBe(2);

        const rec1 = seg12List[0];
        expect(rec1.remark_sequence_number).toBe(1);
        expect(rec1.remark_date_year).toBe(25);
        expect(rec1.remark_line.trim()).toBe("This is a test remark line 1.");

        const rec2 = seg12List[1];
        expect(rec2.remark_sequence_number).toBe(2);
        expect(rec2.remark_line.trim()).toBe("This is a test remark line 2.");
    });
});

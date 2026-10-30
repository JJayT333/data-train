
import { W1Parser } from '../parser.js';
import { DaFreeRestrRecord } from '../models.js';
import * as fs from 'fs';
import * as path from 'path';

describe('DaFreeRestrParsing', () => {
    it('should parse segment 08 from sample correctly', async () => {
        const content =
            "01091198799103MCKNIGHT SAND HILLS UNIT        10073056    20251125BLACKBEARD OPERATING, LLC       00ANNNNNNNNNNN09119872025120400000000N                    7305H N000000000000000000 X00000000000000000000000000000\n" +
            "080129THIS WELL MUST COMPLY TO THE NEW SWR 3.13 REQUIREMENTS CONCERNING THE P0000000000\n" +
            "080229ISOLATION OF ANY POTENTIAL FLOW ZONES AND ZONES WITH CORROSIVE FORMATIP0000000000\n";

        const tempFilePath = path.join(__dirname, 'test_08.txt');
        fs.writeFileSync(tempFilePath, content, { encoding: 'utf8' });

        const parser = new W1Parser();
        const records = await parser.parseFile(tempFilePath);

        fs.unlinkSync(tempFilePath);

        expect(records.length).toBe(1);
        const group = records[0];

        expect(group["08"]).toBeDefined();
        const seg08List = group["08"] as DaFreeRestrRecord[];

        expect(Array.isArray(seg08List)).toBe(true);
        expect(seg08List.length).toBe(2);

        const rec1 = seg08List[0];
        expect(rec1.restriction_key).toBe(1);
        expect(rec1.restriction_type).toBe("29");
        expect(rec1.restriction_remark.trim()).toBe("THIS WELL MUST COMPLY TO THE NEW SWR 3.13 REQUIREMENTS CONCERNING THE");
        expect(rec1.restriction_flag).toBe("P");

        const rec2 = seg08List[1];
        expect(rec2.restriction_key).toBe(2);
        expect(rec2.restriction_type).toBe("29");
        expect(rec2.restriction_remark.trim()).toBe("ISOLATION OF ANY POTENTIAL FLOW ZONES AND ZONES WITH CORROSIVE FORMATI");
        expect(rec2.restriction_flag).toBe("P");
    });
});

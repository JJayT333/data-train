
import { W1Parser } from '../parser.js';
import { DaCanRestrFieldRecord } from '../models.js';
import * as fs from 'fs';
import * as path from 'path';

describe('DaCanRestrFieldParsing', () => {
    it('should parse segment 07 from sample correctly', async () => {
        const content =
            "01091198799103MCKNIGHT SAND HILLS UNIT        10073056    20251125BLACKBEARD OPERATING, LLC       00ANNNNNNNNNNN09119872025120400000000N                    7305H N000000000000000000 X00000000000000000000000000000\n" +
            "060201                                   P0000000000\n" +
            "076999620000000\n" +
            "071234567800000\n" +
            "060306                                   F0000000000\n";

        const tempFilePath = path.join(__dirname, 'test_07.txt');
        fs.writeFileSync(tempFilePath, content, { encoding: 'utf8' });

        const parser = new W1Parser();
        const records = await parser.parseFile(tempFilePath);

        fs.unlinkSync(tempFilePath);

        expect(records.length).toBe(1);
        const group = records[0];

        expect(group["07"]).toBeDefined();
        const seg07List = group["07"] as DaCanRestrFieldRecord[];

        expect(Array.isArray(seg07List)).toBe(true);
        expect(seg07List.length).toBe(2);

        const rec1 = seg07List[0];
        expect(rec1.field_number).toBe("69996200");

        const rec2 = seg07List[1];
        expect(rec2.field_number).toBe("12345678");
    });
});

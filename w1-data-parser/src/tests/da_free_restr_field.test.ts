
import { W1Parser } from '../parser.js';
import { DaFreeRestrFieldRecord } from '../models.js';
import * as fs from 'fs';
import * as path from 'path';

describe('DaFreeRestrFieldParsing', () => {
    it('should parse segment 09 from sample correctly', async () => {
        const content =
            "01091198799103MCKNIGHT SAND HILLS UNIT        10073056    20251125BLACKBEARD OPERATING, LLC       00ANNNNNNNNNNN09119872025120400000000N                    7305H N000000000000000000 X00000000000000000000000000000\n" +
            "091234567800000\n" +
            "098765432100000\n";

        const tempFilePath = path.join(__dirname, 'test_09.txt');
        fs.writeFileSync(tempFilePath, content, { encoding: 'utf8' });

        const parser = new W1Parser();
        const records = await parser.parseFile(tempFilePath);

        fs.unlinkSync(tempFilePath);

        expect(records.length).toBe(1);
        const group = records[0];

        expect(group["09"]).toBeDefined();
        const seg09List = group["09"] as DaFreeRestrFieldRecord[];

        expect(Array.isArray(seg09List)).toBe(true);
        expect(seg09List.length).toBe(2);

        const rec1 = seg09List[0];
        expect(rec1.field_number).toBe("12345678");

        const rec2 = seg09List[1];
        expect(rec2.field_number).toBe("87654321");
    });
});

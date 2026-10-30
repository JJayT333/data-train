
import { W1Parser } from '../parser.js';
import { DaBottomHoleLocationRecord } from '../models.js';
import * as fs from 'fs';
import * as path from 'path';

describe('DaBottomHoleLocationParsing', () => {
    it('should parse segment 15 from sample correctly', async () => {
        let line_1 = "15" + "001234567890" + "009876543210";
        line_1 = line_1.padEnd(100, ' ') + "\n";

        let line_2 = "15" + "002234567890" + "008876543210";
        line_2 = line_2.padEnd(100, ' ') + "\n";

        const content =
            "01091198799103MCKNIGHT SAND HILLS UNIT        10073056    20251125BLACKBEARD OPERATING, LLC       00ANNNNNNNNNNN09119872025120400000000N                    7305H N000000000000000000 X00000000000000000000000000000\n"
            + line_1
            + line_2;

        const tempFilePath = path.join(__dirname, 'test_15.txt');
        fs.writeFileSync(tempFilePath, content, { encoding: 'utf8' });

        const parser = new W1Parser();
        const records = await parser.parseFile(tempFilePath);

        fs.unlinkSync(tempFilePath);

        expect(records.length).toBe(1);
        const group = records[0];

        expect(group["15"]).toBeDefined();
        const seg15List = group["15"] as DaBottomHoleLocationRecord[];

        expect(Array.isArray(seg15List)).toBe(true);
        expect(seg15List.length).toBe(2);

        const rec1 = seg15List[0];
        expect(rec1.longitude).toBe("001234567890");
        expect(rec1.latitude).toBe("009876543210");

        const rec2 = seg15List[1];
        expect(rec2.longitude).toBe("002234567890");
        expect(rec2.latitude).toBe("008876543210");
    });
});

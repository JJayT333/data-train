
import { W1Parser } from '../parser.js';
import { DaSurfaceLocationRecord } from '../models.js';
import * as fs from 'fs';
import * as path from 'path';

describe('DaSurfaceLocationParsing', () => {
    it('should parse segment 14 from sample correctly', async () => {
        // Construct sample
        let line_1 = "14" + "001234567890" + "009876543210"; // Long, Lat
        line_1 = line_1.padEnd(100, ' ') + "\n";

        const content =
            "01091198799103MCKNIGHT SAND HILLS UNIT        10073056    20251125BLACKBEARD OPERATING, LLC       00ANNNNNNNNNNN09119872025120400000000N                    7305H N000000000000000000 X00000000000000000000000000000\n"
            + line_1;

        const tempFilePath = path.join(__dirname, 'test_14.txt');
        fs.writeFileSync(tempFilePath, content, { encoding: 'utf8' });

        const parser = new W1Parser();
        const records = await parser.parseFile(tempFilePath);

        fs.unlinkSync(tempFilePath);

        expect(records.length).toBe(1);
        const group = records[0];

        expect(group["14"]).toBeDefined();

        const seg14 = group["14"] as DaSurfaceLocationRecord;
        expect(seg14.longitude).toBe("001234567890");
        expect(seg14.latitude).toBe("009876543210");
    });
});

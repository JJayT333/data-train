
import { W1Parser } from '../parser.js';
import { DaPermitBhlRecord } from '../models.js';
import * as fs from 'fs';
import * as path from 'path';

describe('DaPermitBhlParsing', () => {
    it('should parse segment 10 from sample correctly', async () => {
        let line_10 = "10"
            + "SECTION1" // 3-10
            + "BLOCK12345" // 11-20
            + "ABSTR1" // 21-26
            + "SURVEY NAME IS HERE                                    " // 27-81
            + "06400000"  // 82-89 Acres
            + "NEAREST WELL INFO           " // 90-117
            + "00100000"  // 118-125
            + "NORTH        " // 126-138
            + "00200000"  // 139-146
            + "EAST         " // 147-159
            + "00300000"  // 160-167
            + "SOUTH        " // 168-180
            + "00400000"  // 181-188
            + "WEST         " // 189-201
            + "LOVING       "; // 202-214

        line_10 = line_10.padEnd(553, ' ') + "\n";

        const content =
            "01091198799103MCKNIGHT SAND HILLS UNIT        10073056    20251125BLACKBEARD OPERATING, LLC       00ANNNNNNNNNNN09119872025120400000000N                    7305H N000000000000000000 X00000000000000000000000000000\n"
            + line_10;

        const tempFilePath = path.join(__dirname, 'test_10.txt');
        fs.writeFileSync(tempFilePath, content, { encoding: 'utf8' });

        const parser = new W1Parser();
        const records = await parser.parseFile(tempFilePath);

        fs.unlinkSync(tempFilePath);

        expect(records.length).toBe(1);
        const group = records[0];

        expect(group["10"]).toBeDefined();
        const rec = group["10"] as DaPermitBhlRecord;

        expect(rec.bhl_section).toBe("SECTION1");
        expect(rec.bhl_block).toBe("BLOCK12345");
        expect(rec.bhl_abstract).toBe("ABSTR1");
        expect(rec.bhl_survey.trim()).toBe("SURVEY NAME IS HERE");
        expect(rec.bhl_acres).toBe("06400000");
        expect(rec.bhl_nearest_well.trim()).toBe("NEAREST WELL INFO");
        expect(rec.bhl_lease_feet_1).toBe("00100000");
        expect(rec.bhl_lease_direction_1.trim()).toBe("NORTH");
        expect(rec.bhl_county.trim()).toBe("LOVING");
    });
});

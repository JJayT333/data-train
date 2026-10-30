
import { W1Parser } from '../parser.js';
import { DaFieldBhlRecord } from '../models.js';
import * as fs from 'fs';
import * as path from 'path';

describe('DaFieldBhlParsing', () => {
    it('should parse segment 05 from sample correctly', async () => {
        const full_content =
            "01091198299103MCKNIGHT SAND HILLS UNIT        10073056    20251125BLACKBEARD OPERATING, LLC       00ANNNNNNNNNNN09119822025120400000000N                    7105H N000000000000000000 X00000000000000000000000000000\n" +
            "0510      B21       1114  PSL/ MC KNIGHT, M B                                    001150000.0                         00000500S            00345100W            00000500S            00181400E            CRANE        00041000S            00175800E            000000\n";

        const tempFilePath = path.join(__dirname, 'test_05.txt');
        fs.writeFileSync(tempFilePath, full_content, { encoding: 'utf8' });

        const parser = new W1Parser();
        const records = await parser.parseFile(tempFilePath);

        fs.unlinkSync(tempFilePath);

        expect(records.length).toBe(1);
        const group = records[0];

        expect(group["05"]).toBeDefined();
        const seg05 = group["05"] as DaFieldBhlRecord;

        expect(seg05.bhl_section.trim()).toBe("10");
        expect(seg05.bhl_block.trim()).toBe("B21");
        expect(seg05.bhl_abstract.trim()).toBe("1114");
        expect(seg05.bhl_survey.trim()).toBe("PSL/ MC KNIGHT, M B");
        expect(seg05.bhl_acres).toBe("00115000");
        expect(seg05.bhl_nearest_well.trim()).toBe("0.0");
        expect(seg05.bhl_county.trim()).toBe("CRANE");
    });
});


import { W1Parser } from '../parser.js';
import { DaCanRestrRecord } from '../models.js';
import * as fs from 'fs';
import * as path from 'path';

describe('DaCanRestrParsing', () => {
    it('should parse segment 06 from sample correctly', async () => {
        const content =
            "01091198799103MCKNIGHT SAND HILLS UNIT        10073056    20251125BLACKBEARD OPERATING, LLC       00ANNNNNNNNNNN09119872025120400000000N                    7305H N000000000000000000 X00000000000000000000000000000\n" +
            "0510      B21       1114  PSL/ MC KNIGHT, M B                                    001150000.0                         00000500S            00312300W            00000500S            00214200E            CRANE        00049400S            00200600E            000000\n" +
            "060201                                   P0000000000\n" +
            "060306                                   F0000000000\n" +
            "078047331000000\n" +
            "060402                                   F0000000000\n";

        const tempFilePath = path.join(__dirname, 'test_06.txt');
        fs.writeFileSync(tempFilePath, content, { encoding: 'utf8' });

        const parser = new W1Parser();
        const records = await parser.parseFile(tempFilePath);

        fs.unlinkSync(tempFilePath);

        expect(records.length).toBe(1);
        const group = records[0];

        expect(group["06"]).toBeDefined();
        const seg06List = group["06"] as DaCanRestrRecord[];

        expect(Array.isArray(seg06List)).toBe(true);
        expect(seg06List.length).toBe(3);

        const rec1 = seg06List[0];
        expect(rec1.restriction_key).toBe(2);
        expect(rec1.restriction_type).toBe("01");
        expect(rec1.restriction_flag).toBe("P");

        const rec2 = seg06List[1];
        expect(rec2.restriction_key).toBe(3);
        expect(rec2.restriction_type).toBe("06");
        expect(rec2.restriction_flag).toBe("F");

        const rec3 = seg06List[2];
        expect(rec3.restriction_key).toBe(4);
        expect(rec3.restriction_type).toBe("02");
        expect(rec3.restriction_flag).toBe("F");
    });
});

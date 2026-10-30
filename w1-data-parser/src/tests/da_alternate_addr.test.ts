
import { W1Parser } from '../parser.js';
import { DaAlternateAddressRecord } from '../models.js';
import * as fs from 'fs';
import * as path from 'path';

describe('DaAlternateAddressParsing', () => {
    it('should parse segment 11 from sample correctly', async () => {
        let line_1 = "11AB1234 MAIN STREET                  ";
        line_1 = line_1.padEnd(100, ' ') + "\n";

        let line_2 = "11ACPO BOX 567                        ";
        line_2 = line_2.padEnd(100, ' ') + "\n";

        const content =
            "01091198799103MCKNIGHT SAND HILLS UNIT        10073056    20251125BLACKBEARD OPERATING, LLC       00ANNNNNNNNNNN09119872025120400000000N                    7305H N000000000000000000 X00000000000000000000000000000\n"
            + line_1
            + line_2;

        const tempFilePath = path.join(__dirname, 'test_11.txt');
        fs.writeFileSync(tempFilePath, content, { encoding: 'utf8' });

        const parser = new W1Parser();
        const records = await parser.parseFile(tempFilePath);

        fs.unlinkSync(tempFilePath);

        expect(records.length).toBe(1);
        const group = records[0];

        expect(group["11"]).toBeDefined();
        const seg11List = group["11"] as DaAlternateAddressRecord[];

        expect(Array.isArray(seg11List)).toBe(true);
        expect(seg11List.length).toBe(2);

        const rec1 = seg11List[0];
        expect(rec1.address_key).toBe("AB");
        expect(rec1.address_line.trim()).toBe("1234 MAIN STREET");

        const rec2 = seg11List[1];
        expect(rec2.address_key).toBe("AC");
        expect(rec2.address_line.trim()).toBe("PO BOX 567");
    });
});

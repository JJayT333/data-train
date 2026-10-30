
import { W1Parser } from '../parser.js';
import { DaFieldSpecificRecord } from '../models.js';
import * as fs from 'fs';
import * as path from 'path';

describe('DaFieldSpecificParsing', () => {

    it('should parse segment 04 from sample correctly', async () => {
        const sampleContent =
            "01091197999003SPDTX SWD                       10900327    20251125WATERBRIDGE STATELINE LLC       00ANNNNNNNNNNN09119792025120300000000N                      18  N000000000000000000 E00000000000000000000000000000\n" +
            "02091197999003SPDTX SWD                       10  18  0702590032701                              000000000000000000000000202511252025120300000000000000000000000000000000 000000002027120300000000                              NNNN00000000000000N10      A40       PSL / MILES, T J                                       781   00000000275002620W     ANDREWS      00015000FWL          00020000FSL          00033400FWL          00049400FSL          0.0                         O00000000 NNNN09748797 NN       00349280\n" +
            "0364890250I  N0000000000000000NN000000000000000000\n" +
            "0410SPDTX SWD                       04260  18  0000027500000000000000000\n" +
            "060201                                   P0000000000\n" +
            "060303                                   F0000000000\n" +
            "076489025000000\n" +
            "080129THIS WELL MUST COMPLY TO THE NEW SWR 3.13 REQUIREMENTS CONCERNING THE P0000000000\n" +
            "080229ISOLATION OF ANY POTENTIAL FLOW ZONES AND ZONES WITH CORROSIVE FORMATIP0000000000\n" +
            "080329ON FLUIDS.  SEE APPROVED PERMIT FOR THOSE FORMATIONS THAT HAVE BEEN IDP0000000000\n" +
            "080429ENTIFIED FOR THE COUNTY IN WHICH YOU ARE DRILLING THE WELL IN.        P0000000000\n" +
            "14-102.9952684  32.3359810\n" +
            "15-102.9952684  32.3359810\n" +
            "01091178998003SPDTX SWD                       10900327    20251202WATERBRIDGE STATELINE LLC       00ANNNNNNNNNNN09117892025111800000000N                      22  N000000000000000000 E00000000000000000000000000000\n" +
            "02091178998003SPDTX SWD                       10  22  0700090032701                              000000000000000000000000202512022025111820251205000000000000000000000000 000000002027111800000000                              NNNN00000000000000N17      A40       PSL / COX, B F                                         715   00000000275002920W     ANDREWS      00020000S            00015000E            00038000N            00043400W            0.0                         O00000000 NNNN09748882 NN       00349271\n" +
            "0364890250I  N0000000000000000NN000000000000000000\n" +
            "0410SPDTX SWD                       04255  22  0000027500000000000000000\n" +
            "060201                                   P0000000000\n" +
            "060303                                   F0000000000\n" +
            "076489025000000\n" +
            "080129THIS WELL MUST COMPLY TO THE NEW SWR 3.13 REQUIREMENTS CONCERNING THE P0000000000\n" +
            "080229ISOLATION OF ANY POTENTIAL FLOW ZONES AND ZONES WITH CORROSIVE FORMATIP0000000000\n" +
            "080329ON FLUIDS.  SEE APPROVED PERMIT FOR THOSE FORMATIONS THAT HAVE BEEN IDP0000000000\n" +
            "080429ENTIFIED FOR THE COUNTY IN WHICH YOU ARE DRILLING THE WELL IN.        P0000000000\n" +
            "14-103.0462655  32.3188856\n" +
            "15-103.0462655  32.3188856\n" +
            "01091180398003SPDTX SWD                       10900327    20251202WATERBRIDGE STATELINE LLC       00ANNNNNNNNNNN09118032025111800000000N                      26  N000000000000000000 E00000000000000000000000000000\n" +
            "02091180398003SPDTX SWD                       10  26  0700090032701                              000000000000000000000000202512022025111820251205000000000000000000000000 000000002027111800000000                              NNNN00000000000000N16      A40       PSL / FRANCIS, A C                                     732   00000000275003020W     ANDREWS      00015000W            00020000S            00023000W            00095700S            0.0                         O00000000 NNNN09748882 NN       00349272\n" +
            "0364890250I  N0000000000000000NN000000000000000000\n" +
            "0410SPDTX SWD                       04255  26  0000027500000000000000000\n" +
            "060201                                   P0000000000\n" +
            "060303                                   F0000000000\n" +
            "076489025000000\n" +
            "080129THIS WELL MUST COMPLY TO THE NEW SWR 3.13 REQUIREMENTS CONCERNING THE P0000000000\n" +
            "080229ISOLATION OF ANY POTENTIAL FLOW ZONES AND ZONES WITH CORROSIVE FORMATIP0000000000\n" +
            "080329ON FLUIDS.  SEE APPROVED PERMIT FOR THOSE FORMATIONS THAT HAVE BEEN IDP0000000000\n" +
            "080429ENTIFIED FOR THE COUNTY IN WHICH YOU ARE DRILLING THE WELL IN.        P0000000000\n" +
            "14-103.0634775  32.3079997\n" +
            "15-103.0634775  32.3079997\n"

        const tempFilePath = path.join(__dirname, 'test_04_full.txt');
        fs.writeFileSync(tempFilePath, sampleContent, { encoding: 'utf8' });

        const parser = new W1Parser();
        const records = await parser.parseFile(tempFilePath);

        fs.unlinkSync(tempFilePath);

        expect(records.length).toBe(3);

        const rec0 = records[0]["04"] as DaFieldSpecificRecord;
        expect(rec0.field_well_number.trim()).toBe("18");
        expect(rec0.field_total_depth).toBe(4260);
        expect(rec0.field_acres).toBe("00000275");

        const rec1 = records[1]["04"] as DaFieldSpecificRecord;
        expect(rec1.field_well_number.trim()).toBe("22");
        expect(rec1.field_total_depth).toBe(4255);
        expect(rec1.field_acres).toBe("00000275");

        const rec2 = records[2]["04"] as DaFieldSpecificRecord;
        expect(rec2.field_well_number.trim()).toBe("26");
        expect(rec2.field_total_depth).toBe(4255);
        expect(rec2.field_acres).toBe("00000275");
    });

});

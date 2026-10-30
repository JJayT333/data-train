
import { W1Parser } from '../index.js';
import * as path from 'path';
import * as fs from 'fs';

describe('Verification Script Port', () => {
    it('should parse the sample file if it exists', async () => {
        const parser = new W1Parser();
        // Resolve path relative to the root of the project
        const samplePath = path.resolve(process.cwd(), 'w1_py_parse/.sample');

        if (fs.existsSync(samplePath)) {
            console.log(`Parsing sample file: ${samplePath}`);
            const records = await parser.parseFile(samplePath, undefined, true);
            console.log(`Successfully parsed ${records.length} records.`);

            expect(records.length).toBeGreaterThan(0);

            if (records.length > 0) {
                const firstRecord = records[0];
                expect(firstRecord["01"]).toBeDefined();
                // console.log('First record sample (Root Segment):', JSON.stringify(firstRecord["01"], null, 2));
            }
        } else {
            console.warn(`Sample file not found at: ${samplePath}. Skipping verification test.`);
        }
    });
});

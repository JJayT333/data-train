
import { W1RecordGroup } from '../models.js';

describe('W1RecordGroup Serialization', () => {
    test('toObject should return a plain object', () => {
        const group = new W1RecordGroup();
        group['01'] = { test: 'data' };

        const plain = group.toObject();

        // It should match the data
        expect(plain['01']).toEqual({ test: 'data' });

        // It should NOT be an instance of W1RecordGroup
        expect(plain).not.toBeInstanceOf(W1RecordGroup);
        // It should be a plain object
        expect(Object.getPrototypeOf(plain)).toEqual(Object.prototype);
    });

    test('JSON.stringify should leverage toJSON', () => {
        const group = new W1RecordGroup();
        group['02'] = { permit: 12345 };

        const jsonString = JSON.stringify(group);
        const parsed = JSON.parse(jsonString);

        expect(parsed).toEqual({ '02': { permit: 12345 } });
    });
});
